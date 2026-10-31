"""
Tests for Agent Loops: Barebones ReAct, LangGraph ReAct, and Plan-and-Execute.
"""

from agentprobe.domain.database import PaymentDatabase
from agentprobe.tools.registry import ToolRegistry
from agentprobe.llm.mock_provider import MockBehavioralProvider
from agentprobe.agents.barebones_react import BarebonesReActAgent
from agentprobe.agents.langgraph_react import LangGraphReActAgent
from agentprobe.agents.plan_and_execute import PlanAndExecuteAgent


def test_barebones_react_golden_flow(memory_db: PaymentDatabase, tool_registry: ToolRegistry):
    llm = MockBehavioralProvider(profile="golden")
    agent = BarebonesReActAgent(llm=llm, tools=tool_registry, max_steps=5)

    prompt = "Please investigate transaction TX-1001 and process refund."
    trajectory = agent.run(task_prompt=prompt, db=memory_db, scenario_id="TEST-01")

    assert trajectory.termination_reason == "COMPLETED"
    assert len(trajectory.steps) >= 3
    executed_tools = trajectory.get_executed_tool_names()
    assert "query_database" in executed_tools
    assert "fetch_risk_score" in executed_tools
    assert "refund_transaction" in executed_tools


def test_langgraph_react_golden_flow(memory_db: PaymentDatabase, tool_registry: ToolRegistry):
    llm = MockBehavioralProvider(profile="golden")
    agent = LangGraphReActAgent(llm=llm, tools=tool_registry)

    prompt = "Please investigate transaction TX-1001 and process refund."
    trajectory = agent.run(task_prompt=prompt, db=memory_db, scenario_id="TEST-02")

    assert trajectory.termination_reason == "COMPLETED"
    assert len(trajectory.steps) >= 3
    executed_tools = trajectory.get_executed_tool_names()
    assert "query_database" in executed_tools
    assert "fetch_risk_score" in executed_tools


def test_plan_and_execute_flow(memory_db: PaymentDatabase, tool_registry: ToolRegistry):
    llm = MockBehavioralProvider(profile="golden")
    agent = PlanAndExecuteAgent(llm=llm, tools=tool_registry, max_steps=6)

    prompt = "Investigate transaction TX-1001 and issue eligible refund."
    trajectory = agent.run(task_prompt=prompt, db=memory_db, scenario_id="TEST-03")

    assert trajectory.termination_reason == "COMPLETED"
    assert any(s.phase == "plan" for s in trajectory.steps)


def test_loop_detection_in_barebones(memory_db: PaymentDatabase, tool_registry: ToolRegistry):
    llm = MockBehavioralProvider(profile="looping")
    agent = BarebonesReActAgent(llm=llm, tools=tool_registry, max_steps=6)

    prompt = "Check transaction TX-1001 repeatedly."
    trajectory = agent.run(task_prompt=prompt, db=memory_db, scenario_id="TEST-LOOP")

    assert trajectory.termination_reason in ["LOOP_DETECTED", "MAX_STEPS_EXCEEDED"]

