# D6 — Verified Disk Evidence Bridge — Plan

**Branch:** `feature/d6-verified-disk-evidence-bridge` (from `product/staging-readiness-p0` @ `765d6a6`).
**Date:** 2026-06-23.

> Goal: close, *honestly*, the mismatch OPS-1 found between legacy evidence
> recorded on disk and the strict review validator — by recognising a validated
> `official_downloaded/` file as a second, conservative form of evidence, WITHOUT
> creating fake attachments/hashes, without network access, and without
> activating any calculation.

## 1. The mismatch (from OPS-1)

D5/D4 only counted a `LegalSourceAttachment` DB row as evidence. But several legacy
APPROVED official sources record their validated file as an on-disk
`official_downloaded/<slug>.<ext>` file + an `[official_source_validation]` notes
block carrying the file's sha256 — never a `LegalSourceAttachment` row. So they
were flagged as false "missing attachment" blockers.

OPS-1 could not fix this safely: `attach_official_source_file` is gated on
`manual_attach_allowed=true` (these are fetch-mode) AND does not create a
`LegalSourceAttachment` row anyway; `download_international_legal_sources` is a
bulk network command (broad blast radius). Hence D6 recognises the *real*
evidence instead of fabricating a row.

## 2. What OPS-1 over-assumed — and the honest finding

OPS-1 assumed "block present = validated". **It is not.** Inspecting the real 4:

| Country | Slug | validation_status | on-disk hash vs marker | verified? |
|---|---|---|---|---|
| EU | `eu-regulation-650-2012-successions` | **passed** | **mismatch** (file drift) | **no** |
| BE | `be-loi-1989-11-21-rc-auto` | **failed** | (n/a) | **no** |
| TN | `tn-code-dip-loi-98-97` | **failed** | (n/a) | **no** |
| TN | `tn-code-statut-personnel-livre-ix-succession` | **failed** | (n/a) | **no** |

So with a conservative bar **none of the 4 qualify**: BE/TN validation actually
*failed*; EU passed but the on-disk `.xml` no longer hashes to the recorded
sha256 (it is not provably the validated file). The honest result: the strict ALL
gate stays exit 1 — but now for *accurate* reasons (failed validation / hash
drift), not a false "missing attachment". **We do not force them green.**

## 3. The conservative bar — `verified_disk_evidence`

`apps/legal_sources/verified_disk_evidence.py` accepts
`verified_official_downloaded_file` ONLY when ALL hold:

1. the slug is a registry candidate;
2. an `official_downloaded/<slug>.<ext>` file exists (matched by glob, any
   extension — tolerates a registry `expected_format` mismatch like EU html→xml);
3. the notes `[official_source_validation]` block has `validation_status = passed`
   (a present-but-failed block is rejected);
4. the file on disk hashes to EXACTLY the `sha256` recorded in that marker.

A real `LegalSourceAttachment` row remains the primary evidence
(`legal_source_attachment`). Read-only, no DB write, no network. It reads the file
only to compute the hash for the equality check; it never exposes the raw content,
the full hash, an absolute path, the reviewer or the notes.

## 4. Integration

- **D5 alignment** — a missing attachment row WITH verified disk evidence becomes
  `ok_verified_disk_evidence` (impact none), no longer a false blocker; otherwise
  it stays blocking with the precise disk sub-reason. New `evidence_kind` field +
  `verified_disk_evidence_ok` summary counter.
- **D4 guard / validator** — an `approve` with no attachment row but verified disk
  evidence is allowed (warning, document-level only), not blocking. `approve`
  stays `calculation_activation_allowed = False`.
- **Admin** — the read-only "Show attachment alignment status" action shows the
  `evidence_kind`.

## 5. CI-safety & determinism

The service takes an optional `legal_data_root`, so tests use a temp dir (never
the real `legal_data/`). In CI (no `legal_data/`) the file is simply absent →
evidence False → deterministic. The default command exit stays 0; only the opt-in
`--fail-on-blocking` reflects the honest blocking set.

## 6. Fail-closed & rollback

No migration, no DB write, no attachment row, no network, no calculation
activation; FR/BE/MA/TN stay `calculation_ready=False`; the IT canary is
untouched. Reverting the branch removes the service + integration; nothing to
undo at the DB level.
