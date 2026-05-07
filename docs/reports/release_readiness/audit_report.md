# Product release-readiness audit — pass 1

- base URL: `http://127.0.0.1:48107`
- pages probed: 78
- pages with issues: 0
- IT baseline 35/10/0: **OK** (amounts=True, PDF first-4='%PDF')
- FR/BE/MA/TN unavailable fixtures: **4/4 pass**
- Legal DB counts unchanged: **True**
- VERDICT: **OK**

## Page checks

| Locale | Path | HTTP | Local CSS | Tailwind CDN | Banned | EN fallback | H1 | Meta | Pexels | API leak |
| --- | --- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| `it` | `/` | — | — | — | — | — | — | — | — | — |
| `it` | `/countries/` | — | — | — | — | — | — | — | — | — |
| `it` | `/countries/italy/` | — | — | — | — | — | — | — | — | — |
| `it` | `/countries/france/` | — | — | — | — | — | — | — | — | — |
| `it` | `/countries/belgium/` | — | — | — | — | — | — | — | — | — |
| `it` | `/countries/morocco/` | — | — | — | — | — | — | — | — | — |
| `it` | `/countries/tunisia/` | — | — | — | — | — | — | — | — | — |
| `it` | `/case-types/` | — | — | — | — | — | — | — | — | — |
| `it` | `/methodology/` | — | — | — | — | — | — | — | — | — |
| `it` | `/wizard/` | — | — | — | — | — | — | — | — | — |
| `it` | `/wizard/it/road-accident/` | — | — | — | — | — | — | — | — | — |
| `it` | `/wizard/fr/road-accident/` | — | — | — | — | — | — | — | — | — |
| `it` | `/wizard/be/road-accident/` | — | — | — | — | — | — | — | — | — |
| `it` | `/wizard/ma/inheritance/` | — | — | — | — | — | — | — | — | — |
| `it` | `/wizard/tn/inheritance/` | — | — | — | — | — | — | — | — | — |
| `it` | `/contact/` | — | — | — | — | — | — | — | — | — |
| `it` | `/contact/thank-you/` | — | — | — | — | — | — | — | — | — |
| `it` | `/privacy/` | — | — | — | — | — | — | — | — | — |
| `it` | `/disclaimer/` | — | — | — | — | — | — | — | — | — |
| `it` | `/sitemap.xml` | — | — | — | — | — | — | — | — | — |
| `it` | `/healthz/` | — | — | — | — | — | — | — | — | — |
| `fr` | `/` | — | — | — | — | — | — | — | — | — |
| `fr` | `/countries/` | — | — | — | — | — | — | — | — | — |
| `fr` | `/countries/italy/` | — | — | — | — | — | — | — | — | — |
| `fr` | `/countries/france/` | — | — | — | — | — | — | — | — | — |
| `fr` | `/countries/belgium/` | — | — | — | — | — | — | — | — | — |
| `fr` | `/countries/morocco/` | — | — | — | — | — | — | — | — | — |
| `fr` | `/countries/tunisia/` | — | — | — | — | — | — | — | — | — |
| `fr` | `/case-types/` | — | — | — | — | — | — | — | — | — |
| `fr` | `/methodology/` | — | — | — | — | — | — | — | — | — |
| `fr` | `/wizard/` | — | — | — | — | — | — | — | — | — |
| `fr` | `/wizard/it/road-accident/` | — | — | — | — | — | — | — | — | — |
| `fr` | `/wizard/fr/road-accident/` | — | — | — | — | — | — | — | — | — |
| `fr` | `/wizard/be/road-accident/` | — | — | — | — | — | — | — | — | — |
| `fr` | `/wizard/ma/inheritance/` | — | — | — | — | — | — | — | — | — |
| `fr` | `/wizard/tn/inheritance/` | — | — | — | — | — | — | — | — | — |
| `fr` | `/contact/` | — | — | — | — | — | — | — | — | — |
| `fr` | `/contact/thank-you/` | — | — | — | — | — | — | — | — | — |
| `fr` | `/privacy/` | — | — | — | — | — | — | — | — | — |
| `fr` | `/disclaimer/` | — | — | — | — | — | — | — | — | — |
| `ar` | `/` | — | — | — | — | — | — | — | — | — |
| `ar` | `/countries/` | — | — | — | — | — | — | — | — | — |
| `ar` | `/countries/italy/` | — | — | — | — | — | — | — | — | — |
| `ar` | `/countries/france/` | — | — | — | — | — | — | — | — | — |
| `ar` | `/countries/belgium/` | — | — | — | — | — | — | — | — | — |
| `ar` | `/countries/morocco/` | — | — | — | — | — | — | — | — | — |
| `ar` | `/countries/tunisia/` | — | — | — | — | — | — | — | — | — |
| `ar` | `/case-types/` | — | — | — | — | — | — | — | — | — |
| `ar` | `/methodology/` | — | — | — | — | — | — | — | — | — |
| `ar` | `/wizard/` | — | — | — | — | — | — | — | — | — |
| `ar` | `/wizard/it/road-accident/` | — | — | — | — | — | — | — | — | — |
| `ar` | `/wizard/fr/road-accident/` | — | — | — | — | — | — | — | — | — |
| `ar` | `/wizard/be/road-accident/` | — | — | — | — | — | — | — | — | — |
| `ar` | `/wizard/ma/inheritance/` | — | — | — | — | — | — | — | — | — |
| `ar` | `/wizard/tn/inheritance/` | — | — | — | — | — | — | — | — | — |
| `ar` | `/contact/` | — | — | — | — | — | — | — | — | — |
| `ar` | `/contact/thank-you/` | — | — | — | — | — | — | — | — | — |
| `ar` | `/privacy/` | — | — | — | — | — | — | — | — | — |
| `ar` | `/disclaimer/` | — | — | — | — | — | — | — | — | — |
| `en` | `/` | — | — | — | — | — | — | — | — | — |
| `en` | `/countries/` | — | — | — | — | — | — | — | — | — |
| `en` | `/countries/italy/` | — | — | — | — | — | — | — | — | — |
| `en` | `/countries/france/` | — | — | — | — | — | — | — | — | — |
| `en` | `/countries/belgium/` | — | — | — | — | — | — | — | — | — |
| `en` | `/countries/morocco/` | — | — | — | — | — | — | — | — | — |
| `en` | `/countries/tunisia/` | — | — | — | — | — | — | — | — | — |
| `en` | `/case-types/` | — | — | — | — | — | — | — | — | — |
| `en` | `/methodology/` | — | — | — | — | — | — | — | — | — |
| `en` | `/wizard/` | — | — | — | — | — | — | — | — | — |
| `en` | `/wizard/it/road-accident/` | — | — | — | — | — | — | — | — | — |
| `en` | `/wizard/fr/road-accident/` | — | — | — | — | — | — | — | — | — |
| `en` | `/wizard/be/road-accident/` | — | — | — | — | — | — | — | — | — |
| `en` | `/wizard/ma/inheritance/` | — | — | — | — | — | — | — | — | — |
| `en` | `/wizard/tn/inheritance/` | — | — | — | — | — | — | — | — | — |
| `en` | `/contact/` | — | — | — | — | — | — | — | — | — |
| `en` | `/contact/thank-you/` | — | — | — | — | — | — | — | — | — |
| `en` | `/privacy/` | — | — | — | — | — | — | — | — | — |
| `en` | `/disclaimer/` | — | — | — | — | — | — | — | — | — |

## Italia 35/10/0 baseline

- result URL: `http://127.0.0.1:48107/wizard/result/e5bea52d-ee6a-47af-a866-ed8973b40364/`
- amounts present (`26268, 27353, 28439` EUR): `True`
- public status calculated: `True`
- PDF status: `200`
- PDF first 4 bytes: `'%PDF'`

## FR/BE/MA/TN unavailable fixtures

| Label | Result URL | Status | Leaks | Has amounts |
| --- | --- | :-: | --- | :-: |
| `fr_road_accident` | `http://127.0.0.1:48107/wizard/result/5cbc91e9-a07e-488f-9eea-a6018ae1e491/` | OK | — | — |
| `be_road_accident` | `http://127.0.0.1:48107/wizard/result/c1d8c063-28ed-431f-9f99-518bd5b858bb/` | OK | — | — |
| `ma_inheritance` | `http://127.0.0.1:48107/wizard/result/0a2d2fff-def0-4a83-bab5-e8aee1d3b584/` | OK | — | — |
| `tn_inheritance` | `http://127.0.0.1:48107/wizard/result/345e322b-c889-46ea-9646-b9b12f801e40/` | OK | — | — |

## Legal data invariants

- before: `{'legal_sources': 25, 'datasets': 5, 'formulas': 1, 'rows': 41309}`
- after:  `{'legal_sources': 25, 'datasets': 5, 'formulas': 1, 'rows': 41309}`
- unchanged: `True`

