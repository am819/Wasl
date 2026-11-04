# WASL Security Architecture

## Overview

This document defines the security controls for the WASL platform. The scope covers the MVP: web portals, FastAPI backend, PostgreSQL database, and public tracking links.

**Principle**: Security is layered. No single control is sufficient. Defence in depth applies throughout.

---

## 1. Authentication

### User Registration

- Email must be valid format and unique across the `users` table
- Phone number must be valid Egyptian format and unique
- Password requirements:
  - Minimum 8 characters
  - Must include uppercase, lowercase, digit, and special character
  - Rejected if found in common password list
- Password hashed with **bcrypt (minimum 10 rounds)** before storage
- Plain-text password is never stored, logged, or returned in any response

### Login

- Email and password verified against stored bcrypt hash
- Failed login attempts tracked per user
- After **5 consecutive failures**: account locked for 15 minutes
- Successful login creates a new JWT token pair

### Password Reset

- Email-based token (valid for 1 hour only)
- Token is single-use and invalidated after use
- Session invalidated on successful password change

---

## 2. JWT Token Strategy

See [docs/ADR/ADR-003.md](./docs/ADR/ADR-003.md) for the full decision record.

### Access Token

| Property | Value |
|----------|-------|
| Algorithm | HS256 (symmetric, MVP) |
| Expiry | 24 hours |
| Payload | `user_id`, `email`, `role`, `merchant_id` or `driver_id`, `issued_at` |
| Storage | HttpOnly cookie (preferred) or localStorage |

### Refresh Token

| Property | Value |
|----------|-------|
| Expiry | 7 days |
| Usage | Single-use only (invalidated after each use) |
| Storage | Database (`user_sessions` table, `token_hash` column — SHA-256 hex digest, `CHAR(64)`, never plaintext) |
| Revocation | `revoked_at` set on logout; all rows for the user deleted on new login |

### Token Rotation

1. Client sends refresh token to `POST /api/v1/auth/refresh`
2. Server validates token and checks it has not been used
3. Server invalidates old refresh token
4. Server issues new access token + new refresh token
5. Replaying an old refresh token returns 401

---

## 3. Role-Based Access Control (RBAC)

### Roles

| Role | Description | Accessible Endpoints |
|------|-------------|---------------------|
| `merchant` | Approved business partner | `/api/v1/merchants/*` |
| `driver` | Approved delivery driver | `/api/v1/drivers/*` |
| `admin` | Platform operator | `/api/v1/admin/*` + all read endpoints |

### Enforcement Layers

1. **Middleware**: Every request validated for JWT + role before reaching route handler
2. **Service layer**: Resource ownership checked (merchant can only access own orders)
3. **Database**: Row-level policies can be added as a third layer

### Ownership Validation Example

```
GET /api/v1/merchants/orders/{order_id}

1. JWT validated → merchant_id extracted from token
2. Order queried from database
3. order.merchant_id compared to token merchant_id
4. If mismatch → 403 Forbidden (never 404, to avoid leaking existence)
```

### Driver Task Ownership

```
PUT /api/v1/drivers/tasks/{order_id}/status

1. JWT validated → driver_id extracted
2. driver_assignments queried for this order + driver
3. If no active assignment found → 403 Forbidden
4. Status transition validated (cannot skip statuses)
```

---

## 4. API Security

### Input Validation

All request bodies parsed through **Pydantic models** on the backend. Validation includes:

- Type checking (string, integer, decimal)
- Length limits (`max_length=255` for names, etc.)
- Format validation (email regex, Egyptian phone regex)
- Range checks (quantity > 0, price ≥ 0)
- No null bytes, no control characters
- No HTML or script tags in string fields

Frontend validation is additional UX only. Backend validation is the security boundary.

### SQL Injection Prevention

- **SQLAlchemy ORM only** — raw SQL strings are prohibited
- All queries use parameterised statements automatically
- Never concatenate user input into query strings

### XSS Prevention

- React renders text content safely by default (no `dangerouslySetInnerHTML`)
- Backend does not accept or return raw HTML in API responses
- Content-Security-Policy headers set on all responses

### CORS

```
Allowed origins (production):
  https://merchant.wasl.eg
  https://driver.wasl.eg
  https://admin.wasl.eg

Development:
  http://localhost:3000

Credentials: true
Methods: GET, POST, PUT, DELETE
```

### Security Headers

All API responses include:

```
Strict-Transport-Security: max-age=63072000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Content-Security-Policy: default-src 'self'
Referrer-Policy: strict-origin-when-cross-origin
```

### Rate Limiting

| Endpoint Group | Limit |
|----------------|-------|
| Merchant endpoints | 100 requests/minute per user |
| Driver endpoints | 100 requests/minute per user |
| Admin endpoints | 500 requests/minute per user |
| Public tracking | 1,000 requests/minute per IP |
| Auth endpoints | 10 requests/minute per IP |

Response headers on rate-limited endpoints:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 75
X-RateLimit-Reset: 1705318245
```

---

## 5. Secure Public Tracking Tokens

### Token Generation

```python
import secrets
token = secrets.token_urlsafe(32)
# Produces a 43-character cryptographically random string
# Example: "6fxHdH7NyQ1_8p9K2L5mNoPqRsT6uVwXyZaBcDeFgHi"
```

### Token Lifecycle

```
Order created
  → Token generated (secrets.token_urlsafe(32))
  → Stored in tracking_tokens table
  → Expires in 7 days (expires_at = NOW() + 7 days)

Customer accesses /tracking/{token}
  → Token looked up in database
  → Expiry checked (expires_at > NOW())
  → access_count incremented
  → Public order info returned (no sensitive data)

Token expires
  → Lookup returns 404 (same as invalid token)
  → Merchant can generate new token if needed
```

### Data Returned on Public Tracking

The public tracking endpoint returns **only**:

- `order_number`
- `status` (human-readable)
- `estimated_delivery_time`
- `actual_delivery_time` (if delivered)
- `driver_first_name` (first name only)
- `delivery_address_line1` (no pickup address)

**Never returned publicly**:
- Customer phone number
- Driver full name or phone
- Merchant details
- Financial amounts
- Internal IDs

---

## 6. Data Protection

### Encryption at Rest

Fields encrypted using AES-256 before database storage:

| Table | Field | Reason |
|-------|-------|--------|
| `drivers` | `national_id_number` | Government ID — sensitive |
| `merchants` | `tax_id` | Business tax ID — sensitive |

Key stored in environment variable `ENCRYPTION_KEY`. Never in code or git.

### Encryption in Transit

- TLS 1.2+ required on all endpoints
- HTTP redirected to HTTPS
- HSTS header prevents downgrade attacks

### Data Minimisation

**Stored**: Only data operationally required.
**Not stored**: Credit card numbers, bank account details, full bank info.
**PII masking in UI**:
- Phone numbers: show first 4 and last 2 digits only (e.g., `0101 *** **78`)
- National IDs: not displayed in UI at all

### Data Retention

| Data Type | Retention |
|-----------|-----------|
| User accounts | Indefinite (or until deletion request) |
| Audit logs | Minimum 1 year |
| Financial transactions | Minimum 5 years (legal/tax) |
| Order records | Minimum 2 years |
| Tracking tokens | 7 days (then auto-expire) |

---

## 7. Audit Logging

### What Is Logged

Every sensitive action writes a record to the `audit_logs` table:

**Authentication events**:
- Successful and failed logins
- Logout
- Password change
- Token refresh

**Data modification events**:
- Order created, cancelled
- Order status changed
- Driver assignment created, accepted, rejected
- Merchant approved or rejected
- Driver approved or rejected
- Settlement processed

**Admin actions**:
- Any approval or rejection
- Commission or pricing changes
- Payout processing
- Dispute resolution

### Log Record Format

```json
{
  "id": 4521,
  "user_id": 42,
  "user_role": "admin",
  "action": "assign_driver",
  "entity_type": "order",
  "entity_id": 1234,
  "old_values": { "assigned_driver_id": null },
  "new_values": { "assigned_driver_id": 67 },
  "ip_address": "197.x.x.x",
  "user_agent": "Mozilla/5.0...",
  "created_at": "2024-01-15T10:31:00Z"
}
```

### Audit Log Integrity

- Audit log records are **never modified or deleted**
- No UPDATE or DELETE permitted on `audit_logs` table
- Database-level trigger rejects modification attempts
- Admin can read but not alter logs

---

## 8. Environment Variables & Secrets

### Required Secrets

```bash
# .env.example (committed — no real values)
DATABASE_URL=postgresql://user:password@localhost/wasl
JWT_SECRET_KEY=CHANGE_ME_IN_PRODUCTION_MIN_32_CHARS
ENCRYPTION_KEY=CHANGE_ME_IN_PRODUCTION_32_BYTE_FERNET_KEY
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

### Rules

- `.env` is **never committed to git** (enforced via `.gitignore`)
- Secrets set as environment variables on the hosting platform (Railway, Vercel)
- Different secrets for development, staging, and production environments
- Secrets **never logged**, even at debug level
- Rotate JWT_SECRET_KEY and ENCRYPTION_KEY every 90 days in production

### Secret Generation

```bash
# Python — generate JWT secret
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Python — generate Fernet encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 9. Error Handling & Information Disclosure

### Safe Error Messages

Errors returned to clients must not reveal:
- Whether a user account exists
- Database schema details
- Stack traces
- Internal IDs beyond what the user owns

```python
# Correct — generic message
raise HTTPException(status_code=401, detail="Invalid credentials")

# Incorrect — reveals account existence
if not user:
    raise HTTPException(detail="No account found for this email")
```

### Exception Logging

```python
# Log full detail internally
logger.error("Database error during order creation", exc_info=True, extra={"order_data": ...})

# Return generic message to client
raise HTTPException(status_code=500, detail="An internal error occurred")
```

---

## 10. Production Security Checklist

Before any production deployment:

**Infrastructure**:
- [ ] Valid SSL certificate installed (not self-signed)
- [ ] Database not publicly accessible (firewall rules)
- [ ] Admin endpoints restricted by IP allowlist (optional)
- [ ] Backups encrypted and stored separately

**Application**:
- [ ] All secrets in environment variables (not code)
- [ ] `.env` confirmed absent from git history
- [ ] Error messages reviewed for information leakage
- [ ] Logging confirmed to never output secret values
- [ ] Security headers verified with securityheaders.com

**Access Control**:
- [ ] Admin account password is 20+ characters, randomly generated
- [ ] Default/test accounts removed before launch
- [ ] Rate limiting enabled and tested
- [ ] Session timeout configured

**Monitoring**:
- [ ] Error tracking enabled (Sentry free tier)
- [ ] Failed login spike alerting configured
- [ ] Audit logs reviewed weekly initially

**Incident Response**:
- [ ] Security contact email configured
- [ ] Breach notification procedure documented
- [ ] Data deletion procedure tested
- [ ] Backup restoration tested and timed

---

## Security Contact

Report vulnerabilities to the project owner privately before any public disclosure.
Do not open public GitHub issues for security vulnerabilities.
