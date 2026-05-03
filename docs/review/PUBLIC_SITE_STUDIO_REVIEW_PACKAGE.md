# Public site — Studio review package (F-product-studio-review-package-public-site)

Stato: aperto 2026-05-03.
Owner tecnico: piattaforma.
Owner legale: Studio Legale Internazionale Badrane.

Pacchetto di review umana per il sito pubblico in stato pre-pre-deploy
(post pass2 a11y/SEO). **Nessun nuovo polish tecnico** in questa
iterazione: scopo è raccogliere il segnale legale/redazionale
dello Studio prima di mostrarlo a un cliente esterno.

---

## 1. Cosa stiamo chiedendo allo Studio

Tre cose, in ordine di priorità:

1. **Validare il wording legale** (IT/FR/AR) sulle pagine pubbliche.
   In particolare: nessuna promessa di outcome, nessun claim non
   dimostrabile, terminologia giuridica corretta nelle 3 lingue.
2. **Approvare le immagini Pexels** scelte come hero/country card.
   Il manifest interno cataloga photographer + URL, ma l'**utente
   finale non vede attribution**: la scelta del soggetto deve
   trasmettere autorevolezza (no foto dating, no foto generiche di
   "successo finanziario").
3. **Confermare i NO-GO** prima di mostrare a un cliente esterno
   (vedi sezione 7).

Lo Studio **non deve** validare in questo pass dataset legali, formule
o tabelle: quei materiali sono fuori scope (vedi
`docs/architecture/MOROCCO_INHERITANCE_MODULE_STATUS.md`,
`TUNISIA_INHERITANCE_MODULE_STATUS.md`, e i `LegalReview` su Italia).

---

## 2. Server live

URL: `http://127.0.0.1:31452/`

Stato: avviato 2026-05-03 per la sessione di review (porta riusata
dalle pass1/pass2 per consistenza handover). Background task id:
`bbzvq2gbk`. PID al momento del package: 19200.

| Path | Lang | Note |
|------|------|------|
| `/` | IT | home, hero image-as-backdrop |
| `/fr/` | FR | home FR (marker pass1: "Cabinet Légal International") |
| `/ar/` | AR | home AR (RTL) — **traduzione non ancora native-validated** |
| `/countries/` | IT | coverage map |
| `/countries/italy/` | IT | landing operativa (TUN 2025 approved) |
| `/countries/france/` | FR (default IT) | landing under review |
| `/countries/belgium/` | FR (default IT) | landing under review |
| `/countries/morocco/` | FR (default IT) | landing under review |
| `/ar/countries/morocco/` | AR | landing AR — **non native-validated** |
| `/countries/tunisia/` | FR (default IT) | landing under review |
| `/wizard/` | IT | wizard start |
| `/wizard/it/road-accident/` | IT | wizard Italia operativo |
| `/wizard/fr/road-accident/` | FR | wizard scaffold |
| `/wizard/be/road-accident/` | FR | wizard scaffold |
| `/wizard/ma/inheritance/` | FR | wizard scaffold |
| `/wizard/tn/inheritance/` | FR | wizard scaffold |
| `/contact/` | IT | form review request |
| `/contact/thank-you/` | IT | post-submit |
| `/methodology/` | IT | how we work |
| `/privacy/` | IT | privacy notice (**da approvare**) |
| `/disclaimer/` | IT | disclaimer (**da approvare**) |
| `/sitemap.xml` | — | XML sitemap |

Per fermare il server quando la sessione è chiusa:

```powershell
powershell -Command "Stop-Process -Id 19200 -Force"
```

---

## 3. Checklist operativa (CSV committabile)

Path: `legal_data/review/public_site_review_checklist_template.csv`.

96 righe, 19 aree:

| area | righe | note |
|------|------:|------|
| home | 9 | IT/FR/AR |
| countries_index | 8 | inclusi badge + Pexels + roadmap |
| country_landing | 20 | 5 country × disclaimer/sources/CTA |
| wizard | 2 | wizard start |
| wizard_italy | 6 | inclusi PDF + risultato |
| wizard_france | 3 | scaffold |
| wizard_belgium | 2 | scaffold |
| wizard_morocco | 3 | scaffold + AR |
| wizard_tunisia | 2 | scaffold |
| contact | 7 | IT/FR/AR + thank-you |
| privacy | 2 | da approvare |
| disclaimer | 2 | da approvare |
| cookie | 1 | banner |
| pexels | 7 | 5 country + license |
| translations | 4 | FR + AR + methodology |
| legal_tone | 3 | IT/FR/AR |
| no_claim_under_review | 8 | FR/BE/MA/TN landing + wizard |
| seo | 4 | sitemap / canonical / robots / meta description |
| a11y | 3 | skip / contrast / lang switcher mobile |

Schema delle colonne:

| Colonna | Esempio | Vincoli |
|---------|---------|---------|
| `area` | `country_landing` | tassonomia interna |
| `page_url` | `/countries/italy/` | path live (oppure tag tipo `license`) |
| `language` | `it` / `fr` / `ar` | ISO 639-1 |
| `review_item` | "Riferimento TUN 2025…" | descrizione del check |
| `current_status` | `delivered_pass1` / `approved_dataset` / `needs_native_review` / `needs_studio_validation` / `engine_contract_pass2` / `delivered_pass2` / `delivered_pass3` / `delivered_pass4` | stato consegna tecnica |
| `reviewer` | "" | nome reviewer Studio (compilare) |
| `status` | `pending` | iniziale; ammessi: `pending` / `approved` / `change_requested` / `rejected` / `not_applicable` |
| `notes` | "blocking before external client" | testo libero |
| `reviewed_at` | "" | ISO date al momento della review |

**Workflow consigliato**

1. Lo Studio apre il CSV (Excel / LibreOffice / Numbers).
2. Per ogni riga compila `reviewer`, aggiorna `status` a uno dei
   valori consentiti, scrive eventuali `notes`, mette `reviewed_at`
   in formato `YYYY-MM-DD`.
3. Il CSV review compilato torna nella stessa cartella con suffisso
   data, es. `public_site_review_checklist_2026-05-10.csv` (il
   `_template.csv` resta sempre vuoto come baseline).
4. Lo script `scripts/qa_public_site_review_package.py` valida che
   gli `status` restino fra i valori ammessi.

---

## 4. Funnel critici da provare durante la review

Suggerito di toccarli a mano con i 3 browser FR/IT/AR:

1. **Italia 35/10/0 happy path**
   ```
   /  →  CTA hero "Avvia simulazione risarcimento Italia"
   →  /wizard/it/road-accident/
   →  age=35, disability=10%, fault=0%, consent ON
   →  /wizard/result/<uuid>/    range 26 268 / 27 353 / 28 439 EUR
   →  PDF download                application/pdf, ~6 KB
   ```

2. **France under review path**
   ```
   /fr/  →  /fr/countries/france/
   →  CTA "Open France validation wizard"
   →  /wizard/fr/road-accident/
   →  POST con consent
   →  pagina ritorna "requires legal validation" (mai numero EUR)
   ```

3. **Morocco AR**
   ```
   /ar/  →  /ar/countries/morocco/  (RTL)
   →  CTA wizard inheritance
   →  /wizard/ma/inheritance/
   →  POST con consent → "requires legal validation"
   ```

4. **Contact**
   ```
   /  →  header CTA "Request legal review"
   →  /contact/  → form + privacy ON
   →  /contact/thank-you/   "Grazie / La tua richiesta è stata ricevuta"
   ```

---

## 5. Screenshot già prodotti

Tutti in `docs/screenshots/live_qa/`. Per la review usare le serie più
recenti (pass2 sostituisce gli artefatti pass1 dove sovrapposti).

### Pass2 (current — F-product-public-site-qa-polish-pass2-a11y-seo)

Path: `docs/screenshots/live_qa/public_site_qa_polish_pass2/`

```
01_home_it_desktop.png            06_wizard_start_desktop.png
02_countries_desktop.png          07_contact_desktop.png
03_country_france_fr_desktop.png  08_methodology_desktop.png
04_country_morocco_ar_desktop.png 09_country_italy_desktop.png
05_wizard_it_form_desktop.png

m01_country_italy_mobile.png      m04_country_morocco_ar_mobile.png
m02_home_mobile.png               m05_wizard_it_form_mobile.png
m03_countries_mobile.png
```

14 PNG (9 desktop 1280×900 + 5 mobile 390×844).

### Pass1 (baseline — F-product-public-site-qa-polish-pass1)

Path: `docs/screenshots/live_qa/public_site_qa_polish_pass1/`

22 PNG inclusi i funnel `15_italy_result_desktop.png` e
`16_contact_thank_you_desktop.png` (post-submit) — utili per
verificare le pagine result e thank-you che il pass2 non ha
ricatturato.

### Premium visual + i18n + country landing pass3/4

Cataloghi storici in:
- `docs/screenshots/live_qa/premium_visual_i18n_pass2/`
- `docs/screenshots/live_qa/i18n_translations_pass3/`
- `docs/screenshots/live_qa/country_landing_pass3/`
- `docs/screenshots/live_qa/country_landing_pass4/`

Da consultare se serve confrontare la traiettoria visiva.

---

## 6. Materiali tecnici di riferimento (read-only per la review)

| File | Cosa contiene |
|------|---------------|
| `docs/architecture/PRODUCT_REQUIREMENTS.md` | I 6 requisiti permanenti di prodotto |
| `docs/architecture/PUBLIC_SITE_QA_POLISH_PASS1.md` | Snapshot QA pass1 (wording, traduzioni) |
| `docs/architecture/PUBLIC_SITE_QA_POLISH_PASS2.md` | Snapshot QA pass2 (a11y, SEO) |
| `docs/architecture/MOROCCO_INHERITANCE_MODULE_STATUS.md` | Stato fonti MA |
| `docs/architecture/TUNISIA_INHERITANCE_MODULE_STATUS.md` | Stato fonti TN |
| `templates/public/*.html` | Tutti i template pubblici |
| `apps/core/views.py:_country_landing_context` | Mapping country → status / sources / wizard |
| `media/pexels/pexels_manifest.json` | Manifest Pexels (photographer, URL — interno) |
| `legal_data/sources/it/dpr-12-2025/` | Pacchetto Italia approvato (TUN 2025) |

---

## 7. NO-GO prima di mostrare a un cliente esterno

I cinque blocker che impediscono ad oggi di mostrare il sito a un
soggetto fuori dal team:

### 7.1 — Traduzioni AR non native-validated

**Stato**: pass3 ha portato la copertura traduzioni AR > 80% sui
template pubblici, ma **nessun native speaker giurista** ha ancora
firmato il lessico. Rischio: terminologia legale arabo-classica
imprecisa (es. successioni, danno biologico, indemnité).

**Azione**: review da giurista madrelingua AR (preferibilmente
maghrebino) sulle 4 pagine `/ar/`, `/ar/countries/morocco/`,
`/ar/contact/`, `/ar/methodology/`.

**Dipende da**: identificazione del reviewer.

### 7.2 — FR/BE/MA/TN non devono sembrare calculator attivi

**Stato**: i wizard scaffold rispondono "requires legal validation"
e i test pass1 #6 / pass2 garantiscono che il POST non ritorni
cifre. Il rischio non è tecnico — è di **percezione**: la presenza
del form completo per un paese non operativo può dare l'impressione
che il calculator esista già.

**Azione**: lo Studio decide se va aggiunto un banner ancora più
esplicito ("nessuna stima è prodotta per questo paese, il modulo è
in fase di catalogazione") oppure se la combinazione attuale (status
badge + introduction box "Module under legal validation") è
sufficiente.

**Riferimento test**:
- `apps/core/test_public_site_qa_polish_pass1.py::test_under_review_wizards_never_show_calculated_amount`
- `apps/core/test_public_site_qa_polish_pass2.py::test_no_remote_pexels_image_url`

### 7.3 — Immagini paese da approvare

**Stato**: 5 country card hanno una foto Pexels ciascuna, scelta in
pass `pexels-curation-pass1` con criteri "no dating / no salesy /
sobrio". Nessuna foto è stata però approvata formalmente dallo
Studio.

**Azione**: lo Studio guarda le 5 immagini in
`media/pexels/country_landing__*.jpg` e ne firma l'uso.
Se una foto va sostituita, indicare il replacement nel campo `notes`
del CSV; il pipeline `manage.py fetch_pexels_site_images` può
essere rilanciato con un override per slot.

### 7.4 — Disclaimer e privacy notice da approvare

**Stato**: i template `/disclaimer/` e `/privacy/` sono presenti,
multilingua, e veicolano il messaggio "non parere / non garanzia /
solo cookie tecnici". **Nessuno dei due è stato firmato dallo
Studio** — il testo attuale è una prima approssimazione tecnica.

**Azione**: lo Studio scrive il testo definitivo (o approva
l'esistente) e lo manda al team tecnico per il drop-in nel
template. Particolare attenzione a:
- titolare del trattamento (nome, P.IVA, sede);
- diritti dell'interessato;
- retention dei dati simulazione + lead;
- riferimento alla normativa applicabile (italiana? UE?).

### 7.5 — Cookie banner / consent flow

**Stato**: banner solo per cookie tecnici (no analytics, no
marketing). Implementazione già conforme al baseline EU.

**Azione**: lo Studio conferma che la formulazione "no analytics o
marketing" è veritiera (e che lo resterà). Se in futuro si attivano
analytics, il banner va promosso a consent management con scelta
granulare.

---

## 8. Out of scope (questo pass)

- Non si modifica engine / calculator / dataset / formula.
- Non si approvano fonti legali (rimangono nel workflow `LegalReview`).
- Non si importa nessun CSV legale.
- Non si fa deploy.
- Nessun nuovo dato Pexels: usiamo la cache locale già presente.
- Nessuna chiave API esterna toccata.

Italia 35/10/0 invariato a 26 268 / 27 353 / 28 439 EUR (contratto
storico, vedi pass2 doc §5).

---

## 9. QA automatica del package

Script: `scripts/qa_public_site_review_package.py`.

Verifica (solo lettura, niente scrittura):

1. `docs/review/PUBLIC_SITE_STUDIO_REVIEW_PACKAGE.md` esiste e ha
   `# Public site — Studio review package` come prima riga.
2. `legal_data/review/public_site_review_checklist_template.csv`
   esiste, ha l'header esatto richiesto, ha `>= 50` righe e ogni
   riga ha `status` in `{pending, approved, change_requested,
   rejected, not_applicable}`.
3. La cartella `docs/screenshots/live_qa/public_site_qa_polish_pass2/`
   esiste e contiene almeno 7 file `.png` fra desktop e mobile.
4. `apps/core/test_public_site_qa_polish_pass1.py` e
   `apps/core/test_public_site_qa_polish_pass2.py` esistono (i
   contratti di non-regressione su cui poggia la review).
5. `media/pexels/pexels_manifest.json` esiste (manifest Pexels
   richiesto dalle landing).

Esecuzione:

```powershell
.venv\Scripts\python.exe scripts\qa_public_site_review_package.py
```

Exit code `0` = tutto verde. Exit code `1` = uno o più check
falliti (lo script stampa la lista delle violazioni).

---

## 10. Comandi utili

```powershell
# Server live già attivo per la review
http://127.0.0.1:31452/

# QA del package
.venv\Scripts\python.exe scripts\qa_public_site_review_package.py

# Run tests pass1 + pass2
.venv\Scripts\python.exe -m pytest apps/core/test_public_site_qa_polish_pass1.py apps/core/test_public_site_qa_polish_pass2.py -q

# Verifica dataset Italia non regredito
.venv\Scripts\python.exe -m pytest apps/core/test_public_site_qa_polish_pass2.py::test_italy_smoke_engine_preserves_pass2_contract -q

# Stop server live
powershell -Command "Stop-Process -Id 19200 -Force"
```
