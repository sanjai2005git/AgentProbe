"""
Pydantic Domain Models for Payment Operations.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    SETTLED = "SETTLED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    FLAGGED = "FLAGGED"
    ESCALATED = "ESCALATED"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Account(BaseModel):
    id: str
    cardholder_name: str
    email: str
    is_frozen: bool = False
    balance_cents: int = 0
    risk_tier: str = "STANDARD"  # VIP, STANDARD, WATCHLIST
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Merchant(BaseModel):
    id: str
    name: str
    category: str  # e.g., "E-COMMERCE", "GAMING", "CRYPTO", "AIRLINE"
    risk_rating: float = 0.05  # baseline fraud rate 0.0 - 1.0
    default_network: str = "VISA"  # VISA, MASTERCARD, AMEX, DCI


class RiskProfile(BaseModel):
    transaction_id: str
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel
    anomaly_flags: List[str] = Field(default_factory=list)
    recommended_action: str  # e.g., "APPROVE", "FLAG_FRAUD", "ESCALATE_HUMAN", "ALLOW_RETRY"


class Transaction(BaseModel):
    id: str
    account_id: str
    merchant_id: str
    amount_cents: int
    currency: str = "USD"
    status: TransactionStatus = TransactionStatus.PENDING
    decline_code: Optional[str] = None  # e.g., "INSUFFICIENT_FUNDS", "NETWORK_TIMEOUT", "SUSPECTED_FRAUD", "EXPIRED_CARD"
    memo: Optional[str] = None
    network: str = "VISA"
    retry_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ApprovalGate(BaseModel):
    id: str
    transaction_id: str
    action_requested: str  # "REFUND", "UNFREEZE", "RETRY_OVER_LIMIT"
    amount_cents: int
    requested_by: str = "AgentProbe"
    status: ApprovalStatus = ApprovalStatus.PENDING
    rationale: str
    token: Optional[str] = None  # Nonce token verified before executing high-risk action
    reviewed_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditLog(BaseModel):
    id: Optional[int] = None
    transaction_id: str
    action: str
    actor: str  # "AgentProbe", "HumanAnalyst", "System"
    payload: Dict[str, Any] = Field(default_factory=dict)
    success: bool = True
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

