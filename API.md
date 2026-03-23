# GymApp API Reference

**Base URL:** `http://localhost:8000` (or your server)

**Content-Type:** `application/json` for all request bodies.

---

## Authentication

Auth endpoints (login, signup, refresh) return tokens. **Payment endpoints (create-order, verify) do not require login**; they use the request body (`email` + `business_slug`) and only allow the business owner’s email for that slug.

For other protected endpoints (if any), use **Bearer token**:

```
Authorization: Bearer <access_token>
```

---

## 1. Auth

### 1.1 Signup

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/auth/signup/` |
| **Auth** | None |

**Body:**
```json
{
  "email": "user@example.com",
  "password": "YourPass123",
  "username": "optional_username"
}
```
- `email` (required), `password` (required, 8–30 chars, at least one uppercase and one number), `username` (optional; defaults to email)

**Success (201):**
```json
{
  "customer": {
    "id": 1,
    "email": "user@example.com",
    "username": "user@example.com",
    "created_at": "2026-03-16T10:00:00Z",
    "updated_at": "2026-03-16T10:00:00Z"
  },
  "access": "<access_token>",
  "refresh": "<refresh_token>"
}
```

---

### 1.2 Login

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/auth/login/` |
| **Auth** | None |

**Body:**
```json
{
  "email": "test@example.com",
  "password": "password123"
}
```

**Success (200):**
```json
{
  "customer": { "id": 1, "email": "test@example.com", "username": "testuser", "created_at": "...", "updated_at": "..." },
  "access": "<access_token>",
  "refresh": "<refresh_token>"
}
```

---

### 1.3 Sign in with Google

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/auth/google/` |
| **Auth** | None |

Sign in or sign up using a Google ID token (from your frontend’s Google Sign-In). Same response shape as login/signup.

**Body:**
```json
{
  "id_token": "<Google ID token from frontend>"
}
```

**Success (200 or 201):**
```json
{
  "customer": { "id": 1, "email": "user@gmail.com", "username": "user", "created_at": "...", "updated_at": "..." },
  "access": "<access_token>",
  "refresh": "<refresh_token>"
}
```

**Errors:**
- `400` – Missing or invalid `id_token`, or token missing email.
- `409` – An account already exists with this email (created with password). Ask user to sign in with password.
- `503` – `GOOGLE_OAUTH_CLIENT_ID` not set (Google sign-in not configured).

Requires `GOOGLE_OAUTH_CLIENT_ID` in env (Web application client ID from Google Cloud Console).

**Error (400):** `{"detail": "Invalid credentials"}`

---

### 1.3 Refresh token

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/auth/refresh/` |
| **Auth** | None |

**Body:**
```json
{
  "refresh": "<refresh_token>"
}
```

**Success (200):**
```json
{
  "access": "<new_access_token>"
}
```

---

### 1.4 Forgot password

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/auth/forgot-password/` |
| **Auth** | None |

**Body:**
```json
{
  "email": "user@example.com"
}
```

**Success (200):**
```json
{
  "detail": "If that account exists, we've emailed you.",
  "reset_url": "/reset-password/?token=...",
  "expires_in_minutes": 60
}
```

---

## 2. Plans

### 2.1 List plans

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/api/plans/plan_list/` |
| **Auth** | None |

**Body:** None

**Success (200):**
```json
[
  {
    "id": 1,
    "name": "Starter",
    "price": "499.00",
    "currency": "INR",
    "duration": 28,
    "features": [
      { "id": 1, "name": "WhatsApp chat" },
      { "id": 2, "name": "Online payments" }
    ],
    "created_at": "..."
  },
  {
    "id": 2,
    "name": "Pro",
    "price": "999.00",
    "currency": "INR",
    "duration": 28,
    "features": [ ... ],
    "created_at": "..."
  }
]
```

---

## 3. Payments

### 3.1 Create order (Razorpay)

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/payments/create-order/` |
| **Auth** | None (email + slug must match: only the business owner’s email can create orders for that slug) |

**Body (frontend sends plan_id, email, slug):**
```json
{
  "email": "test@example.com",
  "business_slug": "my-gym",
  "plan_id": 1
}
```
**Or** custom amount instead of plan:
```json
{
  "email": "test@example.com",
  "business_slug": "my-gym",
  "amount": "999.00",
  "currency": "INR"
}
```
- `email` (required) – must match the authenticated user’s email.
- `business_slug` (required) – slug of the business (e.g. from URL).
- `plan_id` (optional) – use plan price; do not send `amount` if you send `plan_id`.
- `amount` (optional) – custom amount in rupees (string or number).
- `currency` (optional) – default `"INR"`.

**Success (201):**
```json
{
  "order_id": "order_xxxx",
  "amount": 49900,
  "currency": "INR",
  "key_id": "rzp_test_xxxx"
}
```
Use these in the frontend to open Razorpay Checkout. After payment, call **Verify payment** with the same `business_slug` and the IDs returned by Razorpay.

**Errors:**
- 403: `{"detail": "No account found for this email."}` or `{"detail": "This business is not linked to this email."}`
- 400: Validation (e.g. `{"business_slug": "No business found for this slug."}`)

---

### 3.2 Verify payment

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/payments/verify/` |
| **Auth** | None (email + slug must match business owner) |

**Body (frontend sends plan_id, email, slug + Razorpay IDs):**
```json
{
  "razorpay_order_id": "order_xxxx",
  "razorpay_payment_id": "pay_xxxx",
  "razorpay_signature": "xxxx",
  "email": "test@example.com",
  "business_slug": "my-gym",
  "plan_id": 1
}
```
- `razorpay_order_id`, `razorpay_payment_id`, `razorpay_signature` – from Razorpay after successful payment.
- `email` (required) – business owner’s email for the given slug.
- `business_slug` (required) – same as in create-order.
- `plan_id` (optional) – if provided, a **Subscription** is created for this plan.

**Success (201):**
```json
{
  "payment": {
    "id": 1,
    "business": 1,
    "razorpay_order_id": "order_xxxx",
    "razorpay_payment_id": "pay_xxxx",
    "amount": "499.00",
    "currency": "INR",
    "payment_status": "captured",
    "payment_method": "razorpay",
    "created_at": "..."
  },
  "subscription": {
    "id": 1,
    "plan": "Starter",
    "subscription_start_date": "2026-03-16",
    "subscription_end_date": "2026-04-13"
  }
}
```
If `plan_id` was not sent, `subscription` is `null`.

**Errors:**
- 400: `{"detail": "Payment signature verification failed."}` or validation errors.

---

## Businesses

### Get business details by slug (public)

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/api/businesses/public/<slug>/` |
| **Auth** | None |

Returns basic profile fields for a gym/business. Does **not** include owner email, username, or subscription/payment data. Use `/api/businesses/<slug>/active-subscription/` if you need subscription status.

**Example:** `GET /api/businesses/public/my-gym/`

**Success (200):**
```json
{
  "id": 1,
  "name": "My Gym",
  "slug": "my-gym",
  "description": "…",
  "phone": "+91…",
  "address": "…",
  "created_at": "2026-03-16T10:00:00Z",
  "updated_at": "2026-03-16T10:00:00Z"
}
```

**Not found (404):**
```json
{
  "detail": "No business found for this slug.",
  "slug": "unknown-slug"
}
```

### Get business by slug (owner only)

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/api/businesses/<slug>/` |
| **Auth** | Bearer access token (must own the business) |

Returns full details including `owner`, `owner_email`, `owner_username`, and `subscriptions`.

---

### Crystal leads (public POST)

| | |
|---|---|
| **Method** | `POST` |
| **URL** | `/api/businesses/public/<slug>/crystal-leads/` |
| **Auth** | None |

**Example:** `POST /api/businesses/public/power-gym/crystal-leads/`  
`Content-Type: application/json`

Each successful request creates one row with server `created_at`. The full JSON body is stored in `payload`; `lead_type` is indexed. For **WhatsApp**, `click_count` is copied into `quantity` (capped 1–1000) so analytics can `SUM(quantity)` (one POST can represent multiple clicks if you ever batch).

**`lead_type` values:** `join_now` | `book_free_trial` | `plan_visit` | `whatsapp_click`

If `business_slug` is sent, it must match the URL `<slug>`.

**1) Join now**
```json
{
  "lead_type": "join_now",
  "business_slug": "power-gym",
  "submitted_at_ms": 1710000000000,
  "name": "Jane Doe",
  "phone": "+971501234567",
  "focus": "strength",
  "frequency": "3-4"
}
```
`focus`: `strength` \| `weight_loss` \| `general` \| `classes` \| `explore`  
`frequency`: `1-2` \| `3-4` \| `5+` \| `unsure`

**2) Book free trial**
```json
{
  "lead_type": "book_free_trial",
  "business_slug": "power-gym",
  "submitted_at_ms": 1710000000000,
  "name": "Jane Doe",
  "phone": "+971501234567",
  "visit_when": "2025-03-24 at 14:30",
  "interests": ["strength", "cardio", "classes"],
  "notes": "Prefer evenings"
}
```

**3) Plan your visit**
```json
{
  "lead_type": "plan_visit",
  "business_slug": "power-gym",
  "submitted_at_ms": 1710000000000,
  "name": "Jane Doe",
  "phone": "+971501234567",
  "preferred_when": "2025-03-25 (time flexible)",
  "notes": ""
}
```

**4) WhatsApp click**
```json
{
  "lead_type": "whatsapp_click",
  "business_slug": "power-gym",
  "submitted_at_ms": 1710000000000,
  "source": "fab",
  "click_count": 1
}
```

**Success (201):** `{"ok": true}`  
**404:** unknown slug  
**400:** invalid `lead_type` or `business_slug` mismatch

**WhatsApp analytics (recommended approach):** Store **one row per POST** (or per batch with `quantity` = `click_count`). Aggregate with `SUM(quantity)` grouped by `TruncDate` / `TruncWeek` / `TruncMonth` on `created_at`. Avoid only a single running counter on `Business`—you lose time series and cannot do day/week/month/90d charts without extra tables.

---

### Crystal leads analytics (owner)

| | |
|---|---|
| **Method** | `GET` |
| **URL** | `/api/businesses/<slug>/crystal-leads/analytics/` |
| **Auth** | Bearer access token (must own the business) |

Returns WhatsApp click totals (`today`, `last_7_days`, `last_30_days`, `last_90_days`) and series for the last 90 days **by day, week, and month** (`SUM(quantity)` per bucket). Also returns `all_leads`: event counts and units per `lead_type`.

---

## Quick test (curl)

**Login and get token:**
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

**List plans:**
```bash
curl http://localhost:8000/api/plans/plan_list/
```

**Public business by slug:**
```bash
curl http://localhost:8000/api/businesses/public/my-gym/
```

**Crystal lead (WhatsApp click):**
```bash
curl -X POST http://localhost:8000/api/businesses/public/my-gym/crystal-leads/ \
  -H "Content-Type: application/json" \
  -d '{"lead_type":"whatsapp_click","business_slug":"my-gym","submitted_at_ms":1710000000000,"source":"fab","click_count":1}'
```

**Create payment order (no login; email must own the business for this slug):**
```bash
curl -X POST http://localhost:8000/api/payments/create-order/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","business_slug":"my-gym","plan_id":1}'
```

**Verify payment (after user pays in Razorpay):**
```bash
curl -X POST http://localhost:8000/api/payments/verify/ \
  -H "Content-Type: application/json" \
  -d '{
    "razorpay_order_id":"order_xxx",
    "razorpay_payment_id":"pay_xxx",
    "razorpay_signature":"xxx",
    "email":"test@example.com",
    "business_slug":"my-gym",
    "plan_id":1
  }'
```

---

## Dummy test data

After running `python manage.py seed_dummy_data`:

- **Login:** `test@example.com` / `password123`
- **Business slugs:** `my-gym`, `fit-life`, `crossfit-zone` (first two owned by test@example.com)
- **Plans:** `plan_id` 1 = Starter (₹499), 2 = Pro (₹999)
