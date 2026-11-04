# WASL 12-Week Implementation Roadmap

## Philosophy

- **Incremental delivery**: Each phase produces working, demonstrable functionality
- **Test as you build**: Tests written alongside features, not after
- **Solo-developer friendly**: Scope limited to what one developer can build and verify
- **Demoable at every milestone**: Stakeholders can review progress at each phase end
- **No premature optimisation**: Build simply first, optimise when data demands it

---

## Phase Overview

| Phase | Weeks | Focus | Milestone |
|-------|-------|-------|-----------|
| 0 | 1–2 | Setup & infrastructure | Deployable skeleton |
| 1 | 3–4 | Authentication & RBAC | Working login system |
| 2 | 5–7 | Merchant features | Merchant can create orders |
| 3 | 8–9 | Driver features | Driver can accept and complete tasks |
| 4 | 10–11 | Admin & operations | Platform is operationally manageable |
| 5 | 12 | Tracking, testing, deployment | Production-ready MVP |

---

## Phase 0: Setup & Infrastructure (Weeks 1–2)

### Task 0.1 — Repository & Project Scaffolding

**Objective**: Initialise Git repository and document-driven project structure.

**Files / Modules Affected**:
- Root folder structure (`/frontend`, `/backend`, `/docs`)
- `.gitignore`
- All documentation files (already complete)

**Dependencies**: None

**Acceptance Criteria**:
- [ ] GitHub repository initialised
- [ ] `.gitignore` excludes `.env`, `node_modules`, `__pycache__`, `venv`
- [ ] Documentation files committed and readable
- [ ] README accurately describes project status

**Testing Requirements**: N/A (documentation and config)

---

### Task 0.2 — Database Schema & Migrations Setup

**Objective**: Create PostgreSQL schema with Alembic migration tooling.

**Files / Modules Affected**:
- `/backend/migrations/` (Alembic folder)
- `/backend/models/` (SQLAlchemy model files)
- `DATABASE_DESIGN.md` (reference)

**Dependencies**: PostgreSQL instance (local or Supabase free tier)

**Acceptance Criteria**:
- [ ] Alembic configured and connected to database
- [ ] Migration `0001_initial_schema` creates all tables
- [ ] Migration `0002_add_indexes` adds all indexes
- [ ] All foreign key constraints enforced
- [ ] Schema matches `DATABASE_DESIGN.md` exactly
- [ ] Migration runs cleanly on a fresh database

**Testing Requirements**:
- Manual: Run migration on empty database, verify with `\dt` in psql
- Manual: Verify constraints reject invalid data (e.g., invalid role value)

---

### Task 0.3 — Frontend & Backend Project Bootstrap

**Objective**: Bootstrap Next.js and FastAPI projects with TypeScript, linting, and folder structure.

**Files / Modules Affected**:
- `/frontend/package.json`, `tsconfig.json`, `.eslintrc.json`
- `/frontend/pages/`, `/frontend/components/`, `/frontend/lib/`, `/frontend/styles/`
- `/backend/main.py`, `/backend/requirements.txt`, `/backend/config.py`
- `/backend/routers/`, `/backend/services/`, `/backend/models/`, `/backend/schemas/`, `/backend/middleware/`

**Dependencies**: Task 0.2

**Acceptance Criteria**:
- [ ] `npm run dev` starts Next.js without errors on port 3000
- [ ] `uvicorn main:app --reload` starts FastAPI without errors on port 8000
- [ ] Swagger docs accessible at `http://localhost:8000/docs`
- [ ] TypeScript compiles without errors
- [ ] ESLint passes with no warnings
- [ ] `.env.example` documents all required variables

**Testing Requirements**:
- Manual: Both servers start cleanly
- Manual: Visit `/docs` and see empty but valid API documentation

---

### Task 0.4 — CI/CD Pipeline (GitHub Actions)

**Objective**: Automated linting and test runner on every push.

**Files / Modules Affected**:
- `/.github/workflows/ci.yml`

**Dependencies**: Task 0.3

**Acceptance Criteria**:
- [ ] CI runs on every push and pull request
- [ ] Frontend lint step (`npm run lint`) passes
- [ ] Backend lint step (`flake8`) passes
- [ ] Test runner executes (initially passes with empty test suite)
- [ ] PR cannot be merged if CI fails

**Testing Requirements**:
- Manual: Push a branch, verify CI workflow runs in GitHub Actions

---

### Task 0.5 — Environment & Secrets Configuration

**Objective**: Document and configure all environment variables for local and staging.

**Files / Modules Affected**:
- `.env.example` (root, frontend, backend)
- `/backend/config.py`

**Dependencies**: Task 0.3

**Acceptance Criteria**:
- [ ] `.env.example` lists every required variable with placeholder values
- [ ] `.env` excluded from git via `.gitignore`
- [ ] Backend reads config from environment (not hardcoded values)
- [ ] Different configs for `development` and `production` environments

**Testing Requirements**:
- Manual: Verify app starts with `.env` populated from `.env.example`

---

## Phase 1: Authentication & Authorisation (Weeks 3–4)

### Task 1.1 — User Registration

**Objective**: Implement merchant and driver registration with validation.

**Files / Modules Affected**:
- `/backend/routers/auth.py`
- `/backend/services/user_service.py`
- `/backend/schemas/auth_schema.py`
- `/frontend/pages/register.tsx`
- `/frontend/components/RegisterForm.tsx`

**Dependencies**: Task 0.2 (users table), Task 0.3

**Acceptance Criteria**:
- [ ] `POST /api/v1/auth/register` creates user with bcrypt password hash
- [ ] Validates email format and uniqueness
- [ ] Validates phone format and uniqueness
- [ ] Validates password complexity (8+ chars, uppercase, lowercase, digit, special)
- [ ] Returns user object (no password) + status `pending`
- [ ] Duplicate email or phone returns 409 with appropriate error code
- [ ] Plain-text password never stored or returned

**Testing Requirements**:
- Unit: Password hashing (bcrypt round-trip)
- Unit: Email format validation
- Integration: Full registration flow end-to-end
- Edge cases: Duplicate email, weak password, missing fields

---

### Task 1.2 — Login & JWT Token Issuance

**Objective**: Implement login endpoint and JWT token generation.

**Files / Modules Affected**:
- `/backend/routers/auth.py`
- `/backend/services/auth_service.py`
- `/backend/security/jwt_utils.py`
- `/frontend/pages/login.tsx`
- `/frontend/lib/auth.ts`

**Dependencies**: Task 1.1

**Acceptance Criteria**:
- [ ] `POST /api/v1/auth/login` validates email/password against bcrypt hash
- [ ] Returns access token (24h) and refresh token (7d)
- [ ] JWT payload contains `user_id`, `email`, `role`, `issued_at`
- [ ] Refresh token stored in database
- [ ] 5 consecutive failures lock account for 15 minutes
- [ ] Login attempt (success and failure) written to `audit_logs`

**Testing Requirements**:
- Unit: JWT encoding and decoding
- Unit: Account lockout after 5 failures
- Integration: Login with valid/invalid credentials
- Edge cases: Expired token, missing fields

---

### Task 1.3 — JWT Middleware & Protected Routes

**Objective**: Protect all non-public endpoints with JWT validation.

**Files / Modules Affected**:
- `/backend/middleware/auth_middleware.py`
- `/backend/security/permissions.py`
- `/frontend/lib/api.ts` (attach token to requests)
- `/frontend/lib/auth.ts` (redirect on 401)

**Dependencies**: Task 1.2

**Acceptance Criteria**:
- [ ] All protected endpoints reject requests without valid token (401)
- [ ] Expired tokens return 401 with code `TOKEN_EXPIRED`
- [ ] Malformed tokens return 401 with code `TOKEN_INVALID`
- [ ] Frontend automatically includes `Authorization: Bearer` header
- [ ] Frontend redirects to `/login` on 401 response

**Testing Requirements**:
- Integration: Call protected endpoint without token (expect 401)
- Integration: Call protected endpoint with valid token (expect 200)
- Edge cases: Expired token, tampered token

---

### Task 1.4 — Role-Based Access Control

**Objective**: Enforce merchant, driver, and admin role boundaries on every endpoint.

**Files / Modules Affected**:
- `/backend/security/rbac.py`
- All routers (apply `@require_role` decorator)

**Dependencies**: Task 1.3

**Acceptance Criteria**:
- [ ] `merchant` role cannot access `/api/v1/drivers/*` or `/api/v1/admin/*`
- [ ] `driver` role cannot access `/api/v1/merchants/*` or `/api/v1/admin/*`
- [ ] `admin` role can access all endpoints
- [ ] Wrong role returns 403 with code `FORBIDDEN`
- [ ] Resource ownership checked (merchant cannot access another merchant's orders)

**Testing Requirements**:
- Integration: Each role attempts to access endpoints it should not reach
- Integration: Admin accesses all endpoint groups

---

### Task 1.5 — Token Refresh & Logout

**Objective**: Implement refresh token rotation and session invalidation.

**Files / Modules Affected**:
- `/backend/routers/auth.py`
- `/backend/models/user_session.py`
- `/frontend/lib/api.ts` (auto-refresh logic)

**Dependencies**: Task 1.3

**Acceptance Criteria**:
- [ ] `POST /api/v1/auth/refresh` issues new token pair and invalidates old refresh token
- [ ] Replayed refresh token returns 401
- [ ] `POST /api/v1/auth/logout` deletes refresh token from database
- [ ] New login invalidates all previous refresh tokens for that user
- [ ] Frontend auto-refreshes before token expiry

**Testing Requirements**:
- Integration: Refresh flow
- Edge cases: Replay attack, expired refresh token

---

## Phase 2: Merchant Features (Weeks 5–7)

### Task 2.1 — Merchant Registration & Profile

**Objective**: Merchant-specific profile creation, linked to user account.

**Files / Modules Affected**:
- `/backend/routers/merchants.py`
- `/backend/models/merchant.py`
- `/backend/services/merchant_service.py`
- `/backend/schemas/merchant_schema.py`
- `/frontend/pages/merchant/register.tsx`
- `/frontend/pages/merchant/profile.tsx`

**Dependencies**: Task 1.4

**Acceptance Criteria**:
- [ ] Merchant registration endpoint creates `merchants` record linked to `users` record
- [ ] Status defaults to `pending` (cannot use platform until approved)
- [ ] `GET /api/v1/merchants/profile` returns merchant info + stats
- [ ] `PUT /api/v1/merchants/profile` updates editable fields
- [ ] Merchant cannot update another merchant's profile (403)

**Testing Requirements**:
- Integration: Register merchant, verify pending status
- Authorization: Merchant A cannot update Merchant B's profile

---

### Task 2.2 — Order Creation

**Objective**: Merchant creates a delivery order with line items.

**Files / Modules Affected**:
- `/backend/routers/orders.py`
- `/backend/models/order.py`, `/backend/models/order_item.py`
- `/backend/services/order_service.py`
- `/backend/schemas/order_schema.py`
- `/frontend/pages/merchant/orders/create.tsx`
- `/frontend/components/OrderForm.tsx`

**Dependencies**: Task 2.1

**Acceptance Criteria**:
- [ ] `POST /api/v1/merchants/orders` creates order with items
- [ ] `order_number` generated in format `WAS-YYYYMMDD-NNN` (unique, sequential within day)
- [ ] `order_items` records created for each item
- [ ] `order_status_history` record created with status `pending`
- [ ] Tracking token generated and stored in `tracking_tokens`
- [ ] Tracking link returned in response
- [ ] Only approved merchants can create orders (403 if pending)
- [ ] Total calculated as `subtotal + delivery_fee`

**Testing Requirements**:
- Unit: Order number generation (uniqueness, format)
- Unit: Total calculation
- Integration: Full order creation with items
- Edge cases: Zero items, negative prices, missing customer phone

---

### Task 2.3 — Order List & Detail View

**Objective**: Merchant views their own orders with filtering and full detail.

**Files / Modules Affected**:
- `/backend/routers/orders.py`
- `/frontend/pages/merchant/orders/index.tsx`
- `/frontend/pages/merchant/orders/[id].tsx`
- `/frontend/components/OrderList.tsx`

**Dependencies**: Task 2.2

**Acceptance Criteria**:
- [ ] `GET /api/v1/merchants/orders` returns paginated list (limit/offset)
- [ ] Filterable by `status`
- [ ] Merchants only see their own orders
- [ ] `GET /api/v1/merchants/orders/{id}` returns order + items + status_history + driver info
- [ ] Order not found or belonging to another merchant returns 403 (not 404)

**Testing Requirements**:
- Authorization: Merchant A cannot access Merchant B's orders
- Filtering: Status filter returns correct subset

---

### Task 2.4 — Merchant Analytics

**Objective**: Simple metrics dashboard for the merchant.

**Files / Modules Affected**:
- `/backend/routers/merchants.py`
- `/backend/services/analytics_service.py`
- `/frontend/pages/merchant/analytics.tsx`

**Dependencies**: Task 2.3

**Acceptance Criteria**:
- [ ] `GET /api/v1/merchants/analytics?period=week` returns metrics
- [ ] Metrics: total_orders, total_delivery_fees_egp, total_platform_commission_egp, delivered_orders, cancelled_orders, average_rating
- [ ] Period filter: `today`, `week`, `month`
- [ ] Figures calculated from live database (no caching in MVP)

**Testing Requirements**:
- Correctness: Cross-check metrics against raw order records

---

## Phase 3: Driver Features (Weeks 8–9)

### Task 3.1 — Driver Registration & Profile

**Objective**: Driver-specific profile creation linked to user account.

**Files / Modules Affected**:
- `/backend/routers/drivers.py`
- `/backend/models/driver.py`
- `/backend/services/driver_service.py`
- `/backend/schemas/driver_schema.py`
- `/frontend/pages/driver/register.tsx`
- `/frontend/pages/driver/profile.tsx`

**Dependencies**: Task 1.4

**Acceptance Criteria**:
- [ ] Driver registration creates `drivers` record with status `pending`
- [ ] `national_id_number` encrypted before storage
- [ ] `GET /api/v1/drivers/profile` returns profile + stats
- [ ] `PUT /api/v1/drivers/profile` updates editable fields
- [ ] Driver cannot access tasks until status = `approved`

**Testing Requirements**:
- Integration: Register driver, verify pending status
- Security: Verify `national_id_number` is encrypted in DB

---

### Task 3.2 — Driver Availability Toggle

**Objective**: Driver toggles online/offline status.

**Files / Modules Affected**:
- `/backend/routers/drivers.py`
- `/frontend/components/AvailabilityToggle.tsx`

**Dependencies**: Task 3.1

**Acceptance Criteria**:
- [ ] `POST /api/v1/drivers/availability` sets `is_online` in database
- [ ] Unapproved drivers cannot go online (403)
- [ ] Frontend toggle reflects current status

**Testing Requirements**:
- Authorization: Unapproved driver cannot go online
- State: Toggle persists on refresh

---

### Task 3.3 — Driver Task Queue

**Objective**: Driver sees orders assigned to them by admin.

**Files / Modules Affected**:
- `/backend/routers/drivers.py`
- `/frontend/pages/driver/tasks.tsx`
- `/frontend/components/TaskQueue.tsx`

**Dependencies**: Task 3.2, Task 2.2 (orders exist)

**Acceptance Criteria**:
- [ ] `GET /api/v1/drivers/tasks` returns orders where `assigned_driver_id = current_driver`
- [ ] Filterable by assignment status
- [ ] Returns pickup address, delivery address, merchant name, total, scheduled time
- [ ] Driver only sees their own assignments

**Testing Requirements**:
- Authorization: Driver A cannot see Driver B's tasks

---

### Task 3.4 — Task Acceptance & Rejection

**Objective**: Driver accepts or rejects an assigned delivery.

**Files / Modules Affected**:
- `/backend/routers/drivers.py`
- `/backend/models/driver_assignment.py`
- `/backend/services/assignment_service.py`
- `/frontend/components/TaskCard.tsx`

**Dependencies**: Task 3.3

**Acceptance Criteria**:
- [ ] `POST /api/v1/drivers/tasks/{id}/accept` creates accepted `driver_assignments` record
- [ ] `POST /api/v1/drivers/tasks/{id}/reject` records rejection reason
- [ ] `order_status_history` record created on both actions
- [ ] Driver can only act on tasks assigned to them
- [ ] Rejected orders returned to `pending` status for reassignment

**Testing Requirements**:
- State machine: Accept/reject transitions
- Authorization: Driver cannot accept another driver's task

---

### Task 3.5 — Delivery Status Updates

**Objective**: Driver updates delivery progress through status transitions.

**Files / Modules Affected**:
- `/backend/routers/drivers.py`
- `/backend/services/order_service.py`
- `/frontend/components/TaskCard.tsx`

**Dependencies**: Task 3.4

**Acceptance Criteria**:
- [ ] `PUT /api/v1/drivers/tasks/{id}/status` updates order status
- [ ] Valid transitions: `accepted → picked_up → in_transit → delivered`
- [ ] Skipping a status returns 400 with `INVALID_STATUS_TRANSITION`
- [ ] `order_status_history` record created on every transition
- [ ] `delivery_tracking` timestamps updated
- [ ] On `delivered`: two `financial_transactions` records created (commission + payout)
- [ ] `is_on_delivery` set to `false` after delivery

**Testing Requirements**:
- State machine: All valid and invalid transitions tested
- Financial: Verify transaction records created on delivery
- Authorization: Only assigned driver can update status

---

### Task 3.6 — Driver Earnings Dashboard

**Objective**: Driver views earnings summary by period.

**Files / Modules Affected**:
- `/backend/routers/drivers.py`
- `/frontend/pages/driver/earnings.tsx`

**Dependencies**: Task 3.5

**Acceptance Criteria**:
- [ ] `GET /api/v1/drivers/earnings?period=week` returns earnings
- [ ] Shows total_earnings_egp, order_count, pending_payout_egp
- [ ] Calculated from `financial_transactions` (not denormalised stats)

**Testing Requirements**:
- Correctness: Earnings match delivered order count × payout amount

---

## Phase 4: Admin & Operations (Weeks 10–11)

### Task 4.1 — Merchant Approval Workflow

**Objective**: Admin approves or rejects pending merchant applications.

**Files / Modules Affected**:
- `/backend/routers/admin.py`
- `/backend/services/admin_service.py`
- `/frontend/pages/admin/merchants.tsx`
- `/frontend/components/ApprovalList.tsx`

**Dependencies**: Task 2.1

**Acceptance Criteria**:
- [ ] `GET /api/v1/admin/merchants?status=pending` lists pending merchants
- [ ] `POST /api/v1/admin/merchants/{id}/approve` sets status to `approved`
- [ ] `POST /api/v1/admin/merchants/{id}/reject` sets status to `rejected` with reason
- [ ] Action logged to `audit_logs`
- [ ] Only admin role can approve

**Testing Requirements**:
- Authorization: Non-admin cannot call approve endpoint
- Audit: Approval action appears in audit_logs

---

### Task 4.2 — Driver Approval Workflow

**Objective**: Admin approves or rejects pending driver applications.

**Files / Modules Affected**:
- `/backend/routers/admin.py`
- `/frontend/pages/admin/drivers.tsx`

**Dependencies**: Task 3.1

**Acceptance Criteria**:
- Same criteria as Task 4.1, applied to drivers

**Testing Requirements**:
- Same as Task 4.1

---

### Task 4.3 — Manual Order Assignment

**Objective**: Admin assigns a pending order to an available driver.

**Files / Modules Affected**:
- `/backend/routers/admin.py`
- `/backend/services/assignment_service.py`
- `/frontend/pages/admin/orders.tsx`
- `/frontend/components/AssignmentPanel.tsx`

**Dependencies**: Task 4.1, Task 4.2 (approved drivers exist)

**Acceptance Criteria**:
- [ ] `GET /api/v1/admin/orders?status=pending` lists unassigned orders
- [ ] `POST /api/v1/admin/orders/{id}/assign` assigns driver
- [ ] Creates `driver_assignments` record
- [ ] Updates `orders.assigned_driver_id` and status to `assigned`
- [ ] Creates `order_status_history` record
- [ ] Logged to `audit_logs`
- [ ] `POST /api/v1/admin/orders/{id}/reassign` handles reassignment with reason

**Testing Requirements**:
- Integration: Assign order, verify in driver task queue
- Audit: Assignment logged

---

### Task 4.4 — Financial Transaction Logging

**Objective**: Verify financial transactions are created correctly on delivery.

**Files / Modules Affected**:
- `/backend/services/financial_service.py`
- `/backend/models/financial_transaction.py`

**Dependencies**: Task 3.5

**Acceptance Criteria**:
- [ ] Every delivered order creates exactly 2 `financial_transactions` records
- [ ] `order_commission` record with correct EGP amount
- [ ] `driver_payout` record with correct EGP amount
- [ ] Both records start with status `pending`
- [ ] Amounts match configured values (not hardcoded — read from config)

**Testing Requirements**:
- Unit: Financial service creates correct records
- Integration: Deliver order, check transactions in DB

---

### Task 4.5 — Settlement Processing (Admin)

**Objective**: Admin creates and processes weekly settlement records.

**Files / Modules Affected**:
- `/backend/routers/admin.py`
- `/backend/services/settlement_service.py`
- `/backend/models/settlement_record.py`
- `/frontend/pages/admin/settlements.tsx`

**Dependencies**: Task 4.4

**Acceptance Criteria**:
- [ ] `GET /api/v1/admin/settlements?status=pending` lists pending settlements
- [ ] Admin can create settlement record for a driver or merchant for a date range
- [ ] Settlement totals match sum of `financial_transactions` for that period
- [ ] `POST /api/v1/admin/settlements/{id}/process` marks settlement `completed`
- [ ] All actions logged to `audit_logs`

**Testing Requirements**:
- Correctness: Settlement total = sum of transactions for period
- Audit: Settlement processing logged

---

### Task 4.6 — Admin Dashboard & Platform Analytics

**Objective**: Admin sees platform-wide operational metrics.

**Files / Modules Affected**:
- `/backend/routers/admin.py`
- `/backend/services/analytics_service.py`
- `/frontend/pages/admin/dashboard.tsx`

**Dependencies**: Task 4.1–4.5

**Acceptance Criteria**:
- [ ] `GET /api/v1/admin/analytics?period=week` returns platform metrics
- [ ] Metrics: total_orders, active_merchants, active_drivers, delivered, cancelled, completion_rate
- [ ] Audit log viewer: `GET /api/v1/admin/audit-logs` with filters

**Testing Requirements**:
- Correctness: Metrics match aggregate of raw records

---

## Phase 5: Tracking, Testing & Deployment (Week 12)

### Task 5.1 — Public Tracking Page

**Objective**: Customers access order status via secure public link.

**Files / Modules Affected**:
- `/backend/routers/public.py`
- `/frontend/pages/tracking/[token].tsx`
- `/frontend/components/PublicTrackingView.tsx`

**Dependencies**: Task 2.2 (tracking tokens generated on order create)

**Acceptance Criteria**:
- [ ] `GET /api/v1/tracking/{token}` returns public order info (no auth)
- [ ] Expired or invalid token returns 404
- [ ] `access_count` incremented on each access
- [ ] No sensitive data exposed (no phone, no merchant name, no amounts)
- [ ] Frontend page is clean and readable on mobile browser

**Testing Requirements**:
- Public access: No auth required
- Expiry: Token expired → 404
- Privacy: Verify sensitive fields absent from response

---

### Task 5.2 — End-to-End Integration Tests

**Objective**: Automated tests covering the core operational workflow.

**Files / Modules Affected**:
- `/backend/tests/test_order_workflow.py`
- `/backend/tests/test_driver_workflow.py`
- `/backend/tests/test_auth.py`
- `/backend/tests/test_financial.py`

**Dependencies**: All previous tasks

**Acceptance Criteria**:
- [ ] Full workflow test: Merchant creates order → Admin assigns driver → Driver delivers → Transactions created
- [ ] Auth tests: Register, login, refresh, logout
- [ ] RBAC tests: Each role blocked from wrong endpoints
- [ ] Public tracking test: Token valid → returns data; token expired → 404
- [ ] Financial test: Delivery creates correct transaction records
- [ ] All tests pass in CI

**Testing Requirements**:
- Test coverage ≥ 60% of backend service layer

---

### Task 5.3 — Security Review & Hardening

**Objective**: Review all endpoints for security issues before launch.

**Files / Modules Affected**:
- All routers and middleware

**Dependencies**: Task 5.2

**Acceptance Criteria**:
- [ ] All endpoints validate ownership before returning data
- [ ] Error messages do not leak sensitive information
- [ ] Rate limiting enabled on all endpoint groups
- [ ] Security headers confirmed on all responses
- [ ] `.env` confirmed not committed to git history
- [ ] Secrets not visible in logs

**Testing Requirements**:
- Manual: Attempt to access another user's resources
- Manual: Check response headers with browser devtools

---

### Task 5.4 — Staging Deployment

**Objective**: Deploy complete application to staging environment.

**Files / Modules Affected**:
- `/.github/workflows/deploy.yml`
- Railway / Vercel configuration

**Dependencies**: Task 5.3

**Acceptance Criteria**:
- [ ] Frontend deployed to Vercel staging
- [ ] Backend deployed to Railway staging
- [ ] Database migrations run on staging
- [ ] All environment variables set in hosting platform (not in code)
- [ ] Full end-to-end test completed on staging environment
- [ ] Deployment guide in `docs/DEPLOYMENT.md` is accurate

**Testing Requirements**:
- Manual: Full workflow test on staging URL

---

## Deferred Features (Post-MVP)

| Feature | Reason Deferred |
|---------|----------------|
| Native mobile apps | Requires separate codebase; web MVP sufficient |
| Automated driver dispatch | Requires routing logic and driver location data |
| Live GPS tracking | Requires real-time infrastructure (WebSockets, Redis) |
| Online payment gateway | Requires payment processor integration and compliance |
| Push notifications | Requires mobile app or service worker |
| Machine learning / AI | Requires sufficient data volume first |
| Multi-city expansion | Validate unit economics in Alexandria first |
| Merchant API integration | Lower priority than operational MVP |
| Surge pricing | Requires demand data and pricing engine |

---

## Success Criteria for MVP Launch

### Functional
- [ ] Merchant can register, create orders, and view status
- [ ] Driver can register, accept tasks, and update delivery status
- [ ] Admin can approve users, assign orders, and process settlements
- [ ] Customer can view order status via public tracking link
- [ ] Financial transaction trail is complete and auditable

### Quality
- [ ] All integration tests pass in CI
- [ ] No known authentication or authorisation vulnerabilities
- [ ] Audit logs capture all sensitive actions

### Operational
- [ ] Application deployed to staging and tested end-to-end
- [ ] All secrets stored in environment variables, not code
- [ ] Deployment and rollback procedures documented

### Business (targets — unverified)
- [ ] 25–50 merchants recruited and onboarded
- [ ] 100+ drivers recruited and approved
- [ ] 50+ pilot orders completed
- [ ] Unit economics assumptions validated or revised with real data
