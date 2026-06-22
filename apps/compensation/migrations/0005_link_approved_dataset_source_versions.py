# H1-5 follow-up (provenance): backfill the source version of APPROVED
# compensation datasets.
#
# This is a PURE DATA migration. It creates one LegalSourceVersion for the one
# known approved Italian source (D.P.R. 12/2025) and links the two approved
# datasets to it, so they satisfy the new application-level rule "APPROVED
# requires source_version" (enforced in CompensationDataset.clean()).
#
# The DB-level CheckConstraint for that rule is intentionally NOT added here:
# it would fire on every `.create()` and break ~65 test fixtures that create
# synthetic approved datasets without a source version. The constraint is a
# planned follow-up, to be applied after those fixtures are updated.
#
# Determinism / safety: the LegalSourceVersion is derived ENTIRELY from the
# already-approved source metadata (effective date, validity window, and the
# real SHA-256 of its official attachment). No legal value is invented. On a DB
# without this source (e.g. a fresh test DB), this migration is a no-op.

from django.db import migrations

# The single known approved Italian source and its canonical decree edition.
_IT_DECREE_SLUG = "it-dpr-12-2025-tun-danno-biologico"
_IT_DECREE_VERSION_LABEL = "DPR-12-2025"


def link_approved_dataset_source_versions(apps, schema_editor):
    LegalSource = apps.get_model("legal_sources", "LegalSource")
    LegalSourceVersion = apps.get_model("legal_sources", "LegalSourceVersion")
    CompensationDataset = apps.get_model("compensation", "CompensationDataset")

    src = LegalSource.objects.filter(slug=_IT_DECREE_SLUG, status="approved").first()
    if src is None:
        # No-op on databases that do not carry this approved source (e.g. a
        # fresh test DB built from migrations). Never invent a source/version.
        return

    # content_hash: the SHA-256 of the official attachment, but ONLY if it is
    # unambiguous (exactly one hashed attachment). Otherwise leave it blank —
    # do not fabricate an integrity hash.
    hashes = list(src.attachments.exclude(sha256="").values_list("sha256", flat=True))
    content_hash = hashes[0] if len(hashes) == 1 else ""

    version, _created = LegalSourceVersion.objects.get_or_create(
        source=src,
        version_label=_IT_DECREE_VERSION_LABEL,
        defaults={
            "valid_from": src.effective_date,
            "valid_to": src.valid_until,
            "content_hash": content_hash,
            "notes": (
                "Auto-created by migration compensation.0005: canonical version of "
                "the approved D.P.R. 12/2025 source, derived from existing approved "
                "metadata. content_hash = SHA-256 of the official attachment."
            ),
        },
    )

    # Link only APPROVED datasets of this source that still lack a version.
    # Drafts / needs_review / deprecated are left untouched.
    CompensationDataset.objects.filter(
        source=src,
        status="approved",
        source_version__isnull=True,
    ).update(source_version=version)


def unlink_approved_dataset_source_versions(apps, schema_editor):
    LegalSourceVersion = apps.get_model("legal_sources", "LegalSourceVersion")
    CompensationDataset = apps.get_model("compensation", "CompensationDataset")

    version = LegalSourceVersion.objects.filter(
        source__slug=_IT_DECREE_SLUG,
        version_label=_IT_DECREE_VERSION_LABEL,
    ).first()
    if version is None:
        return
    # PROTECT FK: unlink datasets first, then delete the version.
    CompensationDataset.objects.filter(source_version=version).update(source_version=None)
    version.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("compensation", "0004_compensation_data_integrity"),
        ("legal_sources", "0002_legalsourceversion_validity_check"),
    ]

    operations = [
        migrations.RunPython(
            link_approved_dataset_source_versions,
            unlink_approved_dataset_source_versions,
        ),
    ]
