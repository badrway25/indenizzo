# Production preflight — Studio Legale Badrane LegalTech

> Living checklist. Da rivedere prima di ogni deploy su staging o
> produzione. Aggiornare quando si chiude/apre un blocker.
>
> Stato corrente (2026-04-27): **NO-GO per produzione**.
> Pronto per **staging interno** dietro VPN/IP allowlist dopo aver
> chiuso i blocker P0 di sotto.

## 1. Backup / export dello stato approvato

### Snapshot DB completo (SQLite dev)
```
# Spegni il server prima del backup per evitare snapshot inconsistenti.
cp db.sqlite3 backups/db_$(date +%Y%m%d_%H%M%S).sqlite3
```

### Snapshot Postgres staging/prod
```
docker compose -f docker-compose.staging.yml exec db \
    pg_dump -U badrane badrane_staging > backups/postgres_$(date +%Y%m%d_%H%M%S).sql
```
(Schedula via cron / systemd timer / Postgres `pgbackrest` per prod.)

### Export selettivo dello stato legale approvato (no PII)

Il management command `export_italy_tun_dataset` produce un JSON
ricostruibile contenente:

- `LegalSource` (slug, status, dates, citation, ...);
- `LegalSourceAttachment` (solo metadata: filename, mime, size, sha256);
- `CompensationDataset` (status, valid_from/to, notes con audit trail);
- `CalculationFormula` (parameters runtime canonici);
- 9 191 `CompensationTableRow`;
- `LegalReview` (audit umano);
- `ExtractionLog` (audit tecnico).

ESCLUDE per design: `Simulation`, `Lead`, `ConsentRecord`,
`PrivacyAuditEvent`, `User`, `LeadEvent`, `SimulationEvent`,
`SimulationReport`, `DataDeletionRequest`. Nessun dato personale.

```
python manage.py export_italy_tun_dataset
# → legal_data/exports/italy_tun_2025_<ts>.json (gitignored)

python manage.py export_italy_tun_dataset --output /tmp/snapshot.json
```

Il file di export è grosso (~9 191 righe × ~200 byte = ~1.8 MB JSON).
Va custodito offline o in un bucket cifrato. Non committare.

### Restore (procedura riproducibile)
Se si perde lo stato DB ma si ha il PDF + CSV:

```
python manage.py migrate
python manage.py seed_jurisdictions
python manage.py seed_italy_legal_sources
python manage.py import_italy_tun_2025 --source-file legal_data/sources/italy/tun_2025/dpr_12_2025_tun.pdf
python manage.py import_italy_tun_2025 --csv legal_data/sources/italy/tun_2025/tun_2025_rows.csv
# Configurare formula.parameters runtime via admin/shell
# LegalReview + promozione status approved (atto umano dello Studio)
```

### PDF binari delle fonti (esclusi dal git)
Il PDF G.U. del D.P.R. 12/2025 vive in `legal_data/sources/italy/tun_2025/dpr_12_2025_tun.pdf`. Non è committato. Va custodito separatamente con il suo SHA-256 noto:

```
74d4d4f7b4154694bbb47e0257d9d6f7e663f21348fa4bc9346065eb06b82c92
```

## 2. Settings production-ready

`config/settings.py` è ora env-driven. In dev tutti i default restano gli stessi (SQLite, DEBUG=True, dev-only secret). In prod richiede:

| Env var | Valore prod | Note |
|---|---|---|
| `DJANGO_DEBUG` | `False` | Obbligatorio |
| `DJANGO_SECRET_KEY` | random ~50 chars | Guard difensivo: il server rifiuta di partire se rileva il default `django-insecure-...` quando `DEBUG=False` |
| `DJANGO_ALLOWED_HOSTS` | `simulatore.studiolegalebadrane.it,...` | Senza wildcard |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://simulatore.studiolegalebadrane.it` | Richiesto da Django 4+ dietro reverse proxy SSL |
| `DATABASE_URL` | `postgres://user:pass@host:5432/db` | Default fallback SQLite (per dev locale) |
| `DJANGO_SECURE_SSL_REDIRECT` | `True` (default in prod) | Forza HTTPS |
| `DJANGO_SESSION_COOKIE_SECURE` | `True` | |
| `DJANGO_CSRF_COOKIE_SECURE` | `True` | |
| `DJANGO_SECURE_HSTS_SECONDS` | `2592000` (30 giorni) | Default in prod |
| `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` | `True` | |
| `DJANGO_SECURE_HSTS_PRELOAD` | `False` finché non si è certi | Attivare dopo HSTS stabile |
| `DJANGO_SECURE_REFERRER_POLICY` | `same-origin` | |
| `LANGUAGE_CODE` | `it` | |
| `TIME_ZONE` | `Europe/Rome` | |
| `SITE_NAME` | "Simulatore Risarcimenti Studio Legale Badrane" | |
| `SITE_DOMAIN` | `simulatore.studiolegalebadrane.it` | |
| `PARENT_SITE_URL` | `https://international.studiolegalebadrane.it/` | |

In prod sono settati automaticamente:
- `SECURE_CONTENT_TYPE_NOSNIFF = True`
- `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`
- `X_FRAME_OPTIONS = "DENY"`

## 3. Postgres readiness — checklist migrazione

```
[ ] Provisioning Postgres 16 (managed o self-hosted)
[ ] DATABASE_URL configurata e raggiungibile dal web container
[ ] python manage.py migrate                 # tabelle iniziali
[ ] python manage.py createsuperuser         # account staff iniziale
[ ] python manage.py seed_jurisdictions      # paesi/lingue/valute MVP
[ ] python manage.py seed_italy_legal_sources  # 5 fonti italiane needs_review
[ ] Caricamento PDF in legal_data/sources/italy/tun_2025/ (volume montato)
[ ] python manage.py import_italy_tun_2025 --source-file <PDF>
[ ] python manage.py import_italy_tun_2025 --csv <CSV>
[ ] Formula.parameters runtime configurati via admin
[ ] LegalReview umana → promozione cumulativa a approved
[ ] Smoke test wizard: età 35, inv 10, fault 0 → 21.709 €
[ ] python manage.py export_italy_tun_dataset  # primo backup approved
[ ] Test 211/211 verdi su Postgres
```

`docker-compose.staging.yml` skeleton pronto. **Il `Dockerfile` non è
ancora committato**: vedi commento finale del compose file per la
ricetta minima.

## 4. Static / media — checklist

```
[ ] STATIC_ROOT = /app/staticfiles (volume persistente)
[ ] MEDIA_ROOT  = /app/media (volume persistente, backuppato)
[ ] python manage.py collectstatic --noinput
[ ] nginx: serve static/ e media/ direttamente (non proxy_pass al web)
[ ] media/ backup notturno (contiene PDF reports + LegalSourceAttachment)
[ ] Cifratura at-rest del volume media (filesystem o cloud)
[ ] Retention policy media (oggi assente — definire prima del go-live)
```

I `SimulationReport` PDF sono generati on-demand e salvati in
`media/reports/simulations/<sim_uuid>/...`. Crescono linearmente con il
numero di download — implementare retention policy (es. cancellazione
dopo 90 giorni) prima del go-live.

I `LegalSourceAttachment` (PDF G.U.) sono in
`media/legal_sources/<country>/<source_pk>/...` — vanno protetti con
backup forte: la perdita richiede ri-import dell'originale + nuova
legal review.

## 5. Security checklist

### Bloccanti hard (production NO-GO)

```
[ ] DJANGO_DEBUG=False in produzione
[ ] DJANGO_SECRET_KEY non default (guard runtime già attivo)
[ ] DATABASE_URL Postgres (non SQLite)
[ ] DJANGO_ALLOWED_HOSTS configurato (no wildcard)
[ ] DJANGO_CSRF_TRUSTED_ORIGINS configurato
[ ] HTTPS terminato a nginx con cert valido (Let's Encrypt)
[ ] SECURE_SSL_REDIRECT=True
[ ] SESSION_COOKIE_SECURE=True
[ ] CSRF_COOKIE_SECURE=True
[ ] HSTS attivo (30 giorni iniziali)
[ ] Backup DB schedulato + testato (restore funziona)
[ ] Backup media/ schedulato
```

### Bloccanti soft (alto rischio)

```
[ ] MFA obbligatorio sull'admin (django-otp o Auth0/SSO)
[ ] Rate-limit su POST /wizard/ /contact/ /reports/ (django-ratelimit)
[ ] WAF / DDoS protection (Cloudflare / Fastly)
[ ] Sentry / observability per error tracking
[ ] Monitoring + alerting (uptime + DB latenza)
[ ] Log retention policy (con redact PII già attivo)
```

### Best practice (raccomandati pre-go-live)

```
[ ] Cookie consent banner EU (django-cookie-consent o Cookieyes)
[ ] Email transactional configurata (Studio notification su nuovo Lead)
[ ] Tailwind CSS via build PostCSS (rimuovere CDN script)
[ ] Compilazione .mo per fr/en/ar (la UX multilingua oggi è incompleta)
[ ] Verifica accessibilità WCAG 2.1 AA su pagine pubbliche
[ ] Lighthouse audit con score ≥ 90 su Performance/SEO/A11y
[ ] robots.txt + sitemap.xml configurati
[ ] Privacy policy aggiornata e firmata dallo Studio
[ ] Data Processing Agreement con il cloud provider
[ ] Procedura di data deletion request (GDPR art. 17) testata
```

### Già implementato

- ✅ PII-aware logging (`RedactPIIFilter`)
- ✅ Honeypot anti-bot su `/wizard/` e `/contact/`
- ✅ ConsentRecord prima di ogni Simulation
- ✅ PrivacyAuditEvent su `DATA_ACCESSED`/`DATA_EXPORTED`/`DATA_DELETED`
- ✅ Auditlog su modelli sensibili
- ✅ Custom user model
- ✅ Django security middleware ordering corretto
- ✅ XFrameOptions middleware attivo
- ✅ CSRF middleware attivo

## 6. Cosa resta bloccante prima dello staging

In ordine di priorità:

| # | Item | Effort |
|---|---|---|
| P0 | `Dockerfile` per il web container | 1 ora |
| P0 | Postgres provisioning + DATABASE_URL test | 2 ore |
| P0 | Backup automatizzato DB (cron + storage off-site) | 2 ore |
| P0 | nginx + TLS (Let's Encrypt) davanti al web container | 4 ore |
| P0 | Test pytest 211/211 su Postgres (potrebbero esserci quirks JSON) | 2 ore |
| P1 | Sentry / monitoring | 2 ore |
| P1 | Rate-limit base sui POST pubblici | 1 ora |
| P1 | Cookie consent banner | 2 ore |
| P1 | Email SMTP per Lead notification | 1 ora |
| P2 | MFA admin | 4 ore |
| P2 | Tailwind PostCSS build | 4 ore |
| P2 | Compilazione .mo locales | (dipende dal volume di traduzioni) |

**Stima minima per staging accessibile via HTTPS dietro auth basic / IP
allowlist: ~1.5-2 giornate uomo.** Per produzione pubblica con SLA:
+1 settimana.

## 7. Verifica rapida pre-deploy

Eseguire dal repo root prima di ogni promozione di un nuovo build:

```
python manage.py check --deploy   # Django security audit
pytest -q                         # 211/211 atteso
ruff check .
black --check .
python manage.py export_italy_tun_dataset  # snapshot di sicurezza
```

`manage.py check --deploy` riporta i flag di sicurezza non settati;
quando passa pulito sarà uno dei segnali di go-live possibile.
