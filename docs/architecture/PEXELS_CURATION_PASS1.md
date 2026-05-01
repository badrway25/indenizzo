# Pexels image curation — pass 1

**Iter**: F-product-pexels-curation-pass1
**Data**: 2026-05-01
**Stato**: implementato + testato in locale + verificato live nel browser. **Nessun deploy.**

> Sistema di override editoriale per le immagini Pexels: ogni slot
> può ora ricevere una `query` curata, un `photo_id` pinned, una
> lista di `avoid_terms` e note interne. 5 slot fuori contesto sono
> stati rifetchati con immagini più appropriate. Il comando supporta
> `--slot`, `--photo-id`, `--audit`. Italia 35/10/0 invariata.

---

## 1. Audit immagini iniziali (before)

| Slot | photo_id | Giudizio | Motivo |
|---|---|---|---|
| `home_hero` | 6077091 | KEEP | Books + Lady Justice, no people |
| `countries_index` | 7876093 | KEEP | Editorial workspace |
| `country_landing::IT` | 35878530 | KEEP | Real Roman courthouse + palms |
| `country_landing::FR` | 21253838 | KEEP | Palais de Justice (Nice — accettabile per FR) |
| `country_landing::BE` | 14192312 | KEEP | Real Brussels Palais de Justice |
| `country_landing::MA` | 33487094 | **REPLACE** | **Odense Denmark** courthouse — wrong country |
| `country_landing::TN` | 35677445 | KEEP | Tunis government building |
| `methodology_hero` | 7876093 | **REPLACE** | Duplicate of countries_index |
| `wizard_start_hero` | 7876289 | **REPLACE** | "Bald lawyer in office" — person-stock |
| `wizard_italy_road_accident_hero` | 35878530 | KEEP | Same IT landing photo (acceptable) |
| `wizard_france_road_accident_hero` | 21253838 | KEEP | Same FR landing photo (acceptable) |
| `wizard_belgium_road_accident_hero` | 36376007 | KEEP | Royal Palace Brussels, architectural |
| `wizard_morocco_inheritance_hero` | 7876054 | **REPLACE** | "Man holding **divorce** certificate" — wrong topic + person |
| `wizard_tunisia_inheritance_hero` | 27594857 | **REPLACE** | Sidi Bou Said tourist landscape — non-legal |
| `contact_hero` | 7841469 | KEEP | Group meeting in office |

**5 REPLACE** + **10 KEEP**.

---

## 2. After (curated)

| Slot | new photo_id | Subject |
|---|---|---|
| `country_landing::MA` | 35786061 | Mausoleum of Mohammed V, Rabat — real Moroccan institutional landmark |
| `methodology_hero` | 48195 | Hand signing formal document with fountain pen — pure editorial |
| `wizard_start_hero` | 8112198 | Framed legal certificate + Lady Justice on desk — no people |
| `wizard_morocco_inheritance_hero` | 28976477 | Historic Moroccan building with flag — architectural |
| `wizard_tunisia_inheritance_hero` | 35812446 | Roman amphitheater El Jem, Tunisia — historical institution |

---

## 3. Override system

File: `config/pexels_image_overrides.json` (committable, **mai contiene
la API key**).

### Schema

```json
{
  "slots": {
    "<override_lookup_key>": {
      "query": "preferred Pexels search query",
      "photo_id": null,
      "avoid_terms": ["person", "smile", "..."],
      "editorial_notes": "human-readable rationale"
    }
  }
}
```

`<override_lookup_key>` = `purpose` per slot global, oppure
`<purpose>_<COUNTRY_ISO>` per slot country-specific:

- `home_hero`
- `countries_index`
- `country_landing_IT` / `country_landing_FR` / `country_landing_BE` /
  `country_landing_MA` / `country_landing_TN`
- `methodology_hero`
- `wizard_start_hero`
- `wizard_italy_road_accident_hero_IT` /
  `wizard_france_road_accident_hero_FR` /
  `wizard_belgium_road_accident_hero_BE` /
  `wizard_morocco_inheritance_hero_MA` /
  `wizard_tunisia_inheritance_hero_TN`
- `contact_hero`

### Logica fetch

`apps/core/pexels.py::fetch_one_slot()` legge l'override e applica la
seguente priorità:

1. **`pinned_photo_id` esplicito** (CLI `--photo-id`) → fetch diretto
   via `GET /v1/photos/{id}` (`photo_by_id()`).
2. Altrimenti, **`override.photo_id`** se valorizzato nel JSON.
3. Altrimenti, **search** con `override.query` (fallback alla
   `query` di default della slot se l'override non c'è).
4. Filtro `avoid_terms`: foto la cui `alt`/`pexels_url` contiene una
   stringa in `avoid_terms` (case-insensitive) viene scartata. Se il
   filtro lascia il pool vuoto, fallback alla prima foto.

---

## 4. Come fare pin manuale di un photo_id

### Opzione A: file override (persistent)

Modificare `config/pexels_image_overrides.json`:

```json
"country_landing_MA": {
  "query": "Rabat architecture Morocco official building",
  "photo_id": 35786061,
  "avoid_terms": ["denmark"],
  "editorial_notes": "Pinned: Mausoleum Mohammed V, validated by Studio."
}
```

Poi:

```bash
python manage.py fetch_pexels_site_images --slot country_landing_MA --force
```

### Opzione B: CLI `--photo-id` (ad-hoc)

```bash
python manage.py fetch_pexels_site_images \
  --slot country_landing_MA \
  --photo-id 35786061 \
  --force
```

---

## 5. Come rifetchare uno slot

```bash
# audit (zero rete, no API key needed)
python manage.py fetch_pexels_site_images --audit

# refetch single slot
python manage.py fetch_pexels_site_images --slot wizard_start_hero --force

# refetch tutti gli slot
python manage.py fetch_pexels_site_images --all --force
```

---

## 6. Screenshot before/after

In `docs/screenshots/live_qa/pexels_curation_pass1/after/`:

- `01_home.png` — home con backdrop library + Lady Justice (KEEP)
- `03_morocco_landing.png` — Mausoleum Mohammed V, Rabat (REPLACE → corretto)
- `04_tunisia_landing.png` — Tunis institutional building (KEEP)
- `05_wizard_start.png` — Framed certificate + Lady Justice on desk (REPLACE → no people)
- `06_methodology.png` — Hand signing legal document with fountain pen (REPLACE → editorial)
- `07_ar_morocco_rtl.png` — RTL preserved with Mausoleum image

---

## 7. Browser live

| Campo | Valore |
|---|---|
| Porta | **13428** |
| URL base | `http://127.0.0.1:13428/` |
| PID | **63660** |
| Avvio | `DJANGO_DEBUG=true DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost ./.venv/Scripts/python.exe manage.py runserver 127.0.0.1:13428 --noreload` |
| Stop | `Stop-Process -Id 63660 -Force` (PowerShell) o `taskkill //F //PID 63660` (Bash) |

URL principali da rivedere:
- `http://127.0.0.1:13428/countries/morocco/` — verifica Mausoleum
- `http://127.0.0.1:13428/countries/tunisia/` — verifica institutional building
- `http://127.0.0.1:13428/wizard/` — verifica niente persone in primo piano
- `http://127.0.0.1:13428/methodology/` — verifica hand signing document
- `http://127.0.0.1:13428/ar/countries/morocco/` — verifica RTL + Mausoleum

---

## 8. Test (22 nuovi, tutti passati)

`apps/core/test_pexels_curation_pass1.py`:

1. `test_override_file_has_no_api_key_or_secret` — guard hard
2. `test_command_reads_override_query` — query override applicata
3. `test_command_slot_arg_only_fetches_one_slot` — `--slot` mirato
4. `test_command_photo_id_without_slot_raises` — guard CLI
5. `test_command_audit_runs_without_api_key_and_without_network`
6. `test_command_audit_does_not_leak_api_key`
7. `test_curation_no_visible_attribution` × 6 paths
8. `test_curation_api_key_never_in_html` × 6 paths
9. `test_morocco_landing_does_not_serve_denmark_courthouse` — guard difensivo
10. `test_override_lookup_key_for_global_slots`
11. `test_load_overrides_returns_dict_or_empty`
12. `test_curation_italy_smoke_run_simulation` — canarino IT 35/10/0

Totale repo: **687 passed in 34s** (era 665 → +22).

---

## 9. Limiti

- `avoid_terms` matcha solo `alt` + `pexels_url` (no analisi
  immagine). Se Pexels restituisce una foto con persone ma la `alt`
  non lo dichiara, il filtro non la blocca. Mitigation: pin manuale
  via `--photo-id` per i casi visivamente critici.
- `select_best_photo` non esplora `curated_photos` come fallback se
  search vuota dopo `avoid_terms`. Pass futuro.
- Il file override non versiona la storia delle scelte. Per audit
  storico serve git log.

---

## 10. Prossimo step consigliato

**F-product-og-images-pass1**: convertire l'SVG `og-country-default`
in PNG 1200×630 + generare 5 OG image country-specific (Italy,
France, Belgium, Morocco, Tunisia) usando le foto Pexels appena
curate. X non supporta SVG nelle Twitter Card image.

Subito dopo: pin manuale staff-validato dei 15 photo_id nel JSON
override (così che ogni successivo `--all --force` non rischi di
ridurre la qualità con nuove immagini Pexels più recenti).