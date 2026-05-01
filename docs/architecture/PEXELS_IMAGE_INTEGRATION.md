# Pexels image integration

**Iter**: F-product-pexels-image-integration (creato), poi
F-product-pexels-polish-no-caption-live-server-and-i18n-status
(no caption), F-product-premium-visual-i18n-pass1 (slots
site-wide 9 → 15)
**Data**: 2026-05-01
**Stato**: implementato + testato in locale + verificato live nel browser. **Nessun deploy.**

> **Update pass premium-visual-i18n-pass1**: gli slot Pexels sono
> passati da 9 (solo country landing + methodology + contact) a
> **15** site-wide. Aggiunti: `home_hero`, `wizard_start_hero`,
> `wizard_italy_road_accident_hero`, `wizard_france_road_accident_hero`,
> `wizard_belgium_road_accident_hero`, `wizard_morocco_inheritance_hero`,
> `wizard_tunisia_inheritance_hero`. Le slot legacy `methodology`
> e `contact` sono state rinominate in `methodology_hero` e
> `contact_hero`. Il template hero unificato vive in
> `templates/partials/_premium_hero_image.html`.

> **Update pass premium-visual-i18n-pass2**: 15/15 slot fetched
> realmente da Pexels (`PEXELS_API_KEY` impostata come env var di
> sessione, mai committata). Foto di alta risoluzione (1920×1080
> → 8096×5397). Bug `local_path` Windows backslash fixato:
> `(Path("pexels") / fname).as_posix()`. HTTP timeout bumpato da
> 10s → 30s (alcune query Pexels superano i 10s). `og:image`
> punta automaticamente al file Pexels locale quando esiste.
> La home ora ha hero **image-as-backdrop** custom (non usa il
> partial). Le countries cards mostrano la foto country-specific
> in head card.

> **Update pass curation-1**: introdotto sistema override editoriale
> (`config/pexels_image_overrides.json`, committato, mai con secret).
> Schema per slot: `{query, photo_id, avoid_terms, editorial_notes}`.
> Comando esteso con `--slot`, `--photo-id`, `--audit`. 5 slot fuori
> contesto rifetchati: Morocco landing (era Odense Danimarca → ora
> Mausoleum Mohammed V Rabat), methodology_hero (era duplicato →
> ora hand signing legal document), wizard_start_hero (era person
> stock → ora certificate + Lady Justice), wizard_morocco_inheritance
> (era "divorce certificate" → ora historic Moroccan building),
> wizard_tunisia_inheritance (era Sidi Bou Said tourism → ora El Jem
> amphitheater). Vedi `PEXELS_CURATION_PASS1.md` per dettagli.

> Sorgente immagini professionali per home + country landing.
> Server-side, cache-first, opt-in via env var. Niente API key
> esposta. Niente immagine committata.

---

## 1. Env vars

| Var | Default | Scopo |
|---|---|---|
| `PEXELS_API_KEY` | `""` (vuota) | API key personale Pexels. Senza, il sito mostra fallback statico. **Mai committarla.** |
| `PEXELS_ENABLED` | `False` | Soft switch: spegne il flusso anche con la key configurata. |
| `PEXELS_API_BASE_URL` | `https://api.pexels.com/v1` | Base URL Pexels v1. |
| `PEXELS_CACHE_DAYS` | `30` | Hint TTL cache (per future logiche di refresh). |
| `PEXELS_DEFAULT_ORIENTATION` | `landscape` | Orientation default per la search. |
| `PEXELS_DEFAULT_PER_PAGE` | `10` | `per_page` default per la search. |

Tutte env-driven via `django-environ` (vedi `config/settings.py`).
Niente fallback hardcoded della key in codice.

---

## 2. Sicurezza secret

Regole hard del modulo `apps/core/pexels.py`:

- **La key è letta SOLO da settings**, che a loro volta leggono SOLO
  da env. Niente file checked-in la contiene.
- **Mai inviata al browser**: tutte le chiamate Pexels avvengono
  server-side, dal management command. Il rendering pubblico legge
  unicamente file locali + `pexels_manifest.json`.
- **Mai inviata al CDN Pexels**: il download della foto
  (`images.pexels.com/...`) è fatto SENZA `Authorization` header
  (la key è valida solo per `api.pexels.com`).
- **Mai loggata**: `_safe_request()` cattura `requests.RequestException`
  e logga solo la classe d'errore, non il body né gli header.
- **Mai inclusa in error message**: gli errori 401/403/429/5xx
  producono `PexelsAPIError` con messaggio fisso, niente dump.
- **Test esplicito** (`test_api_key_never_appears_in_rendered_html`):
  con la key impostata a un valore stringente, viene visitato un set
  di URL pubblici e si verifica che la stringa NON compaia mai in
  nessun body.

`.gitignore` esclude:

```
media/pexels/*.jpg
media/pexels/*.jpeg
media/pexels/*.png
media/pexels/*.webp
media/pexels/pexels_manifest.json
```

(`media/` è già gitignored a livello globale; le righe sopra sono un
guard esplicito per chiunque sposti la cache fuori da `media/`.)

---

## 3. Query mapping

`apps.core.pexels.SITE_IMAGE_SLOTS` dichiara le slot del sito:

| purpose | country | query |
|---|---|---|
| `home_hero` | — | `modern law office marble` |
| `countries_index` | — | `international law office` |
| `country_landing` | IT | `Rome courthouse architecture` |
| `country_landing` | FR | `Paris courthouse architecture` |
| `country_landing` | BE | `Brussels courthouse architecture` |
| `country_landing` | MA | `Morocco architecture law office` |
| `country_landing` | TN | `Tunis courthouse architecture` |
| `methodology` | — | `legal documents desk` |
| `contact` | — | `law office consultation` |

Tono editoriale: istituzionale, architettura/uffici/documenti.
NIENTE foto di incidenti stradali, persone ferite, o
sensazionalismo. Preferenza `landscape` per coerenza con
hero/og:image (16:9 ish).

---

## 4. Cache & manifest

**Layout**:

```
media/pexels/
├── pexels_manifest.json
├── country_landing__it__1234567.jpg
├── country_landing__fr__9876543.jpg
└── ...
```

**Manifest entry** (campo per campo):

```json
{
  "country_landing::IT": {
    "purpose": "country_landing",
    "country_code": "IT",
    "query": "Rome courthouse architecture",
    "local_path": "pexels/country_landing__it__1234567.jpg",
    "photo_id": 1234567,
    "photographer": "Jane Doe",
    "photographer_url": "https://www.pexels.com/@janedoe",
    "pexels_url": "https://www.pexels.com/photo/1234567/",
    "alt": "Rome courthouse facade",
    "width": 4000,
    "height": 2667,
    "downloaded_at": "2026-05-01T12:00:00+00:00",
    "sha256": "<digest>",
    "extra": {"size_bytes": 524288}
  }
}
```

Le chiavi sono `<purpose>::<COUNTRY_ISO>` (es. `country_landing::IT`,
`home_hero::GLOBAL`). Read in `apps/core/views.py::_render_country_landing`
via `get_image_for_country_landing(country_code)`.

---

## 5. Attribution

Pexels license richiede attribution: il modulo espone
`attribution_for_entry(entry)` che ritorna
`"Photo by <photographer> on Pexels"`. Il template
`country_landing.html` la renderizza dentro `<figcaption>` overlay
sull'immagine, con link al `pexels_url` quando disponibile.

Niente attribution in JS o nascosto in commenti HTML: deve essere
visibile all'utente.

---

## 6. Comando

```
python manage.py fetch_pexels_site_images [--dry-run]
                                          [--country IT|FR|BE|MA|TN]
                                          [--all]
                                          [--force]
                                          [--per-page N]
                                          [--orientation landscape|portrait|square]
```

**Workflow tipico**:

```bash
# 1. Anteprima — niente rete, solo lista delle slot
python manage.py fetch_pexels_site_images --dry-run --all

# 2. Set della key (locale, non committata)
export PEXELS_API_KEY="..."

# 3. Scarica tutto
python manage.py fetch_pexels_site_images --all

# 4. Aggiorna SOLO una landing
python manage.py fetch_pexels_site_images --country IT --force
```

Output esempio (mascherato):

```
[country_landing::IT] query='Rome courthouse architecture'  existing=no
  [ok] photo 1234567  -> pexels/country_landing__it__1234567.jpg
    Photo by Jane Doe on Pexels
    https://www.pexels.com/photo/1234567/
```

**Senza key**:

```
$ python manage.py fetch_pexels_site_images --all
CommandError: PEXELS_API_KEY is empty. Set the env var to enable Pexels integration; without it, the site falls back to local placeholders.
```

L'exit è non distruttivo: nessun file modificato, nessuna chiamata.

---

## 7. Aggiornare immagini

Per rifresh manuale (es. nuove foto Pexels disponibili):

```bash
python manage.py fetch_pexels_site_images --all --force
```

`--force` scarica anche se la slot è già nel manifest. Le foto
precedenti restano sul disco a meno di rimozione manuale; lo Studio
può ripulire `media/pexels/` periodicamente.

In futuro: aggiungere logica TTL basata su `PEXELS_CACHE_DAYS` +
`downloaded_at`, e pulizia via `--prune`.

---

## 8. OG image

Quando il manifest contiene una entry `country_landing::<ISO>`,
`_render_country_landing` SOVRASCRIVE i tag OG:

- `og:image` → URL assoluto del file `media/pexels/<...>.jpg`
- `twitter:image` → idem
- `og:image:alt` / `twitter:image:alt` → `og_title`

Senza manifest, i tag puntano al placeholder
`static/img/og-country-default.svg` di pass 4.

**Niente URL remoti Pexels** in `og:image`: scarichiamo sempre
localmente per evitare:
1. dipendenza dal CDN Pexels (rate-limit, downtime);
2. tracking lato Pexels degli scraper social;
3. perdita dell'immagine se Pexels la deprecca.

---

## 9. Rigenerare OG images

Se cambiamo il pool di foto:

```bash
python manage.py fetch_pexels_site_images --all --force
# i tag OG si aggiornano automaticamente al prossimo render
```

I crawler social (Facebook Sharing Debugger, LinkedIn Post
Inspector, X Card Validator) hanno cache propria: dopo ogni cambio
in produzione, va fatto un "re-scrape" manuale.

---

## 10. Limiti & licenza

- **Pexels free tier**: 200 req/h, 20 000 req/mese. Per la nostra
  scala (≤ 9 query totali) è ampiamente sotto soglia, ma il
  comando rispetta il rate-limit gestendo 429 con `PexelsAPIError`.
- **Licenza Pexels**: free for use, **attribution non obbligatoria
  ma raccomandata**. Noi la mostriamo sempre — è un signal di
  trasparenza coerente con l'identità "Studio + fonti validate".
- **Foto modificate**: la licenza permette modifica/recadrage/
  conversione formato. Non identifichiamo persone riconoscibili
  in foto Pexels in contesti che possano implicare endorsement.
- **PNG vs JPG**: oggi salviamo in `.jpg` (la maggior parte delle
  foto Pexels sono JPG). Per OG ottimale alcuni scraper preferiscono
  PNG; in pass futuro si può aggiungere conversione automatica.

---

## 11. Test

`apps/core/test_pexels_integration.py` (12 test):

1. `test_search_photos_sends_authorization_header_without_bearer`
2. `test_auth_headers_never_include_bearer_prefix`
3. `test_search_photos_without_key_raises_controlled_error`
4. `test_command_dry_run_does_not_call_network`
5. `test_command_writes_manifest_with_attribution`
6. `test_country_landing_renders_without_manifest`
7. `test_country_landing_uses_local_pexels_image_when_manifest_present`
8. `test_og_image_uses_local_pexels_when_manifest_present`
9. `test_api_key_never_appears_in_rendered_html`
10. `test_pages_render_without_pexels_api_key`
11. `test_command_without_key_raises_command_error`
12. `test_italy_smoke_run_simulation_35_10_0` (canarino IT)

Tutti mocked, niente rete reale.

---

## 12. Browser live verification

Porta libera **59159**. Con `PEXELS_API_KEY` non configurata in
dev:

| URL | Risultato |
|---|---|
| `/countries/italy/` | nessun figure, og:image = SVG fallback (verifica fallback elegante) |
| `/countries/italy/` (manifest seedato) | figure con foto + attribution "Photo by Mario Rossi on Pexels" + link Pexels, og:image override su `/media/pexels/...jpg` |
| `/countries/france/` | nessun figure (no entry FR nel manifest), fallback intatto |
| `/ar/countries/morocco/` | RTL preservato, nessun figure, fallback intatto |

Screenshot in `docs/screenshots/live_qa/pexels_integration/`:
- `01_italy_no_manifest_fallback.png` — fallback senza manifest
- `02_italy_with_seeded_manifest.png` — bug iniziale (comment leak `{# … #}`, fixato con `{% comment %}`)
- `03_morocco_ar_rtl_fallback.png` — RTL fallback
- `04_italy_with_seeded_manifest_fixed.png` — pre-restart server (cache)
- `05_italy_with_manifest_clean.png` — final, comment fixato

Bug visivo trovato e fixato: il `{# … #}` Django comment multi-line
non è supportato (regola nota dal pass 1/3); convertito a
`{% comment %}…{% endcomment %}`.

---

## 13. Cosa resta

- **Conversione SVG → PNG** del placeholder pass 4 + 5 PNG country-
  specific per OG image più ottimali (X non supporta SVG card image).
- **TTL automatic refresh** basato su `PEXELS_CACHE_DAYS` +
  `downloaded_at` nel manifest; comando `--prune`.
- **Variants responsive** (srcset multi-size scaricando `large`,
  `medium`, `small` Pexels) per ridurre payload mobile.
- **CDN cache headers** in produzione (Caddy/nginx): `Cache-Control:
  public, max-age=2592000` per `/media/pexels/*`.
- **Curated fallback** automatic: se la search non rende risultati
  rilevanti, fallback a `curated_photos()` (già implementata, non
  ancora cabled nel comando).
- **Hash-based dedup**: due slot diverse possono finire sulla stessa
  foto; gestire con `sha256` collision check.
