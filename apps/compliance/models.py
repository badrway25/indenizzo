"""
Modelli compliance/GDPR.

F3 — fondamenta privacy. NESSUN dato sensibile viene raccolto qui: questi
modelli registrano SOLO il *fatto* del consenso, della richiesta di
cancellazione, dell'evento privacy. I dati di simulazione/lead utenti
saranno trattati nelle app dedicate (cases, crm) e referenziati tramite
`target_model` + `target_object_id` nei `PrivacyAuditEvent`.

Principi:
- minimizzazione: campi tecnici (IP, UA, path) sì; payload utente NO;
- retention: nessun cron qui — sono solo policy dichiarate;
- audit: ogni evento è append-only, mai update/delete dall'app;
- multilingua: testi di consenso versionati per lingua, mai hardcoded.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .enums import ConsentLanguage, DeletionStatus, PrivacyEventType, RetentionScope


class ConsentPurpose(models.Model):
    """
    Finalità di trattamento per cui chiediamo consenso.

    Esempi previsti (non creati qui): simulation_processing, lead_contact,
    marketing, document_storage. Il `code` è l'identificatore stabile
    usato dal codice; `name`/`description` sono per umani.
    """

    code = models.SlugField(_("code"), max_length=64, unique=True)
    name = models.CharField(_("name"), max_length=255)
    description = models.TextField(_("description"), blank=True)
    is_active = models.BooleanField(_("active"), default=True)
    required_for_simulation = models.BooleanField(
        _("required for simulation"),
        default=False,
        help_text=_("Se True, il wizard di simulazione non può procedere senza."),
    )
    required_for_contact = models.BooleanField(
        _("required for contact"),
        default=False,
        help_text=_("Se True, il lead form non può inviare senza."),
    )

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("consent purpose")
        verbose_name_plural = _("consent purposes")
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code


class ConsentTextVersion(models.Model):
    """
    Versione testuale del consenso, per finalità + lingua.

    Ogni versione ha intervallo di validità. Quando aggiorniamo il testo
    ne creiamo una nuova: le `ConsentRecord` esistenti restano legate
    alla versione che il cliente ha effettivamente visto.
    """

    purpose = models.ForeignKey(
        ConsentPurpose,
        on_delete=models.PROTECT,
        related_name="text_versions",
        verbose_name=_("purpose"),
    )
    version = models.CharField(
        _("version"),
        max_length=32,
        help_text=_("Etichetta umana stabile, es. '2026-04' o '1.0'."),
    )
    language = models.CharField(
        _("language"),
        max_length=4,
        choices=ConsentLanguage.choices,
    )
    title = models.CharField(_("title"), max_length=255)
    body = models.TextField(_("body"))

    effective_from = models.DateTimeField(_("effective from"), null=True, blank=True)
    effective_to = models.DateTimeField(_("effective to"), null=True, blank=True)
    is_active = models.BooleanField(_("active"), default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="authored_consent_text_versions",
        verbose_name=_("created by"),
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("consent text version")
        verbose_name_plural = _("consent text versions")
        ordering = ["-effective_from", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["purpose", "version", "language"],
                name="uniq_consent_text_version",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.purpose.code} [{self.language}] v{self.version}"


class ConsentRecord(models.Model):
    """
    Atto di consenso (o rifiuto) registrato.

    Modello append-only: non si aggiorna né si cancella dall'applicazione.
    Per "ritirare" un consenso si crea un nuovo record con accepted=False
    o si registra un PrivacyEventType.CONSENT_WITHDRAWN.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="consent_records",
        verbose_name=_("user"),
        null=True,
        blank=True,
    )
    session_key = models.CharField(_("session key"), max_length=64, blank=True)

    purpose = models.ForeignKey(
        ConsentPurpose,
        on_delete=models.PROTECT,
        related_name="records",
        verbose_name=_("purpose"),
    )
    text_version = models.ForeignKey(
        ConsentTextVersion,
        on_delete=models.PROTECT,
        related_name="records",
        verbose_name=_("text version"),
        null=True,
        blank=True,
        help_text=_("Versione del testo che l'utente ha visto al momento del consenso."),
    )

    accepted = models.BooleanField(_("accepted"), default=False)
    accepted_at = models.DateTimeField(_("accepted at"))

    ip_address = models.GenericIPAddressField(_("ip address"), null=True, blank=True)
    user_agent = models.CharField(_("user agent"), max_length=512, blank=True)
    locale = models.CharField(_("locale"), max_length=16, blank=True)
    source_path = models.CharField(_("source path"), max_length=512, blank=True)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("consent record")
        verbose_name_plural = _("consent records")
        ordering = ["-accepted_at"]
        indexes = [
            models.Index(fields=["purpose", "accepted"]),
            models.Index(fields=["user", "purpose"]),
            models.Index(fields=["session_key", "purpose"]),
        ]

    def __str__(self) -> str:
        who = self.user.get_username() if self.user_id else (self.session_key or "anon")
        return f"{who} → {self.purpose.code}: {'accepted' if self.accepted else 'refused'}"


class DataRetentionPolicy(models.Model):
    """
    Policy dichiarativa di retention. La cancellazione effettiva sarà un
    Celery task in F10/F11. Qui registriamo solo la decisione politica.
    """

    code = models.SlugField(_("code"), max_length=64, unique=True)
    name = models.CharField(_("name"), max_length=255)
    description = models.TextField(_("description"), blank=True)
    retention_days = models.PositiveIntegerField(
        _("retention days"),
        help_text=_("Giorni dopo i quali il dato deve essere eliminato/anonymizzato."),
    )
    applies_to = models.CharField(
        _("applies to"),
        max_length=32,
        choices=RetentionScope.choices,
        default=RetentionScope.OTHER,
    )
    is_active = models.BooleanField(_("active"), default=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("data retention policy")
        verbose_name_plural = _("data retention policies")
        ordering = ["applies_to", "code"]

    def __str__(self) -> str:
        return f"{self.code} ({self.retention_days}d)"


class DataDeletionRequest(models.Model):
    """
    Richiesta GDPR di cancellazione (art. 17). Workflow gestito dallo Studio.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="deletion_requests",
        verbose_name=_("user"),
        null=True,
        blank=True,
    )
    email = models.EmailField(
        _("email"),
        blank=True,
        help_text=_("Email di contatto, anche per richieste anonime senza account."),
    )
    status = models.CharField(
        _("status"),
        max_length=32,
        choices=DeletionStatus.choices,
        default=DeletionStatus.RECEIVED,
        db_index=True,
    )
    reason = models.TextField(_("reason"), blank=True)
    requested_at = models.DateTimeField(_("requested at"), auto_now_add=True)
    completed_at = models.DateTimeField(_("completed at"), null=True, blank=True)

    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="handled_deletion_requests",
        verbose_name=_("handled by"),
        null=True,
        blank=True,
    )
    internal_notes = models.TextField(_("internal notes"), blank=True)

    class Meta:
        verbose_name = _("data deletion request")
        verbose_name_plural = _("data deletion requests")
        ordering = ["-requested_at"]

    def __str__(self) -> str:
        target = self.email or (self.user.get_username() if self.user_id else "anon")
        return f"{target} ({self.status})"


class PrivacyAuditEvent(models.Model):
    """
    Evento privacy append-only.

    Riferito a un oggetto generico via (target_model, target_object_id):
    questo evita di legare l'audit log a tabelle specifiche e tiene il
    modello stabile mentre il dominio cresce.

    REGOLA: nulla qui dentro deve contenere dati sensibili; `metadata`
    è per dati tecnici (es. {"reason": "user request", "trigger": "wizard"}).
    """

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="privacy_audit_events",
        verbose_name=_("actor"),
        null=True,
        blank=True,
    )
    event_type = models.CharField(
        _("event type"),
        max_length=64,
        choices=PrivacyEventType.choices,
    )
    target_model = models.CharField(
        _("target model"),
        max_length=128,
        blank=True,
        help_text=_("Es. 'cases.Simulation' o 'legal_sources.LegalSource'."),
    )
    target_object_id = models.CharField(_("target object id"), max_length=64, blank=True)

    ip_address = models.GenericIPAddressField(_("ip address"), null=True, blank=True)
    user_agent = models.CharField(_("user agent"), max_length=512, blank=True)
    path = models.CharField(_("path"), max_length=512, blank=True)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("privacy audit event")
        verbose_name_plural = _("privacy audit events")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["target_model", "target_object_id"]),
            models.Index(fields=["actor", "created_at"]),
        ]

    def __str__(self) -> str:
        who = self.actor.get_username() if self.actor_id else "system"
        return f"[{self.event_type}] {who} → {self.target_model}:{self.target_object_id}"


class StaffAccessEvent(models.Model):
    """
    Evento di accesso allo staff/admin Django (login success/failed,
    logout). Append-only, privacy-minimized.

    Iter: F-local-product-hardening-pass8-audit-log-staff-access.

    Cosa registra:
    - tipo evento (login_success / login_failed / logout);
    - hash dell'username tentato/loggato (mai in chiaro);
    - FK al `User` quando disponibile (login_success/logout);
    - IP mascherato (ultimo octet → `x`);
    - hash dello user-agent (mai in chiaro);
    - path della richiesta (es. `/admin/login/`);
    - timestamp UTC e metadata JSON.

    Cosa NON registra mai:
    - password (raw o hashed);
    - username in chiaro;
    - IP completo;
    - user-agent raw;
    - body della richiesta.

    Append-only: l'admin disabilita add/change/delete (vedi
    `apps/compliance/admin.py::StaffAccessEventAdmin`).
    """

    class EventType(models.TextChoices):
        LOGIN_SUCCESS = "login_success", _("Login success")
        LOGIN_FAILED = "login_failed", _("Login failed")
        LOGOUT = "logout", _("Logout")

    event_type = models.CharField(
        _("event type"),
        max_length=24,
        choices=EventType.choices,
        db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="staff_access_events",
        verbose_name=_("user"),
        null=True,
        blank=True,
    )
    # SHA-256 troncato dell'username tentato/loggato. Mai in chiaro.
    username_hash = models.CharField(_("username hash"), max_length=64, blank=True, db_index=True)
    # IP normalizzato + mascherato (es. "203.0.113.x"). Mai completo.
    ip_address_masked = models.CharField(_("ip address (masked)"), max_length=64, blank=True)
    # SHA-256 troncato dello user-agent. Mai raw.
    user_agent_hash = models.CharField(_("user agent hash"), max_length=64, blank=True)
    # Path della richiesta (es. /admin/login/). Non PII.
    path = models.CharField(_("path"), max_length=512, blank=True)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("staff access event")
        verbose_name_plural = _("staff access events")
        # Append-only ordering: dal più recente al più vecchio. `-pk`
        # come tiebreak deterministico (timer Windows ~15.6ms).
        ordering = ["-created_at", "-pk"]
        indexes = [
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["user", "event_type"]),
        ]

    def __str__(self) -> str:
        who = self.user.get_username() if self.user_id else f"hash={self.username_hash[:8]}…"
        return f"[{self.event_type}] {who} @ {self.created_at:%Y-%m-%d %H:%M}"


class StaffSecurityAlert(models.Model):
    """
    Alert di sicurezza derivato dall'analisi di `StaffAccessEvent`.

    Iter: F-local-product-hardening-pass9-staff-audit-brute-force-detector.

    Detection-only: questo modello rappresenta un *evento di sospetto*
    consultabile dall'admin (e opzionalmente notificato via email).
    Non blocca login né IP. Lockout/blacklisting sono fuori scope di
    pass 9.

    Privacy: stesso disegno di `StaffAccessEvent`. Mai IP/UA raw, mai
    password, mai username in chiaro.
    """

    class AlertType(models.TextChoices):
        ADMIN_LOGIN_BRUTEFORCE = "admin_login_bruteforce", _("Admin login brute-force")

    class Severity(models.TextChoices):
        LOW = "low", _("Low")
        MEDIUM = "medium", _("Medium")
        HIGH = "high", _("High")

    alert_type = models.CharField(
        _("alert type"),
        max_length=64,
        choices=AlertType.choices,
        db_index=True,
    )
    severity = models.CharField(
        _("severity"),
        max_length=16,
        choices=Severity.choices,
        default=Severity.MEDIUM,
    )
    username_hash = models.CharField(_("username hash"), max_length=64, blank=True, db_index=True)
    ip_address_masked = models.CharField(
        _("ip address (masked)"), max_length=64, blank=True, db_index=True
    )
    event_count = models.PositiveIntegerField(_("event count"), default=0)
    window_seconds = models.PositiveIntegerField(_("window seconds"), default=0)
    triggered_at = models.DateTimeField(_("triggered at"), auto_now_add=True, db_index=True)
    cooldown_until = models.DateTimeField(_("cooldown until"), null=True, blank=True)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    class Meta:
        verbose_name = _("staff security alert")
        verbose_name_plural = _("staff security alerts")
        ordering = ["-triggered_at", "-pk"]
        indexes = [
            models.Index(fields=["alert_type", "triggered_at"]),
            models.Index(fields=["severity", "triggered_at"]),
            models.Index(fields=["alert_type", "cooldown_until"]),
        ]

    def __str__(self) -> str:
        return (
            f"[{self.alert_type}/{self.severity}] "
            f"count={self.event_count} window={self.window_seconds}s "
            f"@ {self.triggered_at:%Y-%m-%d %H:%M}"
        )
