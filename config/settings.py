"""
Django settings for the Studio Legale Badrane LegalTech platform.

Phase F0 scaffolding: env-driven configuration, multilingua (it/fr/en/ar),
custom user model, third-party apps (HTMX, DRF, simple-history, auditlog,
django-extensions, import-export, django-filter), PII-aware logging.

Modelli legali, calcolatori e dati sensibili sono introdotti nelle fasi
successive (F1+). Nessun valore normativo o importo è hardcoded qui.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")


# ---------------------------------------------------------------------------
# Core security
# ---------------------------------------------------------------------------
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="django-insecure-dev-only-do-not-use-in-production",
)
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=["127.0.0.1", "localhost"],
)


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "django_extensions",
    "django_htmx",
    "rest_framework",
    "django_filters",
    "import_export",
    "simple_history",
    "auditlog",
]

PROJECT_APPS = [
    "apps.accounts",
    "apps.core",
    "apps.jurisdictions",
    "apps.legal_sources",
    "apps.calculators",
    "apps.cases",
    "apps.compensation",
    "apps.inheritance",
    "apps.compliance",
    "apps.crm",
    "apps.cms_content",
    "apps.reports",
    "apps.analytics",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + PROJECT_APPS


# ---------------------------------------------------------------------------
# Middleware (order matters)
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "auditlog.middleware.AuditlogMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# ---------------------------------------------------------------------------
# Templates: project-level templates/ + per-app templates/
# ---------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
            ],
        },
    },
]


# ---------------------------------------------------------------------------
# Database — SQLite in dev. PostgreSQL switch in F13 (deploy).
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ---------------------------------------------------------------------------
# Internationalization (it/fr/en/ar)
# ---------------------------------------------------------------------------
LANGUAGE_CODE = env("LANGUAGE_CODE", default="it")
TIME_ZONE = env("TIME_ZONE", default="Europe/Brussels")
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("it", "Italiano"),
    ("fr", "Français"),
    ("en", "English"),
    ("ar", "العربية"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]


# ---------------------------------------------------------------------------
# Static & media
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# Project / parent-site bridge
# ---------------------------------------------------------------------------
SITE_NAME = env("SITE_NAME", default="Simulatore Risarcimenti Studio Legale Badrane")
SITE_DOMAIN = env("SITE_DOMAIN", default="localhost:8000")
PARENT_SITE_URL = env(
    "PARENT_SITE_URL",
    default="https://international.studiolegalebadrane.it/",
)


# ---------------------------------------------------------------------------
# DRF (placeholder; serializers introdotti in fasi successive)
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
}


# ---------------------------------------------------------------------------
# Logging — PII-safe. Mai loggare body di richieste o dati utente in chiaro.
# Il filtro RedactPIIFilter maschera email, telefoni, codici fiscali italiani
# che fossero finiti per errore in messaggi di log.
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "redact_pii": {
            "()": "config.logging_filters.RedactPIIFilter",
        },
    },
    "formatters": {
        "concise": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "concise",
            "filters": ["redact_pii"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
