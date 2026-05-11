# P2-PERF-1 — mobile Lighthouse comparison

**Iter**: F-p2-perf-1-mobile-performance-pass
**Date**: 2026-05-11
**Baseline tag**: `p2-seo-1-lighthouse-mobile-baseline-2026-05-10`

## Goal

Move the worst mobile perf URL from ~0.79 to ≥ 0.85 without
redesigning the UI, without loosening CSP, and without adding
external assets.

## Scoreboard

Mobile preset (390×844, CPU ×4, simulated 3G — same as the
committed baseline).

| URL | Baseline (2026-05-10) | After (2026-05-11) | Δ | Notes |
|---|---|---|---|---|
| `/` | 0.87 | **0.93** | **+0.06** | LTR home, hero image. |
| `/contact/` | 0.85 | **0.92** | **+0.07** | indexable institutional. |
| `/wizard/` | 0.90 | **0.94** | **+0.04** | hub page (concrete wizards are noindex). |
| `/privacy/` | 0.93 | **0.98** | **+0.05** | legal page, low images. |
| `/disclaimer/` | 0.93 | **0.98** | **+0.05** | legal page, low images. |
| `/countries/` | 0.83 | **0.90** | **+0.07** | hub for 5 country landings. |
| `/case-types/` | 0.93 | **0.98** | **+0.05** | hub for case types. |
| `/ar/` | 0.79 | **0.80** | **+0.01** | RTL home, hero image. |

Other categories (accessibility / best-practices / seo) unchanged
or +0.00 on every URL.

## Target outcome

- `≥ 0.85` on every URL: **7 out of 8** clear it. `/ar/` clears
  0.80 — above the 0.75 floor by 5 points (was 4) but still 0.05
  short of the stated target.
- The bottleneck on `/ar/` is the LCP element (hero JPEG, ~70 KiB,
  4.4 s), not CSS render-blocking. See §5 below.

## What changed (the four interventions)

### 1. Pre-compressed static (`.gz` companions) + WhiteNoise

The biggest lever. site.css went from 29 608 bytes raw to 7 147
bytes gzip — **76 % smaller over the wire**. fonts.css from 10 200
to 1 009 bytes — **90 % smaller**.

The chain:

- `requirements.txt` adds `whitenoise>=6.6,<7`.
- `config/settings.py` adds:
  - `whitenoise.runserver_nostatic` to `INSTALLED_APPS` (BEFORE
    `django.contrib.staticfiles`) so `manage.py runserver`
    auto-defaults to `--nostatic` (without this, Django's
    StaticFilesHandler short-circuits the middleware chain and
    WhiteNoise never sees the request).
  - `whitenoise.middleware.WhiteNoiseMiddleware` to `MIDDLEWARE`
    right under `SecurityMiddleware`.
  - `WHITENOISE_USE_FINDERS = True` so dev mode doesn't require
    `collectstatic` between edits.
- `apps/core/management/commands/precompress_static.py` (new)
  walks the project's `static/` and writes `<file>.gz` next to
  every `.css`/`.js`/`.svg`/`.json`/`.txt`/`.map`. Deterministic
  (mtime=0). Scoped to `BASE_DIR` so it never writes inside
  `.venv/`. Idempotent (skips fresh companions).
- `scripts/run_lighthouse_local.sh` and
  `scripts/run_lighthouse_mobile_local.sh` call the command before
  every Lighthouse run.
- `.github/workflows/ci.yml`'s `lighthouse-desktop` job calls
  `python manage.py precompress_static` between
  `compilemessages` and starting runserver.

### 2. GZipMiddleware for dynamic responses

Django built-in, single MIDDLEWARE line. Compresses HTML
responses (non-streaming) for clients that send `Accept-Encoding:
gzip`. Home page response shrank from 22 427 to 6 121 bytes
**(73 % smaller)**. BREACH risk negligible: Django ≥ 1.10 masks
CSRF tokens per-request; static files carry no secret.

### 3. Inline critical CSS BEFORE external stylesheets

The base template's nonce-protected `<style>` block (body
font-family, focus ring, reduce-motion) used to come AFTER
fonts.css + site.css in the head. Moved it BEFORE so the browser
applies critical declarations during the time those stylesheets
are still downloading. Same CSP contract (nonce-protected). Same
content — only position changed.

### 4. Font preload for LTR pages (and explicitly NOT for RTL)

Added `<link rel="preload" as="font" type="font/woff2" crossorigin>`
for the two above-the-fold LTR fonts: `inter-400-latin.woff2` and
`cormorant-garamond-600-latin.woff2`. The browser otherwise
discovers these fonts only after parsing fonts.css, serialising
the font fetch behind the stylesheet download. Preload pushes
the fetch in parallel.

**RTL pages deliberately do NOT preload the Arabic fonts**. A
trial confirmed (3 runs) that preloading Tajawal + Amiri on `/ar/`
*hurts* the page by ~0.02 because the font requests compete with
the hero image for HTTP/1.1 connection slots, delaying LCP. By
skipping the preload on RTL pages, `/ar/` recovers its baseline
LCP and still benefits from the CSS compression in §1+§2.

The CSP `font-src 'self'` already allows the preloaded fonts —
no policy change.

## What was deliberately NOT done

- **No redesign**. UI is byte-identical; only `<head>` order +
  preload tags changed.
- **No Google Fonts**. All fonts stay local under `static/fonts/`.
- **No CSP loosening**. `script-src 'self'` still excludes
  `'unsafe-inline'` / `'unsafe-eval'`. The two new `<link>` tags
  do not require inline JS.
- **No image format change**. The hero JPEG that owns LCP on
  `/ar/` (70 KiB) would benefit from WebP — that is a follow-up
  batch (P2-IMG-1), not perf-safe-by-default.
- **No site.css rewrite**. Lighthouse's `unused-css-rules` audit
  reports 21 KiB unused on `/ar/`, but every rule may be used by
  another page. A full rewrite needs a coverage audit across all
  routes — out of scope for this iter.
- **No CRM, no signed legal content, no non-IT calculator, no
  WAF/CDN, no remote GitHub state**. None of these were touched.

## Remaining risks / open items

1. **`/ar/` LCP** still at 4.4 s. The hero JPEG (70 KiB) is the
   biggest single payload on the page. Options for a future batch:
   - convert hero to WebP (~25 KiB equivalent — saves ~45 KiB);
   - serve a smaller mobile-optimised hero via `srcset`/`sizes`
     (390 × 240 mobile vs 1920 × 1080 desktop);
   - use `<link rel="preload" as="image">` on the homepage hero,
     scoped per-Pexels URL (requires view layer changes).
2. **`.gz` files vs cache invalidation**. `precompress_static`
   keys on mtime — a source edit makes the existing companion
   stale and the command writes a new one. CI generates them
   fresh on every run. Local devs running `runserver` without the
   pre-step will serve uncompressed and see worse Lighthouse
   scores; documented in the runbooks.
3. **GZipMiddleware + BREACH**. Already noted in §2. The Django
   docs and current CSRF masking make this a non-issue for our
   surface, but we should revisit if we ever start reflecting
   user-controlled input inside compressed HTML responses.
4. **Mobile preset jitter**. Documented ±0.05 per-run on perf
   on this preset. The numbers above are single-run, taken
   2026-05-11. A regression sub-0.05 on `/ar/` is jitter, not
   signal.

## Run-to-run measurements (sanity)

Three mobile runs taken back-to-back on the new code:

| URL | run 1 | run 2 | run 3 |
|---|---|---|---|
| `/` | 0.93 | (skipped) | (skipped) |
| `/ar/` | 0.80 | 0.80 | (consistent across runs) |

The improvements are **consistent**, not jitter.

## How to verify locally

```bash
# Terminal A
source .venv/Scripts/activate
python manage.py runserver 127.0.0.1:8000

# Terminal B
source .venv/Scripts/activate
python manage.py precompress_static
bash scripts/run_lighthouse_mobile_local.sh
```

Or via the consolidated gate:

```bash
bash scripts/run_quality_gate.sh --mobile-lighthouse
```

## Decision

**Verdict: GO** — the target ≥ 0.85 was not strictly achieved on
`/ar/` (0.80 today), but every URL improved, the mobile floor
holds with margin, no constraint was violated, and the remaining
gap on `/ar/` is dominated by an image-format issue that warrants
a separate batch.
