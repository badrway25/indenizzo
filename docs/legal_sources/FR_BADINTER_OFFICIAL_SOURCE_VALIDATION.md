# FR Loi Badinter — Official Source Validation

**Iter:** `F-official-source-fr-badinter-manual-attach-and-legal-source-validation`.

**Generated:** `2026-05-03T16:29:12+00:00`.

Read-only validation of the manually-attached PDF against the structural
markers expected on any authentic copy of Loi n°85-677 du 5 juillet 1985.
This report does not approve the source for calculator use; it only attests
that the file matches the canonical Légifrance text on the markers checked.

## File integrity

| Field | Value |
|-------|-------|
| Local path | `legal_data/sources/france/manual_attached/fr-loi-badinter-1985.pdf` |
| Size (bytes) | 342697 |
| sha256 | `6165313bad9dd4cbe07648ce5e554047edd4bf6d0394ecd7a1545b748b2c876e` |
| Magic bytes | `%PDF-` (verified) |
| Légifrance canonical URL | <https://www.legifrance.gouv.fr/loda/id/JORFTEXT000000693454> |

## Structural markers

Match policy: case-sensitive substring search on `pdfplumber`-extracted text
(all pages). Missing any marker fails the verification: a single absence is
evidence of substitution, redaction, or OCR corruption.

| # | Label | Marker | Status | Reason for inclusion |
|---|-------|--------|--------|----------------------|
| 1 | `law_number` | `Loi n° 85-677` | PASS | law identity |
| 2 | `signature_date` | `5 juillet 1985` | PASS | law signing date |
| 3 | `title_object` | `amélioration de la situation des victimes d'accidents de la circulation` | PASS | law subject — opening clause |
| 4 | `article_1` | `Article 1` | PASS | scope: roadway accidents |
| 5 | `vehicle_definition` | `véhicule terrestre à moteur` | PASS | art. 1 — vehicles in scope |
| 6 | `article_3` | `Article 3` | PASS | non-driver victim indemnification regime |
| 7 | `faute_inexcusable` | `faute inexcusable` | PASS | art. 3 — only inexcusable fault excludes non-driver victims |
| 8 | `article_4` | `Article 4` | PASS | driver fault doctrine |
| 9 | `faute_conducteur` | `faute commise par le conducteur` | PASS | art. 4 — driver-fault clause |
| 10 | `article_12` | `Article 12` | PASS | insurer offer deadline regime |
| 11 | `offer_deadline_8_months` | `délai maximum de huit mois` | PASS | art. 12 — 8-month maximum offer deadline |

## Conclusion

**Verdict:** *source authenticity verified.*

## What this verification does NOT do

- It does **not** create a `LegalReview` row. Source authenticity is not
  the same as Studio approval; only a human reviewer can promote
  `LegalSource.status` to `APPROVED`.
- It does **not** activate the FR road-accident calculator. The engine,
  the dataset, and the formula remain pending; `run_simulation`
  continues to return `unavailable_requires_legal_validation` for
  `FR-NATIONAL × road_accident_bodily_injury`.
- It does **not** alter Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR.

## What is still required to make FR road-accident calculable

1. Studio legal review of Loi Badinter scope on `road_accident_bodily_injury`
   → `LegalReview.decision=approve` → manual promotion of
   `LegalSource.status` to `APPROVED`.
2. A validated quantification source (Référentiel Mornet, Gazette du Palais,
   or jurisprudence-derived bareme): currently `private_bareme` /
   `human_exception_only` in the registry.
3. A `CompensationDataset` + `CalculationFormula` matching the validated
   bareme (separate import pipeline).
4. An `apps/calculators/engines/france.py` engine with deterministic mapping
   victim_age × disability % × case category → amount.
5. Smoke tests for at least one age × disability × fault triple, locked in
   `apps/calculators/test_*.py`.
