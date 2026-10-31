"""
SQLite Database Layer for Payment Operations, Transaction State, and Audit Trails.
"""

import sqlite3
import json
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pathlib import Path

from agentprobe.domain.models import (
    Transaction,
    Account,
    Merchant,
    RiskProfile,
    ApprovalGate,
    AuditLog,
    TransactionStatus,
    RiskLevel,
    ApprovalStatus,
)


class PaymentDatabase:
    """Manages SQLite storage for payment transactions, risk metadata, and audit logs."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        """Create tables if they don't exist."""
        cursor = self.conn.cursor()
        cursor.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY,
            cardholder_name TEXT NOT NULL,
            email TEXT NOT NULL,
            is_frozen INTEGER NOT NULL DEFAULT 0,
            balance_cents INTEGER NOT NULL DEFAULT 0,
            risk_tier TEXT NOT NULL DEFAULT 'STANDARD',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS merchants (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            risk_rating REAL NOT NULL DEFAULT 0.05,
            default_network TEXT NOT NULL DEFAULT 'VISA'
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            merchant_id TEXT NOT NULL,
            amount_cents INTEGER NOT NULL,
            currency TEXT NOT NULL DEFAULT 'USD',
            status TEXT NOT NULL,
            decline_code TEXT,
            memo TEXT,
            network TEXT NOT NULL DEFAULT 'VISA',
            retry_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (account_id) REFERENCES accounts (id),
            FOREIGN KEY (merchant_id) REFERENCES merchants (id)
        );

        CREATE TABLE IF NOT EXISTS risk_profiles (
            transaction_id TEXT PRIMARY KEY,
            risk_score REAL NOT NULL,
            risk_level TEXT NOT NULL,
            anomaly_flags TEXT NOT NULL,
            recommended_action TEXT NOT NULL,
            FOREIGN KEY (transaction_id) REFERENCES transactions (id)
        );

        CREATE TABLE IF NOT EXISTS approval_gates (
            id TEXT PRIMARY KEY,
            transaction_id TEXT NOT NULL,
            action_requested TEXT NOT NULL,
            amount_cents INTEGER NOT NULL,
            requested_by TEXT NOT NULL,
            status TEXT NOT NULL,
            rationale TEXT NOT NULL,
            token TEXT,
            reviewed_by TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (transaction_id) REFERENCES transactions (id)
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT NOT NULL,
            action TEXT NOT NULL,
            actor TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            success INTEGER NOT NULL,
            error_message TEXT,
            timestamp TEXT NOT NULL
        );
        """)
        self.conn.commit()

    def reset_database(self) -> None:
        """Wipes all rows from tables."""
        cursor = self.conn.cursor()
        cursor.executescript("""
        DELETE FROM audit_logs;
        DELETE FROM approval_gates;
        DELETE FROM risk_profiles;
        DELETE FROM transactions;
        DELETE FROM merchants;
        DELETE FROM accounts;
        """)
        self.conn.commit()

    def query_sql(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Safe read-only execution for agent database queries."""
        cursor = self.conn.cursor()
        # Security sanity check: only allow SELECT statements for agent generic query tool
        cleaned_sql = sql.strip().upper()
        if not cleaned_sql.startswith("SELECT") and not cleaned_sql.startswith("PRAGMA"):
            raise ValueError("Only SELECT or PRAGMA queries are permitted via the generic query tool.")
        
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    # --- Account Methods ---
    def insert_account(self, account: Account) -> None:
        with self.conn:
            self.conn.execute("""
            INSERT OR REPLACE INTO accounts (id, cardholder_name, email, is_frozen, balance_cents, risk_tier, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                account.id,
                account.cardholder_name,
                account.email,
                1 if account.is_frozen else 0,
                account.balance_cents,
                account.risk_tier,
                account.created_at.isoformat()
            ))

    def get_account(self, account_id: str) -> Optional[Account]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return Account(
            id=row["id"],
            cardholder_name=row["cardholder_name"],
            email=row["email"],
            is_frozen=bool(row["is_frozen"]),
            balance_cents=row["balance_cents"],
            risk_tier=row["risk_tier"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def freeze_account(self, account_id: str) -> bool:
        with self.conn:
            cursor = self.conn.execute("UPDATE accounts SET is_frozen = 1 WHERE id = ?", (account_id,))
            return cursor.rowcount > 0

    # --- Merchant Methods ---
    def insert_merchant(self, merchant: Merchant) -> None:
        with self.conn:
            self.conn.execute("""
            INSERT OR REPLACE INTO merchants (id, name, category, risk_rating, default_network)
            VALUES (?, ?, ?, ?, ?)
            """, (
                merchant.id,
                merchant.name,
                merchant.category,
                merchant.risk_rating,
                merchant.default_network
            ))

    def get_merchant(self, merchant_id: str) -> Optional[Merchant]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM merchants WHERE id = ?", (merchant_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return Merchant(
            id=row["id"],
            name=row["name"],
            category=row["category"],
            risk_rating=row["risk_rating"],
            default_network=row["default_network"],
        )

    # --- Transaction Methods ---
    def insert_transaction(self, tx: Transaction) -> None:
        with self.conn:
            self.conn.execute("""
            INSERT OR REPLACE INTO transactions (
                id, account_id, merchant_id, amount_cents, currency, status, decline_code, memo, network, retry_count, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tx.id,
                tx.account_id,
                tx.merchant_id,
                tx.amount_cents,
                tx.currency,
                tx.status.value if isinstance(tx.status, TransactionStatus) else tx.status,
                tx.decline_code,
                tx.memo,
                tx.network,
                tx.retry_count,
                tx.created_at.isoformat(),
                tx.updated_at.isoformat(),
            ))

    def get_transaction(self, tx_id: str) -> Optional[Transaction]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return Transaction(
            id=row["id"],
            account_id=row["account_id"],
            merchant_id=row["merchant_id"],
            amount_cents=row["amount_cents"],
            currency=row["currency"],
            status=TransactionStatus(row["status"]),
            decline_code=row["decline_code"],
            memo=row["memo"],
            network=row["network"],
            retry_count=row["retry_count"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def update_transaction_status(self, tx_id: str, status: TransactionStatus, decline_code: Optional[str] = None) -> bool:
        now_str = datetime.now(timezone.utc).isoformat()
        with self.conn:
            cursor = self.conn.execute("""
            UPDATE transactions 
            SET status = ?, decline_code = coalesce(?, decline_code), updated_at = ?
            WHERE id = ?
            """, (status.value, decline_code, now_str, tx_id))
            return cursor.rowcount > 0

    def increment_retry(self, tx_id: str, new_network: str) -> bool:
        now_str = datetime.now(timezone.utc).isoformat()
        with self.conn:
            cursor = self.conn.execute("""
            UPDATE transactions
            SET retry_count = retry_count + 1, network = ?, status = 'SETTLED', decline_code = NULL, updated_at = ?
            WHERE id = ?
            """, (new_network, now_str, tx_id))
            return cursor.rowcount > 0

    # --- Risk Profile Methods ---
    def insert_risk_profile(self, profile: RiskProfile) -> None:
        with self.conn:
            self.conn.execute("""
            INSERT OR REPLACE INTO risk_profiles (transaction_id, risk_score, risk_level, anomaly_flags, recommended_action)
            VALUES (?, ?, ?, ?, ?)
            """, (
                profile.transaction_id,
                profile.risk_score,
                profile.risk_level.value if isinstance(profile.risk_level, RiskLevel) else profile.risk_level,
                json.dumps(profile.anomaly_flags),
                profile.recommended_action
            ))

    def get_risk_profile(self, tx_id: str) -> Optional[RiskProfile]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM risk_profiles WHERE transaction_id = ?", (tx_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return RiskProfile(
            transaction_id=row["transaction_id"],
            risk_score=row["risk_score"],
            risk_level=RiskLevel(row["risk_level"]),
            anomaly_flags=json.loads(row["anomaly_flags"]),
            recommended_action=row["recommended_action"],
        )

    # --- Approval Gate Methods ---
    def insert_approval_gate(self, gate: ApprovalGate) -> None:
        with self.conn:
            self.conn.execute("""
            INSERT OR REPLACE INTO approval_gates (
                id, transaction_id, action_requested, amount_cents, requested_by, status, rationale, token, reviewed_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                gate.id,
                gate.transaction_id,
                gate.action_requested,
                gate.amount_cents,
                gate.requested_by,
                gate.status.value if isinstance(gate.status, ApprovalStatus) else gate.status,
                gate.rationale,
                gate.token,
                gate.reviewed_by,
                gate.created_at.isoformat()
            ))

    def get_approval_gate(self, gate_id: str) -> Optional[ApprovalGate]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM approval_gates WHERE id = ?", (gate_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return ApprovalGate(
            id=row["id"],
            transaction_id=row["transaction_id"],
            action_requested=row["action_requested"],
            amount_cents=row["amount_cents"],
            requested_by=row["requested_by"],
            status=ApprovalStatus(row["status"]),
            rationale=row["rationale"],
            token=row["token"],
            reviewed_by=row["reviewed_by"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def get_approval_gates_for_transaction(self, tx_id: str) -> List[ApprovalGate]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM approval_gates WHERE transaction_id = ?", (tx_id,))
        rows = cursor.fetchall()
        return [
            ApprovalGate(
                id=row["id"],
                transaction_id=row["transaction_id"],
                action_requested=row["action_requested"],
                amount_cents=row["amount_cents"],
                requested_by=row["requested_by"],
                status=ApprovalStatus(row["status"]),
                rationale=row["rationale"],
                token=row["token"],
                reviewed_by=row["reviewed_by"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    def approve_gate(self, gate_id: str, reviewer: str = "ComplianceOfficer") -> Optional[str]:
        """Approve an escalation gate and issue an authorization token."""
        token = f"AUTH-GATE-{uuid.uuid4().hex[:12].upper()}"
        with self.conn:
            cursor = self.conn.execute("""
            UPDATE approval_gates
            SET status = 'APPROVED', token = ?, reviewed_by = ?
            WHERE id = ? AND status = 'PENDING'
            """, (token, reviewer, gate_id))
            if cursor.rowcount > 0:
                return token
        return None

    def reject_gate(self, gate_id: str, reviewer: str = "ComplianceOfficer") -> bool:
        with self.conn:
            cursor = self.conn.execute("""
            UPDATE approval_gates
            SET status = 'REJECTED', reviewed_by = ?
            WHERE id = ? AND status = 'PENDING'
            """, (reviewer, gate_id))
            return cursor.rowcount > 0

    # --- Audit Log Methods ---
    def log_audit(self, log: AuditLog) -> int:
        with self.conn:
            cursor = self.conn.execute("""
            INSERT INTO audit_logs (transaction_id, action, actor, payload_json, success, error_message, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                log.transaction_id,
                log.action,
                log.actor,
                json.dumps(log.payload),
                1 if log.success else 0,
                log.error_message,
                log.timestamp.isoformat()
            ))
            return cursor.lastrowid

    def get_audit_logs(self, tx_id: Optional[str] = None) -> List[AuditLog]:
        cursor = self.conn.cursor()
        if tx_id:
            cursor.execute("SELECT * FROM audit_logs WHERE transaction_id = ? ORDER BY id ASC", (tx_id,))
        else:
            cursor.execute("SELECT * FROM audit_logs ORDER BY id ASC")
        rows = cursor.fetchall()
        return [
            AuditLog(
                id=row["id"],
                transaction_id=row["transaction_id"],
                action=row["action"],
                actor=row["actor"],
                payload=json.loads(row["payload_json"]),
                success=bool(row["success"]),
                error_message=row["error_message"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
            )
            for row in rows
        ]

