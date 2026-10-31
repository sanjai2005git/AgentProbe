"""
Central Tool Registry and Dispatcher.
"""

from typing import Dict, List, Any, Optional
from agentprobe.tools.base import BaseTool, ToolResult, ToolCall
from agentprobe.tools.payment_tools import (
    QueryDatabaseTool,
    FetchRiskScoreTool,
    RefundTransactionTool,
    FlagFraudulentTool,
    RouteRetryTool,
    EscalateToHumanTool,
)
from agentprobe.domain.database import PaymentDatabase


class ToolRegistry:
    """Registry maintaining available tools, schema definitions, and safe execution dispatch."""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tool_names(self) -> List[str]:
        return list(self._tools.keys())

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Returns schemas in OpenAI / LLM function calling specification."""
        return [tool.get_json_schema() for tool in self._tools.values()]

    def execute(self, tool_call: ToolCall, db: PaymentDatabase) -> ToolResult:
        """Dispatches execution to the registered tool handler."""
        tool = self._tools.get(tool_call.name)
        if not tool:
            return ToolResult(
                tool_name=tool_call.name,
                success=False,
                error=f"Unknown tool '{tool_call.name}'. Available tools: {list(self._tools.keys())}",
                latency_ms=0.0,
            )
        return tool.run(db, **tool_call.arguments)


def get_default_registry() -> ToolRegistry:
    """Creates registry with all enterprise payment tools."""
    registry = ToolRegistry()
    registry.register(QueryDatabaseTool())
    registry.register(FetchRiskScoreTool())
    registry.register(RefundTransactionTool())
    registry.register(FlagFraudulentTool())
    registry.register(RouteRetryTool())
    registry.register(EscalateToHumanTool())
    return registry

