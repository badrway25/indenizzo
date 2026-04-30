# LOCAL — Product hardening, pass 10 — staff audit retention

**Iter**: F-local-product-hardening-pass10-staff-audit-cleanup-task
**Data**: 2026-04-30
**Stato**: implementato + testato in locale. **Nessun deploy.**
**Default**: dry-run=True ⇒ zero cancellazioni finché lo Studio
non passa esplicitamente a commit.

> Decimo passaggio: retention policy per gli audit log staff
> (`StaffAccessEvent` pass 8 + `StaffSecurityAlert` pass 9), con
> service pure-functions, management command CLI e Celery task
> manualmente invocabile. Tocca SOLO i due modelli di audit
> staff: nessun altro audit/legal-data viene mai cancellato.
> IT smoke 35/10/0 → 26 268 / 27 353 / 28 439 EUR verificato.

---

## 1. Cosa è stato aggiunto

| Area | File | Tipo |
|---|---|---|
| Settings | `config/settings.py` | 4 settings env-driven `STAFF_*_RETENTION_*` |
| Service | `apps/compliance/retention.py` (nuovo) | `get_staff_audit_retention_cutoffs`, `count_expired_staff_audit_events`, `cleanup_staff_audit_events` |
| Mgmt cmd | `apps/compliance/management/commands/cleanup_staff_audit.py` (nuovo) | `--dry-run` (default), `--commit`, `--now ISO` |
| Celery | `apps/compliance/tasks.py` (nuovo) | `cleanup_staff_audit_task` |
| Test | `apps/compliance/test_staff_audit_retention.py` (nuovo) | 10 test |
| Docs | questo file | — |

Niente nuove dipendenze. Niente schema migration (le retention
sono solo policy applicative, nessun nuovo campo). Niente touch
a calculator/engine/wizard/dataset/formula.

---

## 2. Cosa pulisce / cosa NON pulisce

### 2.1 Pulisce
- **`StaffAccessEvent`** con `created_at < now - STAFF_ACCESS_EVENT_RETENTION_DAYS` (default 90 giorni).
- **`StaffSecurityAlert`** con `triggered_at < now - STAFF_SECURITY_ALERT_RETENTION_DAYS` (default 180 giorni).

Le retention dei due modelli sono **separate** perché hanno
volumi e valore investigativo diversi:
- `StaffAccessEvent` cresce molto (login/logout/failed). 90 giorni
  bilancia visibilità e storage.
- `StaffSecurityAlert` è aggregato (un alert per round di attacco).
  180 giorni preserva un'analisi storica utile.

### 2.2 NON pulisce (mai)
Verificato dal test #4:
- `PrivacyAuditEvent` (compliance GDPR — retention diversa).
- `LegalReview` (audit firma legale — legal hold permanente).
- `ConsentRecord` (prova consenso GDPR).
- `SimulationReport` (artefatto storico, retention separata).
- `Lead` (CRM — retention legata a esito pratica).
- `Simulation` (history utente — retention separata).
- `CompensationDataset`, `CalculationFormula`, `CompensationTableRow`,
  `LegalSource`, `LegalSourceAttachment` — **legal data**, mai
  toccati.

---

## 3. Settings retention

In `config/settings.py`, sezione **Staff audit retention**:

| Setting | Default | Override env |
|---|---|---|
| `STAFF_ACCESS_EVENT_RETENTION_DAYS` | `90` | `STAFF_ACCESS_EVENT_RETENTION_DAYS` |
| `STAFF_SECURITY_ALERT_RETENTION_DAYS` | `180` | `STAFF_SECURITY_ALERT_RETENTION_DAYS` |
| `STAFF_AUDIT_RETENTION_ENABLED` | `True` | `STAFF_AUDIT_RETENTION_ENABLED` |
| `STAFF_AUDIT_RETENTION_DRY_RUN` | **`True`** (sicuro) | `STAFF_AUDIT_RETENTION_DRY_RUN` |

**Default dry-run**: la cancellazione è OFF di default. Per
attivarla in produzione lo Studio deve passare esplicitamente
`STAFF_AUDIT_RETENTION_DRY_RUN=False` via env.

`STAFF_AUDIT_RETENTION_ENABLED=False` invece skippa
completamente la task (utile se per un periodo si vuole
disabilitare il cron senza modificare il codice).

---

## 4. Service `cleanup_staff_audit_events`

`apps/compliance/retention.py`:

### 4.1 `get_staff_audit_retention_cutoffs(now=None) -> dict`
Pure read-only. Ritorna i datetime cutoff per i due modelli, dati
i settings + (opzionalmente) un `now` iniettabile per test
deterministici.

### 4.2 `count_expired_staff_audit_events(now=None) -> dict`
Pure read-only. Conta i record sotto cutoff senza cancellare.

### 4.3 `cleanup_staff_audit_events(*, dry_run=True, now=None) -> dict`
- `dry_run=True`: ritorna i counts senza toccare DB.
  `access_deleted=alerts_deleted=0`.
- `dry_run=False`: cancella i record sotto cutoff e ritorna i
  conteggi reali.
- Default `dry_run=True` per sicurezza.

Ritorna sempre un dict con: `now`, `staff_access_cutoff`,
`staff_alert_cutoff`, `staff_access_retention_days`,
`staff_alert_retention_days`, `access_expired`, `alerts_expired`,
`access_deleted`, `alerts_deleted`, `dry_run`.

---

## 5. Management command

```bash
# Dry-run (default, sicuro): mostra cosa verrebbe cancellato
.venv/Scripts/python.exe manage.py cleanup_staff_audit

# Cancellazione reale (richiede flag esplicito)
.venv/Scripts/python.exe manage.py cleanup_staff_audit --commit

# Pin orologio (utile in test/staging)
.venv/Scripts/python.exe manage.py cleanup_staff_audit --now 2026-01-01T00:00:00+00:00
```

**Output dry-run** (esempio):
```
================================================================
Staff audit retention cleanup (DRY-RUN (no delete))
================================================================
now:                          2026-04-30T12:00:00+00:00
StaffAccessEvent retention:   90 days  (cutoff: 2026-01-30T12:00:00+00:00)
StaffSecurityAlert retention: 180 days  (cutoff: 2025-11-01T12:00:00+00:00)

StaffAccessEvent expired:     142
StaffSecurityAlert expired:   3

Nessuna cancellazione eseguita. Aggiungi --commit per applicare.
```

**Output commit**: aggiunge righe `... deleted: N` colorate
warning. Exit code 0 sempre al completamento.

`--commit` e `--dry-run` sono mutuamente esclusivi (errore
esplicito).

---

## 6. Celery task

`apps/compliance/tasks.py::cleanup_staff_audit_task()`:

- Wrapper Celery del service. Legge `STAFF_AUDIT_RETENTION_*`
  da settings.
- `STAFF_AUDIT_RETENTION_ENABLED=False` → ritorna
  `{"skipped": "disabled"}` senza toccare DB.
- Altrimenti chiama `cleanup_staff_audit_events(dry_run=...)`
  con `dry_run` letto da `STAFF_AUDIT_RETENTION_DRY_RUN` (default
  True).
- Logga sempre i counts finali (no PII).
- Failure-soft: eccezioni catchate, ritorna `{"error": ClassName}`.

**Invocazione manuale** (locale o staging):
```bash
celery -A config call apps.compliance.tasks.cleanup_staff_audit_task
```

Oppure via shell:
```python
from apps.compliance.tasks import cleanup_staff_audit_task
cleanup_staff_audit_task.delay()  # async (richiede broker)
cleanup_staff_audit_task.apply()  # eager (utile in test)
```

**Celery Beat NON è cablato in pass 10**: la schedulazione
notturna automatica verrà aggiunta in un pass successivo. Per ora
il task è solo **invocabile manualmente** via CLI/shell/cron
esterno.

---

## 7. Retention suggerita

| Modello | Default | Razionale |
|---|---|---|
| `StaffAccessEvent` | 90 giorni | Volume alto (login/logout/failed). 3 mesi sufficienti per indagare incidenti recenti senza accumulare GB di dati. |
| `StaffSecurityAlert` | 180 giorni | Aggregato (1 alert per round di attacco). 6 mesi consentono di vedere pattern stagionali (es. picchi pre-festività). |

Queste sono **suggested defaults**: lo Studio può alzare/abbassare
via env in base a:
- volumi reali dopo qualche mese di produzione;
- requisiti DPO/GDPR;
- spazio disco DB.

---

## 8. Workflow consigliato

### 8.1 Locale (sviluppo)
- Default `DRY_RUN=True` + `ENABLED=True`. Il task gira ma non
  cancella. Ottimo per testare il flusso senza rischi.

### 8.2 Staging
1. `STAFF_AUDIT_RETENTION_DRY_RUN=True` per N settimane (osserva
   counts nei log Celery).
2. Quando counts sono ragionevoli (no falsi positivi sui giorni
   sbagliati), promuovere `DRY_RUN=False`.
3. Verificare backup.

### 8.3 Produzione
1. **Prima del primo `--commit`**: backup completo DB
   (`pg_dump --format=custom`).
2. Eseguire `cleanup_staff_audit --dry-run` per verifica counts.
3. Eseguire `cleanup_staff_audit --commit` (o lasciare al task
   notturno).
4. Verificare log + spot-check admin (`/admin/compliance/staffaccessevent/`).
5. Schedulare Celery Beat ogni notte (vedi §10).

---

## 9. Backup warning

> ⚠️ **Prima di un primo `--commit` in produzione**: backup DB
> completo. La cancellazione è irreversibile.

Comandi suggeriti:
```bash
# Postgres
pg_dump --format=custom \
    --file=backups/before_audit_cleanup_$(date +%Y%m%d_%H%M%S).dump \
    $DATABASE_URL

# SQLite (dev locale)
cp db.sqlite3 backups/before_audit_cleanup_$(date +%Y%m%d_%H%M%S).sqlite3
```

`backups/` è già in `.gitignore`. Mai committare dump.

---

## 10. Cosa resta per produzione

### 10.1 Celery Beat schedule
Da aggiungere in un pass futuro (`F-local-product-hardening-pass11-celery-beat`):
```python
CELERY_BEAT_SCHEDULE = {
    "cleanup_staff_audit_nightly": {
        "task": "apps.compliance.tasks.cleanup_staff_audit_task",
        "schedule": crontab(hour=3, minute=15),  # 03:15 UTC
    },
}
```
+ container `celery-beat` nel `docker-compose.local.yml` (oggi
abbiamo solo `celery-worker`).

### 10.2 Export pre-cleanup (cold storage)
Per audit GDPR/DPO si può voler **archiviare** gli eventi
expired prima della cancellazione:
- task Celery che, prima di cancellare, esporta su file
  `staff_audit_YYYY-MM.jsonl.gz` in S3/NAS Studio;
- recupero offline per indagini legali.

### 10.3 Legal hold
Se è in corso un'indagine legale che riguarda eventi staff
recenti, lo Studio deve poter **mettere in pausa** la
cancellazione per un set di IDs/IP/username:
- aggiungere flag `StaffAccessEvent.is_under_legal_hold` o
  modello separato `LegalHold` con FK a chi tracciare;
- il cleanup salta i record con hold attivo.
Questo è un requisito DPO ma non urgente per pass 10.

### 10.4 Metriche
- Esportare counts via Prometheus (oggi solo log).
- Alert se `access_expired > soglia` (segnale che il cron è
  inattivo da troppo).

### 10.5 Retention granulare
Pass futuro: retention diversa per `event_type`:
- `login_success`: 30 giorni (rumore basso valore);
- `login_failed`: 365 giorni (audit forensic);
- `logout`: 7 giorni (info trascurabile).

---

## 11. Test aggiunti (10, tutti passati)

`apps/compliance/test_staff_audit_retention.py`:
1. `test_cutoffs_match_settings` — `now - retention_days` corretto per i due modelli.
2. `test_dry_run_counts_but_does_not_delete` — 3 access (2 expired) + 2 alert (1 expired) → counts esatti, 0 delete.
3. `test_commit_deletes_only_expired_records` — i fresh restano in DB, gli expired spariscono.
4. `test_cleanup_does_not_touch_unrelated_audit_models` — `PrivacyAuditEvent`, `ConsentRecord`, `LegalReview`, `CompensationDataset`, `CalculationFormula`, `LegalSource` invariati anche con retention=1day.
5. `test_management_command_dry_run_output` — output contiene `DRY-RUN`, count corretto, niente cancellazione.
6. `test_management_command_commit_deletes_expired` — output `COMMIT`, expired sparito, fresh resta.
7. `test_celery_task_default_dry_run` — `cleanup_staff_audit_task.apply()` con `STAFF_AUDIT_RETENTION_DRY_RUN=True` → counts ma 0 delete.
8. `test_celery_task_skipped_when_disabled` — `STAFF_AUDIT_RETENTION_ENABLED=False` → `{"skipped": "disabled"}`.
9. `test_settings_defaults_are_safe` — DRY_RUN=True, ENABLED=True, days 90/180.
10. `test_italy_smoke_run_simulation_35_10_0` — 35/10/0 → 26 268 / 27 353 / 28 439.

Helper `_make_access_event(created_at)` / `_make_security_alert(triggered_at)` usano `update()` per scrivere timestamp arbitrari (auto_now_add bypassed) per simulare record vecchi.

---

## 12. Validazione

```bash
.venv/Scripts/python.exe manage.py makemigrations --check
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m black --check .
```

---

## 13. Disclaimer

Questo iter aggiunge solo retention degli audit log staff. Non
altera dati legali, calcoli, output del calcolatore Italia. Non
tocca PrivacyAuditEvent, LegalReview, SimulationReport, Lead,
ConsentRecord. La gestione operativa (passaggio a
`DRY_RUN=False`, scheduling Beat, backup pre-cancellazione)
resta in capo allo Studio. Il disclaimer obbligatorio CLAUDE.md
sulle simulazioni indicative resta valido.
