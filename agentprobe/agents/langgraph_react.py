"""
LangGraph ReAct Agent Implementation using StateGraph.
"""

from typing import List, Dict, Any, Optional, TypedDict, Annotated
import operator
import time
from langgraph.graph import StateGraph, END
from agentprobe.agents.base import Trajectory, StepRecord
from agentprobe.llm.base import BaseLLMProvider
from agentprobe.tools.registry import ToolRegistry
from agentprobe.domain.database import PaymentDatabase
from agentprobe.config import settings
from agentprobe.agents.barebones_react import SYSTEM_PROMPT


class AgentGraphState(TypedDict):
    messages: Annotated[List[Dict[str, Any]], operator.add]
    steps: List[StepRecord]
    current_thought: Optional[str]
    current_tool_call: Optional[Any]
    current_tool_result: Optional[Any]
    status: str
    error: Optional[str]
    final_output: Optional[str]
    step_count: int
    db: Any
    tools: Any
    llm: Any
    policy_violations: List[str]


def reasoner_node(state: AgentGraphState) -> Dict[str, Any]:
    """Node that generates reasoning thoughts and chooses tool calls."""
    start_time = time.perf_counter()
    llm = state["llm"]
    tools = state["tools"]
    messages = state["messages"]

    llm_resp = llm.generate(messages=messages, tools=tools.get_schemas())
    latency = (time.perf_counter() - start_time) * 1000.0

    if not llm_resp.has_tool_calls:
        # Agent finished
        step = StepRecord(
            step_index=state["step_count"] + 1,
            phase="plan_finish",
            thought=llm_resp.thought,
            reflection=llm_resp.content,
            latency_ms=latency,
            input_tokens=llm_resp.input_tokens,
            output_tokens=llm_resp.output_tokens,
        )
        return {
            "status": "COMPLETED",
            "final_output": llm_resp.content,
            "current_tool_call": None,
            "steps": state["steps"] + [step],
            "step_count": state["step_count"] + 1,
        }

    tool_call = llm_resp.tool_calls[0]
    return {
        "status": "ACTING",
        "current_thought": llm_resp.thought,
        "current_tool_call": tool_call,
        "step_count": state["step_count"] + 1,
    }


def tool_executor_node(state: AgentGraphState) -> Dict[str, Any]:
    """Node executing selected tool against the database and capturing observation."""
    start_time = time.perf_counter()
    tools: ToolRegistry = state["tools"]
    db: PaymentDatabase = state["db"]
    tool_call = state["current_tool_call"]

    tool_result = tools.execute(tool_call, db)
    latency = (time.perf_counter() - start_time) * 1000.0

    violations = list(state.get("policy_violations", []))
    if not tool_result.success and "PolicyViolation" in (tool_result.error or ""):
        violations.append(tool_result.error or "PolicyViolation")

    obs_str = tool_result.to_observation_string()
    new_messages = [
        {"role": "assistant", "content": state.get("current_thought") or f"Calling {tool_call.name}"},
        {"role": "tool", "name": tool_call.name, "content": obs_str},
    ]

    step = StepRecord(
        step_index=state["step_count"],
        phase="act_observe",
        thought=state.get("current_thought"),
        tool_call=tool_call,
        tool_result=tool_result,
        reflection=f"Observation: {obs_str[:120]}...",
        latency_ms=latency,
        input_tokens=150,
        output_tokens=60,
    )

    return {
        "messages": new_messages,
        "current_tool_result": tool_result,
        "steps": state["steps"] + [step],
        "policy_violations": violations,
    }


def reflector_node(state: AgentGraphState) -> Dict[str, Any]:
    """Node that reflects on execution history, checks limits, and detects infinite loops."""
    steps = state["steps"]
    tool_calls = [s.tool_call for s in steps if s.tool_call]

    # Check loop detection
    if len(tool_calls) >= 2:
        last = tool_calls[-1]
        prev = tool_calls[-2]
        if last.name == prev.name and last.arguments == prev.arguments:
            return {
                "status": "LOOP_DETECTED",
                "error": "LangGraph cycle detector triggered: consecutive duplicate action.",
            }

    # Check max steps limit
    if state["step_count"] >= settings.policies.max_agent_steps:
        return {
            "status": "MAX_STEPS_EXCEEDED",
            "error": "LangGraph step counter reached maximum execution limit.",
        }

    return {"status": "CONTINUE"}


def route_decision(state: AgentGraphState) -> str:
    """Conditional edge router."""
    status = state.get("status")
    if status in ["COMPLETED", "LOOP_DETECTED", "MAX_STEPS_EXCEEDED"]:
        return END
    if status == "ACTING":
        return "tool_executor"
    return "reasoner"


class LangGraphReActAgent:
    """ReAct Agent running on top of compiled LangGraph StateGraph."""

    def __init__(self, llm: BaseLLMProvider, tools: ToolRegistry):
        self.llm = llm
        self.tools = tools
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(AgentGraphState)
        builder.add_node("reasoner", reasoner_node)
        builder.add_node("tool_executor", tool_executor_node)
        builder.add_node("reflector", reflector_node)

        builder.set_entry_point("reasoner")
        builder.add_conditional_edges("reasoner", route_decision, {
            "tool_executor": "tool_executor",
            END: END,
        })
        builder.add_edge("tool_executor", "reflector")
        builder.add_conditional_edges("reflector", route_decision, {
            "reasoner": "reasoner",
            END: END,
        })

        return builder.compile()

    def run(self, task_prompt: str, db: PaymentDatabase, scenario_id: Optional[str] = None) -> Trajectory:
        trajectory = Trajectory(
            scenario_id=scenario_id,
            architecture="langgraph_react",
            model_name=self.llm.model_name,
        )

        initial_state: AgentGraphState = {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": task_prompt},
            ],
            "steps": [],
            "current_thought": None,
            "current_tool_call": None,
            "current_tool_result": None,
            "status": "INIT",
            "error": None,
            "final_output": None,
            "step_count": 0,
            "db": db,
            "tools": self.tools,
            "llm": self.llm,
            "policy_violations": [],
        }

        final_state = self.graph.invoke(initial_state)

        trajectory.steps = final_state.get("steps", [])
        trajectory.policy_violations = final_state.get("policy_violations", [])
        trajectory.finalize(
            reason=final_state.get("status", "COMPLETED"),
            final_output=final_state.get("final_output"),
            error=final_state.get("error"),
        )
        return trajectory

