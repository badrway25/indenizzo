# Case-type landing FAQs — 2026-05-12

**Iter**: `PRODUCT-6-case-type-faqs`
**Branch**: `product/case-type-faqs`
**Companion of**: `docs/product/CASE_TYPE_FAQ_AUDIT_2026-05-12.md` (phase 1 audit).
**Verdict**: shipped — 4 prudent FAQs per case-type landing (32 entries total), data-driven, native `<details>/<summary>` accordion, deontologically clean.

## 1. What was added

A new FAQ section at the bottom of every `/case-types/<slug>/` landing:

> **Domande frequenti**
>
> [Q] Questa simulazione è un parere legale? — universal anchor: no, valutazione indicativa.
> [Q] 2 case-specific questions per landing (process / documents / mandate-adjacent worries).
> [Q] Inviare il modulo crea un incarico professionale? — universal mandate FAQ.
>
> *These answers are informational. They do not replace a legal opinion specific to your case.*

The section sits between the disclaimer (adjacent to the CTAs) and the useful-pages navigation. By construction it does not delay the CTA decision — users who do not click the CTA scroll into the FAQ as a soft on-ramp.

Each FAQ entry renders as `<details><summary>question</summary><p>answer</p></details>`. No JavaScript. The disclosure marker (`+` → `×` via `group-open:rotate-45`) is pure CSS.

## 2. Content discipline (deontology in copy)

The audit listed 8 hard rules. Each one is now codified in tests:

| Rule | Enforcement |
|---|---|
| **First FAQ universal — "is this a legal opinion?"** | `test_first_faq_is_universal_legal_opinion_anchor` + `test_first_faq_is_identical_across_landings` (object-identity check on the module-level constant). |
| **Every landing has a mandate FAQ ("incarico")** | `test_every_landing_has_mandate_faq`. |
| **No banned-promise phrases** | 10-phrase list scanned in `test_no_banned_promise_phrases_in_faqs`. |
| **No EUR amount** | `€` and `\bEUR\b` regex scanned in `test_no_eur_amount_in_faq_answers`. |
| **No specific prescription periods** | Regex `\b\d{1,2}\s*(anni|years|ans|mesi|mois|months|year|month|سنة|سنوات|شهر|أشهر)\b` scanned in `test_no_specific_prescription_period_in_faq_answers`. |
| **FAQ is not legal opinion** | Universal first FAQ literally says so. Closing italic note ("These answers are informational. They do not replace a legal opinion specific to your case.") on every landing reinforces it. |
| **France stays review-gated** | `test_fr_landing_renders_faq_without_eur` — FAQ block renders on `/fr/`, but the whole page is scanned for EUR and must come back empty. |
| **No invented legal doctrine** | Manual review of every Q/A. Answers stay at the level of *process* ("lo Studio verifica caso per caso", "dipende dai documenti", "lo Studio si coordina con corrispondenti locali"), never *legal advice* ("hai diritto a X"). |

## 3. case_type → FAQ entries — what is published

| Landing | 4 FAQ entries (after the universal first + before the universal mandate) |
|---|---|
| road-accident | "Devo già avere tutti i documenti per chiedere una valutazione?" / "Ho già ricevuto un'offerta dall'assicurazione: posso chiedere una verifica?" |
| bodily-injury | "Quali documenti aiutano la valutazione del danno biologico?" / "Se il percorso medico-legale è ancora in corso, posso comunque chiedere una valutazione?" |
| insurance-offer-review | "Posso firmare l'offerta prima della verifica legale?" / "La revisione dell'offerta equivale ad accettarla?" |
| work-injury | "Se l'assicurazione obbligatoria (es. INAIL) copre già l'infortunio, ha senso una valutazione?" / "Quali documenti aiutano la valutazione di un infortunio sul lavoro?" |
| medical-malpractice | "Serve già una perizia medico-legale indipendente per chiedere la valutazione?" / "Una perizia indipendente è sempre obbligatoria?" |
| death-of-relative | "Quali familiari possono chiedere la valutazione?" / "Posso chiedere una verifica se è già in corso una trattativa con l'assicurazione?" |
| foreigners-in-italy | "In quale lingua posso comunicare con lo Studio?" / "Devo necessariamente avviare la causa in Italia?" |
| cross-border-cases | "Come si stabilisce quale legge si applica al caso?" / "Lo Studio collabora con avvocati locali nei paesi coinvolti?" |

Every landing ends up with 4 entries: 1 universal anchor + 2 case-specific + 1 universal mandate. The 4-entry cap is enforced by a module-level `assert` invariant at import time.

## 4. Impact expected

- **Pre-engagement clarity**: the four worries the Studio receives on almost every contact email are now resolved before the user opens the form — "is this a paid consultation?", "do I need all the documents first?", "what if I already have an offer?", "does sending the form bind me?".
- **SEO long-tail capture**: each landing now publishes 4 question-shaped HTML strings that match real query patterns ("incidente stradale offerta assicurazione verifica", "responsabilità medica serve perizia", "successione marocco quale legge"). The questions are crawlable text inside `<summary>` — collapsed `<details>` content is indexed.
- **Lower CTA-skip bounce**: users who are not yet ready to click the primary CTA scroll into the FAQ instead of leaving. The FAQ resolves the last doubt and either nudges back to the CTA or sends the user to the useful-pages nav.
- **Operational ergonomics**: future copy edits are a one-place change. Add a 5th FAQ for `road-accident`? Append one `FAQItem(...)` to `landing.faq_items` (up to the 4-entry cap — bump `MAX_FAQ_ITEMS` if needed). No template change.

Primary CTA, secondary CTA, mandate notice, disclaimer, document partial and useful-pages nav are **unchanged**. The new section is purely additive.

## 5. Files modified / created

| File | Change |
|---|---|
| `apps/core/case_type_landings.py` | Added `FAQItem` frozen dataclass + `MAX_FAQ_ITEMS = 4` constant + `_FAQ_LEGAL_OPINION` / `_FAQ_MANDATE` module-level constants + `faq_items: Sequence[FAQItem]` field on `CaseTypeLanding` + 4 FAQ entries per landing (all 8 landings) + module-level invariant asserting the 4-entry cap. |
| `templates/public/case_type_landing.html` | New `{% if landing.faq_items %}` section between the disclaimer and the useful-pages nav. Native `<details>/<summary>`, no JS. ~22 LOC. |
| `apps/core/test_product_6_case_type_faqs.py` *(new)* | 24 tests: audit doc + module primitives + 3..4 FAQs per landing + universal first FAQ (substring + object identity) + mandate FAQ + banned phrases + EUR + prescription numbers + rendered `<details>/<summary>` for all 8 slugs + FR locale renders without EUR + AR/RTL renders + no `noindex` regression + module invariant. |
| `scripts/capture_product_6_case_type_faqs.py` *(new)* | Playwright harness: 4 IT landings + 1 AR/RTL landing at desktop + mobile. Opens every `<details>` before screenshotting so the FAQ block is fully visible. |
| `docs/product/CASE_TYPE_FAQ_AUDIT_2026-05-12.md` *(new)* | Phase 1 audit. |
| `docs/product/CASE_TYPE_FAQ_IMPROVEMENTS_2026-05-12.md` *(new)* | This file. |
| `docs/screenshots/.../after/product-case-type-faqs/` *(new)* | 10 PNGs documenting the FAQ section at desktop + mobile, IT × 4 + AR × 1. |

No model migration. No new form. No France activation. No CRM / webhook / email change. No banned-phrase introduction. No new template — extension of the existing single landing template.

## 6. Deontological / GDPR / SEO — what stays clean

| Risk | How addressed |
|---|---|
| Promise of result | None. Every answer stays at the level of "lo Studio verifica caso per caso" / "la valutazione è indicativa". Banned-phrase test pin: 10 phrases scanned across every FAQ Q+A, zero leaks. |
| EUR amount in FAQ | None. Test pin: `€` and `\bEUR\b` scanned across every FAQ Q+A, zero matches. Test pin: whole `/fr/` landing page scanned for EUR after the change, zero matches. |
| Invented prescription period | None. Test pin: regex `\b\d{1,2}\s*(anni|years|ans|mesi|mois|months|year|month|سنة|سنوات|شهر|أشهر)\b` scanned across every FAQ Q+A, zero matches. We deliberately do not publish "2 anni / 5 years / etc." anywhere in the FAQ. |
| Automated legal advice | None. First FAQ on every landing explicitly says: "No. La simulazione è una valutazione indicativa... Non sostituisce un parere legale". Closing italic note on every landing repeats the principle. |
| Mandate / engagement confusion | Addressed. Every landing carries the mandate FAQ ("Inviare il modulo crea un incarico professionale?" → no, separate written agreement). Test pin on substring "incarico" being present in every landing's FAQ block. |
| France activation | None. The FAQ block renders on `/fr/case-types/<slug>/` but its copy avoids any French calculation reference, and the whole-page EUR scan on FR comes back empty. |
| Crawlability regression | None. Test pin: `noindex` is not present on any of the 4 most legally-sensitive landings post-change. Landings stay `index, follow`. |
| AR / RTL regression | None. Test pin: `/ar/case-types/road-accident/` returns 200 with `dir="rtl"`, FAQ section present, `<details>/<summary>` rendered. Native browser flips the marker side without CSS hacks. |
| Schema.org FAQPage over-claim | Avoided deliberately — see audit §7. JSON-LD is a follow-up once the copy stabilises. |

## 7. Tests

| Suite | Before | After |
|---|---|---|
| Full `pytest -q` | 2090 passed, 1 skipped (PRODUCT-5 baseline) | **2114 passed, 1 skipped** (+24 new PRODUCT-6) |
| `apps/core/test_product_6_case_type_faqs.py` | n/a | 24/24 passed |
| `python manage.py check` | clean (only W001 STUDIO_* dev) | unchanged |
| `python scripts/legal_data/audit_non_it_readiness.py` | APPROVED-PARTIAL × 4 | APPROVED-PARTIAL × 4 (unchanged — no FR/BE/MA/TN activation) |
| `python scripts/audit_legal_content_hygiene.py --strict` | no findings | no findings |

## 8. Screenshots

`docs/screenshots/delta_audit_2026-05-10/after/product-case-type-faqs/` contains 10 PNGs:

- `road-accident-it-desktop-1280.png` + `road-accident-it-mobile-390.png`
- `insurance-offer-review-it-desktop-1280.png` + `insurance-offer-review-it-mobile-390.png`
- `medical-malpractice-it-desktop-1280.png` + `medical-malpractice-it-mobile-390.png`
- `death-of-relative-it-desktop-1280.png` + `death-of-relative-it-mobile-390.png`
- `road-accident-ar-rtl-desktop-1280.png` + `road-accident-ar-rtl-mobile-390.png`

Every screenshot opens all four `<details>` so the FAQ block is fully visible. Visual check confirmed:

- The "Domande frequenti" card sits between the disclaimer and the useful-pages nav — exactly where the audit said it should.
- Each `<details>` is a calm card row (stone2-200 border, sand-50/40 collapsed bg, white when open).
- The marker (`+` rotated 45° to `×`) flips correctly without flickering on click.
- AR/RTL renders cleanly: marker switches to the right side, question text aligns RTL, answer paragraph aligns RTL with the same `ps-7` start-padding (logical property, not `pl-7`).
- The closing italic note ("These answers are informational. They do not replace a legal opinion specific to your case.") is present and readable on every screenshot.

## 9. Residual risks

| Risk | Severity | Mitigation |
|---|---|---|
| Translation team picks up new FAQ strings late — English fallback on /fr/ /ar/ for one release cycle | low | Same risk profile as PRODUCT-4 and PRODUCT-5. Landings are not on the primary funnel. Documented as residual. |
| Schema.org `FAQPage` JSON-LD not yet added | low | Documented in the audit (§7) as a deferred follow-up. Plain HTML FAQ is already crawler-friendly; JSON-LD is a separate iter once copy has stabilised. |
| 4 open `<details>` on mobile may push the useful-pages nav far below the fold | low | The cards start *closed*; expanding is a deliberate user action. Mobile screenshots (with all 4 open) confirm the layout still flows naturally. |
| A maintainer adds a 5th FAQ and breaks the cap | low | Module-level `assert` invariant raises at import time. Test `test_max_faq_items_invariant_holds` explicitly pins the contract. |
| FAQ answer drifts toward advice over time | medium | Two safety nets: (1) banned-phrase scan in tests, (2) prescription-period regex in tests. If a future edit publishes "2 anni" or "garantiamo il risultato", the test fails before the change can land. |
| Studio wants to add FAQ for an emerging case type (e.g. condominium liability) | low — easy follow-up | One `FAQItem(...)` append to the relevant landing's `faq_items` tuple. No template / view / migration change. |

## 10. Next improvements

In order of value:

1. **Sessione Studio Francia** — still the highest-value pending item carried over from PRODUCT-1 / STUDIO-1. PRODUCT-6 makes the FR landings richer in informational content while the calculation activation remains gated.
2. **PRODUCT-7 — `FAQPage` JSON-LD on the case-type landings** — small follow-up once the FAQ copy is observed in the wild for a release cycle. JSON-LD is added to the head as a `{% block extra_head %}` snippet, scoped only to landings that have `faq_items`. Three weeks of real query data first.
3. **PRODUCT-8 — Studio review pass on the 4 most legally-sensitive FAQ sets** (medical-malpractice, death-of-relative, insurance-offer-review, work-injury) — one-line edits to the data module after Studio sign-off; no template or test changes needed.

## 11. Rollback

A single `git revert` of the PRODUCT-6 commit:

- removes the `FAQItem` dataclass + `MAX_FAQ_ITEMS` + universal FAQ constants + `faq_items` field + module-level invariant from `case_type_landings.py`;
- removes the FAQ section from `case_type_landing.html`;
- removes the new test file + capture script + this report + the audit;
- removes the 10 PNGs.

No DB rollback needed. No new dependency. The pre-PRODUCT-6 landing page returns identical bytes after revert.
