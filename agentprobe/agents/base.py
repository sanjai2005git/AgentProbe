"""
Base Agent Specifications, Trajectory Tracking, and Step Records.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import time
from datetime import datetime, timezone
from agentprobe.tools.base import ToolCall, ToolResult
from agentprobe.config import MODEL_PRICING, settings


class StepRecord(BaseModel):
    step_index: int
    phase: str  # "plan", "act", "observe", "reflect"
    thought: Optional[str] = None
    tool_call: Optional[ToolCall] = None
    tool_result: Optional[ToolResult] = None
    reflection: Optional[str] = None
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Trajectory(BaseModel):
    scenario_id: Optional[str] = None
    architecture: str
    model_name: str
    steps: List[StepRecord] = Field(default_factory=list)
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: Optional[datetime] = None
    total_duration_ms: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    termination_reason: str = "PENDING"  # "COMPLETED", "LOOP_DETECTED", "MAX_STEPS_EXCEEDED", "ERROR"
    final_output: Optional[str] = None
    error_message: Optional[str] = None
    policy_violations: List[str] = Field(default_factory=list)

    def finalize(self, reason: str, final_output: Optional[str] = None, error: Optional[str] = None) -> None:
        self.end_time = datetime.now(timezone.utc)
        self.total_duration_ms = sum(s.latency_ms for s in self.steps)
        self.total_input_tokens = sum(s.input_tokens for s in self.steps)
        self.total_output_tokens = sum(s.output_tokens for s in self.steps)
        self.termination_reason = reason
        self.final_output = final_output
        self.error_message = error

        # Calculate estimated cost
        pricing = MODEL_PRICING.get(self.model_name.lower())
        if pricing:
            in_cost = (self.total_input_tokens / 1_000_000) * pricing.input_cost_per_million
            out_cost = (self.total_output_tokens / 1_000_000) * pricing.output_cost_per_million
            self.estimated_cost_usd = round(in_cost + out_cost, 6)

    def get_executed_tool_names(self) -> List[str]:
        return [s.tool_call.name for s in self.steps if s.tool_call]

    def has_detected_loop(self) -> bool:
        """Detects consecutive repeating tool calls with identical parameters."""
        tool_calls = [s.tool_call for s in self.steps if s.tool_call]
        if len(tool_calls) < 2:
            return False
        # Window-based loop check
        window = settings.policies.loop_detection_window
        for i in range(len(tool_calls) - window):
            current = tool_calls[i]
            consecutive = all(
                tool_calls[i + j].name == current.name and tool_calls[i + j].arguments == current.arguments
                for j in range(1, window + 1)
            )
            if consecutive:
                return True
        return False

