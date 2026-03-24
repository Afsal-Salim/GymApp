# GymApp API Reference

HTTP interfaces for the Django GymApp backend.  
**Example base URL:** `http://127.0.0.1:8000`

## Conventions

- JSON bodies: `Content-Type: application/json`
- Protected routes: `Authorization: Bearer <access_token>`
- List endpoints use query params `page` (default 1) and `page_size` (default 10, max 100); response shape: `{ "results": [...], "meta": { "page", "page_size", "total", "total_pages", "has_next", "has_previous" } }`

---

## 1. Non-API pages (HTML)

| Method | Path |
|--------|------|
| GET | `/admin/` |
| GET | `/login/` |
| GET | `/signup/` |

---

## 2. Authentication: `/api/auth/`

### POST `/api/auth/send-otp/`

- **Auth:** none  
- **Body:** `{ "email": "..." }`  
- **200:** `{ "message": "OTP sent to email", "token": "<uuid>" }`  
- **400:** missing email  

### POST `/api/auth/verify-otp/`

- **Auth:** none  
- **Body:** `{ "token": "<uuid>", "otp": "123456", "email": "..." }` (email optional but recommended)  
- **200:** `{ "message": "Email verified" }`  
- **400:** invalid/expired token or OTP  

### POST `/api/auth/signup/`

- **Auth:** none  
- **Body:** `email`, `password` (8-30 chars, 1 uppercase, 1 number), optional `username` (defaults to email), `token` from send-otp flow after verify  
- **201:** `{ "customer": {...}, "access": "...", "refresh": "..." }`  
- **400:** validation / email not verified  

### POST `/api/auth/login/`

- **Auth:** none  
- **Body:** `{ "email", "password" }`  
- **200:** same shape as signup  
- **400:** `{ "detail": "Invalid credentials" }`  

### POST `/api/auth/google/`

- **Auth:** none  
- **Body:** `{ "id_token": "<Google JWT>" }`  
- **200/201:** same token shape as login  
- **409:** email exists with password provider  
- **503:** Google not configured or `google-auth` missing  

### POST `/api/auth/forgot-password/`

- **Body:** `{ "email" }`  
- **200:** generic message; includes `token` and `expires_in_minutes` when account exists  

### POST `/api/auth/verify-reset-otp/`

- **Body:** `email`, `token`, `otp`  
- **200:** message + token  

### POST `/api/auth/reset-password/`

- **Body:** `email`, `token`, `new_password` (same rules as signup)  
- **200:** success message  

### POST `/api/auth/refresh/`

- **Body:** `{ "refresh": "<token>" }`  
- **200:** `{ "access": "..." }`  

---

## 3. Businesses: `/api/businesses/`

### GET `/api/businesses/`

- **Auth:** Bearer  
- **200:** paginated list of owned businesses; each item includes `website_theme`, `website_content`, `subscriptions`, owner fields  

### POST `/api/businesses/`

- **Auth:** Bearer  
- **Body:** `name`, `slug` (unique), optional `description`, `phone`, `address`  
- **201:** created business  

### POST `/api/businesses/website-setup/`

- **Auth:** Bearer
- **Body:** `slug` (unique), `theme` (object), `content` (object) — Crystal builder payload
- **201:** business with:
  - `name` / `description` from `content.header` / `content.description` when present
  - `phone`, `address`, `location_map_url` from `content.contacts`: `locationMapUrl` (or `location_map_url`), and `items[]` with `id` `"phone"` / `"address"` (`value` or `tel:` `href` for phone)
- Full `content` (including all `contacts` fields) remains in `website_content`

### GET `/api/businesses/public/<slug>/`

- **Auth:** none
- **200:** public profile including `phone`, `address`, `location_map_url`, `website_theme`, `website_content`
- **404:** unknown slug  

### POST `/api/businesses/public/<slug>/crystal-leads/`

- **Auth:** none  
- **Body:** `lead_type` required: `join_now` | `book_free_trial` | `plan_visit` | `whatsapp_click`; optional `business_slug` (must match URL); other fields stored in payload  
- **201:** `{ "ok": true }`  
- Owner email sent for `join_now` and `book_free_trial` when configured  

### GET `/api/businesses/<slug>/`

- **Auth:** Bearer (must own business)  
- **200:** full business + subscriptions  
- **404:** not found or not owner  

### GET `/api/businesses/<slug>/active-subscription/`

- **Auth:** none  
- **200:** `slug`, `has_active_subscription`, `subscription` object or null  

### GET `/api/businesses/<slug>/crystal-leads/analytics/`

- **Auth:** Bearer (owner)  
- **200:** `whatsapp` totals and time series, `all_leads` counts by type  

---

## 4. Plans: `/api/plans/`

### GET `/api/plans/plan_list/`

- **Auth:** none  
- **200:** paginated plans with nested `features`  

---

## 5. Payments: `/api/payments/`

Requires Razorpay env vars; otherwise `503` where applicable.

### POST `/api/payments/create-order/`

- **Auth:** none (email must own `business_slug`)  
- **Body:** `email`, `business_slug`, and either `plan_id` OR `amount` (not both); optional `currency` (default INR)  
- **201:** `order_id`, `amount` (paise), `currency`, `key_id`  
- **403:** email not owner  

### POST `/api/payments/verify/`

- **Auth:** none  
- **Body:** `razorpay_order_id`, `razorpay_payment_id`, `razorpay_signature`, `email`, `business_slug`, optional `plan_id`  
- **201:** `payment` record; optional `subscription` if `plan_id` set  
- **400:** bad signature  

---

## Quick path index

```
GET  /login/  /signup/  /admin/
POST /api/auth/send-otp/  verify-otp/  signup/  login/  google/
     forgot-password/  verify-reset-otp/  reset-password/  refresh/
GET|POST /api/businesses/
POST /api/businesses/website-setup/
GET  /api/businesses/public/<slug>/
POST /api/businesses/public/<slug>/crystal-leads/
GET  /api/businesses/<slug>/  <slug>/active-subscription/  <slug>/crystal-leads/analytics/
GET  /api/plans/plan_list/
POST /api/payments/create-order/  verify/
```

See `DB.md` for database schema. Configure secrets via `.env` (see `.env.example`).

---

## Appendix: example payloads

### Crystal lead: join now

```json
{
  "lead_type": "join_now",
  "business_slug": "my-gym",
  "submitted_at_ms": 1710000000000,
  "name": "Jane Doe",
  "phone": "+971501234567",
  "focus": "strength",
  "frequency": "3-4"
}
```

### Crystal lead: book free trial

```json
{
  "lead_type": "book_free_trial",
  "business_slug": "my-gym",
  "submitted_at_ms": 1710000000000,
  "name": "Jane Doe",
  "phone": "+971501234567",
  "visit_when": "2025-03-24 at 14:30",
  "interests": ["strength", "cardio"],
  "notes": "Evenings preferred"
}
```

### Crystal lead: WhatsApp click

```json
{
  "lead_type": "whatsapp_click",
  "business_slug": "my-gym",
  "submitted_at_ms": 1710000000000,
  "source": "fab",
  "click_count": 1
}
```

### Website setup (abbreviated, with contacts + map)

```json
{
  "slug": "my-gym",
  "theme": {
    "accentHex": "#ea580c",
    "darkHex": "#0c0a09",
    "textHex": "#1c1917"
  },
  "content": {
    "header": { "title": "My Gym", "taglineItems": [], "memberRating": 4.9 },
    "nav": { "items": [], "ctaLabel": "Join now", "ctaHref": "#contact" },
    "layout": { "heroBackgroundImage": "https://...", "heroOverlay": 0.55 },
    "contacts": {
      "sectionTitle": "Contact",
      "whatsappFabHint": "…",
      "locationMapUrl": "https://maps.app.goo.gl/xxxxxxxx",
      "items": [
        { "id": "email", "label": "Email", "value": "hello@gym.com", "href": "mailto:hello@gym.com" },
        { "id": "phone", "label": "Phone", "value": "+91 …", "href": "tel:+91…" },
        { "id": "address", "label": "Address", "value": "12 Wellness Road" }
      ]
    }
  }
}
```

### Create Razorpay order

```json
{
  "email": "owner@example.com",
  "business_slug": "my-gym",
  "plan_id": 1,
  "currency": "INR"
}
```

### Verify payment

```json
{
  "razorpay_order_id": "order_xxx",
  "razorpay_payment_id": "pay_xxx",
  "razorpay_signature": "xxx",
  "email": "owner@example.com",
  "business_slug": "my-gym",
  "plan_id": 1
}
```
