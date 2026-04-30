# Postgres — preparazione locale / staging (no deploy)

**Iter**: F-local-product-hardening-pass4-postgres-prep
**Data**: 2026-04-30
**Stato**: documentazione + script read-only. **Nessuna migrazione
in corso, nessun deploy.**

> Guida operativa per affiancare un database **Postgres** locale
> (o staging) all'attuale **SQLite** di sviluppo, senza migrare
> ancora i dati di produzione né cancellare il `db.sqlite3`
> esistente. Il percorso è progettato per essere *additivo*: lo
> Studio prova Postgres in parallelo, valida lo smoke contract
> Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR, e solo dopo
> decide se promuovere Postgres a default.

---

## 0. Avvertenze

- **Nessun deploy** è oggetto di questo iter.
- **Non cancellare `db.sqlite3`** sotto nessuna circostanza
  durante la prep: è la fonte verità del dev locale.
- **Nessun dato personale reale** deve finire in un dump locale
  o di staging: usare solo i seed di sviluppo + dati legali
  pubblici (TUN 2025 D.P.R., approved via flusso `LegalReview`).
- Nessun calcolo legale viene modificato: il calculator legge
  righe `approved` dal DB qualunque sia il backend.

---

## 1. Perché Postgres prima del deploy

CLAUDE.md (sezione "Stack preferito") richiede:
- **PostgreSQL in produzione**.
- **SQLite solo per sviluppo iniziale**.

Motivazioni operative:
- **Concorrenza**: SQLite ha lock a livello file. Multi-worker
  gunicorn / Celery + Redis genera write contention frequente.
- **Tipi e indici**: Postgres ha `JSONB`, `partial index`, `GIN`
  / `GIST`, transazioni con isolamento `READ COMMITTED` /
  `REPEATABLE READ` configurabile.
- **Backup / restore**: `pg_dump` / `pg_restore` sono lo
  standard di settore; SQLite richiede file copy con DB chiuso.
- **Time zones**: Postgres gestisce timezone-aware nativamente;
  SQLite simula via testo.
- **Auditlog / simple-history**: i payload JSON crescono nel
  tempo; `JSONB` su Postgres è ordine di grandezza più veloce
  per query strutturali.

---

## 2. Differenze attese SQLite → Postgres

| Area | SQLite | Postgres | Impact |
|---|---|---|---|
| Tipi colonna | dinamici | rigorosi | Migrate auto-genera DDL conforme. |
| Boolean | `0/1` integer | `true/false` | Django ORM astrae correttamente; eventuali raw SQL vanno controllati. |
| `JSONField` | TEXT | `JSONB` | Query `__contains` / `__has_key` molto più veloci su Postgres. |
| Datetime | text ISO | `TIMESTAMP WITH TIME ZONE` | `USE_TZ=True` (già presente) garantisce coerenza. |
| `DecimalField` | TEXT | `numeric(p,s)` | I valori IT (importi 26 268…) restano `Decimal` esatti. |
| Migrations | sequenziali | sequenziali | Stesso flusso `manage.py migrate`. |
| Lock | global file lock | row-level | Concorrenza migliore; meno transazioni "database is locked". |
| Backup | file copy | `pg_dump` / WAL | DR plan diverso. |

**Regressioni potenziali**:
- Query case-sensitivity: SQLite è case-insensitive di default
  per stringhe; Postgres no. Eventuali `.filter(name__iexact=...)`
  vanno verificati.
- Ordinamenti deterministici: SQLite e Postgres possono ordinare
  diversamente con `NULL`. Modelli con `Meta.ordering` definito
  esplicitamente sono OK.

---

## 3. Variabili `DATABASE_URL`

Il backend è configurato via `env.db_url("DATABASE_URL", ...)` in
`config/settings.py`. Default fallback = SQLite locale.

| Backend | Esempio `DATABASE_URL` |
|---|---|
| SQLite (default dev) | _non settare_ → `sqlite:///db.sqlite3` |
| Postgres locale (Docker) | `postgres://badrane:badrane@localhost:5432/badrane_dev` |
| Postgres staging | `postgres://staging_user:****@db.internal:5432/badrane_staging` |
| Postgres prod (futuro) | _settato dal sistemista, mai in repo_ |

**Mai committare** `DATABASE_URL` con credenziali reali in repo:
le `.env` sono in `.gitignore` (vedi `config/settings.py`
`environ.Env.read_env(BASE_DIR / ".env")`).

---

## 4. Setup Postgres locale (no Docker)

```bash
# macOS via Homebrew
brew install postgresql@16
brew services start postgresql@16

# Linux (Debian/Ubuntu)
sudo apt-get install postgresql-16
sudo systemctl start postgresql

# Windows
# Installer ufficiale https://www.postgresql.org/download/windows/
```

Crea un DB e un utente dedicati per la prep locale:

```bash
psql -U postgres <<EOF
CREATE USER badrane WITH PASSWORD 'badrane';
CREATE DATABASE badrane_dev OWNER badrane;
\q
EOF
```

`psycopg[binary]>=3.2` è già in `requirements.txt`: nessuna
nuova dipendenza pip da installare.

---

## 5. Setup Postgres locale (Docker, raccomandato)

Senza modificare il codice, basta lanciare un container:

```bash
docker run --rm -d \
  --name badrane-pg \
  -e POSTGRES_USER=badrane \
  -e POSTGRES_PASSWORD=badrane \
  -e POSTGRES_DB=badrane_dev \
  -p 5432:5432 \
  postgres:16-alpine
```

Per spegnere: `docker stop badrane-pg`. Il volume è effimero
(`--rm`), quindi i dati spariscono allo stop — perfetto per
verifiche read-only senza accumulare PII.

---

## 6. Lanciare migrate sul nuovo DB

Una volta che il DB è up, attiva la variabile `DATABASE_URL` per
**la sola sessione** (non scrivere su `.env` finché Postgres non
è stabile):

```bash
# bash / zsh
export DATABASE_URL="postgres://badrane:badrane@localhost:5432/badrane_dev"

# PowerShell
$env:DATABASE_URL = "postgres://badrane:badrane@localhost:5432/badrane_dev"
```

Verifica il backend prima di toccare i dati:

```bash
.venv/Scripts/python.exe scripts/staging/check_database_backend.py
```

Output atteso (Postgres):

```
engine: django.db.backends.postgresql
vendor: postgresql
[OK] Postgres backend attivo. Coerente con CLAUDE.md per produzione.
```

Applica le migrazioni:

```bash
.venv/Scripts/python.exe manage.py migrate
```

Le 46+ migrazioni del progetto vengono applicate da zero. Non
cambia il dev SQLite: il container Postgres è uno scratchpad
isolato.

---

## 7. Caricare i dati Italia da zero

I seed Italia sono già scriptati. Eseguire in ordine:

```bash
.venv/Scripts/python.exe manage.py seed_jurisdictions
.venv/Scripts/python.exe manage.py seed_italy_legal_sources
.venv/Scripts/python.exe manage.py import_italy_tun_2025 --csv legal_data/sources/italy/tun_2025/tun_2025_rows.csv
```

Stato post-import (atteso senza approval):

```
LegalSource (it-dpr-12-2025-tun-danno-biologico): needs_review
CompensationDataset (DPR-12-2025): draft o needs_review
CalculationFormula (italy_art_138_tun_2025_base): draft
```

L'approval finale (`approved`) resta un atto umano via Django
admin con creazione di `LegalReview`. Vedi `STAGING_DEPLOY.md`
e i seed di compliance per i dettagli.

---

## 8. Esportare il dataset Italia (snapshot riproducibile)

Per verificare la simmetria SQLite ↔ Postgres dopo il caricamento,
si può esportare il dataset TUN approved da una fonte e importarlo
nell'altra (entro lo stesso ambiente di prep, mai con PII):

```bash
.venv/Scripts/python.exe manage.py export_italy_tun_dataset \
  --version-label DPR-12-2025 \
  --output /tmp/dpr-12-2025.json
```

Il management command `export_italy_tun_dataset` produce uno
snapshot JSON deterministico (vedi
`apps/legal_sources/management/commands/export_italy_tun_dataset.py`).
**Mai committare** il JSON: contiene il dataset legale completo;
in repo basta lo schema di test.

---

## 9. Validare smoke 35/10/0 sul nuovo backend

Quando il caricamento Italia è completo e la `LegalReview` è
firmata, eseguire lo smoke read-only:

```bash
.venv/Scripts/python.exe scripts/staging/smoke_database_readiness.py
```

Output atteso (Italia approved):

```
DATABASE READINESS SMOKE (read-only)
[OK] all migrations applied

Counts:
  LegalSource:           24
  CompensationDataset:   2
  CalculationFormula:    1

Italy smoke 35/10/0 (pure-compute, no DB write):
  status:        calculated
  estimated_min: 26268
  estimated_mid: 27353
  estimated_max: 28439
[OK] smoke contract Italia confermato: 26268/27353/28439
```

Lo smoke chiama il calculator direttamente (pure-compute), **non
crea Simulation**. È sicuro rieseguirlo quante volte serve.

Su DB pulito (pre-import) lo script stampa `SKIP` con motivo
chiaro e ritorna 0: non è un errore.

---

## 10. Rollback a SQLite

Lo Studio può tornare al setup SQLite in qualunque momento
**senza perdere il dev locale**:

```bash
# bash / zsh
unset DATABASE_URL

# PowerShell
Remove-Item env:DATABASE_URL
```

Riverifica il backend:

```bash
.venv/Scripts/python.exe scripts/staging/check_database_backend.py
```

Output atteso:

```
engine: django.db.backends.sqlite3
vendor: sqlite
[WARNING] Backend = SQLite. OK per sviluppo locale...
```

Il `db.sqlite3` esistente è invariato: tutte le simulazioni,
i lead, i seed Italia restano consultabili come prima.

---

## 11. Backup difensivi

**Prima di promuovere Postgres a default**, fare backup:

```bash
# Backup SQLite (file copy)
cp db.sqlite3 backups/db_pre_postgres_promotion.sqlite3
```

Per Postgres staging (futuro):

```bash
pg_dump --format=custom --file=backups/badrane_staging_$(date +%Y%m%d).dump \
  postgres://badrane:badrane@localhost:5432/badrane_dev
```

**Mai committare** dump in repo. La directory `backups/` è già in
`.gitignore`.

---

## 12. Cosa resta per produzione

Questo iter prepara il path. Per il deploy effettivo serve:

- **Postgres managed** (Cloud SQL / RDS / Supabase / Hetzner) o
  self-hosted con DR plan.
- **Network**: VPC privato tra app server e DB; nessuna esposizione
  pubblica.
- **TLS**: connessione `sslmode=require` (default Postgres 16).
- **Backup automatici** giornalieri + WAL archiving.
- **Restore tested**: almeno una volta in pre-prod.
- **Connection pooling**: `pgbouncer` o Django `CONN_MAX_AGE`
  appropriato.
- **Monitoring**: pg_stat_statements, slow query log, alert su
  connection saturation.
- **Migration policy**: zero-downtime migrations (no
  `RunPython` lunghi su tabelle grandi senza chunking).

---

## 13. Disclaimer

Questo documento è una guida tecnica per la prep locale di
Postgres. Non sostituisce un audit di sicurezza o un piano DR
formale, che sono prerequisiti per il deploy in produzione. Il
disclaimer obbligatorio CLAUDE.md sulle simulazioni indicative
resta valido.
