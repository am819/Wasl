# WASL System Architecture

## Overview

WASL is a B2B delivery management platform built as a **modular monolith** — a single logical application with clear internal separation of concerns, deployed as one unit.

**Architecture pattern**: Modular monolith (see [docs/ADR/ADR-001.md](./docs/ADR/ADR-001.md))
**Database strategy**: PostgreSQL as single source of truth (see [docs/ADR/ADR-002.md](./docs/ADR/ADR-002.md))

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Next.js Frontend                            │
│          Merchant Portal │ Driver Portal │ Admin Dashboard      │
│                TypeScript + Tailwind CSS                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS / REST
            ┌───────────────┴──────────────────┐
            │                                  │
            ▼                                  ▼
┌─────────────────────┐             ┌──────────────────────────┐
│  Next.js API Routes │             │   FastAPI Backend         │
│  (lightweight)      │             │                          │
│  - Auth helpers     │             │  ┌────────────────────┐  │
│  - Static data      │             │  │ Auth Service       │  │
└──────────┬──────────┘             │  │ Merchant Service   │  │
           │                        │  │ Driver Service     │  │
           └───────────┬────────────│  │ Order Service      │  │
                       │            │  │ Assignment Service │  │
                       │            │  │ Tracking Service   │  │
                       │            │  │ Financial Service  │  │
                       │            │  │ Admin Service      │  │
                       │            │  │ Analytics Service  │  │
                       │            │  └────────────────────┘  │
                       │            └────────────┬─────────────┘
                       │                         │ SQLAlchemy ORM
                       └─────────────┬───────────┘
                                     │
                          ┌──────────▼──────────┐
                          │     PostgreSQL       │
                          │  (Single database)   │
                          │  Managed via Railway │
                          │  or Supabase         │
                          └─────────────────────┘
```

---

## Technology Stack

### Frontend: Next.js + TypeScript + Tailwind CSS

**Rationale:**
- Single framework serves all three portals (merchant, driver, admin)
- TypeScript provides compile-time type safety and better tooling
- Server-side rendering (SSR) improves initial load and SEO
- Tailwind CSS enables consistent, responsive UI with minimal custom CSS
- Large ecosystem; easy to find solutions and examples

### Backend: Python FastAPI

**Rationale:**
- Modern async-first framework with high throughput
- Built-in OpenAPI/Swagger documentation (auto-generated)
- Pydantic models provide automatic input validation
- Native async/await for concurrent request handling
- Python ecosystem positions WASL for future data analytics and ML work

### Database: PostgreSQL

**Rationale:**
- Mature, reliable, ACID-compliant relational database
- Rich constraint support prevents data corruption at the DB level
- JSONB type available for flexible fields when needed
- PostGIS extension available for future geographic queries
- Excellent free managed options: Supabase (500 MB free), Railway

### No Redis, No Celery, No Message Queues (MVP)

**Rationale:** See [docs/ADR/ADR-002.md](./docs/ADR/ADR-002.md).
- Polling-based updates are sufficient for MVP scale
- Reduces operational complexity for a solo developer
- Can be added later without architectural changes

---

## Component Architecture

### Frontend Portals

```
Frontend (Next.js)
├── /merchant         Merchant Portal
│   ├── /dashboard    Overview metrics
│   ├── /orders       Order list, create, detail
│   ├── /profile      Business profile management
│   └── /analytics    Order and revenue summaries
│
├── /driver           Driver Portal
│   ├── /dashboard    Current task overview
│   ├── /tasks        Task queue, accept/reject
│   ├── /profile      Driver profile management
│   └── /earnings     Earnings and settlement history
│
├── /admin            Admin Dashboard
│   ├── /dashboard    Platform metrics
│   ├── /merchants    Merchant approval and management
│   ├── /drivers      Driver approval and management
│   ├── /orders       Platform-wide order view and assignment
│   ├── /settlements  Settlement processing
│   └── /audit        Audit log viewer
│
└── /tracking/[token] Public Order Tracking (no auth)
```

### Backend Services

```
Backend (FastAPI)
├── Auth Service          Register, login, JWT, session management
├── Merchant Service      Registration, profile, order creation
├── Driver Service        Registration, profile, availability toggle
├── Order Service         Order CRUD, status management, history
├── Assignment Service    Manual admin assignment, driver acceptance
├── Tracking Service      Token generation, public tracking queries
├── Financial Service     Transaction logging, commission recording
├── Settlement Service    Weekly settlement record generation
├── Admin Service         Approvals, platform-wide queries
└── Analytics Service     Aggregated metrics for dashboards
```

### Middleware

```
Middleware Layer
├── Auth Middleware        JWT validation on every protected request
├── RBAC Middleware        Role check (merchant / driver / admin)
├── Audit Middleware       Log sensitive actions to audit_logs table
├── Rate Limit Middleware  Request throttling per user/IP
└── Error Handler          Standardised error response format
```

---

## Data Flow Examples

### Order Creation

```
1. Merchant fills order form in browser
2. Frontend validates form fields (client-side)
3. POST /api/v1/merchants/orders sent with JWT
4. Auth middleware validates JWT, extracts merchant_id
5. RBAC middleware confirms role = 'merchant'
6. Order service validates request (Pydantic model)
7. Order service confirms merchant status = 'approved'
8. Order service generates order_number (WAS-YYYYMMDD-NNN)
9. DB transaction creates: orders, order_items, order_status_history records
10. Tracking service generates secure token, inserts tracking_tokens record
11. Response: order_id, order_number, tracking_link returned to merchant
```

### Manual Driver Assignment (Admin)

```
1. Admin selects pending order in dashboard
2. Admin selects available driver from dropdown
3. POST /api/v1/admin/orders/{id}/assign {driver_id}
4. Auth + RBAC middleware validates admin role
5. Assignment service validates driver status = 'approved', is_online
6. DB transaction:
   a. driver_assignments record created (status = 'assigned')
   b. orders.assigned_driver_id updated
   c. orders.status = 'assigned'
   d. order_status_history record created
7. Audit middleware logs action to audit_logs
8. Driver sees new task on next poll of GET /api/v1/drivers/tasks
```

### Delivery Completion

```
1. Driver marks order as 'delivered'
2. PUT /api/v1/drivers/tasks/{id}/status {status: 'delivered'}
3. Auth middleware validates driver JWT
4. Order service validates: driver owns assignment, current status = 'in_transit'
5. DB transaction:
   a. orders.status = 'delivered', actual_delivery_at = NOW()
   b. order_status_history record created
   c. delivery_tracking.actual_delivery_time updated
   d. financial_transactions (2 records):
      - order_commission (5 EGP assumed) status='pending'
      - driver_payout (10 EGP assumed) status='pending'
   e. drivers.is_on_delivery = FALSE
6. Merchant and public tracking link updated on next poll
```

---

## Deployment Architecture

### Development

```
Developer Machine
├── Node.js 18+        (Next.js frontend)
├── Python 3.11+       (FastAPI backend)
├── PostgreSQL 14+     (local or Supabase free tier)
└── Git                (version control → GitHub)
```

### Staging

```
GitHub (source)
    │
    └─ GitHub Actions CI (lint + test on push)
         │
         ├─ Vercel (Next.js frontend — free tier)
         └─ Railway (FastAPI + PostgreSQL — free tier credits)
```

### Production (Post-MVP)

```
Cloudflare (CDN, DDoS protection — free tier)
    │
    ├─ Vercel (Next.js frontend)
    └─ Railway or DigitalOcean VPS (~$5-10/month)
         ├─ FastAPI backend (Docker container)
         └─ Managed PostgreSQL
```

---

## API Architecture

| Property | Value |
|----------|-------|
| Protocol | REST over HTTPS |
| Format | JSON request and response |
| Versioning | `/api/v1/` prefix |
| Auth | JWT Bearer token |
| Docs | Auto-generated Swagger at `/docs` |
| Error format | `{ success, data, error, meta }` |

See [API_DESIGN.md](./API_DESIGN.md) for full specification.

---

## Security Architecture Summary

| Concern | Approach |
|---------|---------|
| Authentication | JWT HS256, 24h access / 7d refresh |
| Authorisation | Role-based (merchant, driver, admin) |
| Password storage | bcrypt (minimum 10 rounds) |
| Sensitive fields | AES-256 encryption at rest |
| Input validation | Pydantic models on every endpoint |
| Audit trail | Immutable audit_logs table |
| Tracking links | Cryptographically secure random tokens |

See [SECURITY.md](./SECURITY.md) for full specification.

---

## Scalability Path

| Phase | Approach |
|-------|---------|
| MVP (now) | Single monolith, single PostgreSQL |
| Month 6+ | Add Redis for caching and session storage |
| Month 12+ | Extract high-load services (order, driver) |
| Year 2+ | Geographic sharding, multi-region deployment |

---

## Assumptions and Limitations

- Performance targets have not been measured or verified against real load.
- Polling interval for driver task updates is acceptable for MVP but will need optimisation at scale.
- No background job processing in MVP; all actions are synchronous.
- Single city (Alexandria) only in MVP.
- Cash on delivery only; no online payment gateway in MVP.
