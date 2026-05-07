# Official-source validation readiness — pass 1

Iter: F-legal-sources-official-validation-pass1.

- generated: `2026-05-06T16:28:04.286749+00:00`
- LegalSource rows audited: 25
- bucket counts:
  - `OFFICIAL_BUT_NOT_CALCULATION_READY`: 6
  - `NEEDS_REVIEW_NON_OFFICIAL`: 18
  - `VALIDATED_OFFICIAL_SOURCE`: 1

## Per-source classification

| Country | Slug | Status | Bucket | sha256 match | marker | reasons |
| --- | --- | :-: | --- | :-: | :-: | --- |
| `BE` | `be-loi-1989-11-21-rc-auto` | `approved` | `OFFICIAL_BUT_NOT_CALCULATION_READY` | ✓ | — | — |
| `BE` | `be-tableau-indicatif-2020` | `needs_review` | `NEEDS_REVIEW_NON_OFFICIAL` | — | — | intrinsically_non_official |
| `BE` | `be-tableau-indicatif-2024` | `needs_review` | `NEEDS_REVIEW_NON_OFFICIAL` | — | — | source_kind=court_indicative_table, intrinsically_non_official |
| `BE` | `be-tables-schryvers-2026-page` | `needs_review` | `NEEDS_REVIEW_NON_OFFICIAL` | — | — | intrinsically_non_official |
| `BE` | `be-tables-schryvers-tableurs` | `needs_review` | `NEEDS_REVIEW_NON_OFFICIAL` | — | — | intrinsically_non_official |
| `EU` | `eu-regulation-650-2012-successions` | `approved` | `OFFICIAL_BUT_NOT_CALCULATION_READY` | ✓ | — | — |
| `FR` | `fr-bareme-capitalisation-gazette-palais-2022` | `needs_review` | `NEEDS_REVIEW_NON_OFFICIAL` | — | — | intrinsically_non_official |
| `FR` | `fr-bareme-capitalisation-gazette-palais-2025-page` | `needs_review` | `NEEDS_REVIEW_NON_OFFICIAL` | — | — | intrinsically_non_official |
| `FR` | `fr-loi-badinter-1985` | `approved` | `OFFICIAL_BUT_NOT_CALCULATION_READY` | ✓ | ✓ | — |
| `FR` | `fr-nomenclature-dintilhac-2005` | `needs_review` | `NEEDS_REVIEW_NON_OFFICIAL` | — | — | intrinsically_non_official |
| `FR` | `fr-referentiel-mornet-2024` | `needs_review` | `NEEDS_REVIEW_NON_OFFICIAL` | — | — | source_kind=private_bareme, intrinsically_non_official |
| `IT` | `it-dlgs-209-2005-cap-art-138-139` | `needs_review` | `NEEDS_REVIEW_NON_OFFICIAL` | — | — | no_official_sync_or_manual_attach_block |
| `IT` | `it-dpr-12-2025-tun-danno-biologico` | `approved` | `VALIDATED_OFFICIAL_SOURCE` | ✓ | ✓ | — |
| `IT` | `it-mimit-2025-07-aggiornamento-art-139` | `needs_review` | `NEEDS_REVIEW_NON_OFFICIAL` | — | — | no_official_sync_or_manual_attach_block |
| `IT` | `it-mimit-2025-12-aggiornamento-macrolesioni` | `needs_review` | `NEEDS_REVIEW_NON_OFFICIAL` | — | — | no_official_sync_or_manual_attach_block |
| `IT` | `it-tabelle-milano-2024` | `needs_review` | `NEEDS_REVIEW_NON_OFFICIAL` | — | — | no_official_sync_or_manual_attach_block |
| `MA` | `eu-regulation-650-2012-successions-fr-ma` | `needs_review` | `NEEDS_REVIEW_NON_OFFICIAL` | — | — | no_official_sync_or_manual_attach_block |
| `MA` | `ma-code-droits-reels-loi-39-08` | `needs_review` | `NEEDS_REVIEW_NON_OFFICIAL` | — | — | no_official_sync_or_manual_attach_block |
| `MA` | `ma-code-droits-reels-traduction-aute` | `needs_review` | `NEEDS_REVIEW_NON_OFFICIAL` | — | — | no_official_sync_or_manual_attach_block |
| `MA` | `ma-code-famille-moudawana-fr-pdf` | `approved` | `OFFICIAL_BUT_NOT_CALCULATION_READY` | ✓ | — | — |
| `TN` | `eu-regulation-650-2012-successions-fr-tn` | `needs_review` | `NEEDS_REVIEW_NON_OFFICIAL` | — | — | no_official_sync_or_manual_attach_block |
| `TN` | `tn-code-dip-loi-98-97` | `approved` | `OFFICIAL_BUT_NOT_CALCULATION_READY` | ✓ | — | — |
| `TN` | `tn-code-statut-personnel-compiled` | `needs_review` | `NEEDS_REVIEW_NON_OFFICIAL` | — | — | no_official_sync_or_manual_attach_block |
| `TN` | `tn-code-statut-personnel-livre-ix-succession` | `approved` | `OFFICIAL_BUT_NOT_CALCULATION_READY` | ✓ | — | — |
| `TN` | `tn-jort-code-statut-personnel-1956` | `needs_review` | `NEEDS_REVIEW_NON_OFFICIAL` | — | — | no_official_sync_or_manual_attach_block |

## Draft datasets blocked

| version_label | country | case_type | status | source_slug | reason |
| --- | :-: | --- | :-: | --- | --- |
| `FR-MORNET-2024-DRAFT` | `FR` | `road_accident_bodily_injury` | `draft` | `fr-referentiel-mornet-2024` | non_official_source_validation_pending |
| `FR-GAZETTE-PALAIS-2022-DRAFT` | `FR` | `road_accident_bodily_injury` | `draft` | `fr-bareme-capitalisation-gazette-palais-2022` | non_official_source_validation_pending |
| `BE-TABLEAU-INDICATIF-2020-DRAFT` | `BE` | `road_accident_bodily_injury` | `draft` | `be-tableau-indicatif-2020` | non_official_source_validation_pending |

## What can be approved after this pass

| Slug | Validated by file invariants | Manual status approval candidate |
| --- | :-: | :-: |
| `be-loi-1989-11-21-rc-auto` | ✓ | ✓ |
| `eu-regulation-650-2012-successions` | ✓ | ✓ |
| `fr-loi-badinter-1985` | ✓ | ✓ |
| `it-dpr-12-2025-tun-danno-biologico` | ✓ | — |
| `ma-code-famille-moudawana-fr-pdf` | ✓ | ✓ |
| `tn-code-dip-loi-98-97` | ✓ | ✓ |
| `tn-code-statut-personnel-livre-ix-succession` | ✓ | ✓ |

## Invariants enforced by this pass

- No `LegalSource.status` change (file-only validation).
- No `CompensationDataset` / `CalculationFormula` / `CompensationTableRow` write.
- No `LegalReview` row created (no fake reviewer).
- No FR / BE / MA / TN calculator activation.
- IT 35/10/0 → 26 268 / 27 353 / 28 439 EUR remains.

