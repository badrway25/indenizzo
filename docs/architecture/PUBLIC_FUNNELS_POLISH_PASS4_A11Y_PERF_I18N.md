# Public funnels — pass 4 (a11y / perf / i18n)

Iter: F-product-public-funnels-polish-pass4-a11y-perf-i18n.
Date: 2026-05-04.
Scope: residual i18n fallbacks on FR/AR funnels, low-cost a11y/perf
improvements on the new pass-3 cards. **No** changes to legal data,
calculators, engines or jurisdiction status.

## 1. i18n fallbacks found

`scripts/audit_visible_translation_fallbacks.py` walks the FR and AR
public funnels and scans rendered HTML for high-priority English
phrases that should already be translated. First run flagged:

| Page                         | Fallback                                                                                              | Diagnosis |
| ---                          | ---                                                                                                   | --- |
| `/fr/contact/`, `/ar/contact/` | "What happens next"                                                                                 | msgid present in `.po`, msgstr **EMPTY** in both fr/ar. |
| `/fr/contact/`, `/ar/contact/` | "A lawyer of the Studio reads your message manually …"                                              | EMPTY msgstr. |
| `/fr/contact/`, `/ar/contact/` | "You receive a written reply at the email you provide. Average response: 3–5 working days."        | EMPTY msgstr. |
| `/fr/contact/`, `/ar/contact/` | "If your case fits our scope, the Studio proposes the next step …"                                  | EMPTY msgstr. |
| `/fr/wizard/it/road-accident/`, `/ar/wizard/it/road-accident/` | "Download the PDF of your simulation and ask the Studio for a manual legal review …" | msgstr present but **wrong** (msgmerge fuzzy contamination — translated text was actually that of "Sending this form does not create a professional engagement"). |
| `/fr/wizard/`, `/ar/wizard/`  | "If validated legal sources are available (today: Italy, road accident) …"                          | EMPTY msgstr (multi-line, embedded escaped quotes). |

Plus one false positive in the audit list itself: `min / mid / max`
column labels are universal and intentionally kept verbatim across
languages. The audit phrase was tightened to require surrounding
English context (`"an indicative min / mid / max range"`) to avoid
flagging the legitimate FR rendering.

## 2. i18n fallbacks resolved

A throw-away force-replace script (`_apply_pass4_translations.py`,
deleted after run) rewrote the six msgstr values for both `locale/fr`
and `locale/ar`, stripped any `#| msgid` / `#, fuzzy` hints from the
rewritten blocks, and the catalogues were re-compiled with
`python manage.py compilemessages -l fr -l ar -l it`.

After the fix the audit passes (verdict `OK`). The 11-test pass-4
suite verifies the user-visible AR/FR strings render and that EN
fallbacks no longer leak in visible body text.

Translations applied (one row per msgid; FR / AR):

| msgid | FR | AR |
| --- | --- | --- |
| What happens next | Ce qui se passe ensuite | ما الذي يحدث بعد ذلك |
| A lawyer of the Studio reads your message manually … | Un avocat du Studio lit votre message manuellement … | يقرأ محامٍ من المكتب رسالتك يدوياً … |
| You receive a written reply … 3–5 working days. | Vous recevez une réponse écrite … 3 à 5 jours ouvrés. | ستتلقى رداً مكتوباً … 3 إلى 5 أيام عمل. |
| If your case fits our scope, the Studio proposes the next step … | Si votre dossier entre dans notre champ d’intervention … | إذا كان ملفك ضمن نطاق عملنا … |
| Download the PDF of your simulation and ask the Studio for a manual legal review. | Téléchargez le PDF de votre simulation et demandez au Studio une revue juridique manuelle. | نزّل ملف PDF الخاص بمحاكاتك واطلب من المكتب مراجعة قانونية يدوية. |
| If validated legal sources are available (today: Italy, road accident) … | Si des sources juridiques validées sont disponibles … | إذا توفّرت مصادر قانونية موثّقة … |

## 3. a11y fixes

Baseline (already in place, verified):

- One `<h1>` per public funnel page; heading order never skips a level
  (verified by `test_funnel_page_has_exactly_one_h1`).
- Global `:focus-visible` ring (`outline: 2px solid #b88336;
  outline-offset: 3px`) applies to `a / button / input / select /
  textarea / [role="button"] / summary` via `templates/base.html`.
- `prefers-reduced-motion` is honoured via `@media` block in
  `base.html`.
- "Skip to content" link is the first focusable element.
- The hero partial (`_premium_hero_image.html`) ships proper width /
  height / `loading="lazy"` / `decoding="async"` / non-empty `alt`.

Pass-4 changes (small, scoped):

- `templates/public/contact.html` — bumped the "Useful pages" nav
  buttons from `px-4 py-2` to `px-4 py-2.5 min-h-10` so each touch
  target is ≥ 40 px tall on mobile (WCAG 2.5.5 AAA / 2.5.8 AA).
- `templates/public/contact_thank_you.html` — added
  `target="_blank" rel="noopener noreferrer"` and an `aria-label="Visit
  institutional website (opens in a new tab)"` to the institutional-
  website CTA, since it points at an external domain.
- `templates/public/wizard_result.html` — added a per-source
  `aria-label="Open official source: <title> (opens in a new tab)"` to
  each "Open official source ↗" link, and wrapped the trailing arrow
  in `<span aria-hidden="true">` so screen readers no longer announce
  it as text.

## 4. perf notes

- LCP image on the home hero already uses
  `loading="eager" fetchpriority="high"`. Secondary pages use
  `loading="lazy"` for the editorial banner — appropriate, since
  it's not the LCP element.
- All hero `<img>` elements carry `width` / `height` so layout shift
  is avoided.
- No runtime Pexels fetch — the image partial reads a server-side
  context dict and renders a static `<img>`. Verified by
  `test_fr_ar_funnels_have_no_pexels_attribution`.
- No additional JavaScript was introduced by pass-4. Result page CTAs
  remain plain `<a>` links; the PDF link is a regular hyperlink so
  rendering is not blocked.
- Cookie-consent banner JS is non-blocking (deferred at the bottom of
  the document).

## 5. screenshots (live)

Captured via
`scripts/capture_public_funnels_polish_pass4_screenshots.py` against
`http://127.0.0.1:48107/`. Output:
`docs/screenshots/live_qa/public_funnels_polish_pass4/` (9 PNGs).

| File | Page | Locale |
| --- | --- | --- |
| 01_wizard_start_en.png | `/wizard/` | en (default) |
| 02_wizard_start_fr.png | `/fr/wizard/` | fr |
| 03_wizard_start_ar.png | `/ar/wizard/` | ar (RTL) |
| 04_wizard_italy_form_en.png | `/wizard/it/road-accident/` | en |
| 05_wizard_france_form_fr.png | `/fr/wizard/fr/road-accident/` | fr |
| 06_wizard_morocco_form_ar.png | `/ar/wizard/ma/inheritance/` | ar (RTL) |
| 07_contact_en.png | `/contact/` | en |
| 08_contact_fr.png | `/fr/contact/` | fr |
| 09_contact_ar.png | `/ar/contact/` | ar (RTL) |

## 6. what stays out of scope (residual)

- Color-contrast tightening of `text-stone2-500` (#7a786f) on
  `bg-sand-100` (#f3ece0): contrast is ≈ 3.8 : 1 — passes WCAG AA for
  large text, just under for small text. Used only for *tertiary*
  meta lines (status code, simulation ID labels). A palette-level
  decision, deferred.
- A full Lighthouse mobile run is best done in CI on a representative
  network profile; out of scope for an iter focused on i18n + a11y
  copy fixes.
- "Pexels integration" (the wiring of a real Pexels API call to the
  hero partial) remains the proposal it was at the close of pass-3.
  Pass-4 does not change pexels behaviour.

## 7. validation

- `python manage.py makemigrations --check` — no new migrations.
- `python manage.py check` — no system errors.
- `python manage.py compilemessages -l fr -l ar -l it` — three .mo
  files regenerated.
- `pytest -q` — full suite green.
- `ruff check .` — clean.
- `black --check .` — clean.

## 8. summary

| Verdict | Detail |
| --- | --- |
| FR/AR i18n | Audit OK — six EN fallbacks closed (4 EMPTY + 1 fuzzy + 1 multi-line). |
| a11y | Touch targets ≥ 40 px on the new "Useful pages" nav; external links flagged with `target="_blank" + aria-label`; screen-reader announcement of trailing arrows suppressed. |
| Italia | 35/10/0 → 26 268 / 27 353 / 28 439 EUR — unchanged (smoke test passing). |
| Other countries | FR/BE/MA/TN remain "no automatic estimate" / "no automatic shares". |
| Server | Live on `127.0.0.1:48107`. |
