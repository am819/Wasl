# WASL — B2B Last-Mile Delivery & Logistics Platform

WASL is a B2B delivery management platform enabling merchants in Alexandria, Egypt to centralise order management, driver coordination, and delivery operations.

## Project Vision

Merchants receive orders through their existing channels (Instagram, Facebook, WhatsApp, POS systems). WASL provides:

- Centralised order management dashboard
- Driver coordination and manual task assignment
- Delivery status tracking and updates
- Operational analytics and financial settlement records

## What WASL Is Not (MVP Scope)

- Not a consumer marketplace or customer-facing ordering app
- Not an automated dispatch or route-optimisation system
- No live GPS tracking
- No online payment processing
- No native mobile applications
- No machine learning or AI features

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js + TypeScript + Tailwind CSS |
| Backend | Python FastAPI |
| Database | PostgreSQL |
| Frontend Hosting | Vercel (free tier) |
| Backend + DB Hosting | Railway (free tier) or Supabase |
| Architecture | Modular monolith |

## Project Structure

```
c:\WASL\
├── frontend/                  # Next.js application (to be created)
│   ├── pages/                 # Route pages
│   ├── components/            # Reusable React components
│   ├── lib/                   # Utilities and API client
│   ├── styles/                # Tailwind CSS config
│   └── public/                # Static assets
│
├── backend/                   # FastAPI application (to be created)
│   ├── routers/               # API endpoint definitions
│   ├── services/              # Business logic
│   ├── models/                # SQLAlchemy ORM models
│   ├── schemas/               # Pydantic request/response models
│   ├── middleware/            # Auth and logging middleware
│   ├── database.py            # Database connection
│   └── main.py                # Application entry point
│
├── docs/                      # Extended documentation
│   ├── ADR/                   # Architecture Decision Records
│   │   ├── ADR-001.md
│   │   ├── ADR-002.md
│   │   ├── ADR-003.md
│   │   ├── ADR-004.md
│   │   ├── ADR-005.md
│   │   └── ADR-006.md
│   ├── DEPLOYMENT.md          # Production deployment guide
│   └── OPERATIONS.md          # Operational runbook
│
├── README.md                  # This file
├── ARCHITECTURE.md            # System design overview
├── BUSINESS_MODEL.md          # Financial model and assumptions
├── SECURITY.md                # Security architecture
├── DATABASE_DESIGN.md         # Schema and relationships
├── API_DESIGN.md              # REST API specification
└── ROADMAP.md                 # 12-week implementation roadmap
```

## Key Portals

| Portal | Users | Purpose |
|--------|-------|---------|
| Merchant Portal | Merchants | Create and manage delivery orders |
| Driver Portal | Drivers | Accept tasks, update delivery status |
| Admin Dashboard | Admins | Approve users, assign orders, view analytics |
| Public Tracking | Customers | View order status via secure link (no login) |

## Financial Model (Unverified Assumptions)

All figures are assumptions requiring market validation. See [BUSINESS_MODEL.md](./BUSINESS_MODEL.md).

| Parameter | Assumed Value | Status |
|-----------|--------------|--------|
| Delivery fee per order | 15 EGP | ⚠ Unverified |
| Driver payout per order | 10 EGP | ⚠ Unverified |
| Platform revenue per order | 5 EGP | ⚠ Unverified |
| Break-even volume | ~400 orders/day | ⚠ Unverified |

## Documentation Index

| File | Contents |
|------|---------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System design, components, data flow |
| [BUSINESS_MODEL.md](./BUSINESS_MODEL.md) | Revenue model, unit economics, assumptions |
| [SECURITY.md](./SECURITY.md) | Auth, RBAC, encryption, audit logging |
| [DATABASE_DESIGN.md](./DATABASE_DESIGN.md) | Full schema, indexes, constraints |
| [API_DESIGN.md](./API_DESIGN.md) | REST endpoints, request/response formats |
| [ROADMAP.md](./ROADMAP.md) | 12-week phased implementation plan |
| [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) | Deployment guide for staging and production |
| [docs/OPERATIONS.md](./docs/OPERATIONS.md) | Operational runbook and procedures |
| [docs/ADR/](./docs/ADR/) | Architecture Decision Records (ADR-001 to ADR-006) |

## Development Setup

### Prerequisites

- Node.js 18+
- Python 3.11+
- PostgreSQL 14+ (local or Supabase free tier)
- Git

### Local Development (once application is initialised)

```bash
# Frontend
cd frontend
npm install
npm run dev          # http://localhost:3000

# Backend (separate terminal)
cd backend
python -m venv venv
venv\Scripts\activate     # Windows
pip install -r requirements.txt
uvicorn main:app --reload  # http://localhost:8000
                           # Swagger docs: http://localhost:8000/docs
```

## Current Status

| Item | Status |
|------|--------|
| Architecture design | ✅ Approved |
| Documentation | ✅ Complete |
| Application scaffolding | ⏳ Pending |
| Database migrations | ⏳ Pending |
| MVP implementation | ⏳ Pending |

**Phase**: Documentation complete — awaiting implementation approval.
**Target**: 12-week MVP pilot in Alexandria, Egypt.

## Security & Compliance

- JWT authentication (24-hour access tokens, 7-day refresh)
- Role-based access control: merchant, driver, admin
- Input validation on all API endpoints (Pydantic)
- Immutable audit log for all sensitive actions
- Encrypted sensitive fields (national IDs, tax IDs)
- No credit card or bank account storage in MVP
- Cash on delivery only in MVP

See [SECURITY.md](./SECURITY.md) for full details.

## License

Proprietary. Copyright © 2024 WASL. All rights reserved.
