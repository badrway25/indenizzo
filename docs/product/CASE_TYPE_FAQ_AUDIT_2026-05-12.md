# Case-type landing FAQ — audit (phase 1) — 2026-05-12

**Iter**: `PRODUCT-6-case-type-faqs`
**Branch**: `product/case-type-faqs`
**Companion of**: `docs/product/CASE_TYPE_FAQ_IMPROVEMENTS_2026-05-12.md` (phase 6 report — written after implementation).
**Predecessors**: PRODUCT-4 (case-type landings — `docs/product/CASE_TYPE_LANDING_IMPROVEMENTS_2026-05-12.md`), PRODUCT-5 (result-page recommended next pages — `docs/product/RESULT_PAGE_NEXT_STEPS_IMPROVEMENTS_2026-05-12.md`).

## 1. Why FAQs on the case-type landings

PRODUCT-4 shipped 8 case-type landings under `/case-types/<slug>/`. Each one carries an intro, a "when this applies" list, the "documents to prepare" partial, a "what the Studio does" list, a mandate notice, two CTAs and a disclaimer. They are calm, informational and convert reasonably well.

Three signals say the landings can do more without changing their nature:

1. **The same questions come up on every contact form.** The Studio receives the same handful of pre-engagement worries on almost every initial contact — "is this a paid consultation?", "does sending the form bind me?", "do I need all the documents first?", "is the figure I see online a quote?". Surfacing the answers on the landing itself reduces friction for cautious users and arrives at the Studio with the right mental model.
2. **SEO long-tail value.** Real users search the question, not the case type. "responsabilità medica perizia quanto costa", "incidente stradale offerta assicurazione cosa fare", "successione internazionale marocco" — query-shape patterns that match an FAQ Q/A pair far better than a noun-style H1.
3. **No new page surface area.** The FAQs ride on existing landings, reuse the existing single template, and use the existing i18n + screenshot pipelines. No new URL, no new sitemap entry, no new translation context to onboard.

## 2. What we will NOT do

These are hard guardrails carried over from PRODUCT-1 through PRODUCT-5 and from the legal-content hygiene audit. Each one is a binding constraint on the FAQ copy:

| Hard rule | Operational consequence |
|---|---|
| **No invented legal doctrine.** | Every Q/A stays at the level of *process and informational orientation*, never *legal opinion*. No "you are entitled to X", no "the law says Y". |
| **No specific statutes-of-limitation numbers without a validated source.** | The most legally sensitive area for an FAQ. We will reference *that prescription periods exist and depend on the case* but **never** publish a number ("2 years", "5 years", "10 years") because the underlying validated sources are not signed off for FR / BE / MA / TN. For IT we still defer — the user's instruction was explicit: "non indicare termini di prescrizione specifici se non già firmati / fonte-validati". |
| **No promise of result.** | Banned-phrase list scanned against every FAQ string: `scopri quanto ti spetta`, `ottieni il risarcimento`, `calcolo definitivo`, `paghi solo se vinci`, `pay only if you win`, `no win no fee`, `risarcimento garantito`, `garantiamo il risultato`, `i migliori avvocati`, `leader assoluto`. |
| **No guaranteed amount.** | No EUR sign, no €, no "EUR" string anywhere in the FAQ block on any landing. Tested with a regex pin. |
| **No "you are definitely entitled to X".** | The Italian copy uses "potresti avere diritto", "in linea di massima", "lo Studio verifica caso per caso" — never "hai diritto". |
| **FAQ is not legal opinion.** | First FAQ on every landing is explicitly **"This is not a legal opinion"** — the same disclaimer that exists on the wizard result, restated in question form. Sets the frame for the rest of the block. |
| **Mandate notice / no automatic engagement.** | At least one FAQ on every landing covers: "sending this form does not create a professional engagement; an engagement requires a separate written agreement". |
| **France stays review-gated.** | The FAQ block renders on `/fr/case-types/<slug>/`, but the answers do not invent French calculation references. The "what would the result look like" answer redirects to the review-only contact form, consistent with the FR result-page gate. |
| **No CRM / no email / no DB migration.** | This iter does not touch any flow that exits the page. FAQ is pure read-only content. |

## 3. Scope — which landings get FAQs

All 8 PRODUCT-4 landings:

| # | Slug | H1 (Italian) | Why it needs an FAQ |
|---|---|---|---|
| 1 | `road-accident` | Incidente stradale — danno fisico | Highest-traffic landing in tests; users arrive with a concrete offer in hand and want process clarity. |
| 2 | `bodily-injury` | Lesioni personali e danno biologico | Often arrived at via search; users want to know whether the ITT/ITP framework applies to their case. |
| 3 | `insurance-offer-review` | Revisione dell'offerta assicurativa | Highest-stakes single FAQ ("should I sign?"); answer: NEVER sign before legal review. |
| 4 | `work-injury` | Infortunio sul lavoro | INAIL / civil-liability interaction creates structural confusion. FAQ clarifies. |
| 5 | `medical-malpractice` | Responsabilità medica | Most legally complex; FAQ must emphasise medico-legal expert step. |
| 6 | `death-of-relative` | Morte di un congiunto | Emotionally sensitive; FAQ must stay sober, not procedural-friendly. |
| 7 | `foreigners-in-italy` | Cittadini stranieri infortunati in Italia | Cross-language anxiety dominant; FAQ covers multilingual handling + jurisdiction. |
| 8 | `cross-border-cases` | Casi transfrontalieri | High triage value; FAQ covers conflict-of-laws as *a step we do*, not as advice. |

## 4. FAQ shape and count

- **Up to 4 FAQs per landing.** Hard cap. More than 4 makes the page sprawl on mobile and pushes the disclaimer below the fold.
- **At least 3 FAQs per landing.** Below 3 the section reads as a token addition. Audit tests pin the floor at 3.
- **First FAQ on every landing is identical**: "Is this simulation a legal opinion?" — answers no, anchors the rest of the block.
- **At least one FAQ on every landing covers the mandate / engagement step** — restating the mandate notice in question form.

Each FAQ entry is a `(question, answer)` pair of `gettext_lazy` strings, stored on the dataclass `CaseTypeLanding.faq_items`. The template iterates and renders one `<details>` per item.

## 5. Rendering — accordion via native HTML, no JS

The implementation uses `<details>/<summary>` because:

- **Zero JS.** Aligns with the rest of the public site (which has no fragile accordion JS yet). Removes a whole category of regression: keyboard focus order, ESC handling, ARIA expanded sync.
- **Crawler-friendly.** Search engines parse the closed `<details>` content; the questions and answers are in the rendered HTML even when collapsed. We deliberately do not gate the answers behind JS.
- **AR/RTL safe.** `<details>/<summary>` respects `dir="rtl"` natively — the marker switches sides without any CSS hack.
- **a11y default.** `<summary>` is focusable, toggled with `Enter`/`Space`, and announced as a disclosure widget by screen readers.

The section heading is a clear `<h2>` ("Domande frequenti" / "Frequently asked questions") so it shows up in the document outline.

## 6. Where the FAQ block sits on the page

Decision tree from PRODUCT-4 layout:

```
hero image
H1 + intro
"When this applies" card
"Documents to prepare" partial
"What the Studio does" card
Mandate notice
Primary + secondary CTAs               ← the moment of decision
Disclaimer
FAQ section                            ← NEW — for users not ready to act
"Useful pages" navigation
```

The FAQs sit *after* the CTAs and disclaimer because:

- The primary CTA is the moment of decision; we do not want to delay it with 4 collapsible blocks.
- Users who *do not* press the CTA scroll further. The FAQ is the soft on-ramp for them: it lets them resolve their last doubt and either come back to the CTA or move on.
- This mirrors how PRODUCT-5 placed the "recommended landings" *after* the mandate but *before* the CTA on the wizard result page — same family of decisions, applied to a different layout slot.

## 7. SEO — FAQPage schema.org

The structured data is the obvious win on this iter. However:

- **Schema.org `FAQPage` requires the answer not to be ambiguous about facts** ([Google guidance](https://developers.google.com/search/docs/appearance/structured-data/faqpage)). Our answers are deliberately conservative ("dipende dai documenti", "lo Studio verifica caso per caso"). They are factually accurate but they may not match Google's intent for the FAQ rich result.
- **Risk of misrepresentation.** A rich-result snippet that says "Studio Badrane — è obbligatoria una perizia? — Dipende dai documenti." stripped of context could be read as evasive. Better to ship the FAQ content first, see how it lands on real queries, then decide whether to add `FAQPage` JSON-LD in a follow-up.

Decision: **defer schema.org `FAQPage` to a follow-up iter** (PRODUCT-7 or later). The FAQ block is shipped as plain HTML, which is already crawler-friendly. The follow-up can add JSON-LD once the copy has stabilised.

## 8. Acceptance criteria (gate phase 6)

The iter is acceptable to merge when ALL of the following are true:

1. **Data**: All 8 landings have `faq_items` set, each with 3-4 entries. The cap of 4 is enforced by an assertion at module import (defensive — catches future drift).
2. **Template**: `templates/public/case_type_landing.html` renders the FAQ section between the disclaimer and the useful-pages nav, using `<details>/<summary>`, with a clear `<h2>` heading.
3. **Mandate FAQ**: Every landing's `faq_items` contains at least one entry whose answer mentions the mandate / no-automatic-engagement principle (substring match: "incarico" or the locale equivalent).
4. **First FAQ universal**: First FAQ on every landing is the "is this a legal opinion?" question, with a "no, this is an indicative orientation" answer. Tested by string match.
5. **No EUR**: No `€` symbol, no `EUR` token, no euro-amount regex match in any rendered FAQ answer on any landing. Tested.
6. **No banned phrases**: All 10 banned phrases scanned against every FAQ string for every landing in every locale (IT / FR / AR). Zero leaks.
7. **No specific prescription numbers**: Tests scan for the regex `\b(\d{1,2})\s*(anni|years|ans|سنة|سنوات)\b` in FAQ answers — zero matches expected.
8. **Accessibility**: Every FAQ renders as `<details><summary>question</summary>answer</details>`. No `<button>` with broken `aria-expanded`. Test pins the tag.
9. **AR/RTL**: `/ar/case-types/road-accident/` returns 200, contains `dir="rtl"`, and the FAQ section is present. Test pins.
10. **No noindex regression**: Landings remain crawlable. Test pins absence of `noindex` meta.
11. **Hygiene strict green**: `scripts/audit_legal_content_hygiene.py --strict` returns zero findings post-change.
12. **No France activation**: FR locale renders the FAQ but the answers continue to redirect to the review-only flow where calculation references would otherwise be needed. No EUR figure appears on the FR landing.

## 9. Risks and mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| FAQ copy turns into legal advice through inattention | high | Universal first FAQ ("not a legal opinion") + banned-phrase scan + manual review of every Q/A in the diff. |
| Specific prescription period sneaks into an answer (e.g. "il termine è di 2 anni") | high | Regex pin in tests scans for digit-followed-by-time-unit patterns. Refuses to land if any answer matches. |
| FAQ section pushes the disclaimer below the mobile fold | medium | Section sits *after* the disclaimer in the document order. Cap of 4 entries keeps the block compact even when fully expanded. |
| `<details>` markers conflict visually with the gold-accent design tokens | low | Reuse the existing card border / shadow tokens (stone2-200 / shadow-card / rounded-3xl). One `<details>` per row, no exotic styling. |
| AR/RTL marker on `<summary>` flips wrong | low | Native browser behaviour respects `dir="rtl"`. AR/RTL screenshot in the capture set verifies. |
| Translation team picks up new strings late, English fallback shows on /fr/ /ar/ for a release cycle | low | Same risk as PRODUCT-4 and PRODUCT-5; landings are public but not on the primary funnel path. Acceptable, documented as residual in the report. |
| Schema.org `FAQPage` is asked for during review | low | Documented above as a deferred follow-up with rationale. |

## 10. Implementation plan (phases 2-6)

1. **Phase 2** — Data: extend `CaseTypeLanding` with a `faq_items` field (tuple of `FAQItem(question, answer)` frozen dataclasses); populate 3-4 FAQs per landing; add a module-level invariant (`assert len(landing.faq_items) <= 4`); the existing helper functions and the `_RECOMMENDATIONS_BY_CASE_TYPE` mapping are unchanged.
2. **Phase 3** — Template: append a `{% if landing.faq_items %}...{% endif %}` block at the bottom of `case_type_landing.html`, between the disclaimer and the useful-pages nav, rendering one `<details>` per item.
3. **Phase 4** — Tests: new file `apps/core/test_product_6_case_type_faqs.py` with the 10+ pins enumerated in §8. Reuse the `translation.deactivate_all()` pattern from PRODUCT-3+ to isolate AR/RTL tests.
4. **Phase 5** — Screenshots: new `scripts/capture_product_6_case_type_faqs.py`. Capture 8 PNGs: road-accident IT + AR desktop+mobile, insurance-offer-review IT desktop+mobile, medical-malpractice IT desktop+mobile, death-of-relative IT desktop+mobile.
5. **Phase 6** — Improvements report: `docs/product/CASE_TYPE_FAQ_IMPROVEMENTS_2026-05-12.md` (same shape as the PRODUCT-5 report).
6. **Commit**: `product-6: add prudent faqs to case type landings`. Single commit, no push.

## 11. Rollback

A single `git revert` of the PRODUCT-6 commit removes: the `faq_items` field + module-level invariant; the template FAQ section; the new test file; the capture script; this audit; the improvements report; the 8 PNGs. No DB rollback needed — pure Python data + template change. No migration. No new dependency.
