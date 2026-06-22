# Legal Source Acquisition — Plan v1

**Branch:** `feature/legal-source-acquisition-v1` (stacked on
`feature/source-version-approved-datasets`).
**Date:** 2026-06-22.
**Scope:** read-only consolidation + acquisition planning. **No calculation
activated, no source promoted to `approved`, no legal value invented.**

> Cardinal rule: *meglio nessun calcolo che un calcolo falso.* This phase only
> reports status and plans acquisition. Every legal value used in a public
> calculation must trace to an `approved` `LegalSource` + `approved`
> `CompensationDataset` + `approved` `CalculationFormula`. Today only Italy
> (road-accident, D.P.R. 12/2025) is calculation-ready.

---

## 0. What already exists (do not duplicate)

The platform already has a mature legal-source pipeline. This phase **reinforces**
it; it does not rebuild it.

- **Registry**: `config/official_source_registry.json` — 15 entries with
  official URLs, `source_kind`, content markers, and per-source ingest policy
  (`can_auto_ingest`, `human_exception_review_required`, `ingest_mode`).
- **Models**: `LegalSource`, `LegalSourceVersion`, `LegalSourceAttachment`,
  `LegalReview` (append-only), plus `CompensationDataset` /
  `CompensationTableRow` / `CalculationFormula`.
- **Commands**: `seed_{italy,france,belgium,morocco,tunisia}_legal_sources`,
  `sync_official_sources`, `download_international_legal_sources`,
  `attach_official_source_file`, `validate_official_legal_sources`,
  `promote_official_legal_sources`, `export_italy_tun_dataset`.
- **Audit scripts**: `scripts/legal_data/audit_*` (non-IT readiness, global MVP
  status, official-source validation readiness, …).

**Gap closed by this phase:** there was no single *read-only status report*
command. Added `report_legal_source_status` + a committed snapshot
(`LEGAL_SOURCE_STATUS_2026-06-22.md`).

---

## 1. Source-status vocabulary (and the decisive distinction)

`SourceStatus`: `draft → extracted → needs_review → reviewed → approved →
deprecated → replaced`. Only `approved` may ever feed a calculation.

**Authenticated ≠ calculation-ready.**
- `status == approved` ⇒ the source **document** was downloaded, hashed
  (SHA-256), marker-checked and signed off. It does **not** activate a calc.
- **calculation-ready** ⇒ the source backs an `approved` `CompensationDataset`
  (with rows) and an `approved` `CalculationFormula`. Today: **1 source** (IT).

The current snapshot: **31 sources, 7 authenticated, 1 calculation-ready.**

---

## 2. Online-acquisition reality in this environment

Live fetching is possible but unreliable for primary documents:
- **gazzettaufficiale.it** returns a JS-rendered shell ("Gazzetta in fase di
  caricamento") — no server-side document text.
- **Legifrance** returns HTTP 403 to non-browser clients (registry already
  flags `manual_attach` for `fr-loi-badinter-1985`).
- **EUR-Lex** returns HTTP 202 with empty body to non-browser clients.

**Decision (fail-closed):** this phase does **not** scrape coefficient tables or
fabricate source data from the web. It uses web search only for **bibliographic
verification** (publisher, edition, publication date — matters of public
record), recorded below with access date 2026-06-22. Primary-document
acquisition stays on the existing `attach_official_source_file` /
`sync_official_sources` pipeline, driven by the Studio.

---

## 3. Per-country readiness matrix

Legend: **Calc** = calculation-ready (backs approved dataset); **Auth** =
authenticated approved source(s) present; **Action owner** = who must act next.

| Country | Calc | Auth sources | Needs review | Status | Action owner |
|---|:---:|---:|---:|---|---|
| **IT** | ✅ | 1 | 4 | road-accident live (D.P.R. 12/2025) | dev+Studio (extend) |
| **FR** | ❌ | 1 | 4 | sources catalogued; no approved dataset | Studio review |
| **BE** | ❌ | 1 | 4 | sources catalogued; no approved dataset | Studio review |
| **MA** | ❌ | 1 | 3 | mapping-only; no faraïd dataset | Studio mapping |
| **TN** | ❌ | 2 | 9 | CSP articles catalogued; no dataset | Studio mapping |
| **EU** | n/a | 1 | 0 | Reg. 650/2012 (applicable-law context) | — |

### 3.1 Italia (calculation-ready)
- **Live**: `it-dpr-12-2025-tun-danno-biologico` (`approved`) → approved
  datasets `DPR-12-2025` (biologico) + `DPR-12-2025-MORAL` (morale) →
  art. 138 formula. Canary 35/10/0 = **26 268 / 27 353 / 28 439 €** (frozen).
- **Needs review (catalogued, not calc)**: CAP art. 138/139, MIMIT updates
  (microlesioni/macrolesioni), Tabelle Milano.
- **Bibliographic verification (2026-06-22)**: *Tabelle Milano — danno non
  patrimoniale, ed. 2024* exist, published by the **Osservatorio Giustizia
  Civile del Tribunale di Milano** (released 5 June 2024; ISTAT-revalued to
  1 Jan 2024, +16.2268% vs 2021). **Nature: court orientative table, NOT a
  binding norm** → under the registry policy this is a
  `court_indicative_table` requiring **human exception review**; it is NOT
  auto-promotable and must NOT silently replace the TUN values.
  Distribution: `ordineavvocatimilano.it`.
- **Next step (do not auto-apply)**: if the Studio wants Milano alongside TUN,
  add it as a NEW `LegalSource` + `LegalSourceVersion` in `needs_review`
  (manual attach), never as a silent replacement of the approved TUN dataset.

### 3.2 Francia (catalogued, not calc)
- Sources: `fr-loi-badinter-1985` (Legifrance, manual_attach — 403),
  Nomenclature Dintilhac, référentiel Mornet 2024 (`private_bareme`, never
  auto-promotable), ONIAM, Gazette du Palais capitalisation barème.
- **Distinguish**: Loi Badinter = *binding norm*; Dintilhac = *nomenclature*;
  Mornet / ONIAM / Gazette = *référentiels indicatifs / prassi* (orientative).
- **Next step**: Studio fills the FR review checklist
  (`docs/legal_sources/FRANCE_LEGAL_REVIEW_PACKAGE.md`), then datasets can be
  seeded `needs_review` and promoted only after sign-off.

### 3.3 Belgio (catalogued, not calc)
- Sources: `be-loi-1989-11-21-rc-auto` (`approved` law), `be-tableau-indicatif-2020`
  / `be-tableau-indicatif-2024` (`court_indicative_table`).
- **Bibliographic verification (2026-06-22)**: *Tableau Indicatif 2024* is
  published by the **Union Royale des Juges de Paix et de Police** and is
  **not legally binding** (orientative). The registry already classifies it
  `court_indicative_table`, `auto_ingest=false` — correct.
- **Known blocker (from prior audit)**: TI-2024 PDF is image-scanned; OCR
  needs `fra`/`nld` Tesseract language packs (Studio-side install).
- **Next step**: Studio review checklist + OCR re-spike for TI-2024; TI-2020
  may only be promoted as a `historical_fallback`.

### 3.4 Marocco (mapping-only, not calc)
- Sources: Moudawana (Code de la famille), Code des droits réels (Loi 39-08),
  Reg. 650/2012 (manual download). **No faraïd quote dataset.**
- **Next step**: Studio signs the article mapping (faraïd, ḥajb, ʿawl, radd)
  before any structured quote dataset is transcribed. Calculation impossible
  until then.

### 3.5 Tunisia (mapping-only, not calc)
- Sources: CSP Livre IX (succession) articles, Code DIP (Loi 98-97). 11 rows,
  2 approved (articles authenticated), **no dataset**.
- **Next step**: Studio signs CSP mapping **and** a written position on the
  double conflict rule (Loi 98-97 vs Reg. 650/2012) before any dataset.

---

## 4. Acquisition policy (reaffirmed)

1. **Primary sources only** for calculation: government sites, official
   gazettes, ministries, courts, para-institutional bodies. Doctrine only as
   support, never as the sole calculation basis. No SEO blogs / commercial
   tables as a calculation source.
2. **Manual attach** is the official path for sources with technical blockers
   (403 / anti-bot / JS-only / scanned PDF): download by the Studio →
   `attach_official_source_file` (SHA-256 + marker check + manifest) →
   `validate_official_legal_sources` → `promote_official_legal_sources`
   (re-validates in-process). Never a silent promotion.
3. **Court indicative tables and private barèmes** (Milano, Belgian TI, Mornet,
   Gazette du Palais) are `needs_review` / human-exception only — never
   auto-promoted, even when authenticated.
4. **Heavy / copyrighted raw files** stay gitignored; only manifests, hashes,
   URLs and reports are committed (existing policy).

---

## 5. What this phase delivered

- `apps/legal_sources/status_report.py` + `report_legal_source_status` command
  (read-only, network-free, PII-safe, testable).
- `docs/legal_sources/LEGAL_SOURCE_STATUS_2026-06-22.md` (generated snapshot).
- This plan + per-country readiness matrix.
- Tests for the report command.

**Not delivered (intentionally):** no new approved source, no dataset, no
formula, no calculation, no scraped coefficient table.

---

## 6. Recommended next steps (separate phases)

1. **Studio review packages** (FR, BE, MA, TN) — already drafted; the Studio
   fills them. This is the real unblocker, not dev work.
2. **Milano tables (IT)** — only if the Studio wants them, add as a new
   `needs_review` source/version via manual attach; never replace TUN silently.
3. **H1-8 simulation provenance** — see
   `docs/audits/H1_8_SIMULATION_PROVENANCE_DESIGN.md` (design only; not
   implemented here).
4. **DB CheckConstraint** for `approved → source_version` (deferred in the
   stacked PR) once the ~65 synthetic fixtures are updated.
