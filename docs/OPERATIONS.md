# WASL Operations Runbook

> ⚠ **ASSUMPTION NOTICE**: This runbook describes operational procedures based on the approved
> architecture. All procedures should be tested in staging before being relied upon in production.
> Specific commands may need adjustment once the application is built and deployed.

---

## Overview

This document covers day-to-day operational procedures for running the WASL platform after MVP launch.

**Intended audience**: Platform administrator (solo operator in MVP phase)

---

## 1. Daily Operations

### Morning Checklist (daily, ~15 minutes)

- [ ] Check uptime monitor for overnight alerts
- [ ] Review Sentry error dashboard for new or recurring errors
- [ ] Check pending merchant approval queue (approve or reject within 24 hours)
- [ ] Check pending driver approval queue
- [ ] Review unassigned orders older than 2 hours
- [ ] Verify database is accessible (check Railway/Supabase dashboard)

### Operational Dashboard URLs (to be configured)

| Resource | URL |
|----------|-----|
| Admin dashboard | https://admin.wasl.eg |
| Sentry errors | https://sentry.io/organizations/wasl/ |
| Railway status | https://railway.app |
| Supabase dashboard | https://app.supabase.com |
| Vercel deployments | https://vercel.com/dashboard |
| Uptime monitor | [configure on UptimeRobot or similar] |

---

## 2. User Approval Workflow

### Approving a Merchant

1. Log in to admin dashboard
2. Go to **Merchants → Pending**
3. Review submitted information:
   - Business name and registration number
   - Contact person name and phone
   - Address in Alexandria
4. If valid: click **Approve** (optionally add approval notes)
5. If invalid or suspicious: click **Reject** with a clear reason
6. Decision is logged automatically in audit_logs

**Approval checklist** (informal — no automated verification in MVP):
- [ ] Business name is not suspicious or duplicate
- [ ] Phone number is valid Egyptian format
- [ ] Address appears to be in Alexandria
- [ ] No duplicate registration number already in system

### Approving a Driver

1. Go to **Drivers → Pending**
2. Review submitted information:
   - Full name
   - Vehicle type and plate number
   - License expiry date
3. If valid: click **Approve**
4. If license expired or information incomplete: click **Reject** with reason

> In MVP, document verification is manual. Admin uses judgment based on provided information.
> Automated document scanning is deferred to a future phase.

---

## 3. Order Assignment Workflow

### Daily Assignment Process

1. Go to **Admin → Orders → Pending Assignment**
2. Review unassigned orders (sorted by creation time, oldest first)
3. For each order:
   a. Check delivery address (Alexandria zone)
   b. Go to **Drivers → Online** to see available drivers
   c. Select a driver (consider proximity to pickup address, current load)
   d. Click **Assign to Driver**
4. Driver will see the task on their next task list refresh (polling interval)

### Reassigning an Order

If a driver rejects an assignment or cannot be reached:

1. Go to **Orders → {order_id}**
2. Click **Reassign**
3. Select a different driver
4. Enter reason for reassignment (e.g., "Driver rejected — unavailable")
5. Assignment history is preserved in `driver_assignments`

### Cancelling an Order

If an order cannot be fulfilled:

1. Go to **Orders → {order_id}**
2. Click **Cancel Order**
3. Enter cancellation reason
4. Notify merchant (currently manual — email or phone call)
5. Status history updated automatically

---

## 4. Weekly Settlement Process

Run every **Sunday** for the previous Monday–Sunday period.

### Driver Settlements (run every Friday before week end)

1. Go to **Admin → Settlements → Create Driver Settlement**
2. Select period (e.g., 2024-01-08 to 2024-01-14)
3. System calculates total from `financial_transactions` (type = `driver_payout`, period, status = `pending`)
4. Review totals per driver
5. Arrange cash or bank transfer payment to each driver
6. After payment confirmed: click **Mark as Completed** with notes
7. Settlement status changes to `completed`; transactions updated to `completed`

### Merchant Settlements (run every Sunday)

1. Go to **Admin → Settlements → Create Merchant Settlement**
2. Select period
3. System calculates total commission owed by each merchant
4. Generate invoice (currently manual — export from dashboard)
5. Contact merchant for payment (bank transfer or cash)
6. After payment received: click **Mark as Completed**

### Reconciliation Verification

Before marking any settlement complete:

```sql
-- Verify settlement total matches transaction sum (run in Supabase SQL editor or psql)
SELECT
    related_driver_id,
    COUNT(*)           AS transaction_count,
    SUM(amount_egp)    AS total_egp
FROM financial_transactions
WHERE transaction_type = 'driver_payout'
  AND status           = 'pending'
  AND created_at BETWEEN '2024-01-08' AND '2024-01-15'
GROUP BY related_driver_id;
```

If totals do not match the settlement record: investigate before processing. Do not mark complete if discrepancy exists.

---

## 5. Monitoring & Alerting

### What to Monitor

| Metric | Alert Threshold | Action |
|--------|----------------|--------|
| API health check fails | 2+ consecutive failures | Investigate immediately |
| Sentry error rate spike | > 10 errors/hour (new) | Review and triage |
| Database connections maxed | > 80% of limit | Investigate queries |
| Unassigned orders | Older than 2 hours | Assign manually |
| Driver rejection rate | > 20% in a day | Investigate driver supply |

### Checking Application Logs

**Railway (backend)**:
1. Go to Railway dashboard → your service
2. Click **Logs** tab
3. Filter by severity: ERROR, WARNING

**Vercel (frontend)**:
1. Go to Vercel dashboard → project
2. Click **Functions** tab for API route logs

### Checking Audit Logs

Via admin dashboard:
- Go to **Admin → Audit Logs**
- Filter by action, user, or date range
- All sensitive actions are logged with user_id and timestamp

Via database (for detailed investigation):

```sql
-- Recent admin actions
SELECT action, entity_type, entity_id, created_at
FROM audit_logs
WHERE user_id = [admin_user_id]
ORDER BY created_at DESC
LIMIT 50;
```

---

## 6. Incident Response

### Severity Classification

| Level | Definition | Response Time |
|-------|-----------|---------------|
| P1 — Critical | Platform down, no orders can be created | Immediate |
| P2 — High | Major feature broken (e.g., drivers cannot update status) | < 1 hour |
| P3 — Medium | Minor feature broken, workaround exists | < 4 hours |
| P4 — Low | Cosmetic or edge-case issue | Next deployment |

### P1 Response: Platform Down

1. Check uptime monitor for alert details
2. Check Railway/Vercel dashboard for deployment status
3. Check database connectivity:
   ```bash
   psql $DATABASE_URL -c "SELECT 1"
   ```
4. If recent deployment: initiate rollback (see `DEPLOYMENT.md`)
5. If database issue: check Railway/Supabase status page
6. Once resolved: document what happened and why in incident log

### P1 Response: Security Incident

If unauthorised access or data breach suspected:

1. **Immediately**: Rotate `JWT_SECRET_KEY` in Railway environment variables
   - This invalidates all active sessions
   - All users must log in again
2. **Immediately**: Rotate `ENCRYPTION_KEY` if compromise suspected
   - Warning: encrypted fields must be re-encrypted with new key — plan carefully
3. Review `audit_logs` for suspicious activity:
   ```sql
   SELECT * FROM audit_logs
   WHERE created_at > NOW() - INTERVAL '24 hours'
   ORDER BY created_at DESC;
   ```
4. Identify affected users and notify if required
5. Document incident with timeline

### P2 Response: Feature Broken

1. Reproduce the issue in staging
2. Check Sentry for error details
3. If fix available: deploy via standard process
4. If not: communicate to affected merchants/drivers via phone/WhatsApp

---

## 7. Database Maintenance

### Viewing Database Health

```sql
-- Table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC;

-- Active connections
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';

-- Long-running queries (> 30 seconds)
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '30 seconds'
  AND state != 'idle';
```

### Cleaning Up Expired Tracking Tokens

Run weekly to keep the `tracking_tokens` table clean:

```sql
DELETE FROM tracking_tokens
WHERE expires_at < NOW() - INTERVAL '7 days';
```

> Consider automating this as a scheduled task once background jobs are introduced.

### Recalculating Denormalised Stats

Run daily (or on demand if stats appear incorrect):

```sql
-- Recalculate merchant stats
UPDATE merchants SET
    total_orders                  = (
        SELECT COUNT(*) FROM orders
        WHERE merchant_id = merchants.id AND status = 'delivered'
    ),
    total_delivery_fees_egp       = (
        SELECT COALESCE(SUM(delivery_fee_egp), 0) FROM orders
        WHERE merchant_id = merchants.id AND status = 'delivered'
    ),
    total_platform_commission_egp = (
        SELECT COALESCE(SUM(ft.amount_egp), 0)
        FROM financial_transactions ft
        WHERE ft.related_merchant_id = merchants.id
          AND ft.transaction_type    = 'order_commission'
    );

-- Recalculate driver stats
UPDATE drivers SET
    total_deliveries   = (
        SELECT COUNT(*) FROM orders
        WHERE assigned_driver_id = drivers.id AND status = 'delivered'
    ),
    total_earnings_egp = (
        SELECT COALESCE(SUM(amount_egp), 0)
        FROM financial_transactions
        WHERE related_driver_id = drivers.id
          AND transaction_type  = 'driver_payout'
          AND status            = 'completed'
    );
```

---

## 8. User Management

### Creating an Admin Account

Admin accounts are not self-registered. Create via database or admin CLI:

```sql
-- Insert user (replace values)
INSERT INTO users (email, phone, password_hash, role, status)
VALUES (
    'admin@wasl.eg',
    '01000000000',
    '[bcrypt hash — generate separately]',
    'admin',
    'approved'
);
```

To generate a bcrypt hash:
```python
import bcrypt
password = b"SecureAdminPassword1!"
hashed = bcrypt.hashpw(password, bcrypt.gensalt(rounds=12))
print(hashed.decode())
```

### Suspending a User

```sql
-- Suspend a merchant or driver
UPDATE users SET status = 'suspended' WHERE id = [user_id];
```

Suspended users receive 403 on login. This does not delete their data.

### Deleting a User (GDPR / Data Request)

Only delete when legally required or explicitly requested:

```sql
-- This will cascade-delete merchant or driver profile
-- Orders with this merchant are RESTRICTED from deletion (ON DELETE RESTRICT)
-- Resolve all active orders first

-- Step 1: Verify no active orders
SELECT COUNT(*) FROM orders
WHERE merchant_id = [merchant_id] AND status NOT IN ('delivered', 'cancelled');

-- Step 2: If zero active orders, delete user
DELETE FROM users WHERE id = [user_id];
```

> Document all deletion requests and actions in a separate log outside the database.

---

## 9. Support & Dispute Resolution

### Handling a Merchant Complaint

1. Go to **Support Tickets** (or receive via WhatsApp/phone in MVP)
2. Identify the order in question
3. Review `order_status_history` for full timeline
4. Review `driver_assignments` for assignment history
5. Review `financial_transactions` for payment records
6. Determine resolution:
   - Refund commission: create a `refund` financial_transaction record
   - Re-deliver: create new order or manually reassign
7. Close ticket with resolution notes

### Handling a Driver Earnings Dispute

1. Identify the disputed period and driver
2. Run the reconciliation query from Section 4
3. Compare driver's claimed deliveries against `orders` table
4. If discrepancy found: create correcting `financial_transaction` record
5. Document correction in settlement notes

---

## 10. Communication Templates

These are draft templates for communicating with merchants and drivers. Adjust before use.

### Merchant Approval Notification

> Subject: WASL — Your account has been approved
>
> Dear [Merchant Name],
>
> Your WASL merchant account has been approved. You can now log in and begin creating delivery orders.
>
> Login: https://merchant.wasl.eg
>
> If you have any questions, please contact us at [contact number].
>
> WASL Team

### Driver Rejection Notification

> Subject: WASL — Account application update
>
> Dear [Driver Name],
>
> Unfortunately, your driver application could not be approved at this time.
> Reason: [rejection reason]
>
> You may re-apply after addressing the above. Contact us at [contact number] for more information.
>
> WASL Team

---

## 11. Operational Assumptions (Unverified)

The following operational assumptions have not been validated in practice:

1. Weekly settlement cycle is operationally feasible for MVP transaction volumes
2. Manual order assignment is sustainable at < 200 orders/day
3. Audit log review can be done in < 15 minutes daily
4. Single admin is sufficient for MVP operations
5. Phone/WhatsApp is adequate for merchant/driver communication in MVP
6. Database performance at MVP scale does not require query tuning

These should be revisited after 4 weeks of live operation.
