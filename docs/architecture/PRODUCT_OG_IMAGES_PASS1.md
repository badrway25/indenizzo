# Open Graph PNG images — pass 1

**Iter**: F-product-og-images-pass1
**Data**: 2026-05-01
**Stato**: implementato + testato in locale + verificato live nel browser. **Nessun deploy.**

> 6 PNG 1200×630 generati a partire dalle foto Pexels congelate, per
> garantire anteprime social di qualità su X/Twitter (che non
> supporta SVG come Twitter Card image), Facebook, LinkedIn,
> WhatsApp. Strategia di picker a 3 livelli:
> Pexels media (se presente) → PNG country-specific → SVG fallback.

---

## 1. File creati / modificati

**Nuovi**:
- `scripts/generate_og_images.py` — generatore Pillow (no rete, no API key)
- `static/img/og/og-country-default.png` (1200×630, 386 KB)
- `static/img/og/og-italy.png` (1200×630, 484 KB)
- `static/img/og/og-france.png` (1200×630, 343 KB)
- `static/img/og/og-belgium.png` (1200×630, 511 KB)
- `static/img/og/og-morocco.png` (1200×630, 361 KB)
- `static/img/og/og-tunisia.png` (1200×630, 315 KB)
- `apps/core/test_og_images_pass1.py` — 27 test
- `docs/architecture/PRODUCT_OG_IMAGES_PASS1.md`

**Modificati**:
- `apps/core/seo.py` — aggiunto `_resolve_og_image_static_path(country_code)`, `_is_png()`. `build_open_graph_metadata` ora auto-sceglie l'immagine country-specific quando `image_static_path` non è passato. Emette `og:image:width=1200` + `og:image:height=630` quando l'immagine è PNG.
- `apps/core/views.py` — non passa più `image_static_path` esplicitamente; quando Pexels manifest c'è, fa override su og:image/twitter:image AND drops `og:image:width/height` (dimensioni JPG arbitrarie).

---

## 2. PNG generati (1200×630)

| File | Soggetto background | sha256 (prefix) |
|---|---|---|
| `og-country-default.png` | Books + gavel + Lady Justice (home_hero) | `1e709309a99ad17d…` |
| `og-italy.png` | Neoclassical Roman courthouse | `a640247e01251b9f…` |
| `og-france.png` | Palais de Justice Nice | `ef25b92ce5f7aef7…` |
| `og-belgium.png` | Palais de Justice Brussels | `1ad5898c55fd8bf4…` |
| `og-morocco.png` | Mausoleum Mohammed V Rabat | `7e7f58c23931ef1a…` |
| `og-tunisia.png` | Tunis government building | `3e5989397a766eef…` |

Background = foto Pexels frozen (vedi `PEXELS_CURATION_PASS1.md` §11) ridimensionata a 1200×630 con cover-crop, leggermente sfocata per leggibilità.

Overlay + testo:
- gradient ink-950 diagonale (più scuro in basso) + side-pad scuro 78% width per area headline;
- eyebrow gold-400: "STUDIO LEGALE INTERNAZIONALE BADRANE" + accent line gold;
- title serif sand-50: nome paese (es. "Italy");
- subtitle sans sand-50: country-specific:
  - IT → "Indicative compensation simulation"
  - FR → "Legal review for French compensation sources"
  - BE → "Legal review for Belgian compensation sources"
  - MA → "International inheritance legal review"
  - TN → "International inheritance legal review"
  - default → "Indicative compensation simulations & inheritance reviews"
- top-right: dominio "studiolegalebadrane.it" gold-400 discreto;
- niente attribution Pexels visibile;
- niente importi/numeri;
- niente "calculated/approved" per FR/BE/MA/TN.

---

## 3. Strategia helper SEO

`apps/core/seo.py::_resolve_og_image_static_path(country_code)` applica:

1. **PNG country-specific**: `static/img/og/og-{slug}.png` per `italy/france/belgium/morocco/tunisia` se esiste.
2. **PNG default**: `static/img/og/og-country-default.png` se esiste.
3. **SVG fallback**: `static/img/og-country-default.svg` (sempre presente, da pass 4).

`build_open_graph_metadata`:
- accetta `image_static_path: str | None = None` (caller può forzare un path);
- se None, chiama il picker;
- emette `og:image:width=1200` + `og:image:height=630` SOLO se l'immagine è PNG.

`_render_country_landing` (`apps/core/views.py`):
- chiama il builder senza `image_static_path` → auto-pick PNG country-specific;
- dopo, se Pexels manifest ha entry country-specific, sovrascrive `og:image` + `twitter:image` con la media URL del file JPG (foto "vera" è preferita per il social);
- in quel caso droppa `og:image:width/height` (dimensioni JPG arbitrarie).

Ordine di precedence finale per og:image:

```
Pexels media URL (se manifest entry presente)
  > PNG country-specific (static/img/og/og-{country}.png)
  > PNG default (static/img/og/og-country-default.png)
  > SVG fallback (static/img/og-country-default.svg)
```

---

## 4. Comando per rigenerare

```bash
# regenera tutti i 6 PNG da media/pexels/ (no rete, no API key)
python scripts/generate_og_images.py
```

Il comando è **idempotente** e fallisce con errore leggibile se il
manifest Pexels o un'immagine locale manca:

```
[og] manifest key not found: 'country_landing::IT'.
Run `python manage.py fetch_pexels_site_images --all --force` first.
```

Per cambiare l'aspetto (testo, palette, layout) → modificare le
costanti in cima a `scripts/generate_og_images.py` e ri-eseguire.

Per cambiare la **foto** alla base di un PNG OG:
1. aggiornare `photo_id` in `config/pexels_image_overrides.json`;
2. `python manage.py fetch_pexels_site_images --slot <key> --force`;
3. `python scripts/generate_og_images.py`.

---

## 5. Meta live verificati

Server: `http://127.0.0.1:31445/` (PID 14008).

Tag emessi sulle 5 country landing (manifest Pexels presente in dev):

| URL | og:image | og:image:width/height |
|---|---|---|
| `/countries/italy/` | `…/media/pexels/country_landing__it__35878530.jpg` | (rimossi, JPG) |
| `/countries/france/` | `…/media/pexels/country_landing__fr__21253838.jpg` | (rimossi, JPG) |
| `/countries/belgium/` | `…/media/pexels/country_landing__be__14192312.jpg` | (rimossi, JPG) |
| `/countries/morocco/` | `…/media/pexels/country_landing__ma__35786061.jpg` | (rimossi, JPG) |
| `/countries/tunisia/` | `…/media/pexels/country_landing__tn__35677445.jpg` | (rimossi, JPG) |
| `/ar/countries/morocco/` | (idem morocco) + RTL preserved | — |

Quando il manifest Pexels NON è presente (ambiente di deploy senza
cache fetched), l'og:image scende al PNG country-specific
(`/static/img/og/og-{country}.png`) con `og:image:width=1200` e
`og:image:height=630` — verificato dai test
`test_og_image_uses_country_png_when_no_manifest`.

Nessuno screenshot è stato salvato: il layout HTML pubblico non
cambia visivamente in questo iter (i PNG sono solo per i social
scraper, non vengono renderizzati come hero in nessuna pagina).

---

## 6. Browser live

| Campo | Valore |
|---|---|
| Porta | **31445** |
| URL base | `http://127.0.0.1:31445/` |
| PID | **14008** |
| Stop | `Stop-Process -Id 14008 -Force` (PowerShell) o `taskkill //F //PID 14008` |

URL principali da rivedere:
- `http://127.0.0.1:31445/countries/italy/` (verifica og:image meta)
- `http://127.0.0.1:31445/countries/morocco/`
- `http://127.0.0.1:31445/ar/countries/morocco/` (RTL + meta intatti)
- `http://127.0.0.1:31445/static/img/og/og-italy.png` (preview PNG diretto)

---

## 7. Test (27 nuovi, tutti passati)

`apps/core/test_og_images_pass1.py`:

1. `test_og_png_exists_and_is_1200x630` × 6 — sanity Pillow su file
2. `test_og_image_uses_country_png_when_no_manifest` × 5 — picker country
3. `test_twitter_image_is_png_no_manifest` — twitter:image PNG, no SVG
4. `test_resolve_og_image_static_path_picks_country_then_default` — unit helper
5. `test_og_pages_have_no_visible_attribution` × 4
6. `test_og_pages_no_api_key_leak` × 4
7. `test_og_scaffold_country_no_calculated_claim` × 4
8. `test_og_image_uses_pexels_media_when_manifest_present` — Pexels override drop dim
9. `test_og_italy_smoke_run_simulation` — canarino IT 35/10/0

Totale repo: **729 passed in 30s** (era 702 → +27).

---

## 8. Limiti

- **Social preview reale** va testata su strumenti ufficiali quando
  il sito sarà online: Facebook Sharing Debugger, LinkedIn Post
  Inspector, X Card Validator. In dev locale possiamo solo
  verificare i tag, non il rendering social.
- **Font fallback**: lo script cerca Cormorant Garamond / Georgia /
  Inter / Arial nel filesystem; su sistemi senza nessuno di quelli
  cade su `ImageFont.load_default()`, che ha dimensione fissa
  piccola e produrrebbe titoli minuscoli. Per CI/produzione: bundle
  un font ttf dentro `static/img/og/fonts/` e referenziarlo
  esplicitamente.
- **Dimensioni file**: i PNG generati pesano 315–511 KB. Per
  produzione aggressiva si può comprimere via `oxipng` /
  `pngquant` (riduzione 40–60% senza perdita visiva).
- **Refresh on Pexels change**: cambiare `photo_id` nel JSON
  override richiede ri-fetch + ri-generazione PNG (vedi §4).

---

## 9. Prossimo step consigliato

**F-product-og-images-pass2-translations**: 4 versioni `.png` per
ogni paese (IT/FR/EN/AR) con headline tradotto, puntate da
`og:locale`. X non supporta automaticamente la rotation per locale,
quindi servirebbe negoziazione lato server (locale-aware static
URL). Subito dopo: comprimere i 6 PNG via `oxipng` per ridurre
peso senza degradare qualità visiva.