"""
Tests F3 — apps.compliance.

Coprono:
- creazione modelli base (purpose, text version, retention, deletion request);
- service `record_consent` da request factory + utente anonimo;
- `has_consent` con accettazione, rifiuto e ritiro successivo;
- `log_privacy_event` come append-only;
- redazione PII nei log (RedactPIIFilter applicato al messaggio).
"""

from __future__ import annotations

import logging

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from apps.compliance.enums import (
    ConsentLanguage,
    DeletionStatus,
    PrivacyEventType,
    RetentionScope,
)
from apps.compliance.models import (
    ConsentPurpose,
    ConsentRecord,
    ConsentTextVersion,
    DataDeletionRequest,
    DataRetentionPolicy,
    PrivacyAuditEvent,
)
from apps.compliance.services import (
    get_request_meta,
    has_consent,
    log_privacy_event,
    record_consent,
)
from config.logging_filters import RedactPIIFilter

User = get_user_model()


@pytest.fixture
def simulation_purpose(db) -> ConsentPurpose:
    return ConsentPurpose.objects.create(
        code="simulation_processing",
        name="Trattamento dati per simulazione",
        required_for_simulation=True,
    )


@pytest.fixture
def text_version_it(db, simulation_purpose: ConsentPurpose) -> ConsentTextVersion:
    return ConsentTextVersion.objects.create(
        purpose=simulation_purpose,
        version="2026-04",
        language=ConsentLanguage.IT,
        title="Consenso simulazione (placeholder)",
        body="Testo placeholder. Da sostituire con testo legale definitivo in F10.",
        is_active=True,
    )


@pytest.fixture
def request_factory() -> RequestFactory:
    return RequestFactory()


@pytest.mark.django_db
def test_consent_purpose_minimal_creation():
    purpose = ConsentPurpose.objects.create(
        code="lead_contact",
        name="Contatto Studio",
        required_for_contact=True,
    )
    assert purpose.is_active is True
    assert purpose.required_for_contact is True
    assert purpose.required_for_simulation is False
    assert str(purpose) == "lead_contact"


@pytest.mark.django_db
def test_consent_text_version_active(text_version_it: ConsentTextVersion):
    assert text_version_it.is_active is True
    assert text_version_it.language == ConsentLanguage.IT
    assert "v2026-04" in str(text_version_it)


@pytest.mark.django_db
def test_record_consent_from_request(
    simulation_purpose: ConsentPurpose,
    text_version_it: ConsentTextVersion,
    request_factory: RequestFactory,
):
    request = request_factory.get(
        "/wizard/start",
        HTTP_USER_AGENT="pytest-agent/1.0",
        HTTP_X_FORWARDED_FOR="203.0.113.7, 10.0.0.1",
    )
    request.LANGUAGE_CODE = "it"
    record = record_consent(
        purpose=simulation_purpose,
        accepted=True,
        request=request,
        text_version=text_version_it,
        metadata={"trigger": "wizard"},
    )
    assert record.accepted is True
    assert record.ip_address == "203.0.113.7"
    assert record.user_agent == "pytest-agent/1.0"
    assert record.locale == "it"
    assert record.source_path == "/wizard/start"
    assert record.metadata == {"trigger": "wizard"}


@pytest.mark.django_db
def test_record_consent_without_request(simulation_purpose: ConsentPurpose):
    record = record_consent(purpose=simulation_purpose, accepted=False)
    assert record.accepted is False
    assert record.ip_address is None
    assert record.user_agent == ""
    assert record.source_path == ""


@pytest.mark.django_db
def test_has_consent_for_authenticated_user(simulation_purpose: ConsentPurpose):
    user = User.objects.create_user(username="alice", password="pw")
    assert has_consent(purpose_code="simulation_processing", user=user) is False
    record_consent(purpose=simulation_purpose, accepted=True, user=user)
    assert has_consent(purpose_code="simulation_processing", user=user) is True


@pytest.mark.django_db
def test_has_consent_withdrawn_overrides_previous(simulation_purpose: ConsentPurpose):
    user = User.objects.create_user(username="bob", password="pw")
    record_consent(purpose=simulation_purpose, accepted=True, user=user)
    assert has_consent(purpose_code="simulation_processing", user=user) is True
    record_consent(purpose=simulation_purpose, accepted=False, user=user)
    assert has_consent(purpose_code="simulation_processing", user=user) is False


@pytest.mark.django_db
def test_has_consent_for_anonymous_session(simulation_purpose: ConsentPurpose):
    ConsentRecord.objects.create(
        user=None,
        session_key="abc-session-123",
        purpose=simulation_purpose,
        accepted=True,
        accepted_at=__import__("django").utils.timezone.now(),
    )
    assert has_consent(purpose_code="simulation_processing", session_key="abc-session-123") is True
    assert has_consent(purpose_code="simulation_processing", session_key="other") is False


@pytest.mark.django_db
def test_has_consent_no_user_no_session_returns_false():
    assert has_consent(purpose_code="anything") is False


@pytest.mark.django_db
def test_data_retention_policy_creation():
    policy = DataRetentionPolicy.objects.create(
        code="lead_contact_180d",
        name="Lead retention 180 giorni",
        retention_days=180,
        applies_to=RetentionScope.LEAD_CONTACT,
    )
    assert policy.retention_days == 180
    assert policy.applies_to == RetentionScope.LEAD_CONTACT
    assert "180d" in str(policy)


@pytest.mark.django_db
def test_data_deletion_request_default_status():
    deletion = DataDeletionRequest.objects.create(email="user@example.test")
    assert deletion.status == DeletionStatus.RECEIVED
    assert deletion.requested_at is not None
    assert deletion.completed_at is None


@pytest.mark.django_db
def test_log_privacy_event_creates_append_only_record(request_factory: RequestFactory):
    request = request_factory.get(
        "/admin/legal_sources/legalsource/42/change/",
        HTTP_USER_AGENT="staff-browser/2.0",
        REMOTE_ADDR="198.51.100.5",
    )
    event = log_privacy_event(
        event_type=PrivacyEventType.LEGAL_SOURCE_REVIEWED,
        request=request,
        target_model="legal_sources.LegalSource",
        target_object_id=42,
        metadata={"decision": "approved"},
    )
    assert isinstance(event, PrivacyAuditEvent)
    assert event.event_type == PrivacyEventType.LEGAL_SOURCE_REVIEWED
    assert event.target_model == "legal_sources.LegalSource"
    assert event.target_object_id == "42"
    assert event.ip_address == "198.51.100.5"
    assert event.user_agent == "staff-browser/2.0"
    assert event.metadata == {"decision": "approved"}


@pytest.mark.django_db
def test_get_request_meta_handles_none():
    meta = get_request_meta(None)
    assert meta.ip_address is None
    assert meta.user_agent == ""
    assert meta.path == ""
    assert meta.session_key == ""


def test_redact_pii_filter_masks_email_and_phone():
    """
    Verifica che il filtro PII applicato al logger root mascheri email,
    telefoni e codici fiscali. Difesa-in-profondità rispetto alla regola
    "non passare PII a logger.*".
    """
    pii_filter = RedactPIIFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg="contact: alice@example.com phone: +39 333 1234567 fc: RSSMRA85T10A562S",
        args=None,
        exc_info=None,
    )
    pii_filter.filter(record)
    assert "alice@example.com" not in record.msg
    assert "RSSMRA85T10A562S" not in record.msg
    assert "[email-redacted]" in record.msg
    assert "[fiscalcode-redacted]" in record.msg
    assert "[phone-redacted]" in record.msg
