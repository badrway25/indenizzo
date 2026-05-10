# Local web fonts

**Iter**: P1-SEC-1 (`p1/local-fonts-csp-hardening`).
**Date**: 2026-05-10.

This directory holds the `.woff2` files served from `/static/fonts/`
so the platform no longer depends on `fonts.googleapis.com` and
`fonts.gstatic.com` at runtime. With local fonts, the CSP can drop
the two CDN allowlist entries (`style-src` and `font-src`).

The `@font-face` rules pointing at these files live in
`static/css/fonts.css`. `templates/base.html` includes that file
instead of the Google Fonts `<link>` it used to load.

## Inventory

| Family | Weights | Subsets | Files | Total |
|---|---|---|---|---|
| Inter | 400, 500, 600, 700 | latin, latin-ext | 8 | 520.8 KB |
| Cormorant Garamond | 500, 600, 700 | latin, latin-ext | 6 | 209.1 KB |
| Amiri | 400, 700 | arabic | 2 | 203.6 KB |
| Tajawal | 400, 500, 700 | arabic | 3 | 26.2 KB |

Total: ~960 KB across 19 `.woff2` files.

`latin` covers the basic Latin range used by Italian, French and
English (including the accented letters `à è é ì ò ù ç …`).
`latin-ext` is kept for robustness: the platform handles
cross-border cases where contact-form names may include
Polish/Czech/Romanian glyphs.

`arabic` covers the AR locale (RTL).

## Source

All four families ship under the **SIL Open Font License 1.1**
(commercial self-hosting permitted; see per-family files in
`LICENSES/`).

The `.woff2` binaries were obtained via the official Google Fonts
CSS API (`fonts.googleapis.com/css2?family=…`) which serves a
manifest of versioned files hosted on `fonts.gstatic.com`. Only
the unicode subsets actually needed by the platform were kept; the
script discards `cyrillic`, `greek`, `vietnamese` and similar.

The license `.txt` files were downloaded from each family's
canonical upstream:

- `Inter-OFL.txt` — `github.com/rsms/inter`
- `CormorantGaramond-OFL.txt` — `github.com/CatharsisFonts/Cormorant`
- `Amiri-OFL.txt` — `github.com/aliftype/amiri`
- `Tajawal-OFL.txt` — `github.com/google/fonts`

## How to refresh

`scripts/download_local_fonts.py` regenerates the `.woff2` files and
the `static/css/fonts.css` rules from a single command:

```
python scripts/download_local_fonts.py
```

The script:

1. queries the Google Fonts CSS API for the four families with the
   weights listed in the `FAMILIES` constant;
2. parses the response and keeps only the `@font-face` blocks for
   the configured `subsets`;
3. downloads each `.woff2` from the URL embedded in the response;
4. emits `static/css/fonts.css` with the correct
   `unicode-range` per family.

If a Google Fonts version bumps the URL hashes upstream, re-running
the script and committing the diff is the supported path.

## Why `font-display: swap`

To avoid invisible text on slow networks. The browser renders the
fallback first and swaps in the local font when ready — the same
behavior the previous Google Fonts integration used.
