# GymApp API – Test URLs, Body & Response

**Base URL:** `http://localhost:8000`  
Use **Postman**, **Insomnia**, or **curl**. For protected endpoints add header: `Authorization: Bearer <access_token>`.

---

## 1. Auth

### Login (get token for other requests)

| | |
|---|---|
| **URL** | `http://localhost:8000/api/auth/login/` |
| **Method** | POST |
| **Headers** | `Content-Type: application/json` |

**Body:**
```json
{
  "email": "test@example.com",
  "password": "password123"
}
```

**Response (200):**
```json
{
  "customer": {
    "id": 1,
    "email": "test@example.com",
    "username": "testuser",
    "created_at": "2026-03-16T10:00:00Z",
    "updated_at": "2026-03-16T10:00:00Z"
  },
  "access": "eyJzdWIiOjEsInR5cGUiOiJhY2Nlc3MiLCJleHAiOjE3...",
  "refresh": "eyJzdWIiOjEsInR5cGUiOiJyZWZyZXNoIiwiZXhwIjoxNz..."
}
```
→ Copy `access` for the **Authorization: Bearer** header below.

---

### Send OTP

| | |
|---|---|
| **URL** | `http://localhost:8000/api/auth/send-otp/` |
| **Method** | POST |
| **Headers** | `Content-Type: application/json` |

**Body:**
```json
{
  "email": "test@example.com"
}
```

**Response (200):**
```json
{
  "message": "OTP sent to email",
  "token": "550e8400-e29b-41d4-a716-446655440000"
}
```
→ Use this `token` + the OTP from email in **Verify OTP** and **Signup**.

---

### Verify OTP

| | |
|---|---|
| **URL** | `http://localhost:8000/api/auth/verify-otp/` |
| **Method** | POST |
| **Headers** | `Content-Type: application/json` |

**Body:**
```json
{
  "email": "test@example.com",
  "token": "550e8400-e29b-41d4-a716-446655440000",
  "otp": "123456"
}
```

**Response (200):**
```json
{
  "message": "OTP verified successfully",
  "email": "test@example.com"
}
```

---

### Signup (after OTP verified)

| | |
|---|---|
| **URL** | `http://localhost:8000/api/auth/signup/` |
| **Method** | POST |
| **Headers** | `Content-Type: application/json` |

**Body:**
```json
{
  "email": "newuser@example.com",
  "password": "YourPass123",
  "username": "newuser",
  "token": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response (201):**
```json
{
  "customer": { "id": 2, "email": "newuser@example.com", "username": "newuser", "created_at": "...", "updated_at": "..." },
  "access": "<access_token>",
  "refresh": "<refresh_token>"
}
```

---

### Refresh token

| | |
|---|---|
| **URL** | `http://localhost:8000/api/auth/refresh/` |
| **Method** | POST |
| **Headers** | `Content-Type: application/json` |

**Body:**
```json
{
  "refresh": "<refresh_token>"
}
```

**Response (200):**
```json
{
  "access": "<new_access_token>"
}
```

---

## 2. Plans

### List plans (no auth)

| | |
|---|---|
| **URL** | `http://localhost:8000/api/plans/plan_list/` |
| **Method** | GET |
| **Headers** | None |

**Body:** None

**Response (200):**
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

## 3. Businesses (auth required)

### List my businesses (paginated)

| | |
|---|---|
| **URL** | `http://localhost:8000/api/businesses/` |
| **Method** | GET |
| **Headers** | `Authorization: Bearer <access_token>` |
| **Query params** | `page` (default 1), `page_size` (default 10, max 100) |

**Body:** None (GET uses query string)

**Example URLs:**
- First page (default): `http://localhost:8000/api/businesses/`
- Page 2, 5 per page: `http://localhost:8000/api/businesses/?page=2&page_size=5`

**Response (200):**
```json
{
  "results": [
    {
      "id": 1,
      "owner": 1,
      "owner_email": "afsal_salim@example.com",
      "owner_username": "Afsal_Salim",
      "name": "QaGym",
      "slug": "qagym",
      "description": "Your neighbourhood gym...",
      "phone": "+91 9876543210",
      "address": "123 Fitness Road, City",
      "subscriptions": [
        {
          "id": 1,
          "plan": 1,
          "plan_name": "Starter",
          "payment_id": "pay_xxx",
          "subscription_start_date": "2026-03-16",
          "subscription_end_date": "2026-04-13"
        }
      ],
      "created_at": "...",
      "updated_at": "..."
    }
  ],
  "meta": {
    "page": 1,
    "page_size": 10,
    "total": 4,
    "total_pages": 1,
    "has_next": false,
    "has_previous": false
  }
}
```

---

### Get business by slug

| | |
|---|---|
| **URL** | `http://localhost:8000/api/businesses/qagym/` |
| **Method** | GET |
| **Headers** | `Authorization: Bearer <access_token>` |

**Body:** None

**Response (200):** Same shape as one object in the list above.

---

### Create business

| | |
|---|---|
| **URL** | `http://localhost:8000/api/businesses/` |
| **Method** | POST |
| **Headers** | `Authorization: Bearer <access_token>`, `Content-Type: application/json` |

**Body:**
```json
{
  "name": "My New Gym",
  "slug": "my-new-gym",
  "description": "A new gym.",
  "phone": "+91 9999888777",
  "address": "100 New Street, City"
}
```

**Response (201):** Full business object (same as detail), including `id`, `owner`, `owner_email`, `owner_username`, `subscriptions`, etc.

---

### Check active subscription (no auth)

| | |
|---|---|
| **URL** | `http://localhost:8000/api/businesses/qagym/active-subscription/` |
| **Method** | GET |
| **Headers** | None |

**Body:** None

**Response – has active (200):**
```json
{
  "slug": "qagym",
  "has_active_subscription": true,
  "subscription": {
    "id": 1,
    "plan_name": "Starter",
    "subscription_start_date": "2026-03-16",
    "subscription_end_date": "2026-04-13"
  }
}
```

**Response – no active (200):**
```json
{
  "slug": "qagym",
  "has_active_subscription": false,
  "subscription": null
}
```

---

## 4. Payments (no auth; email + slug must be owner)

### Create order

| | |
|---|---|
| **URL** | `http://localhost:8000/api/payments/create-order/` |
| **Method** | POST |
| **Headers** | `Content-Type: application/json` |

**Body:**
```json
{
  "email": "test@example.com",
  "business_slug": "my-gym",
  "plan_id": 1
}
```

**Response (201):**
```json
{
  "order_id": "order_SRtv4RqR7iL1ie",
  "amount": 49900,
  "currency": "INR",
  "key_id": "rzp_test_xxxx"
}
```

---

### Verify payment (after Razorpay success)

| | |
|---|---|
| **URL** | `http://localhost:8000/api/payments/verify/` |
| **Method** | POST |
| **Headers** | `Content-Type: application/json` |

**Body:**
```json
{
  "razorpay_order_id": "order_SRtv4RqR7iL1ie",
  "razorpay_payment_id": "pay_xxxxxxxxxxxx",
  "razorpay_signature": "xxxxxxxxxxxxxxxx",
  "email": "test@example.com",
  "business_slug": "my-gym",
  "plan_id": 1
}
```

**Response (201):**
```json
{
  "payment": {
    "id": 1,
    "business": 1,
    "razorpay_order_id": "order_xxx",
    "razorpay_payment_id": "pay_xxx",
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

---

## Dummy test data

| Type | Value |
|------|--------|
| **Login** | `test@example.com` / `password123` |
| **Afsal_Salim businesses** | `qagym`, `fitzone-afsal`, `power-gym`, `health-hub` |
| **Seed businesses** | `my-gym`, `fit-life`, `crossfit-zone` (after `python manage.py seed_dummy_data`) |
| **Plans** | `plan_id` 1 = Starter (₹499), 2 = Pro (₹999) |

Replace `<access_token>` with the `access` value from the login response when testing protected endpoints.
