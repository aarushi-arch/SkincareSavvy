"""Django settings for SkincareSavvy project."""
from pathlib import Path
import os
from dotenv import load_dotenv

# Load .env from project root (BASE_DIR)
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ─── Core ─────────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-key-change-me")
DEBUG = os.environ.get("DEBUG", "True") == "True"
ALLOWED_HOSTS: list[str] = os.environ.get("ALLOWED_HOSTS", "").split(",") if os.environ.get("ALLOWED_HOSTS") else []

# ─── Apps ─────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "users",
    "user_management",
    "recommendations",
    "face_analysis",
    "shop",
    "rest_framework",
    "products",
    "widget_tweaks",
    "chat",
    "skin_journal",
]

# Enable optional third-party apps only when installed
try:
    import esewa  # type: ignore
except Exception:
    _ESEWA_PKG_AVAILABLE = False
else:
    _ESEWA_PKG_AVAILABLE = True

if _ESEWA_PKG_AVAILABLE:
    INSTALLED_APPS.append("esewa")

# ─── Middleware ────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "SkincareSavvy.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "users.context_processors.notifications_processor",
                "users.context_processors.chat_messages_processor",
            ],
        },
    },
]

WSGI_APPLICATION = "SkincareSavvy.wsgi.application"

# ─── Database ─────────────────────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ─── Auth ─────────────────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_REDIRECT_URL = "/"
LOGIN_URL = "login"
LOGOUT_REDIRECT_URL = "/"

# ─── Internationalisation ─────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ─── Static / Media ───────────────────────────────────────────────────────────
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─── Shop ─────────────────────────────────────────────────────────────────────
SHOP_FREE_SHIPPING_THRESHOLD = int(os.environ.get("SHOP_FREE_SHIPPING_THRESHOLD", 1000))
SHOP_SHIPPING_RATE            = float(os.environ.get("SHOP_SHIPPING_RATE", "49.00"))

# ===================================================
# eSewa Payment Gateway  (values come from .env)
# ===================================================
# Sandbox:   ESEWA_SANDBOX=True  + ESEWA_MERCHANT_ID=EPAYTEST
# Production: set ESEWA_SANDBOX=False and replace the keys in .env
ESEWA_SANDBOX     = os.environ.get("ESEWA_SANDBOX", "True") == "True"
ESEWA_MERCHANT_ID = os.environ.get("ESEWA_MERCHANT_ID", "EPAYTEST")
ESEWA_SECRET_KEY  = os.environ.get("ESEWA_SECRET_KEY", "8gBm/:&EnhH.1/q")
ESEWA_URL         = os.environ.get(
    "ESEWA_URL",
    "https://rc-epay.esewa.com.np/api/epay/main/v2/form",   # sandbox default
)
# Callbacks are built dynamically from request.build_absolute_uri() in views.py
# They resolve to:  <domain>/shop/esewa/success/  and  <domain>/shop/esewa/failure/

# ===================================================
# PayPal Payment Gateway  (values come from .env)
# ===================================================
# Sandbox:   PAYPAL_SANDBOX=True  + sandbox CLIENT_ID / SECRET
# Production: set PAYPAL_SANDBOX=False and replace the keys in .env
PAYPAL_SANDBOX        = os.environ.get("PAYPAL_SANDBOX", "True") == "True"
PAYPAL_CLIENT_ID      = os.environ.get("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET  = os.environ.get("PAYPAL_CLIENT_SECRET", "")
