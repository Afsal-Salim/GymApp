# GymApp — Database Documentation

This document describes the **logical data model** for the GymApp Django project: entities, relationships, field purposes, and Django table names. It is intended for developers and operators reviewing schema, migrations, or reporting.

---

## 1. Overview

| Item | Detail |
|------|--------|
| **ORM** | Django 5.x |
| **Default engine** | SQLite (`db.sqlite3` in the project root), configurable via environment (see `config/settings.py` — optional PostgreSQL). |
| **Migrations** | Per app under `<app>/migrations/`; apply with `python manage.py migrate`. |
| **Naming** | Django default table names: `<app_label>_<model_name_lowercase>`. |

The project also creates standard **Django contrib** tables (e.g. `django_migrations`, `auth_user`, `django_session`, …) when those apps are installed. Below focuses on **domain** tables.

---

## 2. Entity relationship (high level)

```
Customer (authentication)
    │
    ├──< Business (businesses)
    │       ├──< Subscription (subscriptions) ──> Plan (plans)
    │       ├──< Payment (payments)
    │       ├──< Asset (assets)
    │       └──< CrystalLead (businesses)

Plan (plans)
    └──< Feature (plans)

EmailOTP (authentication) — standalone; links by email + token, not FK to Customer
```

---

## 3. Application: `authentication`

### 3.1 `Customer` → `authentication_customer`

Represents an end-user account (gym owner / customer). **Not** Django’s `auth.User`; authentication for APIs uses custom tokens tied to this model.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | bigint | PK, auto | Surrogate key |
| `username` | varchar(150) | unique, default `""` | Display / login handle |
| `email` | varchar | unique | Primary identifier for email login |
| `password` | varchar(128) | | Stored digest (SHA-256 of optional `CUSTOMER_PASSKEY` + password) |
| `auth_provider` | varchar(20) | choices | `email` or `google` |
| `google_id` | varchar(255) | unique, nullable | Google `sub` when using Google sign-in |
| `created_at` | datetime | auto | Row creation |
| `updated_at` | datetime | auto | Last update |

**Notes:** Plain-looking passwords are hashed on `save()` when not already a 64-char hex digest. Google-only users receive an internal random digest not used for email login.

---

### 3.2 `EmailOTP` → `authentication_emailotp`

Stores one-time codes for **signup** and **password reset** flows.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | bigint | PK | |
| `email` | varchar | | Target email |
| `otp` | varchar(6) | | Numeric/code string |
| `token` | UUID | unique per row | Client passes this with OTP |
| `purpose` | varchar(20) | choices | `signup` or `password_reset` |
| `created_at` | datetime | auto | Used with `OTP_EXPIRE_MINUTES` for expiry |
| `is_verified` | bool | default false | Set true after successful verify |

**Notes:** No foreign key to `Customer`; correlation is by `email` and `token`. Rows may be deleted after password reset completion.

---

## 4. Application: `businesses`

### 4.1 `Business` → `businesses_business`

A gym or business profile owned by one customer.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | bigint | PK | |
| `owner_id` | bigint | FK → `authentication_customer`, CASCADE | Owner |
| `name` | varchar(255) | | Public name |
| `slug` | slug | unique | URL-safe identifier |
| `description` | text | optional | Short / long text |
| `phone` | varchar(50) | optional | Contact (can be synced from Crystal `content.contacts`) |
| `address` | text | optional | Address (synced from contacts item `id: address` on website-setup) |
| `location_map_url` | URL (max 2000) | optional | Map link (e.g. `content.contacts.locationMapUrl`) |
| `website_theme` | JSON | default `{}` | Crystal theme (colors, etc.) |
| `website_content` | JSON | default `{}` | Crystal page content tree |
| `created_at` | datetime | auto | |
| `updated_at` | datetime | auto | |

**Reverse relations:** `subscriptions`, `payments`, `assets`, `crystal_leads`.

---

### 4.2 `CrystalLead` → `businesses_crystallead`

Append-only **lead events** and **analytics** (modals, WhatsApp taps).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | bigint | PK | |
| `business_id` | bigint | FK → `businesses_business`, CASCADE | |
| `lead_type` | varchar(32) | indexed | `join_now`, `book_free_trial`, `plan_visit`, `whatsapp_click` |
| `payload` | JSON | default `{}` | Raw request body snapshot |
| `submitted_at_ms` | bigint | nullable | Client-supplied epoch ms |
| `quantity` | smallint unsigned | default 1 | For WhatsApp: click count (capped in app logic) |
| `created_at` | datetime | auto | Server event time |

**Index:** `(business_id, lead_type, created_at DESC)` for analytics queries.

---

## 5. Application: `plans`

### 5.1 `Plan` → `plans_plan`

Sellable subscription product definition.

| Column | Type | Description |
|--------|------|-------------|
| `id` | bigint PK | |
| `name` | varchar(255) | Plan name |
| `price` | decimal(10,2) | Unit price |
| `currency` | varchar(10) | e.g. `INR` |
| `duration` | positive int | Length in **days** |
| `created_at` | datetime | |

---

### 5.2 `Feature` → `plans_feature`

Feature bullet tied to a plan.

| Column | Type | Description |
|--------|------|-------------|
| `id` | bigint PK | |
| `plan_id` | FK → `plans_plan`, CASCADE | Parent plan |
| `name` | varchar(255) | Feature label |
| `created_at` | datetime | |

---

## 6. Application: `subscriptions`

### 6.1 `Subscription` → `subscriptions_subscription`

Active or historical subscription instance for a business.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | bigint | PK | |
| `business_id` | bigint | FK → `businesses_business`, CASCADE | |
| `plan_id` | bigint | FK → `plans_plan`, PROTECT | Plan cannot be deleted if referenced |
| `payment_id` | varchar(255) | optional | External payment reference (e.g. Razorpay) |
| `subscription_start_date` | date | | Inclusive start |
| `subscription_end_date` | date | | Inclusive end (app logic defines “active”) |

---

## 7. Application: `payments`

### 7.1 `Payment` → `payments_payment`

Recorded payment after successful Razorpay verification.

| Column | Type | Description |
|--------|------|-------------|
| `id` | bigint PK | |
| `business_id` | FK → `businesses_business`, CASCADE | |
| `razorpay_order_id` | varchar(255) | |
| `razorpay_payment_id` | varchar(255) | |
| `razorpay_signature` | varchar(255) | |
| `amount` | decimal(10,2) | |
| `currency` | varchar(10) | |
| `payment_status` | varchar(50) | e.g. `captured` |
| `payment_method` | varchar(50) | optional |
| `created_at` | datetime | |

---

## 8. Application: `assets`

### 8.1 `Asset` → `assets_asset`

Media metadata linked to a business (e.g. gallery images).

| Column | Type | Description |
|--------|------|-------------|
| `id` | bigint PK | |
| `business_id` | FK → `businesses_business`, CASCADE | |
| `image_url` | URL | Remote URL string |
| `asset_type` | varchar(50) | Category / kind |
| `uploaded_at` | datetime | |

---

## 9. Application: `core`

No models defined; no `core_*` domain tables.

---

## 10. Operational notes

| Topic | Guidance |
|--------|-----------|
| **Backups** | For SQLite, copy `db.sqlite3` when the app is idle or use SQLite backup APIs. For PostgreSQL, use provider snapshots / `pg_dump`. |
| **Secrets** | Database credentials and `DJANGO_SECRET_KEY` belong in environment / secret store, not in the repository. |
| **Integrity** | `PROTECT` on `Subscription.plan` prevents orphan subscriptions if someone deletes a `Plan` still in use. |
| **PII** | `Customer.email`, lead `payload`, and payment rows may contain personal data — handle per your privacy policy. |

---

*Schema descriptions reflect the Django models in this repository; after model changes, run `makemigrations` / `migrate` and update this document if the public contract changes.*
