# Premium visual + i18n pass 2 — real images + denser translations

**Iter**: F-product-premium-visual-i18n-pass2-real-images-and-copy
**Data**: 2026-05-01
**Stato**: implementato + testato in locale + verificato live nel browser. **Nessun deploy.**

> Salto reale di qualità rispetto al pass 1: 15 foto Pexels reali
> alta-risoluzione scaricate e cached, hero home con immagine come
> sfondo + overlay ink, country card con immagini per paese,
> traduzioni IT/FR/AR estese da 55 a 138 stringhe ad alta visibilità.
> Italia 35/10/0 invariata. Server live attivo.

---

## 1. File creati / modificati

**Nuovi**:
- `apps/core/test_premium_visual_i18n_pass2.py` — 44 test (pages 200, no caption, API key safety, dense FR/AR translations, html lang, hero render).
- `scripts/fix_manifest_slashes.py` — one-shot per il bug Windows backslash → forward-slash nel manifest.
- `docs/screenshots/live_qa/premium_visual_i18n_pass2/{before,after}/` — 16 screenshot.
- `docs/architecture/PREMIUM_VISUAL_I18N_PASS2.md` — questo file.

**Modificati**:
- `apps/core/pexels.py` — `local_path` ora salvato come POSIX (forward slash) invece del native separator Windows; timeout HTTP da 10 → 30s.
- `apps/core/views.py` — `countries()` passa per ogni paese una entry `image` (lookup manifest country-specific).
- `templates/public/home.html` — **redesign hero**: immagine come sfondo full-bleed con overlay gradient ink-950, headline serif sand, CTA primaria "Start Italy simulation" (gold) + secondaria "Request legal review" (ghost outlined), trust card "Trust by design" su backdrop-blur sand.
- `templates/public/countries.html` — country cards ora mostrano immagine paese-specifica come header (h-40/44) con gradient overlay e country code in serif overlay; status pill ora a colori pieni per maggiore contrasto.
- `templates/partials/_premium_hero_image.html` — hero banner h-52/64/80 con subtle gradient overlay ink-950/30 dall'angolo basso-sinistra (no caption visibile).
- `scripts/populate_translations_pass1.py` — esteso con pass2 batch A (37 long-form copy strings) + batch B (46 labels/CTA strings); helper `_po_escape()` per gestire `"` e `\` negli msgid.
- `apps/core/test_country_landings_pass4.py` — `test_country_landing_og_image_is_absolute_url` accetta sia `og-country-default` che `/media/pexels/` (entrambi validi a seconda del manifest).
- `apps/core/tests.py` — 2 test forzati a `/en/` perché ora la default IT traduce "Module ready" → "Modulo pronto".
- `locale/{it,fr,ar}/LC_MESSAGES/django.{po,mo}` — 138 traduzioni totali (55 pass1 + 37 pass2A + 46 pass2B).

---

## 2. Pexels fetch reale eseguito

Sì. Con `PEXELS_API_KEY` impostata come env var di sessione (non
committata). Output del comando:

```
python manage.py fetch_pexels_site_images --all
…
Done. updated=12 skipped=0 dry_run=False
```

3 slot in timeout (`country_landing::MA`, `country_landing::IT` 2 ×
`wizard_italy_road_accident_hero::IT`). Bumpato il timeout HTTP da
10s → 30s e ri-eseguito il comando per slot mancanti. Manifest
finale ha **15/15 entries** con foto 1920×1080 → 8096×5397 px.

Esempi di photographer attribution conservati nel manifest
(NON visibili nel HTML pubblico):
- IT: Alec Doualetas — `https://www.pexels.com/photo/35878530/`
- FR: Laura Paredis — Palais de Justice (Paris)
- BE: Ivan Dražić — Brussels law courts
- MA: Jasmin Börsig — historic courthouse facade
- TN: Elijah Cobb — Tunisian government building

---

## 3. Miglioramenti visuali

### Home (redesign)

Prima: hero banner sopra + testo separato sotto.
Dopo:
- Immagine **come sfondo** dell'intera hero section, full-bleed
- Overlay gradient `ink-950/85 → ink-950/75 → ink-900/65`
- Headline `font-serif text-4xl sm:text-5xl lg:text-6xl` in sand-50
- Eyebrow gold-400 letterspaced
- CTA primaria pillola gold-500 con shadow → "Start Italy simulation"
- CTA secondaria ghost border sand-50/30 → "Request legal review"
- Trust card destra in backdrop-blur sand-50/95 (leggibilità)
- Country strip cards ora cliccabili con hover gold-400

### Countries index

Prima: card piatte con codice + status pill in alto.
Dopo:
- Card layout 2-section: top h-40/44 con immagine paese + gradient overlay + country code in serif sand-50 + status pill a colori pieni
- Bottom con name serif + descrizione + link "Apri la pagina paese"
- Hover: shadow-lg + border gold-400/60
- CTA banner finale ink-950 invariato (pass1)

### Country landing

Banner partial con foto reale per paese. Layout pass3 invariato.
og:image override sul file Pexels locale.

### Methodology / wizard / contact

Banner partial con foto editoriale. Layout invariato.

---

## 4. Traduzioni completate

Totale per IT/FR/AR: **138 stringhe** ad alta visibilità.

- **Pass 1** (55): nav, footer, hero CTA, status badge, country page basics
- **Pass 2 batch A** (37): hero descriptions long-form, methodology bullets, country landing intro paragraphs, disclaimer
- **Pass 2 batch B** (46): labels short, CTAs, country wizard CTAs, "How to proceed" content, "Need a direct review?" banner, attribution copy disclaimer/privacy

EN resta source. Le 459 stringhe non tradotte sono in larga parte
admin labels / model verbose_name (NON visibili sul sito pubblico).

`compilemessages` produce `.mo` valide per tutti i 4 locale.

**Verificato live**:
- `/fr/countries/france/` mostra "Pays/Méthodologie/Demander une revue juridique/Statut/Base juridique/Sources juridiques en cours de revue/Comment procéder/Option 1/Option 2/Ouvrir l'assistant de validation France"
- `/ar/countries/morocco/` mostra "البلدان/الرئيسية/الحالة/الأساس القانوني/اطلب مراجعة قانونية/كيفية المتابعة/المصادر القانونية قيد المراجعة/اطلب مراجعة الميراث المغربي" + dir=rtl

---

## 5. Browser live + screenshot

| Campo | Valore |
|---|---|
| Porta | **47388** |
| URL base | `http://127.0.0.1:47388/` |
| PID | **23056** |
| Comando avvio | `DJANGO_DEBUG=true DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost ./.venv/Scripts/python.exe manage.py runserver 127.0.0.1:47388 --noreload` |
| Stop manuale | `Stop-Process -Id 23056 -Force` (PowerShell) o `taskkill //F //PID 23056` (Bash) |

URL principali da aprire per validare visivamente:
1. `http://127.0.0.1:47388/` — home con backdrop image library + Lady Justice
2. `http://127.0.0.1:47388/countries/` — coverage map con cards immagine per paese
3. `http://127.0.0.1:47388/countries/italy/` — Palazzo di Giustizia Roma
4. `http://127.0.0.1:47388/fr/countries/france/` — Palais de Justice Paris
5. `http://127.0.0.1:47388/ar/countries/morocco/` — RTL preserved
6. `http://127.0.0.1:47388/methodology/` — banner uffici legali
7. `http://127.0.0.1:47388/wizard/` — banner consultazione studio
8. `http://127.0.0.1:47388/contact/` — banner consultazione cliente

**Screenshot before** (pass2 senza polish, ma con immagini fetched):
- `01_home.png` (hero banner separato)

**Screenshot after** (pass2 finale):
- `01_home_pass2.png` — hero backdrop unificato
- `02_countries_pass2_v2.png` — cards con immagini paese
- `03_methodology.png` — banner editoriale
- `04_italy_landing.png` — hero Palazzo Roma + traduzione IT
- `05_wizard.png` — banner uffici
- `06_contact.png` — banner consulenza
- `07_ar_morocco_rtl.png` — RTL flip
- `08_fr_france.png` — FR traduzioni dense

---

## 6. Conferma nessuna attribution visibile

Test `test_pass2_no_visible_pexels_attribution` su 10 paths × 2
controlli = 20 verifiche → tutte verdi. Helper
`attribution_for_entry()` resta in `apps/core/pexels.py` per uso
interno futuro (audit, credits page, ecc.).

---

## 7. API key non esposta

Test `test_pass2_api_key_never_appears` con valore stringente
"PASS2-SECRET-KEY-NEVER-LEAK-XYZABC123" su 10 paths → mai trovata.
La key di sessione è stata usata SOLO come env var inline al
`fetch_pexels_site_images`; nessun commit, nessun file la contiene.

---

## 8. Nessun DB change legale

`makemigrations --check` → "No changes detected". Niente touch a
LegalReview/CompensationDataset/CalculationFormula/engine. Niente
import CSV.

---

## 9. Italia invariata

`test_pass2_italy_smoke_run_simulation_35_10_0` verde →
26 268 / 27 353 / 28 439 EUR ✅.

---

## 10. Check / lint

- `manage.py makemigrations --check` → No changes detected
- `manage.py check` → 0 issues
- `pytest -q` → **665 passed in 30s** (era 621 → +44 nuovi)
- `ruff check .` → All checks passed
- `black --check .` → 204 files unchanged

---

## 11. Prossimo step consigliato

**F-product-i18n-translations-pass3-validation**: validazione delle
138 traduzioni esistenti da parte di un madrelingua arabo + revisione
legale Studio per i termini sensibili (compensation/indemnisation/
تعويض, jurisdiction/اختصاص, …); tradurre i restanti ~459 msgid che
sono prevalentemente admin/model labels (visibili solo a staff).

Subito dopo: **F-product-pexels-curation**: alcune query (es.
"Morocco architecture courthouse" ha restituito un courthouse
**danese**) producono foto fuori contesto. Curare le query o
aggiungere un meccanismo di selezione manuale (`--photo-id` per
slot).