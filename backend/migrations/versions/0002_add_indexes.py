"""Add all strategic indexes.

Revision ID: 0002
Revises: 0001
Create Date: 2024-01-15

Adds all indexes specified in DATABASE_DESIGN.md.
Kept separate from 0001 so schema structure and performance
tuning are independently reviewable and revertible.
"""

from typing import Sequence, Union
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # users
    op.create_index("idx_users_email",  "users", ["email"])
    op.create_index("idx_users_phone",  "users", ["phone"])
    op.create_index("idx_users_role",   "users", ["role"])
    op.create_index("idx_users_status", "users", ["status"])

    # user_sessions
    op.create_index("idx_us_user_id",    "user_sessions", ["user_id"])
    op.create_index("idx_us_token_hash", "user_sessions", ["token_hash"])
    op.create_index("idx_us_expires_at", "user_sessions", ["expires_at"])

    # merchants
    op.create_index("idx_merchants_user_id",       "merchants", ["user_id"])
    op.create_index("idx_merchants_business_name", "merchants", ["business_name"])

    # drivers
    op.create_index("idx_drivers_user_id",        "drivers", ["user_id"])
    op.create_index("idx_drivers_is_online",      "drivers", ["is_online"])
    op.create_index("idx_drivers_is_on_delivery", "drivers", ["is_on_delivery"])

    # orders
    op.create_index("idx_orders_merchant_id",        "orders", ["merchant_id"])
    op.create_index("idx_orders_assigned_driver_id", "orders", ["assigned_driver_id"])
    op.create_index("idx_orders_status",             "orders", ["status"])
    op.create_index("idx_orders_created_at",         "orders", ["created_at"])
    op.create_index("idx_orders_order_number",       "orders", ["order_number"])
    op.create_index("idx_orders_payment_status",     "orders", ["payment_status"])

    # order_items
    op.create_index("idx_order_items_order_id", "order_items", ["order_id"])

    # order_status_history
    op.create_index("idx_osh_order_id",   "order_status_history", ["order_id"])
    op.create_index("idx_osh_created_at", "order_status_history", ["created_at"])

    # driver_assignments
    op.create_index("idx_da_order_id",  "driver_assignments", ["order_id"])
    op.create_index("idx_da_driver_id", "driver_assignments", ["driver_id"])
    op.create_index("idx_da_status",    "driver_assignments", ["assignment_status"])

    # delivery_tracking
    op.create_index("idx_dt_order_id",  "delivery_tracking", ["order_id"])
    op.create_index("idx_dt_driver_id", "delivery_tracking", ["driver_id"])

    # tracking_tokens
    op.create_index("idx_tt_order_id",   "tracking_tokens", ["order_id"])
    op.create_index("idx_tt_token",      "tracking_tokens", ["token"])
    op.create_index("idx_tt_expires_at", "tracking_tokens", ["expires_at"])

    # financial_transactions
    op.create_index("idx_ft_type",        "financial_transactions", ["transaction_type"])
    op.create_index("idx_ft_status",      "financial_transactions", ["status"])
    op.create_index("idx_ft_created_at",  "financial_transactions", ["created_at"])
    op.create_index("idx_ft_order_id",    "financial_transactions", ["related_order_id"])
    op.create_index("idx_ft_driver_id",   "financial_transactions", ["related_driver_id"])
    op.create_index("idx_ft_merchant_id", "financial_transactions", ["related_merchant_id"])

    # settlement_records
    op.create_index("idx_sr_type",         "settlement_records", ["settlement_type"])
    op.create_index("idx_sr_recipient_id", "settlement_records", ["recipient_id"])
    op.create_index("idx_sr_status",       "settlement_records", ["status"])
    op.create_index("idx_sr_period",       "settlement_records", ["period_start", "period_end"])

    # audit_logs
    op.create_index("idx_al_user_id",    "audit_logs", ["user_id"])
    op.create_index("idx_al_entity",     "audit_logs", ["entity_type", "entity_id"])
    op.create_index("idx_al_action",     "audit_logs", ["action"])
    op.create_index("idx_al_created_at", "audit_logs", ["created_at"])

    # support_tickets
    op.create_index("idx_st_order_id",   "support_tickets", ["order_id"])
    op.create_index("idx_st_status",     "support_tickets", ["status"])
    op.create_index("idx_st_created_at", "support_tickets", ["created_at"])


def downgrade() -> None:
    # support_tickets
    op.drop_index("idx_st_created_at", table_name="support_tickets")
    op.drop_index("idx_st_status",     table_name="support_tickets")
    op.drop_index("idx_st_order_id",   table_name="support_tickets")

    # audit_logs
    op.drop_index("idx_al_created_at", table_name="audit_logs")
    op.drop_index("idx_al_action",     table_name="audit_logs")
    op.drop_index("idx_al_entity",     table_name="audit_logs")
    op.drop_index("idx_al_user_id",    table_name="audit_logs")

    # settlement_records
    op.drop_index("idx_sr_period",       table_name="settlement_records")
    op.drop_index("idx_sr_status",       table_name="settlement_records")
    op.drop_index("idx_sr_recipient_id", table_name="settlement_records")
    op.drop_index("idx_sr_type",         table_name="settlement_records")

    # financial_transactions
    op.drop_index("idx_ft_merchant_id", table_name="financial_transactions")
    op.drop_index("idx_ft_driver_id",   table_name="financial_transactions")
    op.drop_index("idx_ft_order_id",    table_name="financial_transactions")
    op.drop_index("idx_ft_created_at",  table_name="financial_transactions")
    op.drop_index("idx_ft_status",      table_name="financial_transactions")
    op.drop_index("idx_ft_type",        table_name="financial_transactions")

    # tracking_tokens
    op.drop_index("idx_tt_expires_at", table_name="tracking_tokens")
    op.drop_index("idx_tt_token",      table_name="tracking_tokens")
    op.drop_index("idx_tt_order_id",   table_name="tracking_tokens")

    # delivery_tracking
    op.drop_index("idx_dt_driver_id", table_name="delivery_tracking")
    op.drop_index("idx_dt_order_id",  table_name="delivery_tracking")

    # driver_assignments
    op.drop_index("idx_da_status",    table_name="driver_assignments")
    op.drop_index("idx_da_driver_id", table_name="driver_assignments")
    op.drop_index("idx_da_order_id",  table_name="driver_assignments")

    # order_status_history
    op.drop_index("idx_osh_created_at", table_name="order_status_history")
    op.drop_index("idx_osh_order_id",   table_name="order_status_history")

    # order_items
    op.drop_index("idx_order_items_order_id", table_name="order_items")

    # orders
    op.drop_index("idx_orders_payment_status",     table_name="orders")
    op.drop_index("idx_orders_order_number",       table_name="orders")
    op.drop_index("idx_orders_created_at",         table_name="orders")
    op.drop_index("idx_orders_status",             table_name="orders")
    op.drop_index("idx_orders_assigned_driver_id", table_name="orders")
    op.drop_index("idx_orders_merchant_id",        table_name="orders")

    # drivers
    op.drop_index("idx_drivers_is_on_delivery", table_name="drivers")
    op.drop_index("idx_drivers_is_online",      table_name="drivers")
    op.drop_index("idx_drivers_user_id",        table_name="drivers")

    # merchants
    op.drop_index("idx_merchants_business_name", table_name="merchants")
    op.drop_index("idx_merchants_user_id",       table_name="merchants")

    # user_sessions
    op.drop_index("idx_us_expires_at", table_name="user_sessions")
    op.drop_index("idx_us_token_hash", table_name="user_sessions")
    op.drop_index("idx_us_user_id",    table_name="user_sessions")

    # users
    op.drop_index("idx_users_status", table_name="users")
    op.drop_index("idx_users_role",   table_name="users")
    op.drop_index("idx_users_phone",  table_name="users")
    op.drop_index("idx_users_email",  table_name="users")
