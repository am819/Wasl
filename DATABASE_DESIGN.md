# WASL Database Design

## Overview

Single PostgreSQL database serving as the authoritative source of truth for all WASL data.

**Key design principles:**
- Third normal form with justified denormalisation (non-financial display stats only)
- All relationships enforced via foreign key constraints
- Immutable history tables for financial and status audit trails
- Strategic indexes on high-frequency query columns
- Application-level encryption for sensitive fields
- Financial metrics always derived from `financial_transactions` — never from denormalised columns

---

## Entity Relationship Summary

```
users (base identity)
 ├── user_sessions (one-to-many via user_id)   ← refresh token storage
 ├── merchants (one-to-one via user_id)
 │    └── orders (one-to-many via merchant_id)
 │         ├── order_items (one-to-many via order_id)
 │         ├── order_status_history (one-to-many via order_id)
 │         ├── driver_assignments (one-to-many via order_id)
 │         ├── delivery_tracking (one-to-one via order_id)
 │         ├── tracking_tokens (one-to-one via order_id)
 │         ├── financial_transactions (one-to-many via related_order_id)
 │         └── support_tickets (one-to-many via order_id)
 │
 └── drivers (one-to-one via user_id)
      ├── driver_assignments (one-to-many via driver_id)
      └── delivery_tracking (one-to-many via driver_id)
```

---

## Complete Schema

```sql
-- ============================================================
-- USERS (Base Identity Table)
-- ============================================================

CREATE TABLE users (
    id            SERIAL PRIMARY KEY,
    email         VARCHAR(255) UNIQUE NOT NULL,
    phone         VARCHAR(20)  UNIQUE NOT NULL,
    password_hash VARCHAR(255)        NOT NULL,
    role          VARCHAR(50)         NOT NULL,
    status        VARCHAR(50)         NOT NULL DEFAULT 'pending',
    created_at    TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT users_role_check   CHECK (role   IN ('merchant', 'driver', 'admin')),
    CONSTRAINT users_status_check CHECK (status IN ('pending', 'approved', 'suspended', 'rejected'))
);

CREATE INDEX idx_users_email  ON users(email);
CREATE INDEX idx_users_phone  ON users(phone);
CREATE INDEX idx_users_role   ON users(role);
CREATE INDEX idx_users_status ON users(status);


-- ============================================================
-- USER SESSIONS (refresh token storage)
--
-- Stores one record per active refresh token.
-- The raw token is NEVER stored here. Only a SHA-256 hex digest
-- (CHAR(64)) of the token is stored. The plaintext token is returned
-- to the client once at issuance and never held server-side.
-- SHA-256 is used (not bcrypt) so the session can be located by:
--   WHERE token_hash = encode(sha256(incoming_token::bytea), 'hex')
--
-- Token rotation: on each refresh the old record is deleted
-- (or revoked_at set) and a new record is inserted.
-- New login: all existing rows for the user are deleted,
-- invalidating all prior sessions on all devices.
-- ============================================================

CREATE TABLE user_sessions (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER      NOT NULL
                            REFERENCES users(id) ON DELETE CASCADE,

    -- SHA-256 hex digest of the refresh token (CHAR(64), always exactly 64 chars).
    -- SHA-256 is used here (not bcrypt) because the token is a 256-bit random
    -- string — there is no password-cracking risk — and the deterministic digest
    -- is required so the application can look up the session with:
    --   WHERE token_hash = encode(sha256(incoming_token::bytea), 'hex')
    -- Bcrypt's per-hash random salt would make that lookup impossible.
    -- The plaintext token is returned to the client at issuance only and is
    -- never persisted server-side.
    token_hash          CHAR(64) NOT NULL UNIQUE,

    -- Lifecycle timestamps
    created_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at          TIMESTAMP    NOT NULL,          -- created_at + 7 days
    last_used_at        TIMESTAMP,                      -- updated on each successful refresh
    revoked_at          TIMESTAMP,                      -- set on logout or forced revocation

    -- Audit / forensics
    created_ip          VARCHAR(45),                    -- IP that created this session
    user_agent          TEXT,                           -- browser / client fingerprint

    CONSTRAINT us_token_not_empty CHECK (token_hash != ''),
    CONSTRAINT us_expires_after_created CHECK (expires_at > created_at)
);

-- Fast lookup by user to enumerate or revoke all sessions
CREATE INDEX idx_us_user_id    ON user_sessions(user_id);
-- Fast lookup by token hash for the refresh flow
CREATE INDEX idx_us_token_hash ON user_sessions(token_hash);
-- Efficiently find and clean up expired sessions
CREATE INDEX idx_us_expires_at ON user_sessions(expires_at);


-- ============================================================
-- MERCHANTS
-- ============================================================

CREATE TABLE merchants (
    id                           SERIAL PRIMARY KEY,
    user_id                      INTEGER      UNIQUE NOT NULL
                                     REFERENCES users(id) ON DELETE CASCADE,
    business_name                VARCHAR(255) NOT NULL,
    business_phone               VARCHAR(20)  NOT NULL,
    address_line1                VARCHAR(255) NOT NULL,
    address_line2                VARCHAR(255),
    city                         VARCHAR(100) NOT NULL DEFAULT 'Alexandria',
    postal_code                  VARCHAR(10),
    business_registration_number VARCHAR(50)  UNIQUE,
    tax_id                       VARCHAR(100),           -- stored encrypted
    contact_person_name          VARCHAR(255) NOT NULL,

    -- Denormalised DISPLAY stats (recalculated daily — see ADR-005).
    -- These columns are for dashboard display ONLY.
    -- NEVER use them to resolve financial disputes or produce invoices.
    -- For any financial calculation, query financial_transactions directly.
    --
    -- total_delivery_fees_egp  : sum of delivery_fee_egp for all delivered orders
    --                            (what the merchant was charged in total)
    -- total_platform_commission_egp : sum of 'order_commission' transactions
    --                            (what WASL retained — amounts are configurable assumptions,
    --                            see BUSINESS_MODEL.md)
    -- Both figures are stale by up to 24 hours.
    total_orders                  INTEGER        NOT NULL DEFAULT 0,
    total_delivery_fees_egp       DECIMAL(12, 2) NOT NULL DEFAULT 0,
    total_platform_commission_egp DECIMAL(12, 2) NOT NULL DEFAULT 0,
    average_rating                DECIMAL(3, 2)  NOT NULL DEFAULT 0,

    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,

    CONSTRAINT merchants_positive_orders      CHECK (total_orders                  >= 0),
    CONSTRAINT merchants_positive_fees        CHECK (total_delivery_fees_egp       >= 0),
    CONSTRAINT merchants_positive_commission  CHECK (total_platform_commission_egp >= 0),
    CONSTRAINT merchants_valid_rating         CHECK (average_rating BETWEEN 0 AND 5)
);

CREATE INDEX idx_merchants_user_id       ON merchants(user_id);
CREATE INDEX idx_merchants_business_name ON merchants(business_name);


-- ============================================================
-- DRIVERS
-- ============================================================

CREATE TABLE drivers (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER     UNIQUE NOT NULL
                            REFERENCES users(id) ON DELETE CASCADE,
    full_name           VARCHAR(255) NOT NULL,
    national_id_number  VARCHAR(100) NOT NULL UNIQUE,  -- stored encrypted
    vehicle_type        VARCHAR(50)  NOT NULL,
    vehicle_plate_number VARCHAR(50),
    license_expiry      DATE,

    -- Current operational state
    is_online      BOOLEAN NOT NULL DEFAULT FALSE,
    is_on_delivery BOOLEAN NOT NULL DEFAULT FALSE,

    -- Denormalised stats (recalculated daily — see ADR-005)
    total_deliveries   INTEGER        NOT NULL DEFAULT 0,
    total_earnings_egp DECIMAL(12, 2) NOT NULL DEFAULT 0,
    average_rating     DECIMAL(3, 2)  NOT NULL DEFAULT 0,
    cancellation_rate  DECIMAL(5, 4)  NOT NULL DEFAULT 0,

    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,

    CONSTRAINT drivers_vehicle_check       CHECK (vehicle_type IN ('motorcycle', 'car', 'van')),
    CONSTRAINT drivers_positive_deliveries CHECK (total_deliveries   >= 0),
    CONSTRAINT drivers_positive_earnings   CHECK (total_earnings_egp >= 0),
    CONSTRAINT drivers_valid_rating        CHECK (average_rating BETWEEN 0 AND 5),
    CONSTRAINT drivers_valid_cancel_rate   CHECK (cancellation_rate BETWEEN 0 AND 1)
);

CREATE INDEX idx_drivers_user_id       ON drivers(user_id);
CREATE INDEX idx_drivers_is_online     ON drivers(is_online);
CREATE INDEX idx_drivers_is_on_delivery ON drivers(is_on_delivery);


-- ============================================================
-- ORDERS
-- ============================================================

CREATE TABLE orders (
    id            SERIAL PRIMARY KEY,
    merchant_id   INTEGER        NOT NULL REFERENCES merchants(id) ON DELETE RESTRICT,
    order_number  VARCHAR(50)    UNIQUE NOT NULL,   -- WAS-YYYYMMDD-NNN

    -- Customer info (no account required)
    customer_name  VARCHAR(255) NOT NULL,
    customer_phone VARCHAR(20)  NOT NULL,
    customer_email VARCHAR(255),

    -- Addresses
    pickup_address_line1    VARCHAR(255) NOT NULL,
    pickup_address_line2    VARCHAR(255),
    delivery_address_line1  VARCHAR(255) NOT NULL,
    delivery_address_line2  VARCHAR(255),
    delivery_city           VARCHAR(100) NOT NULL DEFAULT 'Alexandria',
    delivery_notes          TEXT,

    -- Financials (in EGP)
    subtotal_egp    DECIMAL(12, 2) NOT NULL,
    delivery_fee_egp DECIMAL(12, 2) NOT NULL,
    total_egp       DECIMAL(12, 2) NOT NULL,

    -- Status
    status          VARCHAR(50) NOT NULL DEFAULT 'pending',
    payment_method  VARCHAR(50) NOT NULL DEFAULT 'cash',
    payment_status  VARCHAR(50) NOT NULL DEFAULT 'pending',

    -- Assignment
    assigned_driver_id INTEGER REFERENCES drivers(id) ON DELETE SET NULL,

    -- Timestamps
    created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    scheduled_pickup_at  TIMESTAMP,
    actual_pickup_at     TIMESTAMP,
    estimated_delivery_at TIMESTAMP,
    actual_delivery_at   TIMESTAMP,

    -- Customer rating (post-delivery)
    customer_rating  SMALLINT,

    CONSTRAINT orders_status_check
        CHECK (status IN ('pending', 'assigned', 'picked_up', 'in_transit', 'delivered', 'cancelled')),
    CONSTRAINT orders_payment_method_check
        CHECK (payment_method IN ('cash')),
    CONSTRAINT orders_payment_status_check
        CHECK (payment_status IN ('pending', 'collected', 'settled')),
    CONSTRAINT orders_positive_subtotal
        CHECK (subtotal_egp >= 0),
    CONSTRAINT orders_positive_fee
        CHECK (delivery_fee_egp > 0),
    CONSTRAINT orders_positive_total
        CHECK (total_egp > 0),
    CONSTRAINT orders_valid_rating
        CHECK (customer_rating IS NULL OR customer_rating BETWEEN 1 AND 5)
);

CREATE INDEX idx_orders_merchant_id        ON orders(merchant_id);
CREATE INDEX idx_orders_assigned_driver_id ON orders(assigned_driver_id);
CREATE INDEX idx_orders_status             ON orders(status);
CREATE INDEX idx_orders_created_at         ON orders(created_at);
CREATE INDEX idx_orders_order_number       ON orders(order_number);
CREATE INDEX idx_orders_payment_status     ON orders(payment_status);


-- ============================================================
-- ORDER ITEMS
-- ============================================================

CREATE TABLE order_items (
    id             SERIAL PRIMARY KEY,
    order_id       INTEGER        NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    item_name      VARCHAR(255)   NOT NULL,
    quantity       INTEGER        NOT NULL DEFAULT 1,
    unit_price_egp DECIMAL(12, 2) NOT NULL,
    subtotal_egp   DECIMAL(12, 2) NOT NULL,

    CONSTRAINT order_items_positive_qty      CHECK (quantity      >  0),
    CONSTRAINT order_items_positive_price    CHECK (unit_price_egp > 0),
    CONSTRAINT order_items_positive_subtotal CHECK (subtotal_egp   >= 0)
);

CREATE INDEX idx_order_items_order_id ON order_items(order_id);


-- ============================================================
-- ORDER STATUS HISTORY (immutable audit trail)
-- ============================================================

CREATE TABLE order_status_history (
    id                SERIAL PRIMARY KEY,
    order_id          INTEGER     NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    previous_status   VARCHAR(50),
    new_status        VARCHAR(50) NOT NULL,
    changed_by_user_id INTEGER    REFERENCES users(id) ON DELETE SET NULL,
    reason            TEXT,
    created_at        TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT osh_new_status_check
        CHECK (new_status IN ('pending', 'assigned', 'picked_up', 'in_transit', 'delivered', 'cancelled'))
);

CREATE INDEX idx_osh_order_id   ON order_status_history(order_id);
CREATE INDEX idx_osh_created_at ON order_status_history(created_at);


-- ============================================================
-- DRIVER ASSIGNMENTS
-- ============================================================

CREATE TABLE driver_assignments (
    id                  SERIAL PRIMARY KEY,
    order_id            INTEGER     NOT NULL REFERENCES orders(id)    ON DELETE CASCADE,
    driver_id           INTEGER     NOT NULL REFERENCES drivers(id)   ON DELETE RESTRICT,
    assigned_by_user_id INTEGER     NOT NULL REFERENCES users(id)     ON DELETE SET NULL,
    assignment_status   VARCHAR(50) NOT NULL DEFAULT 'assigned',
    assigned_at         TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    accepted_at         TIMESTAMP,
    rejected_at         TIMESTAMP,
    rejection_reason    TEXT,

    CONSTRAINT da_status_check
        CHECK (assignment_status IN ('assigned', 'accepted', 'rejected', 'cancelled'))
);

CREATE INDEX idx_da_order_id  ON driver_assignments(order_id);
CREATE INDEX idx_da_driver_id ON driver_assignments(driver_id);
CREATE INDEX idx_da_status    ON driver_assignments(assignment_status);


-- ============================================================
-- DELIVERY TRACKING
-- ============================================================

CREATE TABLE delivery_tracking (
    id                      SERIAL PRIMARY KEY,
    order_id                INTEGER NOT NULL UNIQUE REFERENCES orders(id)  ON DELETE CASCADE,
    driver_id               INTEGER NOT NULL        REFERENCES drivers(id) ON DELETE RESTRICT,

    estimated_pickup_time   TIMESTAMP,
    actual_pickup_time      TIMESTAMP,
    estimated_delivery_time TIMESTAMP,
    actual_delivery_time    TIMESTAMP,

    pickup_photo_url        VARCHAR(500),
    delivery_photo_url      VARCHAR(500),
    delivery_notes          TEXT,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dt_order_id  ON delivery_tracking(order_id);
CREATE INDEX idx_dt_driver_id ON delivery_tracking(driver_id);


-- ============================================================
-- TRACKING TOKENS (public order links)
-- ============================================================

CREATE TABLE tracking_tokens (
    id           SERIAL PRIMARY KEY,
    order_id     INTEGER      NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    token        VARCHAR(255) UNIQUE NOT NULL,
    created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at   TIMESTAMP    NOT NULL,
    accessed_at  TIMESTAMP,
    access_count INTEGER      NOT NULL DEFAULT 0,

    CONSTRAINT tt_token_not_empty  CHECK (token        != ''),
    CONSTRAINT tt_positive_count   CHECK (access_count >= 0)
);

CREATE INDEX idx_tt_order_id   ON tracking_tokens(order_id);
CREATE INDEX idx_tt_token      ON tracking_tokens(token);
CREATE INDEX idx_tt_expires_at ON tracking_tokens(expires_at);


-- ============================================================
-- FINANCIAL TRANSACTIONS (immutable audit ledger)
-- ============================================================

CREATE TABLE financial_transactions (
    id                  SERIAL PRIMARY KEY,
    transaction_type    VARCHAR(50)    NOT NULL,
    related_order_id    INTEGER        REFERENCES orders(id)    ON DELETE SET NULL,
    related_driver_id   INTEGER        REFERENCES drivers(id)   ON DELETE SET NULL,
    related_merchant_id INTEGER        REFERENCES merchants(id) ON DELETE SET NULL,
    amount_egp          DECIMAL(12, 2) NOT NULL,
    status              VARCHAR(50)    NOT NULL DEFAULT 'pending',
    notes               TEXT,
    created_at          TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at        TIMESTAMP,

    CONSTRAINT ft_type_check
        CHECK (transaction_type IN ('order_commission', 'driver_payout', 'merchant_settlement', 'refund')),
    CONSTRAINT ft_status_check
        CHECK (status IN ('pending', 'completed', 'failed')),
    CONSTRAINT ft_positive_amount
        CHECK (amount_egp >= 0)
);

CREATE INDEX idx_ft_type        ON financial_transactions(transaction_type);
CREATE INDEX idx_ft_status      ON financial_transactions(status);
CREATE INDEX idx_ft_created_at  ON financial_transactions(created_at);
CREATE INDEX idx_ft_order_id    ON financial_transactions(related_order_id);
CREATE INDEX idx_ft_driver_id   ON financial_transactions(related_driver_id);
CREATE INDEX idx_ft_merchant_id ON financial_transactions(related_merchant_id);


-- ============================================================
-- SETTLEMENT RECORDS
-- ============================================================

CREATE TABLE settlement_records (
    id               SERIAL PRIMARY KEY,
    settlement_type  VARCHAR(50)    NOT NULL,
    recipient_id     INTEGER        NOT NULL,    -- merchant_id or driver_id
    period_start     DATE           NOT NULL,
    period_end       DATE           NOT NULL,
    total_amount_egp DECIMAL(12, 2) NOT NULL,
    commissions_egp  DECIMAL(12, 2),
    fees_egp         DECIMAL(12, 2),
    refunds_egp      DECIMAL(12, 2),
    status           VARCHAR(50)    NOT NULL DEFAULT 'pending',
    created_at       TIMESTAMP      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at     TIMESTAMP,

    CONSTRAINT sr_type_check
        CHECK (settlement_type IN ('merchant', 'driver')),
    CONSTRAINT sr_status_check
        CHECK (status IN ('pending', 'processed', 'completed', 'failed')),
    CONSTRAINT sr_valid_period
        CHECK (period_end >= period_start)
);

CREATE INDEX idx_sr_type         ON settlement_records(settlement_type);
CREATE INDEX idx_sr_recipient_id ON settlement_records(recipient_id);
CREATE INDEX idx_sr_status       ON settlement_records(status);
CREATE INDEX idx_sr_period       ON settlement_records(period_start, period_end);


-- ============================================================
-- AUDIT LOGS (immutable — no updates or deletes permitted)
-- ============================================================

CREATE TABLE audit_logs (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    action       VARCHAR(255) NOT NULL,
    entity_type  VARCHAR(100) NOT NULL,
    entity_id    INTEGER,
    old_values   JSONB,
    new_values   JSONB,
    ip_address   VARCHAR(45),
    user_agent   TEXT,
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_al_user_id    ON audit_logs(user_id);
CREATE INDEX idx_al_entity     ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_al_action     ON audit_logs(action);
CREATE INDEX idx_al_created_at ON audit_logs(created_at);


-- ============================================================
-- SUPPORT TICKETS
-- ============================================================

CREATE TABLE support_tickets (
    id                   SERIAL PRIMARY KEY,
    order_id             INTEGER      NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    created_by_user_id   INTEGER      NOT NULL REFERENCES users(id)  ON DELETE SET NULL,
    subject              VARCHAR(255) NOT NULL,
    description          TEXT         NOT NULL,
    ticket_type          VARCHAR(50)  NOT NULL,
    status               VARCHAR(50)  NOT NULL DEFAULT 'open',
    assigned_to_user_id  INTEGER      REFERENCES users(id) ON DELETE SET NULL,
    resolution_notes     TEXT,
    created_at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at          TIMESTAMP,

    CONSTRAINT st_type_check
        CHECK (ticket_type IN ('payment', 'delivery', 'damage', 'other')),
    CONSTRAINT st_status_check
        CHECK (status IN ('open', 'in_progress', 'resolved', 'closed'))
);

CREATE INDEX idx_st_order_id   ON support_tickets(order_id);
CREATE INDEX idx_st_status     ON support_tickets(status);
CREATE INDEX idx_st_created_at ON support_tickets(created_at);
```

---

## Foreign Key Deletion Rules

| Relationship | Rule | Rationale |
|---|---|---|
| `user_sessions.user_id → users.id` | CASCADE | Delete all sessions when user deleted |
| `merchants.user_id → users.id` | CASCADE | Delete merchant profile when user deleted |
| `drivers.user_id → users.id` | CASCADE | Delete driver profile when user deleted |
| `orders.merchant_id → merchants.id` | RESTRICT | Cannot delete merchant with orders |
| `orders.assigned_driver_id → drivers.id` | SET NULL | Driver deleted; order becomes unassigned |
| `order_items.order_id → orders.id` | CASCADE | Items have no meaning without parent order |
| `order_status_history.order_id → orders.id` | CASCADE | History follows order lifecycle |
| `driver_assignments.order_id → orders.id` | CASCADE | Assignments follow order lifecycle |
| `driver_assignments.driver_id → drivers.id` | RESTRICT | Preserve assignment history |
| `financial_transactions.related_order_id` | SET NULL | Preserve financial records even if order deleted |
| `audit_logs.user_id → users.id` | SET NULL | Preserve logs even if user deleted |

---

## Financial Audit Trail

### How Records Are Created

```
Order delivered (status → 'delivered')
  │
  ├── financial_transactions INSERT:
  │     type = 'order_commission'
  │     amount_egp = [platform_commission_egp]   ← assumed — see BUSINESS_MODEL.md
  │     related_order_id = order.id
  │     related_merchant_id = order.merchant_id
  │     status = 'pending'
  │
  └── financial_transactions INSERT:
        type = 'driver_payout'
        amount_egp = [driver_payout_egp]          ← assumed — see BUSINESS_MODEL.md
        related_order_id = order.id
        related_driver_id = order.assigned_driver_id
        status = 'pending'

Weekly settlement (admin-triggered)
  │
  └── settlement_records INSERT:
        settlement_type = 'driver'
        recipient_id = driver_id
        period_start / period_end
        total_amount_egp = SUM(driver_payout transactions for period)
        status = 'pending'
        → admin marks 'completed' after payment
```

### Authoritative Financial Metric Queries

> **Rule**: These queries are the source of truth for any financial figure.
> Dashboard display columns (`total_delivery_fees_egp`, `total_platform_commission_egp`)
> are derived from these queries but may be up to 24 hours stale.
> Always run these queries directly for dispute resolution, invoicing, or reconciliation.

#### Merchant: Total Delivery Fees Paid (what the merchant was charged)

```sql
-- Total delivery fees billed to a specific merchant
-- across all their delivered orders in a given period.
SELECT
    merchant_id,
    COUNT(*)                   AS delivered_orders,
    SUM(delivery_fee_egp)      AS total_delivery_fees_egp
FROM orders
WHERE merchant_id = :merchant_id
  AND status      = 'delivered'
  AND actual_delivery_at >= :period_start
  AND actual_delivery_at <  :period_end
GROUP BY merchant_id;
```

#### Merchant: Platform Commission Retained by WASL

```sql
-- Total platform commission WASL retained from a specific merchant's orders.
-- The commission amount per order is stored in financial_transactions
-- at the time of delivery — it is NOT recalculated from a rate.
-- This preserves historical accuracy even if rates change in future.
SELECT
    ft.related_merchant_id   AS merchant_id,
    COUNT(*)                 AS commission_records,
    SUM(ft.amount_egp)       AS total_platform_commission_egp
FROM financial_transactions ft
WHERE ft.transaction_type    = 'order_commission'
  AND ft.related_merchant_id = :merchant_id
  AND ft.created_at         >= :period_start
  AND ft.created_at          < :period_end
GROUP BY ft.related_merchant_id;
```

#### Driver: Total Earnings

```sql
-- Total payout earned by a specific driver in a given period.
SELECT
    ft.related_driver_id   AS driver_id,
    COUNT(*)               AS delivery_count,
    SUM(ft.amount_egp)     AS total_earnings_egp
FROM financial_transactions ft
WHERE ft.transaction_type  = 'driver_payout'
  AND ft.related_driver_id = :driver_id
  AND ft.created_at       >= :period_start
  AND ft.created_at        < :period_end
GROUP BY ft.related_driver_id;
```

### Reconciliation Query

```sql
-- Verify settlement totals match transaction records
SELECT
    ft.transaction_type,
    COUNT(*)             AS transaction_count,
    SUM(ft.amount_egp)   AS total_amount_egp
FROM financial_transactions ft
WHERE ft.status     = 'completed'
  AND ft.created_at >= '2024-01-01'
  AND ft.created_at <  '2024-01-08'
GROUP BY ft.transaction_type;
```

---

## Index Strategy Summary

| Column(s) | Purpose |
|-----------|---------|
| `users.email`, `users.phone` | Fast login lookup |
| `user_sessions.token_hash` | Refresh token validation |
| `user_sessions.user_id` | Enumerate or revoke all sessions for a user |
| `user_sessions.expires_at` | Clean up expired sessions |
| `orders.merchant_id` | Merchant order list |
| `orders.assigned_driver_id` | Driver task list |
| `orders.status` | Filter by status |
| `orders.created_at` | Date-range queries |
| `financial_transactions.related_order_id` | Transactions per order |
| `financial_transactions.related_merchant_id` | Commission records per merchant |
| `financial_transactions.related_driver_id` | Payout records per driver |
| `audit_logs.user_id`, `audit_logs.action` | Audit queries |
| `tracking_tokens.token` | Public tracking validation |
| `tracking_tokens.expires_at` | Expiry cleanup |

---

## Migration Strategy

Migrations managed by **Alembic** (Python, consistent with FastAPI ecosystem).

```
backend/
└── migrations/
    ├── env.py
    ├── alembic.ini
    └── versions/
        ├── 0001_initial_schema.py
        ├── 0002_add_indexes.py
        └── 0003_add_constraints.py
```

Migrations run automatically on application startup in development.
In production, migrations are run explicitly before deployment.

---

## Assumptions

- All EGP financial amounts use 2 decimal precision (DECIMAL(12,2)).
- `delivery_fee_egp` default value (15 EGP) is an assumption — see [BUSINESS_MODEL.md](./BUSINESS_MODEL.md).
- Commission amounts recorded in `financial_transactions` are based on unverified business model assumptions — see [BUSINESS_MODEL.md](./BUSINESS_MODEL.md).
- Stats recalculation frequency (daily) is an assumption; actual performance requirement not yet tested.
- `total_delivery_fees_egp` and `total_platform_commission_egp` in the `merchants` table are **display-only** denormalised caches. They must never be used as authoritative financial figures. Use the queries in the Financial Audit Trail section for any financial calculation.
- `user_sessions.token_hash` stores a SHA-256 hex digest (`CHAR(64)`) of the refresh token. SHA-256 is used (not bcrypt) because the token is a 256-bit cryptographically random string with no password-cracking risk, and the deterministic digest is required to look up a session by incoming token. The plaintext token is returned to the client at issuance only and is never persisted server-side.
