# Staging deploy — Studio Legale Badrane LegalTech

> Guida step-by-step per portare il sistema su un host staging accessibile
> via HTTPS, dietro auth basic / IP allowlist. NON è una guida prod-go-live:
> per quella servono cookie consent, MFA, monitoring, email transactional
> (vedi `PRODUCTION_PREFLIGHT.md`).

## 0. Prerequisiti

Sull'host staging:

- Docker Engine ≥ 24 + `docker compose` plugin (v2.x).
- Almeno 2 GB RAM / 1 CPU / 10 GB disk (con margine per backup).
- DNS già puntato (es. `staging.studiolegalebadrane.it` → IP host).
- Reverse-proxy esterno (nginx/traefik) con TLS — questo guide non lo
  configura ma assume che il proxy faccia `proxy_pass` alla porta
  8000 del container `web`.
- Accesso SSH all'host.

In repository (sul tuo laptop o sull'host dopo `git clone`):

- `legal_data/sources/italy/tun_2025/dpr_12_2025_tun.pdf` (PDF G.U.,
  SHA-256 `74d4d4f7…`).
- `legal_data/sources/italy/tun_2025/tun_2025_rows.csv` (9 191 righe,
  prodotto da review assistita o da estrazione diretta).
- Nessuno dei due viene committato: vanno trasferiti via canale sicuro
  (rsync su SSH, S3 cifrato, ecc.).

## 1. Clone del repo sull'host

```bash
git clone <repo-url> /opt/badrane-legaltech
cd /opt/badrane-legaltech
```

## 2. Configurazione `.env.staging`

```bash
cp .env.staging.example .env.staging
```

Apri `.env.staging` e popola:

- `DJANGO_SECRET_KEY`: 50 caratteri random.
  ```bash
  python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
  ```
- `DJANGO_ALLOWED_HOSTS`: hostname pubblico (e `127.0.0.1,localhost` se
  serve testare dal container).
- `DJANGO_CSRF_TRUSTED_ORIGINS`: l'URL HTTPS del proxy esterno.
- `POSTGRES_PASSWORD`: 32+ caratteri random (`secrets.token_urlsafe(32)`).
- Lascia gli altri valori di default (sono pensati per staging).

Permessi:
```bash
chmod 600 .env.staging
chown root:root .env.staging   # o utente che gira docker
```

## 3. Trasferimento PDF + CSV

Sul tuo laptop:

```bash
# PDF
scp legal_data/sources/italy/tun_2025/dpr_12_2025_tun.pdf \
    user@staging:/opt/badrane-legaltech/legal_data/sources/italy/tun_2025/

# CSV
scp legal_data/sources/italy/tun_2025/tun_2025_rows.csv \
    user@staging:/opt/badrane-legaltech/legal_data/sources/italy/tun_2025/
```

Sull'host, verifica l'hash del PDF:
```bash
sha256sum legal_data/sources/italy/tun_2025/dpr_12_2025_tun.pdf
# Atteso: 74d4d4f7b4154694bbb47e0257d9d6f7e663f21348fa4bc9346065eb06b82c92
```

## 4. Build + start

Linux/macOS:
```bash
./scripts/staging/up.sh
```

Windows PowerShell:
```powershell
.\scripts\staging\up.ps1
```

Equivalenza diretta:
```bash
docker compose -f docker-compose.staging.yml --env-file .env.staging up -d --build
```

Verifica health:
```bash
docker compose -f docker-compose.staging.yml ps
docker compose -f docker-compose.staging.yml logs -f web   # Ctrl+C per uscire
```

Atteso: `db` e `web` entrambi `Up (healthy)`. Il `command` del web fa
`migrate` + `collectstatic` automaticamente al primo avvio.

## 5. Bootstrap iniziale

### Crea superuser staff
```bash
./scripts/staging/manage.sh createsuperuser
```

### Bootstrap dati TUN (one-shot)
```bash
./scripts/staging/bootstrap_italy_tun.sh
```

Lo script esegue:
1. `seed_jurisdictions` (paesi/lingue/valute MVP).
2. `seed_italy_legal_sources` (5 fonti italiane core, status `needs_review`).
3. `import_italy_tun_2025 --source-file <PDF>` (allega PDF + crea
   `CompensationDataset` DRAFT + `CalculationFormula` DRAFT).
4. `import_italy_tun_2025 --csv <CSV>` (importa 9 191 righe).

Stato atteso al termine: source `needs_review`, dataset `draft`, formula
`draft`, righe 9 191. Il calculator pubblico restituisce
`unavailable_requires_legal_validation` perché manca l'approvazione.

## 6. Approvazione legale (atto umano)

### 6.1. Configura `formula.parameters` runtime

Via admin Django (https://staging.../admin/) → CalculationFormula → pk
della formula `italy_art_138_tun_2025_base` → campo `parameters`:

```json
{
  "engine": "italy_tun_point_value_v1",
  "requires": ["victim_age", "permanent_disability_percentage"],
  "row_match": ["victim_age", "permanent_disability_percentage"],
  "amount_rule": "row_amount_direct",
  "fault_reduction": true
}
```

### 6.2. Crea `LegalReview` + promuovi status

Da admin (preferito per audit) o da shell:

```bash
./scripts/staging/manage.sh shell
```

```python
from datetime import date
from apps.legal_sources.models import LegalSource, LegalReview
from apps.legal_sources.enums import SourceStatus
from apps.compensation.models import CompensationDataset, CalculationFormula, DatasetStatus
from apps.accounts.models import User

reviewer = User.objects.get(username="<your-superuser>")
src = LegalSource.objects.get(slug="it-dpr-12-2025-tun-danno-biologico")

LegalReview.objects.create(
    source=src, reviewer=reviewer,
    decision=LegalReview.Decision.APPROVE,
    previous_status=src.status,
    new_status=SourceStatus.APPROVED,
    comment="Formal Studio approval — staging deploy.",
)

src.status = SourceStatus.APPROVED
src.legal_reviewer = reviewer
src.last_checked_at = date.today()
src.save(update_fields=["status", "legal_reviewer", "last_checked_at"])

ds = CompensationDataset.objects.get(version_label="DPR-12-2025")
ds.status = DatasetStatus.APPROVED
ds.save(update_fields=["status"])

fm = CalculationFormula.objects.get(code="italy_art_138_tun_2025_base")
fm.status = DatasetStatus.APPROVED
fm.save(update_fields=["status"])
```

### 6.3. Smoke test post-approval

```bash
./scripts/staging/smoke.sh
```

Atteso:
```
status: calculated
estimated_min/mid/max: 21709.0000 / 21709.0000 / 21709.0000
SMOKE PASSED.
```

## 7. Verifica funnel pubblico via browser

Dal proxy HTTPS (es. `https://staging.studiolegalebadrane.it`):

1. **Home `/`** → layout premium, multilingua switcher.
2. **`/wizard/it/road-accident/`** → form 9 campi.
3. Compila `victim_age=35, permanent_disability_percentage=10, fault_percentage=0`,
   spunta consenso, submit.
4. **Result page** → "Stima disponibile" con MIN/MID/MAX = 21.709,00 EUR,
   sources cita "D.P.R. 13 gennaio 2025, n. 12".
5. **PDF download** → 200 application/pdf (~6 KB).
6. **`/contact/?sim=<uuid>`** → form precompilato → submit → thank-you.
7. **`/staff/project-status/`** (login admin) → snapshot live.

## 8. Backup

### DB Postgres
```bash
./scripts/staging/backup_db.sh
# → backups/staging_<ts>.sql
```

Schedula via cron (ogni notte):
```cron
0 2 * * * cd /opt/badrane-legaltech && ./scripts/staging/backup_db.sh
```

E sposta il file su storage off-site (S3 cifrato, Backblaze B2, ecc.).

### Media (PDF reports + LegalSourceAttachment)
```bash
docker run --rm \
    -v badrane-legaltech_media_data:/data:ro \
    -v $(pwd)/backups:/backup \
    alpine sh -c "tar czf /backup/media_$(date +%Y%m%d_%H%M%S).tar.gz -C /data ."
```

### Export approved (snapshot dati legali)
```bash
./scripts/staging/export_approved.sh
# → legal_data/exports/italy_tun_2025_<ts>.json (~4.6 MB)
```

Trasferisci off-site come per il DB dump.

## 9. Update / redeploy

```bash
git pull
./scripts/staging/up.sh   # rebuild + restart
```

Il command del web fa `migrate` automatico. Se servono nuove env:
edita `.env.staging` prima di `up.sh`.

## 10. Rollback

### Application code
```bash
git log --oneline -10
git checkout <previous-commit>
./scripts/staging/up.sh
```

### Database
```bash
# Spegni il web container (lascia db acceso).
docker compose -f docker-compose.staging.yml stop web

# Restore (CONFERMA prima — sovrascrive il DB):
cat backups/staging_<ts>.sql | docker compose -f docker-compose.staging.yml \
    exec -T db psql -U badrane badrane_staging

docker compose -f docker-compose.staging.yml start web
```

### Media volume
```bash
docker compose -f docker-compose.staging.yml stop web
docker run --rm \
    -v badrane-legaltech_media_data:/data \
    -v $(pwd)/backups:/backup \
    alpine sh -c "rm -rf /data/* && tar xzf /backup/media_<ts>.tar.gz -C /data"
docker compose -f docker-compose.staging.yml start web
```

## 11. Health monitoring (minimo)

L'host deve almeno controllare:

- `curl -fsS https://staging.../` → 200
- `curl -fsS https://staging.../wizard/` → 200
- Disk usage del volume `media_data` (crescita PDF reports)
- Disk usage del volume `postgres_data`
- Backup giornaliero esistente e con dimensione > 0

In prod servirà Sentry + uptime monitor (es. Uptime Kuma) — vedi
`PRODUCTION_PREFLIGHT.md`.

## 12. Cosa NON fa questo guide

- ❌ Configurazione nginx/traefik/Caddy con TLS (responsabilità DevOps).
- ❌ Cookie consent banner EU (richiesto per prod pubblica).
- ❌ MFA admin (richiesto per prod).
- ❌ Email transactional (Studio non riceve notifica Lead in staging).
- ❌ Rate-limit sui POST pubblici.
- ❌ Backup off-site automatizzato verso cloud.

Tutti questi punti sono nel preflight `PRODUCTION_PREFLIGHT.md` e vanno
chiusi prima di esporre il sistema a utenti pubblici reali.

## 13. Smoke test rapido (tutto-in-uno)

Dopo `up.sh` + `bootstrap_italy_tun.sh` + approval umana §6, esegui:

```bash
./scripts/staging/smoke.sh
./scripts/staging/export_approved.sh
./scripts/staging/backup_db.sh
```

Se tutti e tre tornano `OK` con file di output non vuoti, la staging è
in stato sano e il primo backup è già fuori dal container.
