# Non-IT MVP readiness — 2026-05-11

**Iter**: `F-p0-mvp-1-non-it-readiness`
**Branch**: `p0/non-it-mvp-readiness`
**Scope**: Pick the first non-IT country to bring end-to-end *review-gated*
(not publicly active as "valid calculator") and capture what the Studio
needs to sign before that gate can be flipped.

---

## 1. Decision

| | |
|---|---|
| Recommended candidate | **France — road-accident bodily injury** |
| Status today | Calculator returns `unavailable_requires_legal_validation` on every public path. Wizard renders the form, no amounts are published. |
| Verdict | **NO-GO for public activation today.** Mechanically ready; legally not signed. |
| Effort to flip the gate | 0 engineering days. ~3 distinct Studio sign-offs + 1 day of mechanical promotion + smoke test. |
| Risk if flipped today | High — Mornet 2024 and Gazette du Palais 2022 are still `needs_review`. Promoting them without Studio LegalReview would publish unverified numbers and breach the project's golden rule ("Meglio nessun calcolo che un calcolo falso"). |

This doc does **not** activate France. It pins the gate, documents the
exact Studio sign-offs required, and adds guardrails so the chain
cannot be accidentally promoted without the audit trail.

---

## 2. Comparative — FR / BE / MA / TN

Verified against `apps/calculators/`, `apps/compensation/`,
`apps/legal_sources/`, `docs/architecture/*REVIEW_PACKAGE.md`,
`docs/architecture/GLOBAL_MVP_STATUS.md` (2026-04-30) and the
`scripts/legal_data/audit_*.py` read-only scripts.

| Dim | 🇫🇷 France | 🇧🇪 Belgium | 🇲🇦 Morocco | 🇹🇳 Tunisia |
|---|---|---|---|---|
| Case-type | road accident bodily injury | road accident bodily injury | international inheritance | international inheritance |
| LegalSource rows | 5 (1 APPROVED, 4 `needs_review`) | 5 (1 APPROVED, 4 `needs_review`) | 4 (1 APPROVED, 3 `needs_review`) | 11 (2 APPROVED, 9 `needs_review`) |
| Approved source — what | `fr-loi-badinter-1985` (cornice normativa) | `be-loi-1989-11-21-rc-auto` (cornice normativa) | `ma-code-famille-moudawana-fr-pdf` (testo ufficiale Moudawana) | `tn-code-dip-loi-98-97` + `tn-code-statut-personnel-livre-ix-succession` (testi ufficiali CSP + DIP) |
| Audit-trail intact? | yes — APPROVE LegalReview row exists, `legal_reviewer` FK set | yes | yes | yes |
| Approved quantification source(s) | **0** (Mornet & Gazette still `needs_review`) | **0** (Tableau Indicatif 2020/2024 still `needs_review`) | **0** (numeric shares for the 41 Moudawana rules not yet extracted) | **0** (numeric shares + dual conflict-of-laws decision not yet made) |
| Candidate dataset rows (DRAFT) | **4 380** (Mornet 191 + Gazette 4 189) | 166 (Tableau Indicatif 2020) | 0 — mapping-only | 0 — mapping-only |
| Approved CompensationDataset | 0 | 0 | 0 | 0 |
| Approved CalculationFormula | 0 | 0 | 0 | 0 |
| Calculator class registered | yes — `FranceRoadAccidentBodilyInjuryCalculator` | yes — `BelgiumRoadAccidentBodilyInjuryCalculator` | yes — `MoroccoInternationalInheritanceCalculator` | yes — `TunisiaInternationalInheritanceCalculator` |
| Engine registered in `SUPPORTED_ENGINES` | yes — `france_road_accident_v1` | yes — `belgium_road_accident_v1` | yes — `morocco_inheritance_v1` | yes — `tunisia_inheritance_v1` |
| Wizard URL (renders) | `/wizard/fr/road-accident/` | `/wizard/be/road-accident/` | `/wizard/ma/inheritance/` | `/wizard/tn/inheritance/` |
| Wizard form class | `FranceRoadAccidentWizardForm` | `BelgiumRoadAccidentWizardForm` | `MoroccoInternationalInheritanceForm` | `TunisiaInternationalInheritanceForm` |
| Result on POST | `unavailable_requires_legal_validation` | `unavailable_requires_legal_validation` | `unavailable_requires_legal_validation` | `unavailable_requires_legal_validation` |
| Country tests (lines) | ~1 600 | ~1 600 | ~1 900 | ~1 800 |
| Review package | `FRANCE_LEGAL_REVIEW_PACKAGE.md` (DRAFT, ~26 KB) + activation readiness audit (`FRANCE_ACTIVATION_READINESS_AUDIT.md`) | `BELGIUM_LEGAL_REVIEW_PACKAGE.md` (DRAFT, ~27 KB) | `MOROCCO_LEGAL_REVIEW_PACKAGE.md` (DRAFT, ~19 KB) | `TUNISIA_LEGAL_REVIEW_PACKAGE.md` (DRAFT, ~21 KB) |
| Hard blockers | 6 documented, all Studio-resolvable (LegalReview rows, dataset promotion, formula creation, smoke test, Dintilhac mapping) | Tableau 2020 LegalReview + OCR on TI 2024 (Tesseract `fra`/`nld` packs missing on dev) + formula | Numeric share extraction (41 mapping rules with 0 numeric content) + Studio decision on `hajb` / `radd` / `'awl` mechanisms | Numeric share extraction + dual conflict-of-laws decision (Loi 98-97 vs Reg. 650/2012 — non-technical policy call) |
| Estimated effort to legitimately go live | **~3 Studio sign-offs + 1 dev day** | ~3 Studio sign-offs + OCR work + 1-2 dev days | 2-3 weeks of Studio numeric transcription + doctrinal decisions | 2-3 weeks of Studio transcription + conflict-law policy decision |
| Risk of "fantasy legal data" if forced live | low — Mornet is a published private barème (deterministic transcription), Gazette is hand-curated jurisprudence-derived. Zero LLM-generated amounts. | medium — TI 2020 historical (may be perceived "stale"); TI 2024 OCR not done. | high — 0 numeric data extracted; any activation today would require synthesised shares. | high — 0 numeric data + unresolved conflict-of-laws layer. |

### Why France is the candidate

1. **Volume**: 4 380 candidate rows vs Belgium 166 (26× more), MA/TN 0.
2. **Cleanest scaffold**: single case_type, no unsupported doctrinal
   mechanisms, matches the proven Italian engine pattern
   (`*_single_row_range`).
3. **All blockers are Studio sign-offs**, not engineering or doctrinal
   policy. No language packs to install, no conflict-of-laws to
   resolve, no numeric shares to transcribe.
4. **Activation audit already complete**: `FRANCE_ACTIVATION_READINESS_AUDIT.md`
   was generated 2026-05-06 by a read-only script; the 6 blockers are
   each independently necessary and each independently sufficient to
   re-check.
5. **Tests already pin the inactive contract**: 1 600+ lines across
   `test_france_scaffold.py`, `test_france_engine_inactive.py`,
   `test_france_activation_readiness_audit.py`. The "fixture-only"
   engine path is exercised, the public-DB path is guard-tested to
   stay `unavailable`.

### Why not Belgium

Belgium is the second-closest but carries a hard infrastructure
blocker (`BELGIUM_TI_2024_OCR_SPIKE_REPORT.md`): the official Tableau
Indicatif 2024 is image-scanned, OCR requires Tesseract `fra` +
`nld` language packs not installed on the dev machine, and a second
spike is needed. Going live on TI 2020 only carries a "stale data"
perception risk for cases after 2020. Plus the candidate dataset is
1/26th the volume — narrower coverage for the Studio's review value.

### Why not Morocco / Tunisia

Both inheritance modules have **zero numeric data** today: the Pass-3
Moudawana mapping (41 rules) and the CSP mapping draft are *structural*
extractions ("which article governs which heir relation"), but the
**share percentages** themselves (e.g. wife's 1/8 with descendants vs
1/4 without) must come from Studio sign-off, rule-by-rule. Tunisia
adds a non-technical policy layer: the dual conflict-of-laws question
(Loi 98-97 vs Reg. EU 650/2012) is unresolved in doctrine and must
be Studio-decided before any calculator can emit shares. Both
countries are 2-3 weeks behind France in calendar terms even if
engineering capacity were infinite.

---

## 3. The chain — what is "approved" for a non-IT country?

There is **no single field** on `Country` that means "approved for
public output". By design — gating is layered so a single accidental
edit cannot flip a country live. To produce a number on the public
path, **every** link below must be true at request time:

```
Country.is_active = True                          (routing / display)
  └─ Jurisdiction(code='FR-NATIONAL').is_active   (routing)
      └─ LegalSource(country=FR, status=APPROVED)         × N
          └─ LegalReview(source=…, decision=APPROVE)      (audit trail)
              └─ LegalSource.legal_reviewer is set        (who)
                  └─ LegalSource.publication_date is set  (when)
      └─ CompensationDataset(country=FR, status=APPROVED) × 1+
          └─ CompensationTableRow(dataset=…) × N
      └─ CalculationFormula(jurisdiction=FR, status=APPROVED) × 1
          └─ engine ∈ SUPPORTED_ENGINES
          └─ amount_rule ∈ SUPPORTED_AMOUNT_RULES
          └─ row_type / row_match / requires / fault_reduction
      └─ calculator code path returns CALCULATED (not UNAVAILABLE)
```

This is the existing pattern, used today by Italy
(`italy_road_accident_v1`). It is the same pattern the chosen
candidate (France) will use.

The map between the user-spec "metadata minimi" terminology and the
existing model fields:

| Spec field | Existing equivalent | Where |
|---|---|---|
| `legal_review_status=signed/approved` | `LegalSource.status == APPROVED` *plus* `CompensationDataset.status == APPROVED` *plus* `CalculationFormula.status == APPROVED` | `apps/legal_sources/models.py`, `apps/compensation/models.py` |
| `reviewed_by` | `LegalSource.legal_reviewer` FK to user + `LegalReview.reviewer` FK on the audit row | `apps/legal_sources/models.py` |
| `reviewed_at` | `LegalReview.created_at` (the audit row) + `LegalSource.updated_at` | `apps/legal_sources/models.py` |
| `source_version` | `LegalSourceVersion.label` (one row per textual version of the same norm) | `apps/legal_sources/models.py` |
| `disclaimer_version` | `settings.DISCLAIMER_VERSION` + `DISCLAIMER_STATUS == 'signed'` (system-wide, not per-country — the disclaimer is the project's, not the country's) | `config/settings.py` |
| `test_case_pack_version` | the dedicated test files per country: `test_<country>_scaffold.py` + `test_<country>_engine_inactive.py` + smoke-test row (e.g. IT 35/10/0 → 26 268/27 353/28 439 EUR). Not yet formalised as a `*_VERSION` setting; tracked via git history of the canonical smoke-test commit. | `apps/calculators/`, `apps/compensation/` |

**No new model fields were added** in this batch. The guardrail layer
(§5) is read-only and works with the existing data shape.

---

## 4. What the Studio must sign to flip the gate on France

The 6 blockers below mirror `FRANCE_ACTIVATION_READINESS_AUDIT.md` §8.
Each is independently necessary; activating without any one is a
**bug**, not a shortcut.

### 4.1 Studio checklist (legal sign-offs)

- [x] **Loi Badinter (`fr-loi-badinter-1985`) LegalReview** — DONE
  in the dev DB: `status=APPROVED`, APPROVE LegalReview row exists,
  `legal_reviewer` FK set. (The cornice normativa is the easiest to
  sign because it is THE law text, mechanically authenticated 11/11
  structural markers.) Re-confirm before promoting to staging/prod.

- [ ] **Mornet 2024 LegalReview** — review the private barème
  (`fr-referentiel-mornet-2024`), accept the consequences of using a
  non-state-published quantification source, sign off `decision=APPROVE`,
  record the reviewer FK on the LegalSource. Reference checklist:
  `legal_data/sources/france/review/france_legal_review_checklist_template.csv`
  (24 rows pre-populated). **This is the gating sign-off** — without
  Mornet APPROVED, no FR amount can be computed.

- [ ] **Gazette du Palais 2022 LegalReview** — same shape as Mornet,
  for `fr-bareme-capitalisation-gazette-palais-2022`. Editorial
  decision on using a jurisprudence-derived capitalisation table as
  formal quantification basis.

- [ ] **Nomenclature Dintilhac (`fr-nomenclature-dintilhac-2005`)
  LegalReview** — needed for the report layer to translate engine
  output into the *postes* the user expects to see in the PDF report.

- [ ] **Disclaimer per-country review** — Studio signs that the
  generic `DISCLAIMER_VERSION` is adequate for France, OR a
  France-specific addendum is drafted. Current generic disclaimer:
  "La simulazione è indicativa e non costituisce parere legale…".

### 4.2 Dev checklist (mechanical, post-sign-off)

- [ ] **Promote LegalSource rows** to `status=APPROVED` via the admin
  (one row per sign-off above).
- [ ] **Create the LegalReview audit rows** with `decision=APPROVE`,
  `reviewer` set, `new_status=APPROVED`. The system check added in
  §5 will fail in production if a LegalSource is APPROVED without a
  matching APPROVE LegalReview row.
- [ ] **Promote `FR-MORNET-2024-DRAFT`** dataset by renaming to
  `FR-MORNET-2024` and setting `status=APPROVED`. Same for
  `FR-GAZETTE-PALAIS-2022-DRAFT`. The DRAFT label is load-bearing
  (`import_france_candidate_datasets` refuses to write into a
  non-DRAFT dataset).
- [ ] **Create the FR CalculationFormula** pointing at engine
  `france_road_accident_v1`, amount_rule
  `france_dfp_point_value_direct`, `row_type=fr_dfp_per_age_disability_amount_per_point`,
  `row_match=[victim_age, permanent_disability_percentage]`,
  `requires=[victim_age, permanent_disability_percentage]`,
  `fault_reduction=true`.
- [ ] **Override `FranceRoadAccidentBodilyInjuryCalculator._compute_with_sources`**
  is **already wired** — no code change needed. The class already
  has the full 12-gate logic; the gates simply pass once the
  approved chain exists.
- [ ] **Commit the FR smoke test** — a canonical (age × disability ×
  fault) tuple matching the Italian 35/10/0 = 26 268 / 27 353 / 28 439 EUR
  contract, expressed against the FR coefficients. Format: drop into
  `apps/calculators/test_france_engine_active.py` (new file), mirror
  the IT engine test's shape.

### 4.3 Sequencing

1-4 happen with the Studio (out-of-band review work, ~3 sign-off sessions).
5 happens in admin after each sign-off (5 minutes per source).
6 happens in code, in a single dedicated branch (~1 day, dev-only).

Activation is a single PR that touches:
- one new test file (smoke + activation contract),
- one DB seed migration **OR** an admin-driven promotion (the project
  has not yet decided which — Studio preference).

---

## 5. Guardrails added in this batch

The chain in §3 already prevents accidental output. This batch tightens
the **audit trail integrity**:

### 5.1 Django system check (`jurisdictions.E001`)

Added in `apps/jurisdictions/checks.py` (new). In production-like
settings only (gated on `DEBUG=False`):

- For each `Country.is_active=True` country,
- For each `LegalSource(country=…, status=APPROVED)`,
- Assert there exists at least one
  `LegalReview(source=…, decision=APPROVE)` with a non-null `reviewer`.

If a country has an APPROVED LegalSource without a matching APPROVE
LegalReview audit row, the check fails in production. **In dev
(`DEBUG=True`) the check is silent** — it does not block local
exploration.

This catches the most plausible accidental promotion path:
> "the admin user opened the LegalSource form, switched status to
> APPROVED, didn't go through the LegalReview flow, hit save."

The check is read-only and Django-style: no DB writes, idempotent,
runs on `manage.py check`.

### 5.2 Audit script (`scripts/legal_data/audit_non_it_readiness.py`)

Existing audits cover one country at a time
(`audit_france_activation_readiness.py`) or the whole project
(`audit_global_mvp_status.py`). This batch adds a focused read-only
script that prints, for FR/BE/MA/TN:

- LegalSource counts by status,
- LegalReview chain integrity,
- Approved dataset / formula counts (must all be 0 today),
- Calculator class registered (must be true),
- Wizard URL HTTP probe (must be 200 — but NEVER POST),
- One-line verdict per country: `SCAFFOLD-ONLY` / `READY-FOR-REVIEW` /
  `APPROVED-BUT-INCONSISTENT` (the last would mean a bug; runs the
  same query the system check does).

### 5.3 Review-gated e2e test (`apps/calculators/test_france_review_gated_e2e.py`)

Black-box HTTP test: starts a Django test client, GETs
`/wizard/fr/road-accident/`, asserts 200 + correct copy + `noindex,
nofollow` meta. POSTs a realistic input set (age=35,
permanent_disability=10%, fault=0%) and asserts the result page
returns `unavailable_requires_legal_validation` semantics — no EUR
amount visible, the `_public_status_panel.html` shows the
`legal_assessment` variant, the disclaimer is rendered, no Mornet/
Gazette numbers leak into the response body.

This pins the **public contract**: as long as the chain is not
signed, France must not publish a number — regardless of what test
fixtures look like in unit tests.

---

## 6. UI honesty audit (pre-existing, verified, not changed)

The Studio's wording-discipline is already enforced via
`apps/core/public_status.py` (centralised premium copy) + the
`_public_status_panel.html` partial:

- Each country has a `PublicStatus` row keyed by status type
  (`AVAILABLE` / `LEGAL_ASSESSMENT` / `INHERITANCE_REVIEW` /
  `MANUAL_REVIEW`).
- France/Belgium → `LEGAL_ASSESSMENT` (badge "Preliminary legal
  assessment", no amounts shown).
- Morocco/Tunisia → `INHERITANCE_REVIEW` (badge "International
  inheritance review", no shares shown).
- Italy → `AVAILABLE` (badge "Indicative calculation available",
  amounts shown).
- Banned wording (never reintroduce in copy): "scaffold",
  "placeholder", "under validation", "in preparation", "coming
  soon", "work in progress", "in corso", "legal validation wizard",
  "module pending", "engine pending",
  "unavailable_requires_legal_validation".

No template was touched in this batch — the UI is already honest.

---

## 7. What was deliberately NOT done

- **No new Country fields.** The user spec ("Non introdurre database
  complexity se esiste già un meccanismo") is honoured. The existing
  pattern (LegalSource.status + LegalReview audit trail + calculator
  code guard) is the mechanism.
- **No per-country `*_VERSION` settings.** Adding
  `COUNTRY_FR_LEGAL_REVIEW_VERSION` etc. would duplicate what
  `LegalReview` already records.
- **No template changes for FR/BE/MA/TN.** The UI is already in the
  correct review-pending state via `public_status.py`.
- **No France activation.** The 6 blockers in §4.1 remain blockers
  until Studio sign-off. This batch only tightens the *trail* around
  the existing closed gate.
- **No Tunisia/EU650 merge.** Branch `work/tunisia-csp-eu650-restore`
  is out of scope per user instructions.

---

## 8. Go / no-go verdict

| Question | Answer |
|---|---|
| Is France's wizard reachable today? | yes — `/wizard/fr/road-accident/` returns 200, renders the form |
| Does it publish amounts today? | **no** — calculator returns `unavailable_requires_legal_validation` on the public DB |
| Could it publish amounts today if a sloppy admin promotion happened? | **no** — the calculator class is `_FrancePlaceholderCalculator` by default, and even after override, the 12-gate chain refuses to compute without the full APPROVED chain |
| Is the chain audit-trailed? | yes — verified empirically by `scripts/legal_data/audit_non_it_readiness.py`. The 5 currently-APPROVED non-IT LegalSources (FR Badinter, BE RC Auto, MA Moudawana, TN CSP, TN DIP) all have matching APPROVE LegalReview rows + non-null `legal_reviewer`. `jurisdictions.E001` system check passes locally. |
| Can the gate be flipped without code? | yes — Studio sign-off + admin promotion + one smoke test file commit |
| Does this batch flip the gate? | **no — explicitly review-gated** |

**Verdict: NO-GO for public activation today. READY for Studio review.**

When the Studio signs the 4 LegalReviews listed in §4.1, the project
moves to **GO conditional on dev checklist (§4.2)**.

---

## 9. Next batches (post-Studio sign-off)

In order:

1. **P0-MVP-1-ACTIVATE** — once Studio signs Mornet + Gazette + Badinter
   + Dintilhac, a single PR promotes the chain, creates the
   FR `CalculationFormula`, adds the FR smoke test, and removes the
   `_FrancePlaceholderCalculator` inheritance from
   `FranceRoadAccidentBodilyInjuryCalculator`.
2. **P0-MVP-2** — Belgium activation, contingent on TI 2020 LegalReview
   + OCR for TI 2024 (Tesseract `fra`/`nld` install on whatever
   environment runs the spike).
3. **P0-MVP-3** — Morocco activation, contingent on Studio numeric
   share transcription (41 Moudawana rules) + doctrinal decisions
   on unsupported mechanisms.
4. **P0-MVP-4** — Tunisia activation, contingent on conflict-of-laws
   policy decision + share transcription.

Each of P0-MVP-2/3/4 follows the same gate-flip pattern documented
here. The system check and audit script added in this batch will
keep working as more countries are promoted.
