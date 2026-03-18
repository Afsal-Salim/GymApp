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
