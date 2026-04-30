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

# CSRF: lista degli origin trusted (richiesto da Django 4+ per CSRF
# protection dietro reverse proxy SSL). In dev resta vuota.
CSRF_TRUSTED_ORIGINS = env.list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    default=[],
)


# ---------------------------------------------------------------------------
# Production hardening — solo quando DEBUG=False.
# Tutti i flag sono env-driven con default sicuri per dev (False),
# così che attivare la produzione richieda configurazione esplicita.
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = env.bool("DJANGO_SESSION_COOKIE_SECURE", default=True)
    CSRF_COOKIE_SECURE = env.bool("DJANGO_CSRF_COOKIE_SECURE", default=True)
    SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True)
    SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=False)
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = env("DJANGO_SECURE_REFERRER_POLICY", default="same-origin")
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    X_FRAME_OPTIONS = "DENY"

    # Guard difensivo: una piattaforma legale in prod NON deve girare
    # con la SECRET_KEY di sviluppo. Il fail è fatale all'avvio: meglio
    # 500 immediato che vulnerabilità silenziosa.
    if SECRET_KEY.startswith("django-insecure-"):
        raise RuntimeError(
            "DJANGO_SECRET_KEY is the insecure default. Refusing to start "
            "in production. Set a real secret via DJANGO_SECRET_KEY env var."
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
    # MFA admin guard: no-op quando ADMIN_MFA_REQUIRED=False (default).
    # Posizionato dopo AuthenticationMiddleware perché ha bisogno di
    # `request.user` valorizzato.
    "apps.core.admin_mfa.AdminMFAMiddleware",
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
                "apps.core.context_processors.site_context",
            ],
        },
    },
]


# ---------------------------------------------------------------------------
# Database — SQLite in dev, Postgres in prod via DATABASE_URL.
# `env.db_url` parses a single URL like:
#   postgres://user:pass@host:5432/dbname
# Default fallback resta SQLite per non rompere lo sviluppo locale.
# ---------------------------------------------------------------------------
DATABASES = {
    "default": env.db_url(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    ),
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
# Public POST rate-limit (F-local-product-hardening-pass1)
#
# Limite cache-based applicato dal decoratore
# `apps.core.rate_limit.public_post_rate_limit` agli endpoint POST pubblici
# (contact form, wizard simulazione). NON sostituisce un WAF/reverse proxy
# in produzione: serve come prima linea di difesa contro flooding banale e
# come gating per evitare creazione di Lead/Simulation in massa durante
# demo locale o smoke su staging.
# ---------------------------------------------------------------------------
PUBLIC_POST_RATE_LIMIT_ENABLED = env.bool("PUBLIC_POST_RATE_LIMIT_ENABLED", default=True)
PUBLIC_POST_RATE_LIMIT_WINDOW_SECONDS = env.int(
    "PUBLIC_POST_RATE_LIMIT_WINDOW_SECONDS", default=3600
)
PUBLIC_POST_RATE_LIMIT_MAX_ATTEMPTS = env.int("PUBLIC_POST_RATE_LIMIT_MAX_ATTEMPTS", default=20)


# ---------------------------------------------------------------------------
# Email — notifica transazionale Lead (F-local-product-hardening-pass2-email-lead)
#
# In dev (DEBUG=True) il backend default è `console` così le email
# stampano in stdout senza richiedere SMTP. In produzione si configurerà
# `DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` +
# i settings SMTP standard via env. Per i test, `pytest` usa
# automaticamente il backend `locmem` se non override (vedi conftest /
# override_settings nei test dedicati).
# ---------------------------------------------------------------------------
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default=(
        "django.core.mail.backends.console.EmailBackend"
        if DEBUG
        else "django.core.mail.backends.smtp.EmailBackend"
    ),
)
DEFAULT_FROM_EMAIL = env(
    "DJANGO_DEFAULT_FROM_EMAIL",
    default="no-reply@badrane.local",
)
EMAIL_SUBJECT_PREFIX = env("DJANGO_EMAIL_SUBJECT_PREFIX", default="[Badrane LegalTech] ")

# Lead notification: invia un'email allo Studio quando un nuovo Lead
# entra. Privacy-minimized: il body include solo public_id, timestamp,
# nome/email/telefono, country/case_type/lingua, simulation public_id se
# presente. NON include ip_address, user_agent, session_key,
# internal_notes (lo Studio li consulta in admin).
LEAD_NOTIFICATION_ENABLED = env.bool("LEAD_NOTIFICATION_ENABLED", default=True)
LEAD_NOTIFICATION_TO_EMAILS = env.list("LEAD_NOTIFICATION_TO_EMAILS", default=[])


# ---------------------------------------------------------------------------
# Sentry — error monitoring opzionale (F-local-product-hardening-pass3-sentry)
#
# DSN vuoto = no-op completo: `init_sentry_from_settings()` esce
# subito senza importare sentry_sdk, così il codebase resta
# eseguibile anche su una macchina senza il pacchetto installato.
# `send_default_pii=False` di default per non spedire IP/user-id a
# Sentry; il privacy scrubber `scrub_sentry_event` redige email,
# telefoni, nomi, message, session/CSRF token in qualunque punto del
# payload (request body, breadcrumbs, ecc.).
# ---------------------------------------------------------------------------
SENTRY_DSN = env("SENTRY_DSN", default="")
SENTRY_ENVIRONMENT = env(
    "SENTRY_ENVIRONMENT",
    default=("local" if DEBUG else "production"),
)
SENTRY_TRACES_SAMPLE_RATE = env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0)
SENTRY_PROFILES_SAMPLE_RATE = env.float("SENTRY_PROFILES_SAMPLE_RATE", default=0.0)
SENTRY_SEND_DEFAULT_PII = env.bool("SENTRY_SEND_DEFAULT_PII", default=False)


# ---------------------------------------------------------------------------
# MFA admin (F-local-product-hardening-pass5-mfa-admin)
#
# Quando `ADMIN_MFA_REQUIRED=False` (default in dev), il middleware
# `apps.core.admin_mfa.AdminMFAMiddleware` non altera il flusso admin.
# Quando `True`, gli staff senza OTP verificato vedono una pagina di
# enforcement (HTTP 403) e devono passare per il flusso TOTP. Il
# verifier è duck-typed:
# - se django-otp è installato + cabled (OTPMiddleware), usa
#   `user.is_verified()`;
# - altrimenti fallback a `request.session["mfa_verified"]==True`,
#   utile per test e per un eventuale flusso custom interno.
# ---------------------------------------------------------------------------
ADMIN_MFA_REQUIRED = env.bool("ADMIN_MFA_REQUIRED", default=False)


# ---------------------------------------------------------------------------
# Celery (F-local-product-hardening-pass7-celery-async)
#
# Locale-first: i settings sono pronti ma il dispatch async è OFF di
# default (`LEAD_NOTIFICATION_ASYNC_ENABLED=False`). In dev/test,
# avviare Celery non è obbligatorio: il fallback sincrono in
# `apps/crm/views.py::contact` continua a funzionare.
#
# In Docker locale (vedi docker-compose.local.yml + il pass 6),
# `redis` è già up come broker. Per attivare il dispatch async:
#   LEAD_NOTIFICATION_ASYNC_ENABLED=True
#   CELERY_BROKER_URL=redis://redis:6379/0  (default in compose)
# e un container `celery-worker` deve essere in piedi.
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = env(
    "CELERY_BROKER_URL",
    default=env("REDIS_URL", default="redis://localhost:6379/0"),
)
# Result backend disabilitato di default: il task `send_lead_notification_task`
# non ha bisogno di tracking risultato (è "fire-and-forget" con retry).
# Settare a `redis://...` o a `db+postgresql://...` se si introducono task
# che richiedono il risultato (es. PDF report jobs).
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="")
# In dev/test eager=False di default così il flusso resta esplicito.
# Test che vogliono eseguire il task sincronamente fanno
# `override_settings(CELERY_TASK_ALWAYS_EAGER=True)`.
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = env.bool("CELERY_TASK_EAGER_PROPAGATES", default=True)
# Serializzazione esplicita (default storico Celery 5.x).
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE

# Lead notification: dispatch async opt-in. Default False = comportamento
# del pass 2 (sincrono in-request).
LEAD_NOTIFICATION_ASYNC_ENABLED = env.bool("LEAD_NOTIFICATION_ASYNC_ENABLED", default=False)


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
