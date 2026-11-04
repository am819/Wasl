# WASL API Design Specification

## Overview

RESTful JSON API served by the FastAPI backend.

| Property | Value |
|----------|-------|
| Base URL | `https://api.wasl.eg/api/v1` |
| Protocol | HTTPS only |
| Format | JSON (request and response) |
| Auth | JWT Bearer token |
| Versioning | `/api/v1/` prefix |
| Documentation | Auto-generated Swagger at `/docs` |

---

## Standard Response Envelope

All endpoints return a consistent envelope:

### Success

```json
{
  "success": true,
  "data": { },
  "error": null,
  "meta": {
    "timestamp": "2024-01-15T10:30:45Z",
    "request_id": "req-abc123"
  }
}
```

### Error

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Email or password is incorrect",
    "details": null
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:45Z",
    "request_id": "req-abc123"
  }
}
```

---

## HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | OK | GET or PUT succeeded |
| 201 | Created | Order or user created |
| 204 | No Content | Logout succeeded |
| 400 | Bad Request | Validation error |
| 401 | Unauthorized | Missing or invalid token |
| 403 | Forbidden | Wrong role or resource not owned |
| 404 | Not Found | Resource does not exist |
| 409 | Conflict | Duplicate email or order number |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unhandled exception |

---

## Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| `INVALID_CREDENTIALS` | 401 | Email/password incorrect |
| `TOKEN_EXPIRED` | 401 | Access token expired — refresh required |
| `TOKEN_INVALID` | 401 | Malformed or tampered token |
| `FORBIDDEN` | 403 | User not authorised for this action |
| `MERCHANT_NOT_APPROVED` | 403 | Merchant status is not 'approved' |
| `DRIVER_NOT_APPROVED` | 403 | Driver status is not 'approved' |
| `ORDER_NOT_FOUND` | 404 | Order ID does not exist |
| `DRIVER_NOT_FOUND` | 404 | Driver ID does not exist |
| `TRACKING_TOKEN_INVALID` | 404 | Token not found or expired |
| `DUPLICATE_EMAIL` | 409 | Email already registered |
| `INVALID_STATUS_TRANSITION` | 400 | Cannot move to requested status |
| `VALIDATION_ERROR` | 400 | Request body failed validation |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Unhandled server exception |

---

## Rate Limits

| Endpoint Group | Limit |
|----------------|-------|
| Auth endpoints | 10 requests/minute per IP |
| Merchant endpoints | 100 requests/minute per user |
| Driver endpoints | 100 requests/minute per user |
| Admin endpoints | 500 requests/minute per user |
| Public tracking | 1,000 requests/minute per IP |

Response headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 75
X-RateLimit-Reset: 1705318245
```

---

## Authentication Endpoints

### Register

```
POST /api/v1/auth/register
Auth: None

Body:
{
  "email":    "merchant@example.com",
  "phone":    "01012345678",
  "password": "SecurePass1!",
  "role":     "merchant"              // "merchant" or "driver"
}

Response 201:
{
  "data": {
    "user_id": 42,
    "email":   "merchant@example.com",
    "role":    "merchant",
    "status":  "pending"
  }
}
```

### Login

```
POST /api/v1/auth/login
Auth: None

Body:
{
  "email":    "merchant@example.com",
  "password": "SecurePass1!"
}

Response 200:
{
  "data": {
    "user_id":       42,
    "email":         "merchant@example.com",
    "role":          "merchant",
    "token":         "eyJhbG...",
    "refresh_token": "eyJhbG...",
    "expires_in":    86400
  }
}
```

### Refresh Token

```
POST /api/v1/auth/refresh
Auth: None

Body:
{
  "refresh_token": "eyJhbG..."
}

Response 200:
{
  "data": {
    "token":         "eyJhbG...",
    "refresh_token": "eyJhbG...",
    "expires_in":    86400
  }
}
```

### Logout

```
POST /api/v1/auth/logout
Auth: Bearer token

Response 204: (no body)
```

---

## Merchant Endpoints

All merchant endpoints require `Authorization: Bearer {token}` with role `merchant`.

### Get Profile

```
GET /api/v1/merchants/profile

Response 200:
{
  "data": {
    "id":            1,
    "business_name": "Al Nour Restaurant",
    "business_phone":"01198765432",
    "address_line1": "45 El Geish Road",
    "city":          "Alexandria",
    "contact_person":"Omar Hassan",
    "stats": {
      "total_orders":                   142,
      "total_delivery_fees_egp":        2130.00,
      "total_platform_commission_egp":  710.00,
      "average_rating":                 4.3
    },
    "status":        "approved",
    "created_at":    "2024-01-01T09:00:00Z"
  }
}
```

### Update Profile

```
PUT /api/v1/merchants/profile

Body:
{
  "business_phone": "01198765433",
  "address_line1":  "46 El Geish Road",
  "contact_person_name": "Omar Hassan"
}

Response 200: { updated merchant object }
```

### Create Order

```
POST /api/v1/merchants/orders

Body:
{
  "customer_name":           "Ahmed Hassan",
  "customer_phone":          "01012345678",
  "customer_email":          "ahmed@example.com",
  "pickup_address_line1":    "45 El Geish Road",
  "delivery_address_line1":  "123 Corniche St",
  "delivery_address_line2":  "Apt 5",
  "delivery_notes":          "Please call before arriving",
  "items": [
    { "item_name": "Grilled Chicken", "quantity": 2, "unit_price_egp": 45.00 },
    { "item_name": "Iced Tea",        "quantity": 2, "unit_price_egp": 10.00 }
  ]
}

Response 201:
{
  "data": {
    "order_id":       1234,
    "order_number":   "WAS-20240115-001",
    "status":         "pending",
    "subtotal_egp":   110.00,
    "delivery_fee_egp": 15.00,
    "total_egp":      125.00,
    "tracking_token": "6fxHdH7NyQ1_8p9K2...",
    "tracking_link":  "/tracking/6fxHdH7NyQ1_8p9K2...",
    "created_at":     "2024-01-15T10:30:00Z"
  }
}
```

### List Orders

```
GET /api/v1/merchants/orders?status=pending&limit=20&offset=0

Query parameters:
  status  (optional) pending | assigned | picked_up | in_transit | delivered | cancelled
  limit   (optional, default 20, max 100)
  offset  (optional, default 0)

Response 200:
{
  "data": {
    "orders":      [ ...order objects... ],
    "total_count": 142,
    "limit":       20,
    "offset":      0
  }
}
```

### Get Order Detail

```
GET /api/v1/merchants/orders/{order_id}

Response 200:
{
  "data": {
    "order":          { ...order fields... },
    "items":          [ ...order items... ],
    "status_history": [ ...history records... ],
    "driver":         { "full_name": "...", "vehicle_type": "..." } | null
  }
}
```

### Cancel Order

```
PUT /api/v1/merchants/orders/{order_id}

Body:
{
  "status": "cancelled",
  "reason": "Customer requested cancellation"
}

Response 200: { updated order object }
```

### Get Analytics

```
GET /api/v1/merchants/analytics?period=week

Query parameters:
  period  today | week | month  (default: week)

Response 200:
{
  "data": {
    "period":                         "week",
    "total_orders":                   28,
    "total_delivery_fees_egp":        420.00,
    "total_platform_commission_egp":  140.00,
    "delivered_orders":               26,
    "cancelled_orders":               2,
    "average_rating":                 4.4,
    "top_items":                      [ ...item names... ],
    "_note": "Figures are display aggregates, up to 24 hours stale. For invoicing or disputes query financial_transactions directly."
  }
}
```

### Get Settlements

```
GET /api/v1/merchants/settlements?status=pending

Response 200:
{
  "data": {
    "settlements": [ ...settlement records... ]
  }
}
```

---

## Driver Endpoints

All driver endpoints require `Authorization: Bearer {token}` with role `driver`.

### Get Profile

```
GET /api/v1/drivers/profile

Response 200:
{
  "data": {
    "id":              5,
    "full_name":       "Mohamed Ali",
    "vehicle_type":    "motorcycle",
    "vehicle_plate":   "ABC-1234",
    "is_online":       true,
    "is_on_delivery":  false,
    "stats": {
      "total_deliveries":   87,
      "total_earnings_egp": 870.00,
      "average_rating":     4.6,
      "cancellation_rate":  0.02
    },
    "status":     "approved",
    "created_at": "2024-01-05T08:00:00Z"
  }
}
```

### Toggle Availability

```
POST /api/v1/drivers/availability

Body:
{
  "is_online": true
}

Response 200:
{
  "data": {
    "driver_id": 5,
    "is_online": true,
    "updated_at": "2024-01-15T09:00:00Z"
  }
}
```

### Get Task Queue

```
GET /api/v1/drivers/tasks?status=assigned

Query parameters:
  status  assigned | picked_up | in_transit  (default: assigned)

Response 200:
{
  "data": {
    "tasks": [
      {
        "order_id":                1234,
        "order_number":            "WAS-20240115-001",
        "merchant_name":           "Al Nour Restaurant",
        "customer_name":           "Ahmed Hassan",
        "pickup_address_line1":    "45 El Geish Road",
        "delivery_address_line1":  "123 Corniche St",
        "total_egp":               125.00,
        "scheduled_pickup_at":     "2024-01-15T10:45:00Z",
        "delivery_notes":          "Call before arriving",
        "assignment_status":       "assigned",
        "assigned_at":             "2024-01-15T10:00:00Z"
      }
    ],
    "count": 1
  }
}
```

### Accept Task

```
POST /api/v1/drivers/tasks/{order_id}/accept

Response 200:
{
  "data": {
    "order_id":         1234,
    "order_number":     "WAS-20240115-001",
    "assignment_status": "accepted",
    "accepted_at":       "2024-01-15T10:05:00Z"
  }
}
```

### Reject Task

```
POST /api/v1/drivers/tasks/{order_id}/reject

Body:
{
  "reason": "Vehicle issue"
}

Response 200:
{
  "data": {
    "order_id":         1234,
    "assignment_status": "rejected",
    "rejected_at":       "2024-01-15T10:05:00Z"
  }
}
```

### Update Delivery Status

```
PUT /api/v1/drivers/tasks/{order_id}/status

Body:
{
  "status": "picked_up"
}

Valid transitions:
  accepted → picked_up
  picked_up → in_transit
  in_transit → delivered

Response 200:
{
  "data": {
    "order_id":     1234,
    "order_number": "WAS-20240115-001",
    "status":       "picked_up",
    "updated_at":   "2024-01-15T10:20:00Z"
  }
}
```

### Get Earnings

```
GET /api/v1/drivers/earnings?period=week

Response 200:
{
  "data": {
    "period":            "week",
    "total_earnings_egp": 150.00,
    "order_count":        15,
    "pending_payout_egp": 100.00,
    "breakdown": [
      { "date": "2024-01-15", "orders": 5, "earnings_egp": 50.00 }
    ]
  }
}
```

### Get Settlements

```
GET /api/v1/drivers/settlements

Response 200:
{
  "data": {
    "settlements": [ ...settlement records... ]
  }
}
```

---

## Admin Endpoints

All admin endpoints require `Authorization: Bearer {token}` with role `admin`.

### Merchant Management

```
GET  /api/v1/admin/merchants?status=pending&limit=50
POST /api/v1/admin/merchants/{merchant_id}/approve
POST /api/v1/admin/merchants/{merchant_id}/reject

Approve body:  { "approval_notes": "Verified business registration" }
Reject body:   { "rejection_reason": "Invalid documentation" }
```

### Driver Management

```
GET  /api/v1/admin/drivers?status=pending&limit=50
POST /api/v1/admin/drivers/{driver_id}/approve
POST /api/v1/admin/drivers/{driver_id}/reject

Approve body:  { "approval_notes": "License verified" }
Reject body:   { "rejection_reason": "Expired license" }
```

### Order Management

```
GET /api/v1/admin/orders?merchant_id=1&status=pending&limit=50

POST /api/v1/admin/orders/{order_id}/assign
Body: { "driver_id": 67 }

POST /api/v1/admin/orders/{order_id}/reassign
Body: { "driver_id": 68, "reason": "Driver unavailable" }
```

### Settlement Processing

```
GET  /api/v1/admin/settlements?settlement_type=driver&status=pending
POST /api/v1/admin/settlements/{settlement_id}/process
Body: { "processing_notes": "Paid via cash handoff" }
```

### Platform Analytics

```
GET /api/v1/admin/analytics?period=week

Response 200:
{
  "data": {
    "period":                         "week",
    "total_orders":                   280,
    "total_delivery_fees_egp":        4200.00,
    "total_platform_commission_egp":  1400.00,
    "active_merchants":               35,
    "active_drivers":                 60,
    "delivered_orders":               265,
    "cancelled_orders":               15,
    "completion_rate":                0.946
  }
}
```

### Audit Logs

```
GET /api/v1/admin/audit-logs?user_id=5&action=assign_driver&limit=100

Response 200:
{
  "data": {
    "logs":        [ ...log records... ],
    "total_count": 42
  }
}
```

---

## Public Tracking Endpoint

No authentication required.

```
GET /api/v1/tracking/{tracking_token}

Response 200:
{
  "data": {
    "order_number":           "WAS-20240115-001",
    "status":                 "in_transit",
    "status_label":           "On the way",
    "customer_name":          "Ahmed Hassan",
    "delivery_address_line1": "123 Corniche St",
    "driver_first_name":      "Mohamed",
    "estimated_delivery_at":  "2024-01-15T11:00:00Z",
    "actual_delivery_at":     null,
    "last_updated":           "2024-01-15T10:30:00Z"
  }
}

Response 404 (expired or invalid token):
{
  "success": false,
  "error": {
    "code": "TRACKING_TOKEN_INVALID",
    "message": "This tracking link is no longer valid"
  }
}
```

**Data not returned on public endpoint** (privacy):
- Customer phone number
- Driver full name or phone
- Merchant details
- Financial amounts
- Internal IDs

---

## Pagination

All list endpoints support:

| Parameter | Default | Max |
|-----------|---------|-----|
| `limit` | 20 | 100 |
| `offset` | 0 | — |

Response always includes `total_count` for client-side pagination.

---

## Authentication Header

All protected endpoints require:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Missing or invalid header returns `401 Unauthorized`.
