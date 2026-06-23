# D5 — Legacy Attachment Alignment & Strict Validator Cleanup — Plan

**Branch:** `feature/d5-legacy-attachment-alignment-audit` (from `product/staging-readiness-p0` @ `9505321`).
**Date:** 2026-06-23.

> Goal: make the D4 strict validator (`--fail-on-blocking`) *actionable* by
> explaining its blocking findings — approved sources with no
> `LegalSourceAttachment` row — and recommending the SAFE resolution, WITHOUT
> inventing attachments/hashes and WITHOUT activating any calculation.

## 1. The blocking findings

`validate_legal_review_decisions --country ALL --fail-on-blocking` exits 1 today
because 4 sources have a latest `approve` review but **no `LegalSourceAttachment`
DB row**:

| Country | Slug | Why |
|---|---|---|
| BE | `be-loi-1989-11-21-rc-auto` | promoted on a disk-file validation; no attachment row |
| EU | `eu-regulation-650-2012-successions` | same |
| TN | `tn-code-dip-loi-98-97` | same |
| TN | `tn-code-statut-personnel-livre-ix-succession` | same |

Plus 1 warning: `ma-code-famille-moudawana-fr-pdf` has an attachment + hash but
no `LegalSourceVersion`. Italy is fully aligned (attachment + hash + version).

All 4 are **registry candidates** (`in_registry = True`) but `manual_attach_allowed`
is unset (ingest_mode `fetch`). They were promoted to APPROVED by
`promote_official_legal_sources` (which re-validates the file on disk) without the
separate `attach_official_source_file` step that creates the DB attachment row.

## 2. Why apply is NOT implemented

`legal_data/` is **gitignored** — the official files live on disk locally but are
NOT in the repo or CI. Per the project rule "se i file ufficiali non sono nel
repo, NON inventare attachment / NON creare hash fittizi", an `--apply` that
fabricated attachment rows would either depend on local-only files
(unreproducible / untestable in CI) or risk fake evidence. **So D5 ships
read-only audit + dry-run + runbook only.** The only safe way to attach is the
existing `attach_official_source_file` command, run by ops with the real file.

## 3. Design — read-only, additive, no schema change

- **No migration.** The audit is derived from DB state (attachment/hash/version)
  + the committed registry (candidate yes/no) — deterministic and CI-safe.
- **`apps/legal_sources/attachment_alignment.py`** — pure
  `classify_attachment_gap(source)` →
  `ok | missing_attachment_row | manual_review_required | hash_unavailable |
  missing_source_version`, with `strict_validator_impact` and a safe
  `recommended_action`; `build_legacy_attachment_alignment_report(country)`.
  Safe fields only (present/absent flags; no full hash, path, reviewer, notes).
- **`audit_legacy_attachment_alignment`** command — `--country`, `--format`,
  `--output`, `--include-ok`, `--fail-on-blocking`, `--fail-on-manual-required`.
  Read-only, PII-safe, defensive stdout. Default exit 0.
- **Validator hint** — `validate_legal_review_decisions` adds a non-invasive
  "Run `audit_legacy_attachment_alignment` for details" hint when a blocking
  finding exists. Default behaviour / exit codes unchanged; IT strict stays
  green.
- **Admin** — a 4th read-only action "Show attachment alignment status".
- **Runbook** `docs/ops/LEGAL_SOURCE_ATTACHMENT_ALIGNMENT_RUNBOOK.md`.

## 4. Classifications — fixable vs Studio-required

- `missing_attachment_row` (registry candidate) → **ops/Studio** can attach the
  documented official file via `attach_official_source_file`, then re-validate.
- `manual_review_required` (not a registry candidate) → **Studio must source**
  the official file first.
- `missing_source_version` → create a `LegalSourceVersion` (warning).
- `hash_unavailable` → run `validate_official_legal_sources`.
- D5 corrects **none** of these automatically — it reports and recommends.

## 5. Fail-closed

The audit never attaches, hashes, approves, promotes or activates. FR/BE/MA/TN
stay `calculation_ready=False`. The IT canary is untouched. `--fail-on-blocking`
is opt-in; the default validator gate stays green.

## 6. Rollback

No schema change → reverting the branch removes the service, command, validator
hint, admin action and tests; nothing to undo at the DB level.
