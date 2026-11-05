"""Initial schema — all tables with constraints.

Revision ID: 0001
Revises:
Create Date: 2024-01-15

Creates all WASL tables exactly as specified in DATABASE_DESIGN.md:
  users, user_sessions, merchants, drivers, orders, order_items,
  order_status_history, driver_assignments, delivery_tracking,
  tracking_tokens, financial_transactions, settlement_records,
  audit_logs, support_tickets.

Indexes are added in the next migration (0002_add_indexes.py) so
this file stays focused on structure and constraints.
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ------------------------------------------------------------------
    # USERS
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id",            sa.Integer(),     nullable=False),
        sa.Column("email",         sa.String(255),   nullable=False),
        sa.Column("phone",         sa.String(20),    nullable=False),
        sa.Column("password_hash", sa.String(255),   nullable=False),
        sa.Column("role",          sa.String(50),    nullable=False),
        sa.Column("status",        sa.String(50),    nullable=False, server_default="pending"),
        sa.Column("created_at",    sa.TIMESTAMP(),   nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at",    sa.TIMESTAMP(),   nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("phone"),
        sa.CheckConstraint("role   IN ('merchant', 'driver', 'admin')",                      name="users_role_check"),
        sa.CheckConstraint("status IN ('pending', 'approved', 'suspended', 'rejected')",     name="users_status_check"),
    )

    # ------------------------------------------------------------------
    # USER_SESSIONS  (refresh token storage — SHA-256 hash only)
    # ------------------------------------------------------------------
    op.create_table(
        "user_sessions",
        sa.Column("id",           sa.Integer(),    nullable=False),
        sa.Column("user_id",      sa.Integer(),    nullable=False),
        sa.Column("token_hash",   sa.CHAR(64),     nullable=False),   # SHA-256 hex digest
        sa.Column("created_at",   sa.TIMESTAMP(),  nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("expires_at",   sa.TIMESTAMP(),  nullable=False),
        sa.Column("last_used_at", sa.TIMESTAMP(),  nullable=True),
        sa.Column("revoked_at",   sa.TIMESTAMP(),  nullable=True),
        sa.Column("created_ip",   sa.String(45),   nullable=True),
        sa.Column("user_agent",   sa.Text(),       nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint("token_hash != ''",              name="us_token_not_empty"),
        sa.CheckConstraint("expires_at > created_at",       name="us_expires_after_created"),
    )

    # ------------------------------------------------------------------
    # MERCHANTS
    # ------------------------------------------------------------------
    op.create_table(
        "merchants",
        sa.Column("id",                           sa.Integer(),      nullable=False),
        sa.Column("user_id",                      sa.Integer(),      nullable=False),
        sa.Column("business_name",                sa.String(255),    nullable=False),
        sa.Column("business_phone",               sa.String(20),     nullable=False),
        sa.Column("address_line1",                sa.String(255),    nullable=False),
        sa.Column("address_line2",                sa.String(255),    nullable=True),
        sa.Column("city",                         sa.String(100),    nullable=False, server_default="Alexandria"),
        sa.Column("postal_code",                  sa.String(10),     nullable=True),
        sa.Column("business_registration_number", sa.String(50),     nullable=True),
        sa.Column("tax_id",                       sa.String(100),    nullable=True),
        sa.Column("contact_person_name",          sa.String(255),    nullable=False),
        # Display-only stats (recalculated daily — see ADR-005)
        sa.Column("total_orders",                  sa.Integer(),      nullable=False, server_default="0"),
        sa.Column("total_delivery_fees_egp",       sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_platform_commission_egp", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("average_rating",                sa.Numeric(3, 2),  nullable=False, server_default="0"),
        sa.Column("created_at",   sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at",   sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("approved_at",  sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("business_registration_number"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint("total_orders                  >= 0",        name="merchants_positive_orders"),
        sa.CheckConstraint("total_delivery_fees_egp       >= 0",        name="merchants_positive_fees"),
        sa.CheckConstraint("total_platform_commission_egp >= 0",        name="merchants_positive_commission"),
        sa.CheckConstraint("average_rating BETWEEN 0 AND 5",            name="merchants_valid_rating"),
    )

    # ------------------------------------------------------------------
    # DRIVERS
    # ------------------------------------------------------------------
    op.create_table(
        "drivers",
        sa.Column("id",                   sa.Integer(),     nullable=False),
        sa.Column("user_id",              sa.Integer(),     nullable=False),
        sa.Column("full_name",            sa.String(255),   nullable=False),
        sa.Column("national_id_number",   sa.String(100),   nullable=False),
        sa.Column("vehicle_type",         sa.String(50),    nullable=False),
        sa.Column("vehicle_plate_number", sa.String(50),    nullable=True),
        sa.Column("license_expiry",       sa.Date(),        nullable=True),
        sa.Column("is_online",            sa.Boolean(),     nullable=False, server_default="false"),
        sa.Column("is_on_delivery",       sa.Boolean(),     nullable=False, server_default="false"),
        sa.Column("total_deliveries",     sa.Integer(),     nullable=False, server_default="0"),
        sa.Column("total_earnings_egp",   sa.Numeric(12, 2),nullable=False, server_default="0"),
        sa.Column("average_rating",       sa.Numeric(3, 2), nullable=False, server_default="0"),
        sa.Column("cancellation_rate",    sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("created_at",  sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at",  sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("approved_at", sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("national_id_number"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint("vehicle_type IN ('motorcycle', 'car', 'van')",  name="drivers_vehicle_check"),
        sa.CheckConstraint("total_deliveries   >= 0",                       name="drivers_positive_deliveries"),
        sa.CheckConstraint("total_earnings_egp >= 0",                       name="drivers_positive_earnings"),
        sa.CheckConstraint("average_rating BETWEEN 0 AND 5",                name="drivers_valid_rating"),
        sa.CheckConstraint("cancellation_rate BETWEEN 0 AND 1",             name="drivers_valid_cancel_rate"),
    )

    # ------------------------------------------------------------------
    # ORDERS
    # ------------------------------------------------------------------
    op.create_table(
        "orders",
        sa.Column("id",                    sa.Integer(),     nullable=False),
        sa.Column("merchant_id",           sa.Integer(),     nullable=False),
        sa.Column("order_number",          sa.String(50),    nullable=False),
        sa.Column("customer_name",         sa.String(255),   nullable=False),
        sa.Column("customer_phone",        sa.String(20),    nullable=False),
        sa.Column("customer_email",        sa.String(255),   nullable=True),
        sa.Column("pickup_address_line1",  sa.String(255),   nullable=False),
        sa.Column("pickup_address_line2",  sa.String(255),   nullable=True),
        sa.Column("delivery_address_line1",sa.String(255),   nullable=False),
        sa.Column("delivery_address_line2",sa.String(255),   nullable=True),
        sa.Column("delivery_city",         sa.String(100),   nullable=False, server_default="Alexandria"),
        sa.Column("delivery_notes",        sa.Text(),        nullable=True),
        sa.Column("subtotal_egp",          sa.Numeric(12, 2),nullable=False),
        sa.Column("delivery_fee_egp",      sa.Numeric(12, 2),nullable=False),
        sa.Column("total_egp",             sa.Numeric(12, 2),nullable=False),
        sa.Column("status",                sa.String(50),    nullable=False, server_default="pending"),
        sa.Column("payment_method",        sa.String(50),    nullable=False, server_default="cash"),
        sa.Column("payment_status",        sa.String(50),    nullable=False, server_default="pending"),
        sa.Column("assigned_driver_id",    sa.Integer(),     nullable=True),
        sa.Column("created_at",            sa.TIMESTAMP(),   nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at",            sa.TIMESTAMP(),   nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("scheduled_pickup_at",   sa.TIMESTAMP(),   nullable=True),
        sa.Column("actual_pickup_at",      sa.TIMESTAMP(),   nullable=True),
        sa.Column("estimated_delivery_at", sa.TIMESTAMP(),   nullable=True),
        sa.Column("actual_delivery_at",    sa.TIMESTAMP(),   nullable=True),
        sa.Column("customer_rating",       sa.SmallInteger(),nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_number"),
        sa.ForeignKeyConstraint(["merchant_id"],        ["merchants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assigned_driver_id"], ["drivers.id"],   ondelete="SET NULL"),
        sa.CheckConstraint("status IN ('pending','assigned','picked_up','in_transit','delivered','cancelled')", name="orders_status_check"),
        sa.CheckConstraint("payment_method IN ('cash')",                                                        name="orders_payment_method_check"),
        sa.CheckConstraint("payment_status IN ('pending','collected','settled')",                               name="orders_payment_status_check"),
        sa.CheckConstraint("subtotal_egp    >= 0",                                                              name="orders_positive_subtotal"),
        sa.CheckConstraint("delivery_fee_egp > 0",                                                              name="orders_positive_fee"),
        sa.CheckConstraint("total_egp        > 0",                                                              name="orders_positive_total"),
        sa.CheckConstraint("customer_rating IS NULL OR customer_rating BETWEEN 1 AND 5",                        name="orders_valid_rating"),
    )

    # ------------------------------------------------------------------
    # ORDER ITEMS
    # ------------------------------------------------------------------
    op.create_table(
        "order_items",
        sa.Column("id",             sa.Integer(),     nullable=False),
        sa.Column("order_id",       sa.Integer(),     nullable=False),
        sa.Column("item_name",      sa.String(255),   nullable=False),
        sa.Column("quantity",       sa.Integer(),     nullable=False, server_default="1"),
        sa.Column("unit_price_egp", sa.Numeric(12,2), nullable=False),
        sa.Column("subtotal_egp",   sa.Numeric(12,2), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.CheckConstraint("quantity      >  0", name="order_items_positive_qty"),
        sa.CheckConstraint("unit_price_egp > 0", name="order_items_positive_price"),
        sa.CheckConstraint("subtotal_egp  >= 0", name="order_items_positive_subtotal"),
    )

    # ------------------------------------------------------------------
    # ORDER STATUS HISTORY  (immutable)
    # ------------------------------------------------------------------
    op.create_table(
        "order_status_history",
        sa.Column("id",                  sa.Integer(),   nullable=False),
        sa.Column("order_id",            sa.Integer(),   nullable=False),
        sa.Column("previous_status",     sa.String(50),  nullable=True),
        sa.Column("new_status",          sa.String(50),  nullable=False),
        sa.Column("changed_by_user_id",  sa.Integer(),   nullable=True),
        sa.Column("reason",              sa.Text(),      nullable=True),
        sa.Column("created_at",          sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["order_id"],           ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"],  ondelete="SET NULL"),
        sa.CheckConstraint(
            "new_status IN ('pending','assigned','picked_up','in_transit','delivered','cancelled')",
            name="osh_new_status_check",
        ),
    )

    # ------------------------------------------------------------------
    # DRIVER ASSIGNMENTS
    # ------------------------------------------------------------------
    op.create_table(
        "driver_assignments",
        sa.Column("id",                  sa.Integer(),   nullable=False),
        sa.Column("order_id",            sa.Integer(),   nullable=False),
        sa.Column("driver_id",           sa.Integer(),   nullable=False),
        sa.Column("assigned_by_user_id", sa.Integer(),   nullable=False),
        sa.Column("assignment_status",   sa.String(50),  nullable=False, server_default="assigned"),
        sa.Column("assigned_at",         sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("accepted_at",         sa.TIMESTAMP(), nullable=True),
        sa.Column("rejected_at",         sa.TIMESTAMP(), nullable=True),
        sa.Column("rejection_reason",    sa.Text(),      nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["order_id"],            ["orders.id"],  ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["driver_id"],           ["drivers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assigned_by_user_id"], ["users.id"],   ondelete="SET NULL"),
        sa.CheckConstraint(
            "assignment_status IN ('assigned','accepted','rejected','cancelled')",
            name="da_status_check",
        ),
    )

    # ------------------------------------------------------------------
    # DELIVERY TRACKING
    # ------------------------------------------------------------------
    op.create_table(
        "delivery_tracking",
        sa.Column("id",                      sa.Integer(),   nullable=False),
        sa.Column("order_id",                sa.Integer(),   nullable=False),
        sa.Column("driver_id",               sa.Integer(),   nullable=False),
        sa.Column("estimated_pickup_time",   sa.TIMESTAMP(), nullable=True),
        sa.Column("actual_pickup_time",      sa.TIMESTAMP(), nullable=True),
        sa.Column("estimated_delivery_time", sa.TIMESTAMP(), nullable=True),
        sa.Column("actual_delivery_time",    sa.TIMESTAMP(), nullable=True),
        sa.Column("pickup_photo_url",        sa.String(500), nullable=True),
        sa.Column("delivery_photo_url",      sa.String(500), nullable=True),
        sa.Column("delivery_notes",          sa.Text(),      nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id"),
        sa.ForeignKeyConstraint(["order_id"],  ["orders.id"],  ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"], ondelete="RESTRICT"),
    )

    # ------------------------------------------------------------------
    # TRACKING TOKENS
    # ------------------------------------------------------------------
    op.create_table(
        "tracking_tokens",
        sa.Column("id",           sa.Integer(),   nullable=False),
        sa.Column("order_id",     sa.Integer(),   nullable=False),
        sa.Column("token",        sa.String(255), nullable=False),
        sa.Column("created_at",   sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("expires_at",   sa.TIMESTAMP(), nullable=False),
        sa.Column("accessed_at",  sa.TIMESTAMP(), nullable=True),
        sa.Column("access_count", sa.Integer(),   nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.CheckConstraint("token        != ''", name="tt_token_not_empty"),
        sa.CheckConstraint("access_count >= 0",  name="tt_positive_count"),
    )

    # ------------------------------------------------------------------
    # FINANCIAL TRANSACTIONS  (immutable ledger)
    # ------------------------------------------------------------------
    op.create_table(
        "financial_transactions",
        sa.Column("id",                  sa.Integer(),     nullable=False),
        sa.Column("transaction_type",    sa.String(50),    nullable=False),
        sa.Column("related_order_id",    sa.Integer(),     nullable=True),
        sa.Column("related_driver_id",   sa.Integer(),     nullable=True),
        sa.Column("related_merchant_id", sa.Integer(),     nullable=True),
        sa.Column("amount_egp",          sa.Numeric(12,2), nullable=False),
        sa.Column("status",              sa.String(50),    nullable=False, server_default="pending"),
        sa.Column("notes",               sa.Text(),        nullable=True),
        sa.Column("created_at",    sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("completed_at",  sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["related_order_id"],    ["orders.id"],    ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["related_driver_id"],   ["drivers.id"],   ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["related_merchant_id"], ["merchants.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "transaction_type IN ('order_commission','driver_payout','merchant_settlement','refund')",
            name="ft_type_check",
        ),
        sa.CheckConstraint("status IN ('pending','completed','failed')", name="ft_status_check"),
        sa.CheckConstraint("amount_egp >= 0",                            name="ft_positive_amount"),
    )

    # ------------------------------------------------------------------
    # SETTLEMENT RECORDS
    # ------------------------------------------------------------------
    op.create_table(
        "settlement_records",
        sa.Column("id",               sa.Integer(),     nullable=False),
        sa.Column("settlement_type",  sa.String(50),    nullable=False),
        sa.Column("recipient_id",     sa.Integer(),     nullable=False),
        sa.Column("period_start",     sa.Date(),        nullable=False),
        sa.Column("period_end",       sa.Date(),        nullable=False),
        sa.Column("total_amount_egp", sa.Numeric(12,2), nullable=False),
        sa.Column("commissions_egp",  sa.Numeric(12,2), nullable=True),
        sa.Column("fees_egp",         sa.Numeric(12,2), nullable=True),
        sa.Column("refunds_egp",      sa.Numeric(12,2), nullable=True),
        sa.Column("status",           sa.String(50),    nullable=False, server_default="pending"),
        sa.Column("created_at",   sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("processed_at", sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("settlement_type IN ('merchant','driver')",                       name="sr_type_check"),
        sa.CheckConstraint("status IN ('pending','processed','completed','failed')",         name="sr_status_check"),
        sa.CheckConstraint("period_end >= period_start",                                     name="sr_valid_period"),
    )

    # ------------------------------------------------------------------
    # AUDIT LOGS  (immutable — no updates or deletes permitted)
    # ------------------------------------------------------------------
    op.create_table(
        "audit_logs",
        sa.Column("id",          sa.Integer(),   nullable=False),
        sa.Column("user_id",     sa.Integer(),   nullable=True),
        sa.Column("action",      sa.String(255), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id",   sa.Integer(),   nullable=True),
        sa.Column("old_values",  sa.JSON(),      nullable=True),
        sa.Column("new_values",  sa.JSON(),      nullable=True),
        sa.Column("ip_address",  sa.String(45),  nullable=True),
        sa.Column("user_agent",  sa.Text(),      nullable=True),
        sa.Column("created_at",  sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )

    # ------------------------------------------------------------------
    # SUPPORT TICKETS
    # ------------------------------------------------------------------
    op.create_table(
        "support_tickets",
        sa.Column("id",                  sa.Integer(),   nullable=False),
        sa.Column("order_id",            sa.Integer(),   nullable=False),
        sa.Column("created_by_user_id",  sa.Integer(),   nullable=False),
        sa.Column("subject",             sa.String(255), nullable=False),
        sa.Column("description",         sa.Text(),      nullable=False),
        sa.Column("ticket_type",         sa.String(50),  nullable=False),
        sa.Column("status",              sa.String(50),  nullable=False, server_default="open"),
        sa.Column("assigned_to_user_id", sa.Integer(),   nullable=True),
        sa.Column("resolution_notes",    sa.Text(),      nullable=True),
        sa.Column("created_at",  sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at",  sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("resolved_at", sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["order_id"],            ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"],  ["users.id"],  ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_to_user_id"], ["users.id"],  ondelete="SET NULL"),
        sa.CheckConstraint("ticket_type IN ('payment','delivery','damage','other')", name="st_type_check"),
        sa.CheckConstraint("status IN ('open','in_progress','resolved','closed')",  name="st_status_check"),
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("support_tickets")
    op.drop_table("audit_logs")
    op.drop_table("settlement_records")
    op.drop_table("financial_transactions")
    op.drop_table("tracking_tokens")
    op.drop_table("delivery_tracking")
    op.drop_table("driver_assignments")
    op.drop_table("order_status_history")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("drivers")
    op.drop_table("merchants")
    op.drop_table("user_sessions")
    op.drop_table("users")
