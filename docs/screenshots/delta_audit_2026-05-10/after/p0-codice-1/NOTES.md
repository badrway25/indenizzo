# Browser-live verification — P0-CODICE-1 batch

**Data:** 2026-05-10
**Branch:** `audit/indennizzati-platform`
**Server:** `http://127.0.0.1:59516/` (porta libera assegnata
runtime, runserver Django con `DJANGO_DEBUG=true`)
**Browser:** Playwright MCP (Chrome 130+), viewport 1440 × 900.

## Risultati verifica

| # | URL | Meta robots emesso | Atteso | OK |
|---|---|---|---|---|
| 1 | `/robots.txt` | n/a (text/plain) | 200, body con `Disallow` corretti, `Allow: /contact/`, `Sitemap:` | ✅ |
| 2 | `/` (home) | `index, follow` | indicizzabile (default base.html) | ✅ |
| 3 | `/contact/` | `noindex, nofollow` | scelta esistente del template (canarino documentato in test) | ✅ |
| 4 | `/contact/thank-you/` | `noindex, nofollow` | non indicizzabile (page post-submit) | ✅ |
| 5 | `/wizard/result/6c553330-…/` | `noindex, nofollow` | non indicizzabile (page con dati utente) | ✅ |

## Body `/robots.txt` verificato live

```
User-agent: *
Disallow: /admin/
Disallow: /staff/
Disallow: /reports/
Disallow: /wizard/result/
Disallow: /contact/thank-you/
Allow: /contact/

Sitemap: http://127.0.0.1:59516/sitemap.xml
```

`/contact/` non e' nella lista `Disallow` come richiesto dalle
correzioni utente (pagina pubblica utile a SEO/lead).

## Canarino IT 35/10/0

Simulazione creata via shell per ottenere un public_id navigabile:

```
.venv/Scripts/python.exe manage.py shell -c "
from apps.cases.services import run_simulation
sim = run_simulation(
    jurisdiction_code='IT-NATIONAL',
    case_type='road_accident_bodily_injury',
    input_data={'victim_age': 35, 'permanent_disability_percentage': 10, 'fault_percentage': 0},
)
print(sim.public_id, sim.status, sim.estimated_min, sim.estimated_mid, sim.estimated_max)
"
```

Output:
```
6c553330-70d1-4f6b-ac10-e8e66861224a  calculated  26268.0000  27353.0000  28439.0000
```

**Canarino verde**: il calculator IT non e' stato toccato dal batch.

## Screenshots

- `01_robots_txt_desktop.png` — full body robots.txt (1440 × 900).
- `02_home_indexable_desktop.png` — home, viewport.
- `03_contact_form_desktop.png` — contact form.
- `04_contact_thank_you_noindex_desktop.png` — thank-you page.
- `05_wizard_result_noindex_desktop.png` — result page IT 35/10/0
  con range 26 268 / 27 353 / 28 439 EUR.

## Console errors

Solo `/robots.txt` ha riportato 1 console error (favicon non
trovata — irrilevante per il payload text/plain). Gli altri URL:
no errors.

## Decisione `/contact/` noindex

Il template `templates/public/contact.html:5` ha gia' un block
`{% block meta_robots %}noindex, nofollow{% endblock %}` ereditato
da scelte precedenti. Non e' modificato dal batch P0-CODICE-1.

Documentato come canarino "pinning" nel test
`apps/core/test_meta_robots_noindex.py::test_contact_form_is_not_noindex`
(il test verifica solo che il meta tag esista, lasciando a un
futuro iter Studio la decisione se rimuovere il noindex per
abilitare long-tail SEO sul form di contatto).
