# P1 — Premium Product & Calculation Reality Audit

**Branch baseline:** `product/staging-readiness-p0` @ `c78c01b` · **Date:** 2026-06-24 · **Mode:** audit-only (no code changes).
Method: 6 parallel read-only code auditors + real browser QA (desktop 1440 / mobile 390) + the full read-only gate.

---

## 1. Executive summary

The platform is **further along and more honest than most MVPs** — and **not yet ready for unsupervised public use**. Two things are genuinely strong: (a) the **visual identity is real and premium** (navy/ivory/bronze, Cormorant Garamond + Inter, hand-written token system — not Bootstrap), and (b) the **trust/provenance layer is rigorously fail-closed** (Italy-only public calculation, approved-source gating, a reproducible canary, DB constraints, leak guards, FR/BE/MA/TN truly inert). The gaps are equally real: the **calculation covers a narrow slice** of Italian bodily-injury damages; **PDF reports, retention/deletion, lead webhook, and several apps are stubs**; **FR/AR i18n is ~49%** with visible English/Italian text leaking onto French/Arabic pages; and the **footer still shows `[da configurare prima del go-live]` for the law-firm's legally-required identification** (Ordine, P.IVA, PEC).

**Honest one-liners:** Premium? *Visually yes (7.5/10), as an end-to-end product no.* Calculations trustworthy? *Yes for the one modelled scenario (IT permanent biological + moral), source-backed and reproducible — but narrow and not yet independently legal-reviewed.* Publicly reliable today? *No — needs the items in §13/§14 first.*

## 2. Stato tecnico attuale

Gate (this run): `check` OK · `makemigrations --check` no changes · canary `--fail-on-drift` **exit 0** (IT 35/10/0 → 26.268 / 27.353 / 28.439 €, reproducible) · all D1–D6 commands exit 0 · strict IT **0** · strict ALL **1** (EU only, OPS-2). i18n: IT 58.8% / FR 49.3% / AR 49.3%. 126 test files; CI green (python-tests, production-checks, Playwright, Lighthouse-desktop). 0 open PRs. Tree clean.

## 3. Architettura software

**Solid:** jurisdictions, legal_sources (provenance + SHA-256 + review workflow), compliance/consent (double GDPR art.6/9, append-only audit), cases (Simulation persistence, status-gated), crm (Lead + outbox), calculators registry (`get_calculator`, fail-soft), security hardening (CSP, HSTS, MFA middleware, secret guard). Public flow home→countries→wizard→result is ~80% wired.

**Fragile / incomplete:** `compensation` datasets populated only for IT; **FR/BE/MA/TN engines are scaffolds** returning `unavailable_requires_legal_validation`; **`analytics`, `cms_content`, `inheritance`, `calculators` models are empty stubs**; **PDF rendering missing** (no weasyprint/reportlab generator found — `apps/reports` persists models only); **retention/deletion declared but not enforced** (no Celery task); **lead webhook dispatcher not implemented** (rows created, never processed); D1–D6 are manual CLI (no orchestration). Public readiness is cached and can go stale after a promotion.

## 4. Flussi utente pubblici

home → `/countries/` → country/case-type landing → wizard (Italia road-accident bodily injury active) → result with provenance → lead/contact. Italy path produces a real, source-backed range. FR/BE/MA/TN case-type pages render and **offer a "Lancer la simulation indicative" CTA**, but the simulator fail-closes to an "unavailable / requires legal validation" result — confirmed by `can_calculate=False`. **UX gap:** `/countries/` and the case-type CTAs don't visually distinguish "available now" from "coming soon", which risks a dead-end click.

## 5. Flussi Studio/admin

Django admin + a read-only D1–D6 chain: readiness (D1) → evidence/pack-index (D2) → batch (D3) → intake guard + validator (D4) → attachment-alignment audit (D5) → verified-disk-evidence bridge (D6). LegalReview is append-only with a fail-closed decision guard; promotion (`promote_official_legal_sources`) re-validates the file + SHA-256 and is allow-listed. No admin "approve calculation" button anywhere. There is **no finished Studio dashboard / readiness UI** — everything is CLI + raw admin.

## 6. UX/UI audit

- **Bottoni:** premium — primary `bg-ink-950`, secondary outline, gold accent, all `rounded-full` with transitions. Missing `:disabled` / `:loading` / `:success` states.
- **Icone:** sparse, inline SVG; consistent but minimal.
- **Forms:** styled (sand bg, rounded-xl, gold focus) but **only server-side validation**, no inline hints, no real-time feedback.
- **Modali/popup:** cookie banner uses `classList` toggle, not animated; no real modal system.
- **Badges/status:** mature multi-variant (ok/gold/neutral, uppercase tracking). Good.
- **Cards:** premium (`rounded-3xl`, `shadow-card`, sand/white, stone borders).
- **Navbar:** clean on desktop; **cramped on mobile** (no hamburger; nav items truncate).
- **Footer:** premium structure **but shows `[da configurare prima del go-live]` placeholders** for AVVOCATO / ORDINE FORENSE / P.IVA / PEC / SEDE / ASSICURAZIONE — a legal/regulatory blocker, not just cosmetic.
- **Tipografia:** Cormorant Garamond (serif H1–H4, −0.01em) + Inter (body), vendored locally with unicode-range subsetting. Genuinely premium.
- **Colori:** ink notte / oro sobrio / warm sand / cool stone — matches the brief; tokens in `static/css/site.css:30-50`.
- **Mobile (390):** responsive (hero stacks, 2-col country grid, full-width CTAs). Nav cramped.
- **RTL (AR):** structure mirrors correctly (navbar, alignment, Amiri/Tajawal fonts). **But large untranslated English blocks leak** ("What the Studio will do", "Documents to prepare") plus an IT heading ("Situazioni rischio") — same leak on FR. Premium-breaking.
- **Accessibilità:** focus rings (2px gold, offset), skip-to-content, `aria-live` on cookie banner, sr-only. No dark mode. Keyboard nav partial (few landmarks).

**Console/CSP:** 0 errors on every page checked.

## 7. Valutazione premium

- **Già professionale:** palette, typography, cards, badges, buttons, static pages (home/countries/case-type), provenance result card, accessibility fundamentals.
- **Non premium / amatoriale:** mixed-language leaks on FR/AR, footer go-live placeholders, no wizard stepper, no loading/error states, no available-vs-coming-soon signalling, cramped mobile nav.
- **Da rifare prima:** (1) wizard stepper + loading/error/validation states; (2) i18n leak fix on FR/AR; (3) configure the firm's legal identification; (4) country availability signalling. Verdict: **visually premium foundation (7.5/10), interactive/wizard UX ~5/10**.

## 8. Palette e direzione visuale proposta (non implementare ora)

The current palette is already close to the brief's target; **keep it, refine — do not restart.** Existing tokens: ink `#07172f`/`#0c2046`, gold `#b88336`, sand `#faf6ef`, stone `#d6d3cc`. For P2, formalise:
- **Heading** Cormorant Garamond (keep); **Body** Inter (keep); add a documented type scale (eyebrow 11px/0.22em → H1 serif 36–44px → body 15–18px/1.6).
- **Component system to name & document** (currently arbitrary Tailwind values): `.btn-primary/.btn-secondary/.btn-ghost/.btn-legal`, `.badge-{ok,gold,neutral,country}`, `.card`, `.provenance-card`, `.unavailable-country-card`, `.wizard-step`, `.disclaimer-block`, plus `:disabled/:loading/:success/error` states.
- Add **loading** (skeleton) and **error** patterns; a **wizard stepper**; standardise hero gradients.

## 9. Calculation reality audit

### Italia
Engine `apps/calculators/engines/italy.py` is **active and source-backed**. Normative source: **D.P.R. 13 gennaio 2025 n. 12 — Tabella Unica Nazionale (TUN), art. 138 CAP** (`seed_italy_legal_sources.py:75-93`, `import_italy_tun_2025.py`). Two versioned datasets: `DPR-12-2025` (base biological) and `DPR-12-2025-MORAL` (moral range), each tied to a `LegalSourceVersion` with `content_hash`; APPROVED status requires a `source_version` FK (CheckConstraint, H1-9). Four gates enforced before any number (source approved → dataset approved → formula approved → unique row match).

### Canarino
**Explainable & reproducible.** 35/10/0 → 26.268 / 27.353 / 28.439 € comes from `row_amount_range_direct`: the moral dataset rows store min/mid/max **directly** (not multiplied by disability%), with optional fault reduction (`fault=0` in canary). Locked by `test_provenance_drift_guard.py` + `verify_calculation_provenance --canary`.

### Fonti normative
Real, official, ministerial (D.P.R. n.12/2025). No hardcoded amounts in code; all coefficients come from approved datasets backed by the source version hash.

### Cosa è realistico
Permanent biological damage + moral damages by **age band + permanent-disability %**, with optional **fault reduction**. For that scenario the output is coherent and provenance-traceable.

### Cosa NON è verificato / NON coperto
- **non verificato:** whether APPROVED datasets/formulas actually exist in the staging/prod DB vs. only in test fixtures (seed creates DRAFT; promotion is a manual step outside code).
- **Non coperto:** invalidità **temporanea** (schema has `daily_amount` but the engine never reads it), **danno morale standalone** (no biological anchor), **decorrenza** (no injury-date/accrual modelling), **personalizzazione** (no income, family structure, heir count, professional loss). Formula params are not auto-versioned to the source `content_hash` (drift risk if the source changes).

### Disclaimer / cosa non calcolare / revisione
The mandatory disclaimer is present. **Must not be auto-calculated:** anything outside the modelled RCA-bodily-injury scenario (temporary disability, customization, non-IT, inheritance). **Independent legal + medico-legal review of the TUN mapping and the moral-range derivation is required before public reliance** — currently the approval is a manual Studio step, not independently attested in-repo.

## 10. Paesi non Italia

- **FR** (`fr-loi-badinter-1985`): source present but in `NOT_CALCULATION_READY_SLUGS`; **no approved CompensationDataset/formula**; engine inert. Needs dataset + formula + canary + legal review + UX availability state.
- **BE** (`be-loi-1989-11-21-rc-auto`): same; zero datasets for road_accident. (OPS-2 revalidated its disk evidence, but it is **not** calculation-ready.)
- **MA** (`ma-code-famille-moudawana-fr-pdf`): inheritance domain; no dataset/formula mapping Moudawana articles to shares.
- **TN** (`tn-code-statut-personnel-livre-ix-succession`, `tn-code-dip-loi-98-97`): approved sources but **no formula mapping** Livre IX articles to inheritance shares.
- All four: confirmed **fail-closed** (`can_calculate=False`, `is_calculation_available=False`, engines return `unavailable_requires_legal_validation`).
- **EU finding (OPS-2 confirmed):** `eu-regulation-650-2012-successions` — the `[official_sync]` block records a `.html` `local_path` that **does not exist**, while the on-disk file is `.xml`; `validate_official_legal_sources` returns `local_file_missing`; `official_sync_manifest.json` shows `fetch_failed`. **strict ALL stays exit 1.** Needs a controlled re-sync OR a surgical provenance `.html→.xml` fix + Studio confirmation that the `.xml` is the correct official file + revalidation. **Do not hand-edit the marker.**

## 11. i18n/copywriting audit

IT 58.8% (2 fuzzy), **FR 49.3% (43 fuzzy)**, **AR 49.3% (43 fuzzy)** — FR/AR are effectively maintenance-mode and **leak English/Italian onto user-facing pages**. Coverage floors (it=56/fr=48/ar=48) are far below the 85–90% production norm. **Consent texts are flagged "working copies pending legal sign-off"** — a launch blocker. No `FALLBACK_LANGUAGE`. RTL structure works but lacks an edge-case QA matrix. Tone where translated is appropriately authoritative/prudent; CTAs could be more confident. Recommend: fuzzy-clear sprint, glossary, native-AR review, raise+enforce floors, finalise consent texts.

## 12. Performance/accessibilità

CI Lighthouse-desktop passes first-try (H1-10.1 metric-zero guard prevents flakes). Only **2 CSS files**, fonts vendored + subsetted — lean. Real-UX caveats: no loading states (perceived performance during async submit), no skeletons, partial keyboard landmarks, no dark mode, RTL not perf-baselined. Accessibility fundamentals (focus, skip-link, aria-live, semantic HTML) are present but not audited cross-browser. Verdict: **technically green, UX-perceived performance untested for the interactive flows.**

## 13. Rischi prodotto (ranked)

1. **Legal-identity placeholders live** (Ordine/P.IVA/PEC `[da configurare]`) — regulatory non-compliance for an Italian avvocato site if shipped.
2. **i18n leaks** (EN/IT on FR/AR) + consent texts still draft — breaks trust and GDPR sign-off for non-IT markets.
3. **Calculation scope is narrow & not independently legal-reviewed** — risk of users over-relying on a single-scenario estimate; temporal/personalization absent.
4. **PDF report + retention/deletion + lead webhook are stubs** — the "report PDF / GDPR retention / CRM" promised flows don't fully work.
5. **EU strict-ALL finding open** (provenance `.html`/`.xml`).
6. **Provenance verifier never tested against real approved IT rows in CI** (fixture-seeded only); canary amounts hardcoded, not in an auditable config file.
7. **Non-IT readiness audit + D1–D6 read-only/PII not CI-gated by default** (silent in DEBUG=true).
8. **Wizard UX immaturity** (no stepper/loading/error states) lowers perceived premium and conversion.

## 14. Roadmap consigliata

- **P2 — Premium Design System Foundation:** tokenise + document the existing palette/typography; name components (`.btn-*`, badges, cards, provenance/unavailable cards, wizard-step, disclaimer block); add loading/error/disabled/success states; wizard stepper; refine navbar/footer.
- **P3 — Public UX Redesign:** home, countries (with availability signalling), wizard (stepper + validation UX), result, unavailable-country card, methodology, contact.
- **P4 — Calculation Trust Layer:** explanation cards, source provenance surfacing, confidence/assumptions/limitations, explicit "manual review recommended", scope-of-coverage notice.
- **P5 — Admin/Studio Review UX:** legal_sources admin polish, LegalReview intake UI, batch UI, readiness dashboard.
- **P6 — Calculation Audit & Legal Validation:** independent legal+medico-legal review of the TUN mapping; dataset/formula audit; canary expansion (temporary disability, more age/disability bands); EU drift fix; FR/BE/MA/TN activation **only after** full data + legal review.

## 15. Quick wins (low-risk, high-trust)

1. Configure `STUDIO_*` env vars → remove footer go-live placeholders. 2. Finalise + sign off consent texts. 3. Clear the 43 FR + 43 AR fuzzy entries and fix the EN/IT heading leaks on case-type pages. 4. Add an "available / coming soon" badge on `/countries/` + case-type CTAs. 5. Move the canary expected values into an auditable `docs/canaries/italy_tun_2025.json`. 6. Add a visible "coverage & limits" note to the IT result (what is/ isn't modelled).

## 16. Fasi successive consigliate

Proceed P2 → P3 (design+UX), in parallel start P6 legal validation (longest lead time). Keep FR/BE/MA/TN fail-closed until P6 clears each. Do not activate any non-IT calculation without a filed Studio go-live sign-off.

## 17. Test eseguiti

`check` (1 non-blocking issue) · `makemigrations --check` no changes · `compilemessages` OK · `check_po_coverage` it 58.8 / fr 49.3 / ar 49.3 · `verify_calculation_provenance --canary --fail-on-drift` **exit 0** · `--all-calculated` reproducible · readiness / pack-index / batch / validate_legal_review_decisions / audit_legacy_attachment_alignment **exit 0** · strict IT **0** · strict ALL **1** (EU).

## 18. QA browser

- **Porta:** 8781 · **PID:** 17680 (left running).
- **URL verificati:** home, `/countries/`, `/countries/readiness.json`, `/fr/case-types/bodily-injury/`, result IT (provenance), `/ar/case-types/bodily-injury/` (RTL), admin smoke.
- **Desktop 1440:** premium palette/typography confirmed; provenance result rich; footer placeholders visible.
- **Mobile 390:** responsive; nav cramped.
- **Console/CSP:** 0 errors everywhere.
- **HTTP:** all 200; canary 26.268 / 27.353 / 28.439 € intact; FR/BE/MA/TN `can_calculate=False`.
- **Problemi visuali:** EN/IT text leaks on FR/AR; footer go-live placeholders; no wizard stepper/loading/error states; no availability signalling; cramped mobile nav.

## 19. File modificati

None (audit-only). This report is the sole artifact. No code/dataset/calculation/marker changed. Screenshots used for QA were discarded (never committed).

## 20. Stato git finale

Baseline `c78c01b` unchanged; tree clean apart from this report doc; 0 PRs touched; canary intact; FR/BE/MA/TN fail-closed.

## 21. Conclusione onesta

This is a **credible, honest legal-tech foundation** with a **real premium visual identity** and an **unusually disciplined trust layer** — the "better no calculation than a false one" principle is genuinely enforced in code and CI. It is **not yet a finished premium product**: the calculation is narrow and pending independent legal review; PDF/retention/CRM are incomplete; FR/AR localisation and the firm's own legal identification are unfinished; and the interactive UX (wizard) lags the excellent static design. **Before declaring it publicly reliable:** finish the legal identity + consent texts, fix the i18n leaks, surface calculation scope/limits, complete an independent legal+medico-legal review of the Italian mapping, and resolve the EU finding — keeping every non-IT jurisdiction fail-closed until each clears P6.
