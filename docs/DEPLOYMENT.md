# WASL Deployment Guide

This guide covers deploying the WASL MVP to Railway (backend + PostgreSQL)
and Vercel (frontend). Every command listed here matches the actual
codebase as of the current commit.

---

## Architecture Overview

```
Internet → Cloudflare CDN
            ├── Vercel  (Next.js frontend)   merchant.wasl.eg / driver.wasl.eg / admin.wasl.eg
            └── Railway (FastAPI backend)    api.wasl.eg
                   └── Railway PostgreSQL    (same Railway project)
```

---

## Step 0 — Generate Secrets (do this first, on your local machine)

You need two secrets before any deployment step.
Generate them **now** and store them in a password manager.
**Never commit them to git.**

### JWT Secret Key
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Example output: Kx3mP9...  (keep this private)
```
This value goes into `JWT_SECRET_KEY` on Railway.

### Encryption Key (Fernet)
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Example output: xKj7Q...=  (keep this private)
```
This value goes into `ENCRYPTION_KEY` on Railway.

---

## Step 1 — Push Code to GitHub

```bash
git remote add origin https://github.com/YOUR_ORG/wasl.git
git push -u origin master
```

---

## Step 2 — Deploy the Database (Railway PostgreSQL)

1. Go to https://railway.app and create a new project.
2. Click **+ New Service → Database → PostgreSQL**.
3. In the PostgreSQL service, open the **Connect** tab and copy the
   **Internal** connection string for use within Railway, or the
   **External** string to run migrations from your laptop.

The string looks like:
```
postgresql://postgres:PASSWORD@HOST:PORT/railway
```

### Run Migrations

Migrations must be applied before the backend starts for the first time.

```bash
# From your laptop (with the external DATABASE_URL)
cd backend

# Windows
set DATABASE_URL=postgresql://postgres:PASSWORD@HOST:PORT/railway
venv\Scripts\alembic.exe upgrade head

# macOS / Linux
export DATABASE_URL=postgresql://postgres:PASSWORD@HOST:PORT/railway
venv/bin/alembic upgrade head
```

Expected output:
```
INFO  Running upgrade  -> 0001, Initial schema — all tables with constraints.
INFO  Running upgrade 0001 -> 0002, Add all strategic indexes.
```

Verify:
```bash
psql $DATABASE_URL -c "\dt"
# Should list 14+ tables: users, merchants, drivers, orders, ...
```

### Rollback (if needed)
```bash
alembic downgrade -1   # roll back one migration
```

---

## Step 3 — Deploy the Backend (Railway)

1. In the same Railway project, click **+ New Service → GitHub Repo**.
2. Select your repository.
3. Set **Root Directory** to `backend`.
4. Set the **Start Command** to:
   ```
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

### Environment Variables — Railway Dashboard

Open the backend service → **Variables** tab and add every variable below.
**Leave no placeholder values.**

| Variable | Value | Notes |
|----------|-------|-------|
| `DATABASE_URL` | `postgresql://...` | Use the Railway internal URL |
| `ENVIRONMENT` | `production` | Enables production guards |
| `LOG_LEVEL` | `INFO` | `DEBUG` logs SQL queries — too noisy for prod |
| `JWT_SECRET_KEY` | *(generated in Step 0)* | Min 32 bytes; app refuses to start if placeholder |
| `ENCRYPTION_KEY` | *(generated in Step 0)* | Fernet key; app refuses to start if placeholder |
| `ALLOWED_ORIGINS` | `https://merchant.wasl.eg,https://driver.wasl.eg,https://admin.wasl.eg` | Comma-separated, no trailing slash |
| `NUMBER_OF_PROXIES` | `1` | Railway sits behind 1 proxy hop; used for safe IP extraction |

Optional (add when configured):
| Variable | Value |
|----------|-------|
| `DELIVERY_FEE_EGP` | `15.0` *(or adjust per market research)* |
| `PLATFORM_COMMISSION_EGP` | `5.0` |
| `DRIVER_PAYOUT_EGP` | `10.0` |

### Health Check

Railway pings the health endpoint to confirm startup. Configure it in
**Settings → Health Check**:

```
Path:   /health
Method: GET
```

Expected response:
```json
{"status": "ok", "environment": "production", "database": "connected"}
```

If `"database": "unreachable"` appears, check `DATABASE_URL`.

### Verify Backend

```bash
curl https://api.wasl.eg/health
# {"status":"ok","environment":"production","database":"connected"}
```

`/docs` is hidden in production (`ENVIRONMENT=production`). To test
endpoints, use Postman or set `ENVIRONMENT=staging` temporarily.

---

## Step 4 — Create the First Admin User

Run the seed script **after** migrations and **after** the database is
reachable. This creates the admin account you will use to approve
merchants and drivers.

```bash
# From your laptop, pointing at the production database
cd backend

# Windows
set DATABASE_URL=postgresql://postgres:PASSWORD@HOST:PORT/railway
set ADMIN_EMAIL=admin@yourcompany.eg
set ADMIN_PHONE=01000000000
set ADMIN_PASSWORD=YourStrongRandomPassword1!
venv\Scripts\python.exe ..\scripts\seed_admin.py

# macOS / Linux
export DATABASE_URL=...
export ADMIN_EMAIL=admin@yourcompany.eg
export ADMIN_PHONE=01000000000
export ADMIN_PASSWORD=YourStrongRandomPassword1!
python ../scripts/seed_admin.py
```

Expected output:
```
Admin user created successfully: admin@yourcompany.eg
You can now log in and approve merchants/drivers.
```

The script is idempotent — safe to run again if interrupted.

---

## Step 5 — Deploy the Frontend (Vercel)

1. Go to https://vercel.com → **Add New Project** → import your GitHub repo.
2. Set **Root Directory** to `frontend`.
3. Framework preset: **Next.js** (auto-detected).
4. Build command: `npm run build` (default).
5. Output directory: `.next` (default).

### Environment Variables — Vercel Dashboard

Open the project → **Settings → Environment Variables**:

| Variable | Value | Notes |
|----------|-------|-------|
| `NEXT_PUBLIC_API_URL` | `https://api.wasl.eg` | Backend base URL, visible to browser |

`NEXT_PUBLIC_` prefix means the value is embedded in the client bundle.
**Never put secrets in a `NEXT_PUBLIC_` variable.**

### Custom Domains

1. **Settings → Domains** → Add each subdomain:
   - `merchant.wasl.eg`
   - `driver.wasl.eg`
   - `admin.wasl.eg`
2. Vercel shows CNAME/A records — add them in Cloudflare (Step 6).

---

## Step 6 — DNS (Cloudflare)

Add these records in Cloudflare, with **Proxy enabled (orange cloud)**:

| Type | Name | Target |
|------|------|--------|
| CNAME | `merchant` | `cname.vercel-dns.com` |
| CNAME | `driver` | `cname.vercel-dns.com` |
| CNAME | `admin` | `cname.vercel-dns.com` |
| CNAME | `api` | `<your-railway-app>.up.railway.app` |

Cloudflare provides free HTTPS, DDoS mitigation, and CDN.

---

## Step 7 — Verify End-to-End

Run through the smoke-test checklist after every deployment:

```bash
# 1. Backend health
curl https://api.wasl.eg/health
# → {"status":"ok","environment":"production","database":"connected"}

# 2. Register a test merchant (should succeed)
curl -X POST https://api.wasl.eg/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"smoke@test.eg","phone":"01012345678",
       "password":"SmokeTest1!","role":"merchant"}'
# → 201 Created

# 3. Public tracking (invalid token should 404 cleanly)
curl https://api.wasl.eg/api/v1/tracking/invalid-token-000
# → 404 with code TRACKING_TOKEN_INVALID

# 4. Frontend loads
curl -I https://merchant.wasl.eg
# → HTTP/2 200
```

---

## Environment Variable Checklists

### Railway (Backend) — Complete List

```
# Required — app will not start without these in production
DATABASE_URL                   postgresql://...
ENVIRONMENT                    production
JWT_SECRET_KEY                 <32-byte random — see Step 0>
ENCRYPTION_KEY                 <Fernet key — see Step 0>

# Required — controls CORS
ALLOWED_ORIGINS                https://merchant.wasl.eg,https://driver.wasl.eg,https://admin.wasl.eg

# Recommended
LOG_LEVEL                      INFO
NUMBER_OF_PROXIES              1

# Optional — financial amounts (defaults shown; adjust after market validation)
DELIVERY_FEE_EGP               15.0
PLATFORM_COMMISSION_EGP        5.0
DRIVER_PAYOUT_EGP              10.0
```

Railway automatically provides `PORT` — do not set it manually.

### Vercel (Frontend) — Complete List

```
# Required
NEXT_PUBLIC_API_URL            https://api.wasl.eg
```

That is the only variable the frontend currently reads.

---

## Rollback Procedures

### Frontend (Vercel)
Vercel → **Deployments** → find previous → **Promote to Production**.

### Backend (Railway)
Railway → **Deployments** → find previous → **Redeploy**.

### Database Migration Rollback
```bash
alembic downgrade -1   # roll back most recent migration
```

Rollbacks are irreversible if data was written under the new schema.
Always take a backup before running migrations in production.

---

## Monitoring

| Tool | Purpose | Setup |
|------|---------|-------|
| Railway built-in logs | Backend errors | Dashboard → Logs tab |
| Vercel built-in logs | Frontend errors | Dashboard → Functions tab |
| UptimeRobot (free) | Uptime alerts | Monitor `https://api.wasl.eg/health` |
| Sentry (free tier) | Exception tracking | Add `SENTRY_DSN` to both Railway and Vercel |

---

## Notes and Assumptions

- Railway free-tier credit: verify current limits at https://railway.app/pricing
- Vercel hobby tier: sufficient for Next.js SSR at MVP scale
- Supabase is an alternative to Railway PostgreSQL; it pauses after
  1 week of inactivity on the free tier — not recommended for production
- `NUMBER_OF_PROXIES=1` is correct for Railway. If you add Cloudflare as
  an additional proxy in front of Railway, set it to `2`.
