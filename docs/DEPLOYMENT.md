# WASL Deployment Guide

> ⚠ **ASSUMPTION NOTICE**: This guide describes a deployment approach based on the approved
> architecture. Specific commands and configurations will need to be verified against actual
> platform documentation at time of deployment. Free-tier limits and pricing may have changed.

---

## Overview

WASL uses a split-deployment model:

| Component | Platform | Tier |
|-----------|----------|------|
| Next.js Frontend | Vercel | Hobby (free) |
| FastAPI Backend | Railway | Starter (free credits) |
| PostgreSQL Database | Railway or Supabase | Free tier |
| CDN / DDoS | Cloudflare | Free tier |

---

## Environments

| Environment | Purpose | Branch |
|-------------|---------|--------|
| `development` | Local developer machine | any feature branch |
| `staging` | Integration testing before release | `main` |
| `production` | Live platform | `main` (after staging pass) |

---

## Prerequisites

Before deploying, confirm:

- [ ] GitHub repository created and code pushed
- [ ] Vercel account created (free): https://vercel.com
- [ ] Railway account created (free): https://railway.app
- [ ] Cloudflare account created (free): https://cloudflare.com
- [ ] Domain name registered (e.g., `wasl.eg`)
- [ ] All environment variables documented in `.env.example`

---

## 1. Database Deployment (Railway or Supabase)

### Option A: Railway PostgreSQL

1. Create a new Railway project
2. Add a PostgreSQL service from the Railway dashboard
3. Note the connection string from the Railway dashboard:
   ```
   DATABASE_URL=postgresql://postgres:password@host:port/railway
   ```
4. Run migrations:
   ```bash
   cd backend
   DATABASE_URL=<railway_url> alembic upgrade head
   ```

### Option B: Supabase PostgreSQL (Free Tier)

1. Create project at https://supabase.com
2. Go to **Settings → Database**
3. Copy the connection string (use the "Connection pooling" URI)
4. Run migrations:
   ```bash
   cd backend
   DATABASE_URL=<supabase_url> alembic upgrade head
   ```

**Supabase free tier limits** (verify at time of use):
- 500 MB database storage
- 2 GB bandwidth
- Pauses after 1 week of inactivity

### Verify Database Deployment

```bash
# Connect and verify tables exist
psql $DATABASE_URL -c "\dt"
```

Expected output: all tables listed from `DATABASE_DESIGN.md`.

---

## 2. Backend Deployment (Railway)

### Initial Setup

1. In your Railway project, add a new service from GitHub
2. Select the repository and set the root directory to `/backend`
3. Set the start command:
   ```
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

### Environment Variables (set in Railway dashboard)

```
DATABASE_URL         = [from step 1]
JWT_SECRET_KEY       = [generate: python -c "import secrets; print(secrets.token_urlsafe(32))"]
ENCRYPTION_KEY       = [generate: see SECURITY.md]
ENVIRONMENT          = production
LOG_LEVEL            = INFO
ALLOWED_ORIGINS      = https://merchant.wasl.eg,https://driver.wasl.eg,https://admin.wasl.eg
```

> Never commit these values to git. Set them only in the Railway dashboard.

### Health Check

Railway will call a health endpoint to verify the deployment. Ensure the backend exposes:

```
GET /health
Response 200: { "status": "ok", "environment": "production" }
```

### Verify Backend Deployment

```bash
curl https://api.wasl.eg/health
# Expected: {"status": "ok", "environment": "production"}

curl https://api.wasl.eg/docs
# Expected: Swagger UI loads
```

---

## 3. Frontend Deployment (Vercel)

### Initial Setup

1. Go to https://vercel.com and import your GitHub repository
2. Set the root directory to `/frontend`
3. Framework: Next.js (auto-detected)
4. Build command: `npm run build`
5. Output directory: `.next`

### Environment Variables (set in Vercel dashboard)

```
NEXT_PUBLIC_API_URL  = https://api.wasl.eg
NEXT_PUBLIC_APP_ENV  = production
```

### Custom Domain

1. In Vercel: **Settings → Domains**
2. Add `merchant.wasl.eg`, `driver.wasl.eg`, `admin.wasl.eg`
3. Update DNS records at your domain registrar (Cloudflare handles this)

### Verify Frontend Deployment

```
Visit https://merchant.wasl.eg
Expected: Login page loads without errors
```

---

## 4. CI/CD Pipeline (GitHub Actions)

### Automated Deploy Workflow

The file `/.github/workflows/deploy.yml` should:

1. Run on push to `main`
2. Run all tests (must pass)
3. Run linting (must pass)
4. Deploy backend to Railway (via Railway CLI or webhook)
5. Deploy frontend to Vercel (automatic via Vercel GitHub integration)

### Workflow File Structure

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  test:
    # Run tests first — deployment blocked if tests fail
    ...

  deploy-backend:
    needs: test
    # Railway deployment
    ...

  deploy-frontend:
    needs: test
    # Vercel deploys automatically via GitHub integration
    ...
```

> Actual workflow content to be created during Task 0.4 and Task 5.4.

---

## 5. Domain & DNS Configuration (Cloudflare)

### DNS Records

Set up the following records in Cloudflare:

| Type | Name | Value | Proxy |
|------|------|-------|-------|
| CNAME | `merchant` | `cname.vercel-dns.com` | ✅ |
| CNAME | `driver` | `cname.vercel-dns.com` | ✅ |
| CNAME | `admin` | `cname.vercel-dns.com` | ✅ |
| CNAME | `api` | `[railway-backend-url]` | ✅ |

Cloudflare free tier provides:
- HTTPS (automatic SSL)
- DDoS protection
- CDN caching

---

## 6. Running Database Migrations

### Development

```bash
cd backend
alembic upgrade head
```

### Staging / Production

Migrations are run manually before deploying a new version:

```bash
# Set DATABASE_URL to target environment
export DATABASE_URL="postgresql://..."

# Preview migration plan
alembic upgrade head --sql

# Apply migrations
alembic upgrade head
```

**Rule**: Never run migrations automatically in production without reviewing the migration file first.

### Rollback

```bash
# Roll back one migration
alembic downgrade -1

# Roll back to specific version
alembic downgrade 0001
```

---

## 7. Monitoring Setup

### Error Tracking (Sentry — free tier)

1. Create account at https://sentry.io
2. Create a new project (Python FastAPI + Next.js)
3. Add `SENTRY_DSN` to backend and frontend environment variables
4. Verify errors appear in Sentry dashboard after triggering a test error

### Uptime Monitoring

Use a free uptime monitor (e.g., UptimeRobot, Better Stack):
- Monitor `https://api.wasl.eg/health` every 5 minutes
- Alert via email if down for > 2 minutes

---

## 8. Backup Strategy

> ⚠ Assumption: The following backup approach is reasonable but has not been tested.

### Database Backups

**Railway**: Enables automatic daily backups on paid plans. Verify free tier backup availability.

**Supabase**: Provides daily backups on free tier (verify retention period).

**Manual backup (always available)**:

```bash
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql
```

Store backup files in a separate location (not the same server).

### Backup Verification (monthly)

```bash
# Test restore to a fresh database
psql $TEST_DATABASE_URL < backup_20240115.sql
```

---

## 9. Rollback Procedure

If a deployment causes issues:

### Frontend Rollback (Vercel)

1. Go to Vercel dashboard → Deployments
2. Find previous successful deployment
3. Click **Promote to Production**

### Backend Rollback (Railway)

1. Go to Railway dashboard → Deployments
2. Find previous successful deployment
3. Click **Redeploy**

### Database Rollback

```bash
# Only if the migration is reversible
alembic downgrade -1
```

> Database rollbacks are risky in production. Always review migration files before applying.

---

## 10. Pre-Launch Checklist

Complete all items before accepting real orders:

**Infrastructure**:
- [ ] SSL certificates active on all domains
- [ ] Database backups enabled and tested
- [ ] Health check endpoint responding
- [ ] Error tracking (Sentry) receiving events

**Application**:
- [ ] All environment variables set (no placeholder values)
- [ ] Admin account created with strong password
- [ ] `.env` not in git history (`git log -- .env` returns nothing)
- [ ] All migrations applied to production database

**Security**:
- [ ] HTTPS enforced (HTTP redirects to HTTPS)
- [ ] CORS restricted to known domains
- [ ] Security headers verified
- [ ] Rate limiting enabled

**Functional**:
- [ ] Merchant registration and login working
- [ ] Driver registration and login working
- [ ] Admin login working
- [ ] Order creation end-to-end tested on staging
- [ ] Public tracking link tested

**Monitoring**:
- [ ] Uptime monitor configured
- [ ] Error alerts configured
- [ ] Admin receives alert on first real error

---

## Deployment Assumptions (Unverified)

The following assumptions in this guide require verification at time of deployment:

1. Railway free-tier credits sufficient for MVP traffic — check current pricing
2. Supabase free tier not paused under MVP usage patterns
3. Vercel hobby tier sufficient for Next.js SSR under MVP load
4. Cloudflare free tier covers WASL use case without restrictions
5. Alembic migration commands work as documented with the chosen database provider
