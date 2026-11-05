"""
Settlement service.

Roadmap Task 4.5:
- Admin creates a settlement_record for a driver or merchant
  covering a date range.
- Total is calculated as the sum of matching financial_transactions
  for that period.
- POST /admin/settlements/{id}/process marks the record completed
  and sets the underlying transactions to 'completed'.
- All actions logged to audit_logs.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.audit_log import AuditLog
from models.financial_transaction import FinancialTransaction
from models.settlement_record import SettlementRecord


class SettlementError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


def _txn_type_for(settlement_type: str) -> str:
    return "driver_payout" if settlement_type == "driver" else "order_commission"


def create_settlement(
    db: Session,
    settlement_type: str,
    recipient_id: int,
    period_start: date,
    period_end: date,
    created_by_user_id: int,
) -> SettlementRecord:
    """Create a settlement record with total summed from transactions.

    Sums all financial_transactions of the matching type for recipient
    in [period_start, period_end] with status='pending'.
    """
    if settlement_type not in ("driver", "merchant"):
        raise SettlementError(
            code="VALIDATION_ERROR",
            message="settlement_type must be 'driver' or 'merchant'",
        )
    if period_end < period_start:
        raise SettlementError(
            code="VALIDATION_ERROR",
            message="period_end must be >= period_start",
        )

    txn_type = _txn_type_for(settlement_type)

    # Build query for matching transactions
    q = db.query(
        func.sum(FinancialTransaction.amount_egp),
        func.sum(FinancialTransaction.amount_egp),  # reused for type split
    )
    q = db.query(
        func.count(FinancialTransaction.id),
        func.coalesce(
            func.sum(FinancialTransaction.amount_egp), Decimal("0")
        ),
    ).filter(
        FinancialTransaction.transaction_type == txn_type,
        FinancialTransaction.status == "pending",
        func.date(FinancialTransaction.created_at) >= period_start,
        func.date(FinancialTransaction.created_at) <= period_end,
    )

    if settlement_type == "driver":
        q = q.filter(
            FinancialTransaction.related_driver_id == recipient_id
        )
    else:
        q = q.filter(
            FinancialTransaction.related_merchant_id == recipient_id
        )

    count, total = q.first()
    total = total or Decimal("0")

    record = SettlementRecord(
        settlement_type=settlement_type,
        recipient_id=recipient_id,
        period_start=period_start,
        period_end=period_end,
        total_amount_egp=total,
        status="pending",
    )
    db.add(record)
    db.flush()

    log = AuditLog(
        user_id=created_by_user_id,
        action="create_settlement",
        entity_type="settlement_record",
        entity_id=record.id,
        new_values={
            "type": settlement_type,
            "recipient_id": recipient_id,
            "period_start": str(period_start),
            "period_end": str(period_end),
            "total_egp": float(total),
            "transaction_count": count,
        },
    )
    db.add(log)
    db.commit()
    db.refresh(record)
    return record


def process_settlement(
    db: Session,
    settlement_id: int,
    processed_by_user_id: int,
) -> SettlementRecord:
    """Mark a settlement record completed and its transactions completed."""
    record = db.get(SettlementRecord, settlement_id)
    if record is None:
        raise SettlementError(
            code="NOT_FOUND",
            message="Settlement record not found",
            http_status=404,
        )
    if record.status != "pending":
        raise SettlementError(
            code="VALIDATION_ERROR",
            message=f"Settlement is already '{record.status}'",
        )

    txn_type = _txn_type_for(record.settlement_type)
    now = datetime.now(timezone.utc)

    # Mark matching pending transactions as completed
    q = db.query(FinancialTransaction).filter(
        FinancialTransaction.transaction_type == txn_type,
        FinancialTransaction.status == "pending",
        func.date(FinancialTransaction.created_at) >= record.period_start,
        func.date(FinancialTransaction.created_at) <= record.period_end,
    )
    if record.settlement_type == "driver":
        q = q.filter(
            FinancialTransaction.related_driver_id == record.recipient_id
        )
    else:
        q = q.filter(
            FinancialTransaction.related_merchant_id == record.recipient_id
        )

    txns = q.all()
    for t in txns:
        t.status = "completed"
        t.completed_at = now

    record.status = "completed"
    record.processed_at = now

    log = AuditLog(
        user_id=processed_by_user_id,
        action="process_settlement",
        entity_type="settlement_record",
        entity_id=settlement_id,
        new_values={
            "status": "completed",
            "transactions_completed": len(txns),
        },
    )
    db.add(log)
    db.commit()
    db.refresh(record)
    return record
