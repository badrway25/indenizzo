# POSTGRES STAGING RUNBOOK

**Branch:** `product/staging-readiness-p0`
**Data:** 2026-05-13
**Audience:** DevOps. Executable end-to-end without source-code reading.

> Postgres locale non è installato sulla macchina sviluppo Windows
> dell'audit. Il piano qui sotto è quindi operativo per DevOps
> (Linux/macOS server o container). Tutti i comandi sono validati
> contro lo stato del codice (`Dockerfile`, `docker-compose.staging.yml`,
> `requirements.txt`, `config/settings.py`).
>
> **Non sostituisce un test reale**: appena Postgres è disponibile in
> staging, ripetere § "Smoke test su DB reale" e annotare l'esito qui.

---

## 0. Pre-requisiti

- Codebase **al merge `00cda4e`** (merge `product/go-live-readiness-p0`).
- Docker + Docker Compose v2+, o accesso a un Postgres 16 managed.
- `.env.staging` popolato da `docs/go_live/staging_env_template.example`
  (mai committato).

### Verifica codice pronto Postgres

```bash
grep -E "^psycopg" requirements.txt
# Expected: psycopg[binary]>=3.2

grep -nE "django.db.backends.sqlite" apps/ -r --include="*.py" | grep -v test_
# Expected: empty (no production code branches on sqlite backend)

grep -n "DATABASE_URL" config/settings.py
# Expected: env.db_url('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}')
```

Il default SQLite resta solo per dev: in staging `DATABASE_URL=postgres://...`
sovrascrive il default.

---

## 1. Provisioning Postgres (2 percorsi)

### Path A — Postgres managed (consigliato per staging serio)

Provider esempio: AWS RDS, GCP Cloud SQL, DigitalOcean Managed DB,
Hetzner, Render, Fly Postgres.

```bash
# 1. Crea database "badrane_staging" con utente dedicato "badrane".
# 2. Annota: host, port (default 5432), username, password.
# 3. Imposta SSL on (richiesto da provider managed).
# 4. Whitelista IP del web container in inbound firewall.
# 5. Setta in .env.staging:
#    DATABASE_URL=postgres://badrane:<PW>@<HOST>:5432/badrane_staging?sslmode=require
```

### Path B — Postgres in compose (staging self-hosted)

Già definito in `docker-compose.staging.yml`:

```yaml
db:
  image: postgres:16-alpine
  environment:
    POSTGRES_DB: ${POSTGRES_DB:-badrane_staging}
    POSTGRES_USER: ${POSTGRES_USER:-badrane}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?required}
  volumes:
    - postgres_data:/var/lib/postgresql/data
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-badrane} -d ${POSTGRES_DB:-badrane_staging}"]
```

Nessun expose verso host: solo rete docker interna.

---

## 2. Comandi di provisioning + migrate

```bash
# 1. Copia il template, popola i secret (mai committare):
cp docs/go_live/staging_env_template.example .env.staging
# editor di scelta: imposta DJANGO_SECRET_KEY, POSTGRES_PASSWORD,
# STUDIO_*, LEAD_NOTIFICATION_TO_EMAILS, EMAIL_HOST_*, *_VERSION ecc.

# 2. Generate SECRET_KEY:
python -c "import secrets; print(secrets.token_urlsafe(64))"
# copia output in DJANGO_SECRET_KEY (non riusare cross-environment).

# 3. Build + start (db parte prima del web grazie a depends_on healthcheck):
docker compose -f docker-compose.staging.yml --env-file .env.staging up -d --build

# 4. Verifica healthcheck DB:
docker compose -f docker-compose.staging.yml ps
# Aspettato: db = healthy, web = running (healthy after start_period 20s)

# 5. Migrate viene eseguito dal command del web service (vedi
#    docker-compose.staging.yml linea 83). Se serve forzare manualmente:
docker compose -f docker-compose.staging.yml exec web python manage.py migrate --noinput
# Aspettato: tutte le migrazioni applicate, 0 pending.

# 6. Collectstatic (idempotente, già eseguito allo start):
docker compose -f docker-compose.staging.yml exec web python manage.py collectstatic --noinput
# Aspettato: N file collected nel volume staticfiles_data.

# 7. Verifica system check (deve essere CLEAN se tutti i P0 env sono settati):
docker compose -f docker-compose.staging.yml exec web python manage.py check --deploy
# Aspettato: "System check identified no issues (0 silenced)."
# Se rimangono issue: vedi docs/PRODUCTION_ENV_REQUIRED_VARS.md
# per la variabile mancante associata a ogni codice errore.
```

---

## 3. Superuser staff (opzionale)

```bash
# Crea superuser per accesso /admin/. NON eseguire se l'accesso admin
# viene gestito via SSO o tramite seed esistente.
docker compose -f docker-compose.staging.yml exec web python manage.py createsuperuser
# Inserire username, email, password al prompt. Password forte
# (>= 14 char, generata da password manager). Non riusare credenziali
# personali.
```

Se è attivo `ADMIN_MFA_REQUIRED=True`:

```bash
# Configurazione TOTP per il superuser appena creato:
docker compose -f docker-compose.staging.yml exec web python manage.py addtotp <username>
# Output: TOTP secret + QR ASCII. Salvare nel proprio password manager.
```

---

## 4. Smoke test su DB reale

Eseguire i 4 controlli minimi per confermare che Postgres si comporta
come SQLite a livello applicativo. Nessuno deve fallire.

### 4.1 Connettività

```bash
docker compose -f docker-compose.staging.yml exec db \
  pg_isready -U badrane -d badrane_staging
# Aspettato: accepting connections
```

### 4.2 Migrazioni applicate

```bash
docker compose -f docker-compose.staging.yml exec web \
  python manage.py showmigrations | grep -c '\[X\]'
# Aspettato: numero migrazioni applicate (>0), 0 pending.

docker compose -f docker-compose.staging.yml exec web \
  python manage.py makemigrations --check --dry-run
# Aspettato: "No changes detected"
```

### 4.3 Canarino Italia RCA (DEVE essere identico al dev)

```bash
docker compose -f docker-compose.staging.yml exec web python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()

# Per il canarino servono fonti+dataset+formula approved in DB.
# In staging fresco vanno seedati via i fixture esistenti o ripetuti
# i management commands documentati in docs/architecture/.
# Lo smoke qui assume DB già seedato come dev/baseline.

from apps.cases.services import run_simulation
sim = run_simulation(
    jurisdiction_code='IT-NATIONAL',
    case_type='road_accident_bodily_injury',
    input_data={'victim_age':35,'permanent_disability_percentage':10,'fault_percentage':0},
    locale='it',
)
print('status:', sim.status)
print('min/mid/max:', sim.estimated_min, sim.estimated_mid, sim.estimated_max)
assert (int(sim.estimated_min), int(sim.estimated_mid), int(sim.estimated_max)) == (26268, 27353, 28439), 'CANARY DRIFT'
print('OK canary preserved')
"
# Aspettato:
#   status: calculated
#   min/mid/max: 26268.0000 27353.0000 28439.0000
#   OK canary preserved
```

### 4.4 Test suite su Postgres

```bash
# pytest-django gestisce la creazione di test DB Postgres in automatico
# (richiede CREATEDB sul user). Per evitare di intaccare il DB di staging,
# usare un DB di test separato OR mantenere DB staging vuoto fino al
# primo smoke.
docker compose -f docker-compose.staging.yml exec web pytest -q --no-header
# Aspettato: 2148 passed, 1 skipped (identico a baseline dev).
# Tempo atteso: 4-7 min su DB Postgres (più lento di SQLite in dev).
```

> **Nota Postgres vs SQLite test runtime**: il setup/teardown del test
> DB è più lento su Postgres (~2-3x). Considerare in CI l'uso di
> `--reuse-db` e `--keepdb` per i run iterativi.

---

## 5. Considerazioni specifiche Postgres

### 5.1 JSONField

Il codice usa `models.JSONField` su almeno:
- `cases.Simulation.input_data`, `.output_data`, `.sources_snapshot`
- `compensation.CompensationTableRow.extra_data`
- `compliance.PrivacyAuditEvent.metadata`
- vari altri

**Postgres usa nativo `jsonb`** (efficiente, indicizzabile). SQLite
usa text-emulation. Nessuna modifica codice richiesta.

### 5.2 DecimalField

`Simulation.estimated_*` sono `DecimalField(max_digits=12, decimal_places=4)`.

Su Postgres mappa a `numeric(12, 4)`. SQLite usa text-emulation.

**Verifica round-trip Decimal**:
```bash
docker compose -f docker-compose.staging.yml exec web python manage.py shell -c "
from decimal import Decimal
from apps.cases.models import Simulation
# crea + salva + reload per verificare round-trip
"
# Eseguire dopo il canarino § 4.3 — basta che il canarino sia uguale.
```

### 5.3 Indici e Constraints

Tutti gli indici sono dichiarati nelle migrazioni (`Meta.indexes`,
`Meta.constraints`). Postgres applica tutto. SQLite ignora alcuni
constraint (es. CHECK su FK opzionali) ma non è un problema in prod.

### 5.4 Timezone

`USE_TZ=True`, `TIME_ZONE=Europe/Brussels` di default. Postgres usa
`timestamp with time zone` per i `DateTimeField`. **Verificare** che il
container `db` abbia timezone allineato (default UTC va bene; Django
fa la conversione).

### 5.5 Collation

Default Postgres `en_US.utf8` va bene per ASCII. Se serve sort
locale-aware (es. ordinamento nomi avvocati con accenti), Postgres
supporta collate per-column. Non in scope P0.

---

## 6. Backup automatico

### 6.1 Strategia consigliata

- **Daily full dump** (pg_dump custom format) — retention 30 giorni.
- **WAL streaming** verso S3 / object storage — per point-in-time
  recovery, se RPO < 24h è richiesto.
- **Test restore** mensile su DB pulito.

### 6.2 Backup manuale (smoke test procedura)

```bash
# Dump custom format (binario, compresso, restore selettivo).
docker compose -f docker-compose.staging.yml exec db \
  pg_dump -U badrane -d badrane_staging -F c -f /tmp/badrane.dump

# Copia fuori container:
docker compose -f docker-compose.staging.yml cp \
  db:/tmp/badrane.dump ./backups/staging_$(date +%Y%m%d_%H%M%S).dump

# Verifica integrità (controlla che il file sia un dump valido senza
# applicarlo):
docker compose -f docker-compose.staging.yml exec db \
  pg_restore -l /tmp/badrane.dump | head -20
# Aspettato: lista TOC con table/data/index entries.
```

### 6.3 Restore di test (su DB separato)

```bash
# 1. Crea DB target di test (mai sovrascrivere staging vivo):
docker compose -f docker-compose.staging.yml exec db \
  psql -U badrane -d postgres -c "CREATE DATABASE badrane_restore_test;"

# 2. Restore:
docker compose -f docker-compose.staging.yml exec db \
  pg_restore -U badrane -d badrane_restore_test --no-owner --clean \
  /tmp/badrane.dump

# 3. Verifica row count su tabella canary:
docker compose -f docker-compose.staging.yml exec db \
  psql -U badrane -d badrane_restore_test -c \
  "SELECT count(*) FROM cases_simulation;"

# 4. Cleanup:
docker compose -f docker-compose.staging.yml exec db \
  psql -U badrane -d postgres -c "DROP DATABASE badrane_restore_test;"
```

### 6.4 Automazione cron

`cronjob` o systemd timer (esempio su host che ospita docker):

```bash
# /etc/cron.daily/badrane-postgres-backup
#!/usr/bin/env bash
set -euo pipefail
TS=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/var/backups/badrane
mkdir -p "$BACKUP_DIR"
docker compose -f /path/to/repo/docker-compose.staging.yml exec -T db \
  pg_dump -U badrane -d badrane_staging -F c > "$BACKUP_DIR/staging_$TS.dump"
# Retention 30 giorni:
find "$BACKUP_DIR" -name "staging_*.dump" -mtime +30 -delete
# Sincronizza opzionale su object storage:
# aws s3 sync "$BACKUP_DIR" s3://badrane-backups/staging/ --delete
```

> **Non committare credenziali AWS/object storage** nel repo. Usare IAM
> role della VM/container.

---

## 7. Disaster recovery — runbook breve

| Scenario | Azione | RTO atteso |
|---|---|---|
| DB corrotto | Stop web → restore ultimo dump → restart | 30-60 min |
| Container `db` perso | docker compose up -d db → migrate (idempotente) → restore dump | 15-30 min |
| Volume `postgres_data` perso | Re-provisionare volume → restore ultimo dump | 30-60 min |
| Errore migrazione | `git revert` migrazione → ricreare migrazione corretta → applicare | variabile |

---

## 8. Stato del runbook al 2026-05-13

| Item | Stato |
|---|---|
| Dockerfile multi-stage Postgres-ready | ✅ committed |
| docker-compose.staging.yml con `db` service | ✅ committed |
| psycopg[binary] in requirements | ✅ |
| `.env.staging.example` repo-root | ⚠️ esiste localmente, gitignored (non committato per safety) — vedi `docs/go_live/staging_env_template.example` come doc-side canonical |
| Postgres smoke su DB reale | ❌ non eseguito (no Postgres locale sull'host dev Windows) — eseguire in staging |
| Backup automation cron | ❌ non installato (manuale o managed-provider) |
| Restore di test mensile | ❌ da schedulare in calendar DevOps |

---

## 9. Quando questo runbook si considera "validato"

Lo è quando, su staging reale:

1. `docker compose ps` mostra `db=healthy` e `web=healthy`.
2. `manage.py check --deploy` riporta 0 issue.
3. Il canarino IT RCA produce **26 268 / 27 353 / 28 439 EUR**.
4. `pytest -q` (in container) riporta **2148 passed, 1 skipped**.
5. Un `pg_dump` test passa il `pg_restore -l` di verifica.
6. Un restore di test su DB separato + count tabelle non-zero.

Annota qui esito e data:

| Step | Esito | Data | Operatore |
|---|---|---|---|
| 1. compose healthy | — | — | — |
| 2. check --deploy clean | — | — | — |
| 3. canary IT preserved | — | — | — |
| 4. pytest 2148 | — | — | — |
| 5. dump integrity | — | — | — |
| 6. restore test passes | — | — | — |
