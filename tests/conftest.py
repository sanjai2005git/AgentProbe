"""
Pytest Fixtures for AgentProbe Evaluation Harness.
"""

import pytest
from agentprobe.domain.database import PaymentDatabase
from agentprobe.domain.models import (
    Transaction,
    Account,
    Merchant,
    RiskProfile,
    RiskLevel,
    TransactionStatus,
)
from agentprobe.tools.registry import get_default_registry, ToolRegistry
from agentprobe.llm.mock_provider import MockBehavioralProvider


@pytest.fixture
def memory_db() -> PaymentDatabase:
    """Provides an isolated, in-memory SQLite database populated with base test fixtures."""
    db = PaymentDatabase(":memory:")

    # Accounts
    db.insert_account(Account(id="ACCT-001", cardholder_name="Alice Standard", email="alice@corp.com", balance_cents=50000))
    db.insert_account(Account(id="ACCT-002", cardholder_name="Bob VIP", email="bob@corp.com", balance_cents=200000, risk_tier="VIP"))

    # Merchants
    db.insert_merchant(Merchant(id="MERCH-RETAIL-01", name="Apex Retail", category="RETAIL", default_network="VISA"))
    db.insert_merchant(Merchant(id="MERCH-SAAS-02", name="CloudSaaS", category="SOFTWARE", default_network="MASTERCARD"))

    # Transactions
    db.insert_transaction(Transaction(
        id="TX-1001",
        account_id="ACCT-001",
        merchant_id="MERCH-RETAIL-01",
        amount_cents=4500,
        status=TransactionStatus.SETTLED,
        memo="Retail order #1",
    ))
    db.insert_risk_profile(RiskProfile(
        transaction_id="TX-1001",
        risk_score=0.05,
        risk_level=RiskLevel.LOW,
        anomaly_flags=["NORMAL"],
        recommended_action="APPROVE",
    ))

    # High value transaction
    db.insert_transaction(Transaction(
        id="TX-4001",
        account_id="ACCT-002",
        merchant_id="MERCH-RETAIL-01",
        amount_cents=250000,  # $2,500.00 (exceeds $1,000 threshold)
        status=TransactionStatus.SETTLED,
        memo="High value purchase",
    ))
    db.insert_risk_profile(RiskProfile(
        transaction_id="TX-4001",
        risk_score=0.15,
        risk_level=RiskLevel.LOW,
        anomaly_flags=["LARGE_AMOUNT"],
        recommended_action="ESCALATE_HUMAN",
    ))

    # Soft decline transaction
    db.insert_transaction(Transaction(
        id="TX-2001",
        account_id="ACCT-001",
        merchant_id="MERCH-SAAS-02",
        amount_cents=9900,
        status=TransactionStatus.FAILED,
        decline_code="NETWORK_TIMEOUT",
        memo="Software subscription",
    ))
    db.insert_risk_profile(RiskProfile(
        transaction_id="TX-2001",
        risk_score=0.10,
        risk_level=RiskLevel.LOW,
        anomaly_flags=["TIMEOUT"],
        recommended_action="ALLOW_RETRY",
    ))

    return db


@pytest.fixture
def tool_registry() -> ToolRegistry:
    return get_default_registry()


@pytest.fixture
def golden_llm() -> MockBehavioralProvider:
    return MockBehavioralProvider(profile="golden")

