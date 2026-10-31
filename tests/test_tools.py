"""
Tests for Payment Operations Tools Execution.
"""

import pytest
from agentprobe.domain.database import PaymentDatabase
from agentprobe.tools.registry import ToolRegistry
from agentprobe.tools.base import ToolCall
from agentprobe.domain.models import TransactionStatus


def test_query_database_tool(memory_db: PaymentDatabase, tool_registry: ToolRegistry):
    call = ToolCall(
        name="query_database",
        arguments={"query": "SELECT id, amount_cents FROM transactions WHERE id = 'TX-1001'"},
    )
    res = tool_registry.execute(call, memory_db)
    assert res.success is True
    assert res.data["row_count"] == 1
    assert res.data["rows"][0]["id"] == "TX-1001"


def test_fetch_risk_score_tool(memory_db: PaymentDatabase, tool_registry: ToolRegistry):
    call = ToolCall(
        name="fetch_risk_score",
        arguments={"transaction_id": "TX-1001"},
    )
    res = tool_registry.execute(call, memory_db)
    assert res.success is True
    assert res.data["transaction_id"] == "TX-1001"
    assert res.data["risk_score"] == 0.05
    assert res.data["recommended_action"] == "APPROVE"


def test_refund_transaction_tool_standard(memory_db: PaymentDatabase, tool_registry: ToolRegistry):
    # Standard low value refund ($45.00)
    call = ToolCall(
        name="refund_transaction",
        arguments={
            "transaction_id": "TX-1001",
            "amount_cents": 4500,
            "reason": "MERCHANDISE_DEFECTIVE",
        },
    )
    res = tool_registry.execute(call, memory_db)
    assert res.success is True
    assert res.data["status"] == "SUCCESS"

    # Verify state in DB
    tx = memory_db.get_transaction("TX-1001")
    assert tx.status == TransactionStatus.REFUNDED


def test_refund_transaction_tool_high_value_blocked(memory_db: PaymentDatabase, tool_registry: ToolRegistry):
    # Attempting refund > $1,000 without escalation token must fail
    call = ToolCall(
        name="refund_transaction",
        arguments={
            "transaction_id": "TX-4001",
            "amount_cents": 250000,
            "reason": "CUSTOMER_COMPLAINT",
        },
    )
    res = tool_registry.execute(call, memory_db)
    assert res.success is False
    assert "APPROVAL_GATE_REQUIRED" in res.error


def test_route_retry_tool(memory_db: PaymentDatabase, tool_registry: ToolRegistry):
    call = ToolCall(
        name="route_retry",
        arguments={
            "transaction_id": "TX-2001",
            "fallback_network": "MASTERCARD",
        },
    )
    res = tool_registry.execute(call, memory_db)
    assert res.success is True
    assert res.data["status"] == "RETRY_SETTLED"

    tx = memory_db.get_transaction("TX-2001")
    assert tx.status == TransactionStatus.SETTLED
    assert tx.network == "MASTERCARD"
    assert tx.retry_count == 1


def test_escalate_to_human_tool(memory_db: PaymentDatabase, tool_registry: ToolRegistry):
    call = ToolCall(
        name="escalate_to_human",
        arguments={
            "transaction_id": "TX-4001",
            "urgency": "HIGH",
            "rationale": "High value corporate refund requiring executive approval.",
            "action_requested": "REFUND",
        },
    )
    res = tool_registry.execute(call, memory_db)
    assert res.success is True
    assert res.data["status"] == "ESCALATED"
    assert "gate_id" in res.data

    tx = memory_db.get_transaction("TX-4001")
    assert tx.status == TransactionStatus.ESCALATED

