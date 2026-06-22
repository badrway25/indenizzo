# Generated legal review packages

These files are **machine-generated, read-only** snapshots produced by:

```bash
python manage.py generate_legal_review_package --country <CODE> --format markdown \
  --output docs/legal_sources/generated/<CODE>_REVIEW_PACKAGE_GENERATED_<date>.md
```

They merge the **live `LegalSource` state** with the **registry ingest policy**
(`config/official_source_registry.json`) into a per-country package that lists,
for each source still needing review, the registry policy and the GO/NO-GO
decisions the Studio must record. **They approve nothing.**

## Relationship to the existing docs (no duplication)

| Artifact | Nature | Owner |
|---|---|---|
| `<COUNTRY>_LEGAL_REVIEW_PACKAGE.md` | Hand-written, detailed analysis per source/CSV | dev + Studio |
| `<CODE>_REVIEW_PACKAGE_GENERATED_<date>.md` (here) | Auto-generated, always-current summary | command |
| `MANUAL_ATTACH_OFFICIAL_SOURCE_RUNBOOK.md` | The attach procedure for blocked sources | (existing) |

The generated packages **complement** the hand-written ones: they stay in sync
with the DB (statuses change as the Studio works), while the hand-written docs
carry the deep per-CSV analysis. The manual-attach **runbook already exists** —
this phase does not duplicate it; the generated packages link to it.

## Regenerating

Re-run the command after any source-status change to refresh the snapshot. The
command is idempotent and side-effect-free (no DB writes, no network).

## Cardinal rule

A source may feed a public calculation **only** when it is `approved` AND backs
an `approved` dataset/formula. Authenticating a document is necessary but not
sufficient. *Meglio nessun calcolo che un calcolo falso.*
