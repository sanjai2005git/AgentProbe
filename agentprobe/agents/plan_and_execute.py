"""
Plan-and-Execute Agent with Runtime Reflection and Dynamic Re-planning.
"""

from typing import List, Dict, Any, Optional
import time
from agentprobe.agents.base import Trajectory, StepRecord
from agentprobe.llm.base import BaseLLMProvider
from agentprobe.tools.registry import ToolRegistry
from agentprobe.domain.database import PaymentDatabase
from agentprobe.config import settings


PLANNER_PROMPT = """You are a senior payment operations planner.
Generate a concise structured step-by-step investigation plan for this incident.
List of standard phases:
1. Query transaction database
2. Fetch ML risk score
3. Analyze risk and policy limits
4. Execute remediation or escalate to human supervisor
"""


class PlanAndExecuteAgent:
    """Two-stage architecture that plans upfront, executes steps, and reflects before proceeding."""

    def __init__(self, llm: BaseLLMProvider, tools: ToolRegistry, max_steps: Optional[int] = None):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps or settings.policies.max_agent_steps

    def run(self, task_prompt: str, db: PaymentDatabase, scenario_id: Optional[str] = None) -> Trajectory:
        trajectory = Trajectory(
            scenario_id=scenario_id,
            architecture="plan_and_execute",
            model_name=self.llm.model_name,
        )

        # Stage 1: Generate Plan
        plan_start = time.perf_counter()
        plan_messages = [
            {"role": "system", "content": PLANNER_PROMPT},
            {"role": "user", "content": f"Create plan for: {task_prompt}"},
        ]
        plan_resp = self.llm.generate(messages=plan_messages)
        plan_text = plan_resp.content or "1. Query database\n2. Fetch risk score\n3. Execute resolution"

        plan_step = StepRecord(
            step_index=1,
            phase="plan",
            thought=f"Generated structured plan:\n{plan_text}",
            reflection="Plan approved. Commencing execution phase.",
            latency_ms=(time.perf_counter() - plan_start) * 1000.0,
            input_tokens=plan_resp.input_tokens,
            output_tokens=plan_resp.output_tokens,
        )
        trajectory.steps.append(plan_step)

        # Stage 2 & 3: Execute and Reflect Loop
        context_messages: List[Dict[str, Any]] = [
            {"role": "system", "content": f"Operational Plan:\n{plan_text}\nFollow this plan to investigate the payment."},
            {"role": "user", "content": task_prompt},
        ]

        step_idx = 1
        while step_idx < self.max_steps:
            step_idx += 1
            step_start = time.perf_counter()

            # Executor step
            exec_resp = self.llm.generate(messages=context_messages, tools=self.tools.get_schemas())

            if not exec_resp.has_tool_calls:
                # Finished execution
                final_step = StepRecord(
                    step_index=step_idx,
                    phase="reflect_finish",
                    thought=exec_resp.thought,
                    reflection=exec_resp.content,
                    latency_ms=(time.perf_counter() - step_start) * 1000.0,
                    input_tokens=exec_resp.input_tokens,
                    output_tokens=exec_resp.output_tokens,
                )
                trajectory.steps.append(final_step)
                trajectory.finalize(reason="COMPLETED", final_output=exec_resp.content)
                return trajectory

            # Act
            tool_call = exec_resp.tool_calls[0]
            tool_result = self.tools.execute(tool_call, db)

            if not tool_result.success and "PolicyViolation" in (tool_result.error or ""):
                trajectory.policy_violations.append(tool_result.error or "PolicyViolation")

            # Reflection Phase: Analyze observation against plan
            obs_str = tool_result.to_observation_string()
            reflection = (
                f"Evaluation: Step executed {tool_call.name}. Success: {tool_result.success}. "
                f"Next step will adapt to this result."
            )

            context_messages.append({"role": "assistant", "content": exec_resp.thought or f"Calling {tool_call.name}"})
            context_messages.append({"role": "tool", "name": tool_call.name, "content": obs_str})

            step_record = StepRecord(
                step_index=step_idx,
                phase="act_reflect",
                thought=exec_resp.thought,
                tool_call=tool_call,
                tool_result=tool_result,
                reflection=reflection,
                latency_ms=(time.perf_counter() - step_start) * 1000.0,
                input_tokens=exec_resp.input_tokens,
                output_tokens=exec_resp.output_tokens,
            )
            trajectory.steps.append(step_record)

            # Infinite loop check
            if trajectory.has_detected_loop():
                trajectory.finalize(
                    reason="LOOP_DETECTED",
                    error="Plan-and-Execute reflector aborted: repeating identical action cycle.",
                )
                return trajectory

        trajectory.finalize(
            reason="MAX_STEPS_EXCEEDED",
            error=f"Plan-and-Execute reached step limit ({self.max_steps}).",
        )
        return trajectory

