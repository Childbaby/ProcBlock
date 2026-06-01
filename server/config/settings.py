"""
ProcBase – Django Settings
All secrets are read from environment variables.
No credentials are hardcoded.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Security ─────────────────────────────────────────────────────────────────
DEBUG = os.environ.get("DEBUG", "False") == "True"
if DEBUG:
    SECRET_KEY = os.environ.get("SECRET_KEY", "unsafe-development-secret")
    ALLOWED_HOSTS = os.environ.get(
        "ALLOWED_HOSTS",
        "localhost,127.0.0.1,0.0.0.0",
    ).split(",")
else:
    SECRET_KEY = os.environ["SECRET_KEY"]
    ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# ── Application registry ─────────────────────────────────────────────────────
JAZZMIN_SETTINGS = {
    "site_title": "ProcBase Admin",
    "site_header": "ProcBase Zambia",
    "site_brand": "ProcBase",
    "welcome_sign": "ProcBase Supply Chain Management",
    "theme": "darkly",
    "dark_mode_theme": "darkly",
    "icons": {
        "auth": "fas fa-users-cog",
        "app.medicine": "fas fa-pills",
        "app.auditEvent": "fas fa-clipboard-list",
    },
    "custom_css": "admin/css/custom.css",
    "show_ui_builder": False,
}

INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "app",
    # Celery helper apps
    "django_celery_beat",
    "django_celery_results",
]

# ── Middleware ────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # ↓  PII firewall – runs before any view sees the request body
    "middleware.privacy.PIISanitizationMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

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
            ],
        },
    }
]

# ── Database ──────────────────────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "procbase"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "db"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "OPTIONS": {"connect_timeout": 10},
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Auth / DRF ────────────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    # Token auth for API consumers; session auth for the browsable API
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

# ── Celery + Redis (Burst Sync – NFR-03) ─────────────────────────────────────
CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_ACKS_LATE = True          # tasks survive worker restart
CELERY_WORKER_PREFETCH_MULTIPLIER = 1 # prevent hoarding during poor connectivity

CELERY_BEAT_SCHEDULE = {
    "flush-pending-syncs": {
        "task": "app.tasks.flush_pending_syncs",
        "schedule": 300,  # every 5 minutes
    },
}

# ── Security headers ──────────────────────────────────────────────────────────
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
# Enable HSTS and SSL redirect in production (controlled by env var)
if os.environ.get("DJANGO_SECURE", "False") == "True":
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# ── Static files ──────────────────────────────────────────────────────────────
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ── Solana bridge – read-only config (keys stay in env) ───────────────────────
SOLANA_RPC_URL = os.environ.get("SOLANA_RPC_URL", "https://api.devnet.solana.com")
SOLANA_PROGRAM_ID = os.environ.get("SOLANA_PROGRAM_ID", "")
SOLANA_PAYER_KEYPAIR_PATH = os.environ.get("SOLANA_PAYER_KEYPAIR_PATH", "")
SOLANA_BRIDGE_MODE = os.environ.get("SOLANA_BRIDGE_MODE", "anchor")
SOLANA_HUB_CODE = os.environ.get("SOLANA_HUB_CODE", "")
SOLANA_MEDICINE_CODE_PREFIX = os.environ.get("SOLANA_MEDICINE_CODE_PREFIX", "MED")
SOLANA_ALLOW_MEMO_FALLBACK = os.environ.get("SOLANA_ALLOW_MEMO_FALLBACK", "True") == "True"

# ── Internationalisation ──────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lusaka"
USE_I18N = True
USE_TZ = True
