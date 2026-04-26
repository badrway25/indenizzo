"""
Seed dei `ConsentPurpose`, `ConsentTextVersion` e `DataRetentionPolicy` base.

Idempotente. NON sostituisce la revisione legale: i testi qui sono
*placeholder neutri* marcati esplicitamente "working version — requires
legal review". Il legale Studio dovrà sostituirli prima del go-live (F10).

Esecuzione:
    python manage.py seed_compliance_basics [--quiet]

Cosa crea/aggiorna:
- 2 purpose: lead_contact, simulation_processing;
- 8 text version (2 purpose × 4 lingue ufficiali it/fr/en/ar);
- 4 retention policy base (lead, simulation, document, audit).
"""

from __future__ import annotations

from dataclasses import dataclass

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.compliance.enums import ConsentLanguage, RetentionScope
from apps.compliance.models import (
    ConsentPurpose,
    ConsentTextVersion,
    DataRetentionPolicy,
)

PLACEHOLDER_TAG = "[working version — requires legal review]"


@dataclass(frozen=True)
class _PurposeSeed:
    code: str
    name: str
    description: str
    required_for_simulation: bool = False
    required_for_contact: bool = False


@dataclass(frozen=True)
class _TextSeed:
    purpose_code: str
    version: str
    language: str
    title: str
    body: str


@dataclass(frozen=True)
class _RetentionSeed:
    code: str
    name: str
    description: str
    retention_days: int
    applies_to: str


PURPOSES: list[_PurposeSeed] = [
    _PurposeSeed(
        code="lead_contact",
        name="Lead contact request",
        description=(
            "Consent to process contact data submitted via the public "
            "/contact/ form so the Studio can reply."
        ),
        required_for_contact=True,
    ),
    _PurposeSeed(
        code="simulation_processing",
        name="Simulation data processing",
        description=(
            "Consent to process the inputs provided in the public simulator "
            "for the sole purpose of producing an indicative simulation."
        ),
        required_for_simulation=True,
    ),
]

# Testi placeholder. Brevissimi e neutri di proposito: il legale li
# sostituirà con le versioni firmate.
_TEXT_BODIES = {
    "lead_contact": {
        "it": (
            "Acconsento al trattamento dei dati personali forniti tramite "
            "questo modulo al solo fine di consentire allo Studio di "
            "rispondere alla richiesta. {tag}"
        ),
        "fr": (
            "Je consens au traitement des données personnelles fournies via "
            "ce formulaire à seule fin de permettre à l'Étude de répondre à "
            "la demande. {tag}"
        ),
        "en": (
            "I consent to the processing of the personal data provided via "
            "this form for the sole purpose of allowing the Studio to reply "
            "to the request. {tag}"
        ),
        "ar": (
            "أوافق على معالجة البيانات الشخصية المقدمة عبر هذا النموذج "
            "فقط بهدف تمكين المكتب من الرد على الطلب. {tag}"
        ),
    },
    "simulation_processing": {
        "it": (
            "Acconsento al trattamento dei dati inseriti nel simulatore al "
            "solo fine di produrre una simulazione indicativa. {tag}"
        ),
        "fr": (
            "Je consens au traitement des données saisies dans le simulateur "
            "à seule fin de produire une simulation indicative. {tag}"
        ),
        "en": (
            "I consent to the processing of the data entered in the simulator "
            "for the sole purpose of producing an indicative simulation. {tag}"
        ),
        "ar": (
            "أوافق على معالجة البيانات المدخلة في المحاكاة فقط بهدف إنتاج " "محاكاة إرشادية. {tag}"
        ),
    },
}


def _build_text_seeds() -> list[_TextSeed]:
    seeds: list[_TextSeed] = []
    for purpose_code, langs in _TEXT_BODIES.items():
        for lang in (
            ConsentLanguage.IT,
            ConsentLanguage.FR,
            ConsentLanguage.EN,
            ConsentLanguage.AR,
        ):
            body_template = langs[lang.value]
            seeds.append(
                _TextSeed(
                    purpose_code=purpose_code,
                    version="2026-04-placeholder",
                    language=lang.value,
                    title=f"{purpose_code} ({lang.value}) — placeholder",
                    body=body_template.format(tag=PLACEHOLDER_TAG),
                )
            )
    return seeds


RETENTIONS: list[_RetentionSeed] = [
    _RetentionSeed(
        code="lead_contact_180d",
        name="Lead contact retention 180 days",
        description="Personal data attached to inbound contact requests.",
        retention_days=180,
        applies_to=RetentionScope.LEAD_CONTACT,
    ),
    _RetentionSeed(
        code="simulation_input_90d",
        name="Simulation input retention 90 days",
        description="User-provided inputs persisted in cases.Simulation.",
        retention_days=90,
        applies_to=RetentionScope.SIMULATION_INPUT,
    ),
    _RetentionSeed(
        code="uploaded_document_365d",
        name="Uploaded document retention 365 days",
        description="Supporting documents attached by users.",
        retention_days=365,
        applies_to=RetentionScope.UPLOADED_DOCUMENT,
    ),
    _RetentionSeed(
        code="audit_log_730d",
        name="Audit log retention 730 days",
        description="PrivacyAuditEvent and SimulationEvent records.",
        retention_days=730,
        applies_to=RetentionScope.AUDIT_LOG,
    ),
]


class Command(BaseCommand):
    help = (
        "Seed idempotente per ConsentPurpose, ConsentTextVersion (placeholder) "
        "e DataRetentionPolicy base. Testi non legali definitivi."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Sopprime l'output riga-per-riga.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        quiet = options["quiet"]
        purposes = self._seed_purposes(quiet)
        texts = self._seed_texts(quiet)
        retentions = self._seed_retentions(quiet)

        self.stdout.write(self.style.SUCCESS("seed_compliance_basics completato:"))
        for label, (created, updated) in {
            "purposes": purposes,
            "text_versions": texts,
            "retentions": retentions,
        }.items():
            self.stdout.write(f"  {label}: {created} creati, {updated} aggiornati")

        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                "  ATTENZIONE: i testi di consenso sono placeholder. "
                "Il legale dello Studio deve sostituirli prima del go-live."
            )
        )

    # ---- helpers -------------------------------------------------------

    def _log(self, quiet: bool, msg: str) -> None:
        if not quiet:
            self.stdout.write(msg)

    def _seed_purposes(self, quiet: bool) -> tuple[int, int]:
        created = updated = 0
        for seed in PURPOSES:
            obj, was_created = ConsentPurpose.objects.update_or_create(
                code=seed.code,
                defaults={
                    "name": seed.name,
                    "description": seed.description,
                    "required_for_simulation": seed.required_for_simulation,
                    "required_for_contact": seed.required_for_contact,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
                self._log(quiet, f"  + ConsentPurpose {obj.code}")
            else:
                updated += 1
        return created, updated

    def _seed_texts(self, quiet: bool) -> tuple[int, int]:
        created = updated = 0
        for seed in _build_text_seeds():
            purpose = ConsentPurpose.objects.get(code=seed.purpose_code)
            obj, was_created = ConsentTextVersion.objects.update_or_create(
                purpose=purpose,
                version=seed.version,
                language=seed.language,
                defaults={
                    "title": seed.title,
                    "body": seed.body,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
                self._log(
                    quiet,
                    f"  + ConsentTextVersion {seed.purpose_code} [{seed.language}]",
                )
            else:
                updated += 1
        return created, updated

    def _seed_retentions(self, quiet: bool) -> tuple[int, int]:
        created = updated = 0
        for seed in RETENTIONS:
            obj, was_created = DataRetentionPolicy.objects.update_or_create(
                code=seed.code,
                defaults={
                    "name": seed.name,
                    "description": seed.description,
                    "retention_days": seed.retention_days,
                    "applies_to": seed.applies_to,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
                self._log(quiet, f"  + DataRetentionPolicy {obj.code}")
            else:
                updated += 1
        return created, updated
