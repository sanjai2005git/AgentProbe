"""
Base Tool Abstractions, Parameter Schemas, and Execution Results.
"""

from typing import Dict, Any, Optional, Type
from pydantic import BaseModel, Field
import time


class ToolResult(BaseModel):
    tool_name: str
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    latency_ms: float = 0.0

    def to_observation_string(self) -> str:
        """Formatted string representation for the agent's observation window."""
        if self.success:
            return f"[{self.tool_name} SUCCESS] {self.data}"
        return f"[{self.tool_name} ERROR] {self.error}"


class ToolCall(BaseModel):
    id: Optional[str] = None
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class BaseTool:
    """Abstract base class for payment operations tools."""
    name: str = ""
    description: str = ""
    args_schema: Type[BaseModel]

    def get_json_schema(self) -> Dict[str, Any]:
        """Returns OpenAI / Anthropic compatible function schema."""
        schema = self.args_schema.model_json_schema()
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": schema.get("properties", {}),
                    "required": schema.get("required", []),
                },
            },
        }

    def run(self, db: Any, **kwargs) -> ToolResult:
        """Executes tool with timing and error handling."""
        start = time.perf_counter()
        try:
            # Validate input arguments using pydantic schema
            validated_args = self.args_schema(**kwargs)
            result_data = self._execute(db, validated_args)
            latency_ms = (time.perf_counter() - start) * 1000.0
            return ToolResult(
                tool_name=self.name,
                success=True,
                data=result_data,
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000.0
            return ToolResult(
                tool_name=self.name,
                success=False,
                error=str(e),
                latency_ms=latency_ms,
            )

    def _execute(self, db: Any, args: BaseModel) -> Any:
        raise NotImplementedError

