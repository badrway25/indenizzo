# Docker Compose locale (web + db + redis) — no deploy

**Iter**: F-local-product-hardening-pass6-docker-compose
**Data**: 2026-04-30
**Stato**: stack di sviluppo. **Nessun deploy.** **Redis predisposto
ma non usato per Celery in questo iter.**

> Stack docker-compose **locale-only** per testare la piattaforma
> con Postgres + Redis senza toccare il dev SQLite. Pensato per
> demo locale, smoke test, validazione manuale di /healthz/,
> rate-limit, cookie banner, MFA, e tutto il resto del prodotto
> in un ambiente che assomigli a staging/prod ma senza i rischi
> e i costi di un deploy reale.

---

## 0. Avvertenze

- **Nessun deploy** è oggetto di questo iter. Il file
  `docker-compose.local.yml` è esplicitamente per sviluppo
  locale.
- **Non cancellare `db.sqlite3`** sotto nessuna circostanza
  durante l'uso di questo stack: è la fonte verità del dev
  Python locale.
- Il container Postgres è **separato** dal `db.sqlite3`: hanno
  storage indipendenti.
- **Nessun dato personale reale** deve finire nel Postgres
  locale o nei volumi. Solo seed di sviluppo + dati legali
  pubblici (TUN 2025 D.P.R., quando approved via flusso
  `LegalReview`).
- **Nessun secret reale** in `.env.local.docker`: usare i valori
  del template `.env.local.docker.example`.

---

## 1. Scopo dello stack locale

- **Smoke test** del comportamento Postgres prima dell'eventuale
  promozione (vedi `POSTGRES_LOCAL_STAGING_PREP.md`).
- **Demo locale** della piattaforma con i servizi di
  riferimento (Postgres 16, Redis 7) attivi.
- **Validazione manuale** del funnel pubblico (`/wizard/...`,
  `/contact/`, `/healthz/`) in un ambiente che assomiglia a
  staging.
- **Rehearsal** dell'attivazione futura di Celery (Redis è già
  in piedi).

Cosa NON è:
- Non è uno stack di produzione.
- Non ha nginx/Caddy davanti.
- Non ha TLS.
- Non ha backup automatici, monitoring, alerting.
- Non gira gunicorn — usa `runserver` per avere hot reload.

---

## 2. Differenze rispetto a `docker-compose.staging.yml`

| Aspetto | Locale (`docker-compose.local.yml`) | Staging (`docker-compose.staging.yml`) |
|---|---|---|
| Server WSGI | `runserver 0.0.0.0:8000` | `gunicorn` 3 worker |
| `DJANGO_DEBUG` | `True` | `False` |
| Bind mount codice | `.:/app` (hot reload) | nessuno (immagine immutabile) |
| Porta DB esposta su host | `5432:5432` | solo `expose` interno |
| Porta Redis esposta su host | `6379:6379` | n/d (Redis non è in staging) |
| Redis | sì (predisposto, no-op) | no |
| nginx davanti | no | sì (esterno al compose) |
| TLS / HSTS | no | sì |
| `collectstatic` | no (DEBUG serve direttamente) | sì |
| Persistenza | volume `postgres_local_data` separato | `postgres_data` separato |

---

## 3. Setup iniziale

### 3.1 Copia env template

```bash
# bash / zsh
cp .env.local.docker.example .env.local.docker

# PowerShell
Copy-Item .env.local.docker.example .env.local.docker
```

`.env.local.docker` è gitignored (vedi `.gitignore` riga 19 +
exception riga 23). Mai committare.

I valori di default del template sono dev-only: `SECRET_KEY`
`django-insecure-...`, password Postgres `badrane_local_dev`.
**Mai usare in staging/prod.**

### 3.2 Avvio stack

```bash
# bash / zsh
./scripts/local/up.sh

# PowerShell
.\scripts\local\up.ps1
```

Il primo avvio fa il build dell'immagine `badrane-legaltech:local`
(può richiedere 1-2 min). Successivi avvii usano la cache.

Lo script wrapper:
1. Verifica che `.env.local.docker` esista (errore esplicito se
   manca).
2. Esegue `docker compose -f docker-compose.local.yml --env-file
   .env.local.docker up --build`.
3. Stampa hint per logs e ps.

### 3.3 Verifica health

```bash
docker compose -f docker-compose.local.yml ps
```

Atteso: `db` healthy, `redis` healthy, `web` running. Con il
browser: `http://localhost:8000/` → home pubblica.
`http://localhost:8000/healthz/` → `{"status":"ok"}`.

---

## 4. Eseguire migrate / shell / createsuperuser

```bash
# bash
./scripts/local/manage.sh migrate
./scripts/local/manage.sh createsuperuser
./scripts/local/manage.sh shell

# PowerShell
.\scripts\local\manage.ps1 migrate
.\scripts\local\manage.ps1 createsuperuser
.\scripts\local\manage.ps1 shell
```

**Nota**: il `command` del compose web esegue già `migrate
--noinput` all'avvio del container. La chiamata manuale è utile
solo se aggiungi nuove migrazioni e vuoi applicarle senza
restart container.

---

## 5. Caricare i dati Italia da zero (Postgres locale)

I seed Italia sono già scriptati e sono read-only sul filesystem
host (legge i CSV da `legal_data/sources/italy/tun_2025/`).

```bash
./scripts/local/manage.sh seed_jurisdictions
./scripts/local/manage.sh seed_italy_legal_sources
./scripts/local/manage.sh import_italy_tun_2025 --csv legal_data/sources/italy/tun_2025/tun_2025_rows.csv
```

Stato post-import (atteso):
- `LegalSource it-dpr-12-2025-tun-danno-biologico` → `needs_review`.
- `CompensationDataset DPR-12-2025` → `draft` o `needs_review`.
- `CalculationFormula italy_art_138_tun_2025_base` → `draft`.

L'approval finale (`approved`) resta un atto umano via Django
admin con creazione `LegalReview`. Vedi
`STAGING_DEPLOY.md` per la procedura.

---

## 6. Verificare smoke 35/10/0

Quando i dati Italia sono caricati e approvati:

```bash
# bash
./scripts/local/smoke.sh

# PowerShell
.\scripts\local\smoke.ps1
```

Lo script wrapper esegue dentro il container web:
1. `scripts/staging/check_database_backend.py`: deve stampare
   `vendor: postgresql` + `[OK]`.
2. `scripts/staging/smoke_database_readiness.py`: deve stampare
   `Italy smoke 35/10/0` + `26268` / `27353` / `28439` + `[OK]
   smoke contract Italia confermato`.

Su DB Postgres senza dati IT approvati lo smoke stampa `[SKIP]`
con motivo chiaro e ritorna 0 (è atteso, non è errore).

---

## 7. Fermare lo stack

```bash
# bash
./scripts/local/down.sh

# PowerShell
.\scripts\local\down.ps1
```

Questo **NON** cancella i volumi: il prossimo `up` ripartirà
dallo stesso stato Postgres.

---

## 8. Cancellare i volumi (con avvertenza forte)

> ⚠️ **AZIONE DISTRUTTIVA**: cancella tutti i dati Postgres
> locali (LegalSource, Lead, Simulation, ConsentRecord, ecc.).
> NON cancella `db.sqlite3` (è separato).

```bash
docker compose -f docker-compose.local.yml --env-file .env.local.docker down -v
```

Conferma prima di lanciare:
- Esiste un backup recente in `backups/`?
- Lo Studio ha approvato la cancellazione?
- I dati che si stanno per perdere sono solo seed dev (no PII)?

Per backup difensivo prima di cancellare:

```bash
# Dump Postgres locale → file SQL
docker compose -f docker-compose.local.yml --env-file .env.local.docker \
    exec -T db pg_dump -U badrane badrane_local > backups/local_$(date +%Y%m%d_%H%M%S).sql
```

`backups/` è già in `.gitignore`. Mai committare dump.

---

## 9. Tornare a SQLite (rollback dev locale)

Lo stack docker locale è **additivo**: il dev Python tradizionale
con SQLite continua a funzionare in parallelo, su un altro
processo, su un altro DB.

Per tornare al dev SQLite "tradizionale":

```bash
# Ferma lo stack docker
./scripts/local/down.sh

# Lavora con il venv locale come sempre
.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000
```

`db.sqlite3` non è stato toccato. Tutti i tuoi dati di sviluppo
SQLite sono invariati.

Vedi anche `docs/deploy/POSTGRES_LOCAL_STAGING_PREP.md` §10 per
il rollback più ampio.

---

## 10. Ruolo di Redis: solo predisposto

Redis è in piedi (`redis:7-alpine`, healthcheck attivo) ma NON
è ancora cablato a Celery o a un broker async.

**Cosa è usabile oggi:**
- `REDIS_URL=redis://redis:6379/0` è disponibile come variabile
  d'ambiente nel container web.
- `django.core.cache` può essere puntato a Redis aggiungendo a
  settings:
  ```python
  CACHES = {
      "default": {
          "BACKEND": "django.core.cache.backends.redis.RedisCache",
          "LOCATION": env("REDIS_URL", default="redis://redis:6379/0"),
      }
  }
  ```
  (oggi `CACHES` non è settato; il rate-limit pass 1 usa
  `LocMemCache` di default. Questo cambio è **fuori scope** di
  questo iter.)

**Cosa è ancora da fare (pass futuri):**
- `F-local-product-hardening-pass7-celery-async` — aggiungere
  `celery` worker container che consuma da Redis (broker +
  result backend). Spostare `send_lead_notification` su task
  async + retry. CLAUDE.md richiede già Celery in produzione.

Per ora, Redis sta lì pronto. Non costa nulla.

---

## 11. Troubleshooting Windows / PowerShell

### 11.1 Errore: `docker: command not found`
Installa Docker Desktop per Windows: https://docs.docker.com/desktop/.

### 11.2 Errore: bind mount `.:/app` su Windows
Docker Desktop monta i volumi via WSL2. Se hai problemi di
performance: sposta il repo dentro `\\wsl$\Ubuntu\home\...`
(filesystem WSL2 nativo, non `/c/...`).

### 11.3 Errore: porta 5432 già in uso
Hai un Postgres locale (non-docker) attivo? O un altro container?
- Verifica: `Get-Process postgres` o `netstat -an | findstr 5432`.
- Soluzione 1: ferma l'altro Postgres.
- Soluzione 2: cambia la porta in `docker-compose.local.yml`
  (`"5433:5432"` per esporre su `localhost:5433`).

### 11.4 Errore: porta 8000 già in uso
Hai un `runserver` Python attivo? Termina il processo o usa
`./scripts/local/down.sh && .venv/Scripts/python.exe manage.py runserver 127.0.0.1:8001`.

### 11.5 Hot reload non funziona
Su Windows + WSL2 + bind mount, il file watcher di Django può
non vedere le modifiche. Workaround: aggiungere
`USE_POLLING=True` alle env del web container, oppure restart
manuale `./scripts/local/down.sh && ./scripts/local/up.sh`.

### 11.6 Codifica caratteri (æ, è, °) nei log
Su PowerShell legacy (Windows 10), settare:
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001
```

---

## 12. File del package

### 12.1 Committable
- `docker-compose.local.yml`
- `.env.local.docker.example`
- `scripts/local/up.sh` + `up.ps1`
- `scripts/local/down.sh` + `down.ps1`
- `scripts/local/manage.sh` + `manage.ps1`
- `scripts/local/logs.sh` + `logs.ps1`
- `scripts/local/smoke.sh` + `smoke.ps1`
- `docs/deploy/LOCAL_DOCKER_COMPOSE.md` (questo file)

### 12.2 Gitignored
- `.env.local.docker` (creato dall'utente, mai committato)
- volumi docker (`postgres_local_data`, `media_local_data`,
  `staticfiles_local_data`)
- `backups/local_*.sql` (dump locali; dir già gitignored)

---

## 13. Disclaimer

Questo iter aggiunge solo uno stack docker di sviluppo locale.
Non altera dati legali, calcoli, o l'output del calcolatore
Italia. Lo Studio resta libero di promuovere o meno questo
stack a setup di default per il dev. Il disclaimer obbligatorio
CLAUDE.md sulle simulazioni indicative resta valido.
