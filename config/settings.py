"""
Django settings for config project.

Sensitive and environment-specific values are loaded from the process environment
(typically via a `.env` file — see `.env.example`).
"""

from datetime import timedelta
from pathlib import Path
import os

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def _env_bool(key: str, default: str = "false") -> bool:
    return os.getenv(key, default).lower() in ("1", "true", "yes", "on")


def _split_csv(key: str) -> list[str]:
    raw = (os.getenv(key) or "").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


# --- Security (required / env-only) ---
SECRET_KEY = (os.getenv("DJANGO_SECRET_KEY") or "").strip()
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY is missing. Add it to your .env file. "
        'Generate one: python -c "from django.core.management.utils import '
        'get_random_secret_key; print(get_random_secret_key())"'
    )

DEBUG = _env_bool("DJANGO_DEBUG", "true")

ALLOWED_HOSTS = _split_csv("DJANGO_ALLOWED_HOSTS")

# CORS (django-cors-headers)
CORS_ALLOW_ALL_ORIGINS = _env_bool("CORS_ALLOW_ALL_ORIGINS", "true")
CORS_ALLOWED_ORIGINS = _split_csv("CORS_ALLOWED_ORIGINS")

# HTTPS / cookies (enable in production behind TLS)
CSRF_TRUSTED_ORIGINS = _split_csv("CSRF_TRUSTED_ORIGINS")
SECURE_SSL_REDIRECT = _env_bool("DJANGO_SECURE_SSL_REDIRECT", "false")
SESSION_COOKIE_SECURE = _env_bool("DJANGO_SESSION_COOKIE_SECURE", "false")
CSRF_COOKIE_SECURE = _env_bool("DJANGO_CSRF_COOKIE_SECURE", "false")


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "core",
    "authentication",
    "businesses",
    "plans",
    "subscriptions",
    "assets",
    "payments",
    "corsheaders",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.RequestLoggingMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database: SQLite (default) or PostgreSQL via env
_db_backend = (os.getenv("DJANGO_DATABASE_BACKEND") or "sqlite").strip().lower()
if _db_backend in ("postgres", "postgresql"):
    _pg_user = os.getenv("POSTGRES_USER", "").strip()
    _pg_password = os.getenv("POSTGRES_PASSWORD", "")
    _pg_db = os.getenv("POSTGRES_DB", "").strip()
    if not (_pg_user and _pg_db):
        raise ImproperlyConfigured(
            "POSTGRES_USER and POSTGRES_DB are required when DJANGO_DATABASE_BACKEND=postgresql."
        )
    _pg_options = {}
    _sslmode = (os.getenv("POSTGRES_SSLMODE") or "").strip().lower()
    if _sslmode in ("disable", "allow", "prefer", "require", "verify-ca", "verify-full"):
        _pg_options["sslmode"] = _sslmode
    _default_db = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _pg_db,
        "USER": _pg_user,
        "PASSWORD": _pg_password,
        "HOST": os.getenv("POSTGRES_HOST", "localhost").strip() or "localhost",
        "PORT": os.getenv("POSTGRES_PORT", "5432").strip() or "5432",
    }
    if _pg_options:
        _default_db["OPTIONS"] = _pg_options
    # Persistent connections avoid a full TCP/TLS handshake on every request (often 0.5–4s on remote RDS).
    # Set DJANGO_DB_CONN_MAX_AGE=0 to restore per-request connect. SQLite keeps default (short-lived) behavior below.
    _conn_max_raw = (os.getenv("DJANGO_DB_CONN_MAX_AGE") or "600").strip()
    try:
        _conn_max_age = int(_conn_max_raw)
    except ValueError:
        _conn_max_age = 600
    _default_db["CONN_MAX_AGE"] = max(0, _conn_max_age)
    DATABASES = {"default": _default_db}
else:
    _sqlite_name = (os.getenv("DJANGO_SQLITE_NAME") or "db.sqlite3").strip()
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / _sqlite_name,
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = os.getenv("DJANGO_LANGUAGE_CODE", "en-us").strip() or "en-us"

TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "UTC").strip() or "UTC"

USE_I18N = True

USE_TZ = True


STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Logs directory (optional override)
LOGS_DIR = Path(os.getenv("DJANGO_LOGS_DIR", str(BASE_DIR / "logs")))
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# --- Logging (gymapp + Django integration) ---
_default_gymapp_level = "DEBUG" if DEBUG else "INFO"
GYMAPP_LOG_LEVEL = (os.getenv("DJANGO_LOG_LEVEL") or _default_gymapp_level).upper()
if GYMAPP_LOG_LEVEL not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
    GYMAPP_LOG_LEVEL = _default_gymapp_level

LOG_TO_CONSOLE = _env_bool("DJANGO_LOG_TO_CONSOLE", "true" if DEBUG else "false")

_gymapp_handlers: list[str] = ["gymapp_file"]
if LOG_TO_CONSOLE:
    _gymapp_handlers.append("console")

_root_handlers: list[str] = ["gymapp_file"]
if LOG_TO_CONSOLE:
    _root_handlers.append("console")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "gymapp": {
            "format": "{asctime} [{levelname}] {name} | {message}",
            "style": "{",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "gymapp_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOGS_DIR / "gymapp.log"),
            "maxBytes": int(os.getenv("DJANGO_LOG_FILE_MAX_BYTES", str(10 * 1024 * 1024))),
            "backupCount": int(os.getenv("DJANGO_LOG_FILE_BACKUP_COUNT", "5")),
            "formatter": "gymapp",
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "gymapp",
        },
    },
    "loggers": {
        "gymapp": {
            "handlers": _gymapp_handlers,
            "level": GYMAPP_LOG_LEVEL,
            "propagate": False,
        },
        "django.request": {
            "handlers": _gymapp_handlers,
            "level": "ERROR",
            "propagate": False,
        },
        "django.server": {
            "handlers": _gymapp_handlers,
            "level": "INFO",
            "propagate": False,
        },
    },
    "root": {
        "handlers": _root_handlers,
        "level": "WARNING",
    },
}


# --- Auth token lifetimes ---
AUTH_ACCESS_TOKEN_LIFETIME = timedelta(
    minutes=int(os.getenv("AUTH_ACCESS_TOKEN_MINUTES", "15"))
)
AUTH_REFRESH_TOKEN_LIFETIME = timedelta(days=int(os.getenv("AUTH_REFRESH_TOKEN_DAYS", "7")))
AUTH_PASSWORD_RESET_TOKEN_LIFETIME = timedelta(
    minutes=int(os.getenv("AUTH_PASSWORD_RESET_MINUTES", "60"))
)


# --- Razorpay (no defaults in code — set in .env for payments) ---
RAZORPAY_KEY_ID = (os.getenv("RAZORPAY_KEY_ID") or "").strip()
RAZORPAY_KEY_SECRET = (os.getenv("RAZORPAY_KEY_SECRET") or "").strip()


# --- Email ---
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@gymapp.local").strip()
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
).strip()
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com").strip()
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() in ("1", "true", "yes")
EMAIL_HOST_USER = (os.getenv("EMAIL_HOST_USER") or "").strip()
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD") or ""


# --- OTP ---
OTP_EXPIRE_MINUTES = max(1, int(os.getenv("OTP_EXPIRE_MINUTES", "10")))
OTP_EMAIL_SUBJECT = os.getenv("OTP_EMAIL_SUBJECT", "Your OTP Code").strip()


PAYMENT_CONFIRMATION_EMAIL_SUBJECT = os.getenv(
    "PAYMENT_CONFIRMATION_EMAIL_SUBJECT",
    "Payment confirmed – GymApp",
).strip()


OTP_PASSWORD_RESET_EMAIL_SUBJECT = os.getenv(
    "OTP_PASSWORD_RESET_EMAIL_SUBJECT",
    "Your password reset code",
).strip()


CRYSTAL_LEAD_OWNER_EMAIL_SUBJECT = (os.getenv("CRYSTAL_LEAD_OWNER_EMAIL_SUBJECT") or "").strip()


# Team inbox (new signups + website enquiries). Use the same Gmail as SMTP user for simplest setup.
CRYSTAL_TEAM_NOTIFY_EMAIL = (
    os.getenv("CRYSTAL_TEAM_NOTIFY_EMAIL") or "crystal.gym.in@gmail.com"
).strip()
NEW_USER_NOTIFY_ENABLED = _env_bool("NEW_USER_NOTIFY_ENABLED", "true")
NEW_USER_NOTIFY_SUBJECT = (
    os.getenv("NEW_USER_NOTIFY_SUBJECT") or "New potential client – Crystal Gym"
).strip()
SITE_ENQUIRY_EMAIL_SUBJECT = (
    os.getenv("SITE_ENQUIRY_EMAIL_SUBJECT") or "Website enquiry – Crystal Gym"
).strip()
SERVICE_ENQUIRY_EMAIL_SUBJECT = (
    os.getenv("SERVICE_ENQUIRY_EMAIL_SUBJECT") or "Service enquiry – Crystal Gym"
).strip()

CLIENT_SUPPORT_EMAIL_SUBJECT_PREFIX = (
    os.getenv("CLIENT_SUPPORT_EMAIL_SUBJECT_PREFIX") or "[Crystal Gym]"
).strip()


GOOGLE_OAUTH_CLIENT_ID = (os.getenv("GOOGLE_OAUTH_CLIENT_ID") or "").strip()


# --- S3 gym images (owner uploads; keys: {slug}/{uuid}.ext) ---
# Standard AWS names, or aliases S3_ACCESS_KEY / S3_SECRET_KEY (same values).
AWS_ACCESS_KEY_ID = (
    os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("S3_ACCESS_KEY") or ""
).strip()
AWS_SECRET_ACCESS_KEY = (
    os.getenv("AWS_SECRET_ACCESS_KEY") or os.getenv("S3_SECRET_KEY") or ""
).strip()
AWS_S3_REGION_NAME = (os.getenv("AWS_S3_REGION_NAME") or "ap-south-1").strip()
AWS_S3_GYM_IMAGES_BUCKET = (os.getenv("AWS_S3_GYM_IMAGES_BUCKET") or "").strip()
# Bucket's actual AWS region for public URLs (host = bucket.s3.<region>.amazonaws.com). Set when the bucket
# is not in AWS_S3_REGION_NAME or s3:GetBucketLocation is unavailable — avoids PermanentRedirect in browsers.
AWS_S3_GYM_IMAGES_BUCKET_REGION = (os.getenv("AWS_S3_GYM_IMAGES_BUCKET_REGION") or "").strip()
# Optional: public base URL (e.g. CloudFront https://dxxxx.cloudfront.net). If empty, URL is built as https://{bucket}.s3.{region}.amazonaws.com/
AWS_S3_GYM_IMAGES_URL_PREFIX = (os.getenv("AWS_S3_GYM_IMAGES_URL_PREFIX") or "").strip()
# Comma-separated origins for S3 CORS (browser fetch/canvas). Empty = use "*" in configure_s3_gym_bucket.
AWS_S3_GYM_IMAGES_CORS_ORIGINS = _split_csv("AWS_S3_GYM_IMAGES_CORS_ORIGINS")
# When true, gym image S3 calls use boto3 default credential chain without requiring env keys (EC2 role, ~/.aws).
# Do not enable on random laptops unless credentials exist — otherwise put_object may hang probing IMDS.
GYM_IMAGES_USE_DEFAULT_AWS_CREDENTIALS = _env_bool(
    "GYM_IMAGES_USE_DEFAULT_AWS_CREDENTIALS", "false"
)
# Private bucket: return time-limited presigned GET URLs from the images API instead of plain object URLs.
# Default true: private buckets get working browser URLs. Set false if objects are public and you want stable, cacheable URLs.
AWS_S3_GYM_IMAGES_USE_PRESIGNED_GET = _env_bool("AWS_S3_GYM_IMAGES_USE_PRESIGNED_GET", "true")
# Presigned GET lifetime in seconds (default 1 hour). SigV4 URLs include X-Amz-Expires=<this value>.
try:
    _gym_presign_exp = int((os.getenv("AWS_S3_GYM_IMAGES_PRESIGNED_EXPIRES") or "3600").strip())
except ValueError:
    _gym_presign_exp = 3600
AWS_S3_GYM_IMAGES_PRESIGNED_EXPIRES = max(60, min(_gym_presign_exp, 604800))
