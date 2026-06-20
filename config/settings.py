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
    # WhiteNoise's runserver_nostatic shim (F-p2-perf-1). Subclasses
    # `runserver` to default `--nostatic` to True so the static-files
    # handler doesn't short-circuit our middleware chain — required
    # for WhiteNoiseMiddleware to actually serve / compress static
    # files in dev. Must be listed BEFORE `django.contrib.staticfiles`
    # for the management-command resolution order.
    "whitenoise.runserver_nostatic",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Sitemap framework — usato da apps.core.sitemaps per /sitemap.xml.
    # Non richiede `django.contrib.sites`: il view-helper passa
    # `RequestSite(request)` quando il sites framework non è installato.
    "django.contrib.sitemaps",
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
    # Static-file serving with auto-compression (F-p2-perf-1).
    # WhiteNoise serves files under STATIC_URL with gzip (and
    # brotli if available), and sets Cache-Control. Must sit
    # directly under SecurityMiddleware so it short-circuits
    # static-file requests early in the chain — see WhiteNoise
    # docs.  In dev (DEBUG=True) it uses the staticfiles finders
    # directly (WHITENOISE_USE_FINDERS=True below), so it works
    # without a `collectstatic` step.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # GZip compression for dynamic responses (F-p2-perf-1). Django
    # built-in, no new dependency. Compresses non-streaming
    # responses (HTML) for clients that send `Accept-Encoding:
    # gzip`. WhiteNoise above already handles static files.
    # BREACH: Django >= 1.10 masks CSRF tokens per-request, which
    # defangs the BREACH attack on the most common Django leak
    # vector. In production the upstream CDN/WAF typically owns
    # transport compression; this middleware is a no-op when the
    # upstream layer has already set `Content-Encoding`.
    "django.middleware.gzip.GZipMiddleware",
    # CSP middleware (F-p0-codice-4-csp): emette Content-Security-Policy
    # quando CONTENT_SECURITY_POLICY e' configurato (vedi sotto). Posizionato
    # subito dopo SecurityMiddleware (early in the chain) cosi' che la policy
    # esca anche per response generate da middleware/view in seguito.
    # Lazy: se CSP_ENABLED=False, le DIRECTIVES sono vuote e il middleware
    # non emette nulla.
    "csp.middleware.CSPMiddleware",
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
                # F-p0-codice-2-hreflang-globale: inietta
                # `hreflang_alternates` per pagine pubbliche multilingua
                # (allowlist esplicita).
                "apps.core.context_processors.seo_global_hreflang",
                # F-p0-codice-4-csp: espone `CSP_NONCE` al template per
                # gli inline `<script>` e `<style>`. Il valore e' lazy:
                # se il template non lo usa, il middleware non emette
                # `'nonce-...'` nell'header.
                "csp.context_processors.nonce",
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
# Caches — backend CONDIVISO obbligatorio in produzione.
#
# Il rate limiter pubblico (`apps/core/rate_limit.py`) e il rilevatore di
# brute-force admin (`apps/compliance/staff_security.py`) usano
# `django.core.cache.cache`. Senza un `CACHES` esplicito Django ripiega su
# LocMemCache per-processo: con più worker gunicorn ogni worker conta i
# tentativi in isolamento, moltiplicando di fatto il limite per il numero di
# worker e azzerando i contatori a ogni restart.
#
# In produzione (DEBUG=False) usiamo Redis — già nello stack come broker
# Celery — quando è disponibile un URL (`CACHE_URL`, fallback `REDIS_URL`).
# In dev/test (o se nessun URL Redis è configurato) restiamo su LocMemCache
# per non introdurre una dipendenza esterna. Quando lo staging guadagnerà il
# servizio Redis (cfr. roadmap H3-3), basterà valorizzare `REDIS_URL`.
# ---------------------------------------------------------------------------
_SHARED_CACHE_URL = env("CACHE_URL", default=env("REDIS_URL", default=""))
if not DEBUG and _SHARED_CACHE_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _SHARED_CACHE_URL,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "badrane-legaltech-default",
        }
    }


# ---------------------------------------------------------------------------
# System checks volutamente silenziati.
#
# `security.W021` (SECURE_HSTS_PRELOAD non True) è una scelta deliberata: il
# preload HSTS è opt-in e va richiesto esplicitamente solo quando il dominio
# è pronto a essere inviato alla preload list del browser (vedi
# `SECURE_HSTS_PRELOAD` più sotto). La silenziamo così che
# `manage.py check --deploy --fail-level WARNING` possa essere un gate CI
# rigido su TUTTI gli altri controlli di hardening (SSL redirect, HSTS,
# cookie sicuri, SECRET_KEY, ALLOWED_HOSTS, ...). Per abilitare il preload:
# `SECURE_HSTS_PRELOAD=True` e rimuovere questa riga.
# ---------------------------------------------------------------------------
SILENCED_SYSTEM_CHECKS = ["security.W021"]


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

# WhiteNoise — static file delivery with auto-compression (P2-PERF-1).
#
# - In dev (DEBUG=True) `WHITENOISE_USE_FINDERS=True` makes WhiteNoise
#   read the source static dirs via the staticfiles finders, so no
#   `collectstatic` is needed between edits. In production the
#   deploy step still runs `collectstatic`; WhiteNoise will then
#   serve from STATIC_ROOT (the canonical path).
# - `WHITENOISE_MAX_AGE` controls Cache-Control: 600 s for unhashed
#   files in dev (the default 60 was too aggressive for Lighthouse's
#   `cache-insight` audit on hashed-free assets). In production with
#   `ManifestStaticFilesStorage` files carry content-hashes and
#   WhiteNoise auto-bumps them to year-long immutable.
# - Auto-compression: WhiteNoise pre-compresses on first request and
#   caches the compressed payload in memory; subsequent requests are
#   served without recompression cost.
WHITENOISE_USE_FINDERS = True
WHITENOISE_MAX_AGE = 600
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Root for the project's legal-data tree. Every official-source
# fetch / attach / extraction command must derive its on-disk
# location from this setting (never from ``BASE_DIR`` directly), so
# pytest can redirect it to a per-test ``tmp_path`` and never
# clobber the real Moudawana / Badinter / DPR / Loi-1989 / EU-650
# downloads on disk.
#
# Source-of-truth iter: F-legal-data-test-fixture-isolation-pass1.
LEGAL_DATA_ROOT = BASE_DIR / "legal_data"

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
# Studio professional identification (F-p0-codice-3-footer-pass1)
#
# Identificativi obbligatori per conformita' deontologica forense
# (art. 17-bis Cod. deont. + D.Lgs. 70/2003 art. 7 + L. 247/2012 art. 12).
# Esposti al template via `apps.core.context_processors.site_context`.
#
# Default: stringa vuota -> il footer mostra placeholder
# `[da configurare prima del go-live]` (vedi
# `templates/partials/footer.html`). In produzione il system check
# `core.E001` (`apps/core/checks.py`) fa fallire `manage.py check`
# se i campi minimi obbligatori sono vuoti.
#
# Filosofia: niente dati inventati. Lo Studio fornisce i valori reali
# via env var prima del go-live. La struttura e' pronta, i dati no.
# ---------------------------------------------------------------------------
STUDIO_LEAD_LAWYER_NAME = env("STUDIO_LEAD_LAWYER_NAME", default="")
STUDIO_BAR_ASSOCIATION = env("STUDIO_BAR_ASSOCIATION", default="")
STUDIO_BAR_REGISTRATION_NUMBER = env("STUDIO_BAR_REGISTRATION_NUMBER", default="")
STUDIO_VAT_NUMBER = env("STUDIO_VAT_NUMBER", default="")
STUDIO_TAX_CODE = env("STUDIO_TAX_CODE", default="")
STUDIO_PEC_EMAIL = env("STUDIO_PEC_EMAIL", default="")
STUDIO_PHYSICAL_ADDRESS = env("STUDIO_PHYSICAL_ADDRESS", default="")
STUDIO_PROFESSIONAL_INSURANCE_INSURER = env("STUDIO_PROFESSIONAL_INSURANCE_INSURER", default="")
STUDIO_PROFESSIONAL_INSURANCE_POLICY = env("STUDIO_PROFESSIONAL_INSURANCE_POLICY", default="")
STUDIO_PROFESSIONAL_INSURANCE_CEILING = env("STUDIO_PROFESSIONAL_INSURANCE_CEILING", default="")


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
# Staff brute-force detector (F-local-product-hardening-pass9)
#
# Detection-only: nessun blocco automatico, nessuna lockout. Quando
# il detector individua N failed login admin entro la window per lo
# stesso username_hash o ip_address_masked, crea un
# `StaffSecurityAlert` consultabile dall'admin (e opzionalmente
# notificato via email).
# ---------------------------------------------------------------------------
STAFF_LOGIN_ALERTS_ENABLED = env.bool("STAFF_LOGIN_ALERTS_ENABLED", default=True)
STAFF_LOGIN_ALERT_WINDOW_SECONDS = env.int("STAFF_LOGIN_ALERT_WINDOW_SECONDS", default=900)
STAFF_LOGIN_ALERT_THRESHOLD = env.int("STAFF_LOGIN_ALERT_THRESHOLD", default=5)
STAFF_LOGIN_ALERT_COOLDOWN_SECONDS = env.int("STAFF_LOGIN_ALERT_COOLDOWN_SECONDS", default=3600)
STAFF_LOGIN_ALERT_EMAIL_ENABLED = env.bool("STAFF_LOGIN_ALERT_EMAIL_ENABLED", default=False)
STAFF_LOGIN_ALERT_TO_EMAILS = env.list("STAFF_LOGIN_ALERT_TO_EMAILS", default=[])


# ---------------------------------------------------------------------------
# Staff audit retention (F-local-product-hardening-pass10)
#
# Policy retention per StaffAccessEvent (pass 8) e StaffSecurityAlert
# (pass 9). Default dry-run=True: nessuna cancellazione finché lo
# Studio non setta esplicitamente STAFF_AUDIT_RETENTION_DRY_RUN=False.
# Si applica SOLO ai due modelli di audit staff: NON tocca
# PrivacyAuditEvent, LegalReview, SimulationReport, Lead, Simulation.
# ---------------------------------------------------------------------------
STAFF_ACCESS_EVENT_RETENTION_DAYS = env.int("STAFF_ACCESS_EVENT_RETENTION_DAYS", default=90)
STAFF_SECURITY_ALERT_RETENTION_DAYS = env.int("STAFF_SECURITY_ALERT_RETENTION_DAYS", default=180)
STAFF_AUDIT_RETENTION_ENABLED = env.bool("STAFF_AUDIT_RETENTION_ENABLED", default=True)
STAFF_AUDIT_RETENTION_DRY_RUN = env.bool("STAFF_AUDIT_RETENTION_DRY_RUN", default=True)


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
# Pexels image integration (F-product-pexels-image-integration)
#
# Sorgente immagini professionali per le country landing e la home.
# Tutto è opt-in: senza `PEXELS_API_KEY` impostato, il sito serve
# il fallback statico (SVG OG + nessuna hero photo). Niente chiamata
# Pexels viene fatta dal browser; la API key resta server-side e
# viene letta SOLO da env. Il modulo `apps.core.pexels` ha un
# guard hardcoded che rifiuta di operare se la key è vuota.
#
# `PEXELS_ENABLED` permette di disattivare il flusso anche con la
# key configurata (utile in test/staging per non chiamare il
# rate-limited endpoint reale).
# ---------------------------------------------------------------------------
PEXELS_API_KEY = env("PEXELS_API_KEY", default="")
PEXELS_ENABLED = env.bool("PEXELS_ENABLED", default=False)
PEXELS_API_BASE_URL = env(
    "PEXELS_API_BASE_URL",
    default="https://api.pexels.com/v1",
)
PEXELS_CACHE_DAYS = env.int("PEXELS_CACHE_DAYS", default=30)
PEXELS_DEFAULT_ORIENTATION = env("PEXELS_DEFAULT_ORIENTATION", default="landscape")
PEXELS_DEFAULT_PER_PAGE = env.int("PEXELS_DEFAULT_PER_PAGE", default=10)


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


# ---------------------------------------------------------------------------
# Privacy & special-category consent versions (F-p0-leg-3-consent)
#
# Versionamento del testo dei due consensi che la piattaforma raccoglie
# da ogni form pubblico (vedi `templates/partials/consent_checkboxes.html`).
# Il valore qui memorizzato finisce in:
#  - `crm.Lead.privacy_consent_version` /
#    `crm.Lead.special_categories_consent_version`
#  - `cases.Simulation.privacy_consent_version` /
#    `cases.Simulation.special_categories_consent_version`
#  - `compliance.ConsentRecord.text_version` (quando il record viene
#    creato con `purpose=privacy_general` o `purpose=special_categories_processing`)
# cosi' il consenso e' tracciabile alla versione esatta del testo
# che l'utente ha visto al momento del submit.
#
# Default `working-copy-...`: scaffold tecnico. Lo Studio firmera' la
# versione definitiva (es. `2026-09-15-final`) prima del go-live. Il
# system check `core.E004` (`apps/core/checks.py`) blocca il deploy
# in produzione finche' la versione contiene `working-copy` o `draft`.
# ---------------------------------------------------------------------------
PRIVACY_NOTICE_VERSION = env("PRIVACY_NOTICE_VERSION", default="working-copy-2026-05-10")
SPECIAL_CATEGORIES_NOTICE_VERSION = env(
    "SPECIAL_CATEGORIES_NOTICE_VERSION", default="working-copy-2026-05-10"
)


# ---------------------------------------------------------------------------
# CRM webhook dispatcher (F-p1-crm-1-webhook-dispatcher)
#
# Outbox pattern verso un endpoint CRM/n8n. Default OFF: nessuna
# delivery viene creata o spedita finche' lo Studio non configura
# l'endpoint reale + il secret HMAC.
#
# Tutti i payload sono firmati HMAC-SHA256 su `timestamp + "." + body`.
# Vedi `docs/integrations/N8N_CRM_WEBHOOK.md` per il runbook lato n8n.
# Il system check `crm.E002` blocca produzione se ENABLED=True con
# URL/secret invalidi.
# ---------------------------------------------------------------------------
CRM_WEBHOOK_ENABLED = env.bool("CRM_WEBHOOK_ENABLED", default=False)
CRM_WEBHOOK_URL = env("CRM_WEBHOOK_URL", default="")
CRM_WEBHOOK_SECRET = env("CRM_WEBHOOK_SECRET", default="")
CRM_WEBHOOK_TIMEOUT_SECONDS = env.int("CRM_WEBHOOK_TIMEOUT_SECONDS", default=10)
CRM_WEBHOOK_MAX_ATTEMPTS = env.int("CRM_WEBHOOK_MAX_ATTEMPTS", default=5)
CRM_WEBHOOK_BACKOFF_SECONDS = env.int("CRM_WEBHOOK_BACKOFF_SECONDS", default=300)
CRM_WEBHOOK_INCLUDE_SPECIAL_CATEGORY_SUMMARY = env.bool(
    "CRM_WEBHOOK_INCLUDE_SPECIAL_CATEGORY_SUMMARY", default=False
)
CRM_WEBHOOK_PAYLOAD_VERSION = env("CRM_WEBHOOK_PAYLOAD_VERSION", default="v1")


# ---------------------------------------------------------------------------
# Mandate / professional engagement scaffold (F-p0-leg-2-mandate)
#
# Una richiesta entrata via /contact/ o una /wizard/ NON equivalgono a un
# incarico professionale. L'incarico nasce solo dopo un accordo scritto
# firmato (mandato professionale).
#
# I tre setting `MANDATE_TEMPLATE_*` versionano il TESTO del mandato
# (working copy finche' lo Studio non lo firma).
# `REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION` (default True) e' il flag che
# protegge qualsiasi flow futuro di promozione lead → pratica: nessun
# percorso interno deve trattare un lead come pratica attiva senza
# `mandate_signed=True` su quel lead.
#
# Il system check `core.E008` blocca il deploy in produzione finche' la
# versione del template e' working-copy/draft, lo status non e' `signed`,
# o `REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION` e' stato spento.
# ---------------------------------------------------------------------------
MANDATE_TEMPLATE_VERSION = env("MANDATE_TEMPLATE_VERSION", default="working-copy-2026-05-10")
MANDATE_TEMPLATE_STATUS = env("MANDATE_TEMPLATE_STATUS", default="working_copy")
MANDATE_TEMPLATE_SIGNED_AT = env("MANDATE_TEMPLATE_SIGNED_AT", default="")
REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION = env.bool(
    "REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION", default=True
)


# ---------------------------------------------------------------------------
# Privacy policy & disclaimer page versions (F-p0-leg-1-6-legal-pages)
#
# Le due pagine pubbliche /privacy/ e /disclaimer/ sono "atti firmati":
# devono avere una versione tracciabile e una data di firma.
#
# `*_STATUS` ammette solo i due valori `working_copy` o `signed`. Il
# system check `core.E006`/`core.E007` blocca il deploy in produzione
# finche' lo status non e' `signed` (e finche' la versione contiene
# marker `working-copy` o `draft`).
#
# `*_SIGNED_AT` deve essere una data ISO (`2026-09-15`) quando lo
# status diventa `signed`; in dev resta vuoto.
#
# Default: working_copy + version `working-copy-2026-05-10`. La pagina
# pubblica mostra un banner visibile finche' lo status e' working_copy.
# ---------------------------------------------------------------------------
PRIVACY_POLICY_VERSION = env("PRIVACY_POLICY_VERSION", default="working-copy-2026-05-10")
PRIVACY_POLICY_STATUS = env("PRIVACY_POLICY_STATUS", default="working_copy")
PRIVACY_POLICY_SIGNED_AT = env("PRIVACY_POLICY_SIGNED_AT", default="")
DISCLAIMER_VERSION = env("DISCLAIMER_VERSION", default="working-copy-2026-05-10")
DISCLAIMER_STATUS = env("DISCLAIMER_STATUS", default="working_copy")
DISCLAIMER_SIGNED_AT = env("DISCLAIMER_SIGNED_AT", default="")


# ---------------------------------------------------------------------------
# Data retention policy scaffold (F-p0-leg-4-retention)
#
# Policy retention "wide": Lead, Simulation, ConsentRecord, audit log
# privacy. Iter complementare a STAFF_AUDIT_RETENTION_* (pass 10), che
# resta dedicato esclusivamente a StaffAccessEvent + StaffSecurityAlert.
#
# Filosofia P0:
# - SCAFFOLD ONLY: lo Studio non ha ancora firmato i giorni effettivi.
#   I default `*_DAYS` qui sono valori di sviluppo (1 anno per dati
#   personali, 5 anni per consensi e audit) per permettere ai test di
#   produrre cutoff deterministici. NON sono un parere legale.
# - DRY-RUN PRIMA DI TUTTO: `RETENTION_MODE` default = `dry_run`.
# - ANONYMIZE PRIMA DI DELETE: il delete fisico non gira in automatico
#   sui dati legali, neanche con `--yes-i-understand`, finche' lo Studio
#   non firma la policy (`RETENTION_REQUIRE_SIGNED_VERSION=True` in
#   produzione).
# - SYSTEM CHECK BLOCCANTE: in produzione (`DEBUG=False`) il check
#   `compliance.E001` blocca `manage.py check` se la policy version e'
#   ancora `working-copy-*` o `draft-*` o se `RETENTION_MODE` e' un
#   valore invalido.
# ---------------------------------------------------------------------------
RETENTION_POLICY_VERSION = env("RETENTION_POLICY_VERSION", default="working-copy-2026-05-10")
RETENTION_ENABLED = env.bool("RETENTION_ENABLED", default=False)
RETENTION_MODE = env("RETENTION_MODE", default="dry_run")
RETENTION_LEAD_DAYS = env.int("RETENTION_LEAD_DAYS", default=365)
RETENTION_SIMULATION_DAYS = env.int("RETENTION_SIMULATION_DAYS", default=365)
RETENTION_CONSENT_RECORD_DAYS = env.int("RETENTION_CONSENT_RECORD_DAYS", default=1825)
RETENTION_AUDIT_LOG_DAYS = env.int("RETENTION_AUDIT_LOG_DAYS", default=1825)
# In prod-like il go-live richiede una versione policy firmata. In dev
# (DEBUG=True) il flag e' silenzioso.
RETENTION_REQUIRE_SIGNED_VERSION = env.bool("RETENTION_REQUIRE_SIGNED_VERSION", default=True)


# ---------------------------------------------------------------------------
# Content-Security-Policy (F-p0-codice-4-csp)
#
# Chiude P0-SEC-1 (vedi `docs/SECURITY_INDEX.md`). Usiamo `django-csp` 4.x
# con nonce per-request via `csp.middleware.CSPMiddleware`. Inline
# `<script>` e `<style>` ricevono `nonce="{{ CSP_NONCE }}"` (vedi
# `templates/base.html` e `templates/partials/cookie_consent_banner.html`).
#
# Filosofia:
# - default-src 'self': baseline restrittiva.
# - script-src/style-src: 'self' + nonce (no `unsafe-inline`).
# - frame-ancestors 'none', object-src 'none', base-uri 'self',
#   form-action 'self': lock-down clickjacking/XSS.
# - img-src include `data:` e `blob:` per le immagini Pexels in
#   media/ e per data URI generati dal frontend (es. SVG inline).
# - font-src e' `'self'` solo: P1-SEC-1 (`p1/local-fonts-csp-hardening`)
#   ha vendored Inter / Cormorant Garamond / Amiri / Tajawal sotto
#   `static/fonts/` (vedi `static/fonts/README.md`). Niente fetch
#   runtime verso `fonts.gstatic.com`.
# - style-src e' `'self'` + nonce. Stessa motivazione: niente piu'
#   `fonts.googleapis.com` perche' il CSS `@font-face` e' locale
#   (`static/css/fonts.css`).
#
# `CSP_ENABLED` e' opt-in via env; default True. Disattivabile per
# debug locale. In prod (`DEBUG=False`) un system check
# `core.E002` blocca il deploy se CSP_ENABLED=False.
#
# `CSP_REPORT_ONLY=True` emette `Content-Security-Policy-Report-Only`
# invece di enforcing — utile per dry-run su staging. Default False
# (enforcing). In prod (`DEBUG=False`) il system check `core.E003`
# blocca il deploy se CSP_REPORT_ONLY=True (preferiamo enforcing).
#
# `CSP_REPORT_URI` opzionale: endpoint dove il browser POST violations.
# ---------------------------------------------------------------------------
CSP_ENABLED = env.bool("CSP_ENABLED", default=True)
CSP_REPORT_ONLY = env.bool("CSP_REPORT_ONLY", default=False)
CSP_REPORT_URI = env("CSP_REPORT_URI", default="")


def _build_csp_directives() -> dict:
    """
    Costruisce le DIRECTIVES per `CONTENT_SECURITY_POLICY`.

    Tutte le voci sono parametrizzate via env per permettere override
    tattico in staging/prod senza toccare il codice. I default sono
    una baseline ragionevole per il sito reale (verificata in
    P0-CODICE-4 con browser live).
    """
    from csp.constants import NONCE, NONE, SELF

    directives = {
        "default-src": env.list("CSP_DEFAULT_SRC", default=[SELF]) or [SELF],
        "script-src": env.list("CSP_SCRIPT_SRC", default=[SELF]) + [NONCE],
        "style-src": (
            env.list(
                "CSP_STYLE_SRC",
                default=[SELF],
            )
            + [NONCE]
        ),
        "img-src": env.list(
            "CSP_IMG_SRC",
            default=[SELF, "data:", "blob:"],
        ),
        "font-src": env.list(
            "CSP_FONT_SRC",
            default=[SELF],
        ),
        "connect-src": env.list("CSP_CONNECT_SRC", default=[SELF]),
        "frame-ancestors": env.list("CSP_FRAME_ANCESTORS", default=[NONE]),
        "base-uri": env.list("CSP_BASE_URI", default=[SELF]),
        "form-action": env.list("CSP_FORM_ACTION", default=[SELF]),
        "object-src": env.list("CSP_OBJECT_SRC", default=[NONE]),
    }
    if CSP_REPORT_URI:
        directives["report-uri"] = [CSP_REPORT_URI]
    return directives


if CSP_ENABLED:
    _csp_config = {"DIRECTIVES": _build_csp_directives()}
    if CSP_REPORT_ONLY:
        CONTENT_SECURITY_POLICY_REPORT_ONLY = _csp_config
    else:
        CONTENT_SECURITY_POLICY = _csp_config
