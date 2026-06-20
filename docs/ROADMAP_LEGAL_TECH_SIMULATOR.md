# Roadmap — Legal-Tech Simulator (derivata dall'audit 2026-06-19)

**Fonte:** `docs/audits/LEGAL_TECH_SIMULATOR_AUDIT.md` (53 finding).
**Relazione con le roadmap esistenti:** questa è una **vista d'azione** dei
finding dell'audit, **mappata** sullo schema P0–P5 canonico di
`docs/ROADMAP_PRIORITIZED.md` e sulle fasi A→E di
`docs/architecture/LOCAL_NEXT_STEPS.md`. In caso di conflitto prevalgono i
documenti canonici e `docs/architecture/PRODUCT_REQUIREMENTS.md`.

**Principio guida (invariato):** *meglio nessun calcolo che un calcolo falso*.
Nessun deploy in produzione finché il gate `manage.py check` (DEBUG=False) non è
verde e le firme Studio non sono presenti.

---

## 0. Mappa fasi prompt → P-level esistente

| Fase prompt (FASE 0–7) | Stato reale | P-level canonico |
|---|---|---|
| FASE 0 Audit | ✅ **questo audit** | — |
| FASE 1 Fondamenta | ✅ già fatta | — |
| FASE 2 Fonti/archiviazione | ✅ già fatta (IT approved; FR/BE candidate) | — |
| FASE 3 Simulatore Italia | ✅ operativo | — |
| FASE 4 Report PDF | ✅ operativo (coverage da estendere) | — |
| FASE 5 Back-office Studio | ⚠️ parziale (admin sì; export/360/priorità no) | P1/P2 |
| FASE 6 SEO/landing | ✅ in larga parte (gap canonical/OG/FAQ schema) | P1 |
| FASE 7 Estensione paesi | ⛔ bloccata da firma Studio | P0-MVP-1 / Fase B-C |

---

## 1. Batch H-1 — Hardening "difesa in profondità" (P1, basso rischio, dev-only)

> **Stato: COMPLETATO il 2026-06-19** per i 6 item richiesti (H1-1, H1-2,
> H1-3, H1-4, H1-6, H1-7). Full suite verde (2164 passed), canarino IT
> 35/10/0 invariato, `manage.py check` pulito. Vedi
> `docs/audits/LEGAL_TECH_SIMULATOR_AUDIT.md` §6 / il report Bundle H-1.
> Restano aperti H1-5 e H1-8 (constraint DB + provenienza calcolo), non
> nel bundle perché richiedono migrazioni/scelte di schema.

Tutti questi **non toccano** i dati legali e **non possono produrre regressioni
di importo** (sono guard più stretti o integrità di workflow). Ordinati per
valore/sforzo.

| ID | Finding | Intervento | Effort | Stato |
|---|---|---|---|---|
| H1-1 | engine NULL `point_value`→0 € CALCULATED | fail-closed: riga APPROVED con `point_value` NULL → `UNAVAILABLE` + diagnostica `compensation_row_value_missing` | S | ✅ |
| H1-2 | render guard disaccoppiato da status | result page **e** PDF legati a `status=='calculated'` oltre a `estimated_* is not None` | S | ✅ |
| H1-3 | promozione si fida di `notes` (H3) | ricomputo file-hash/marker in-process in `promote_official_legal_sources._evaluate` (via `_validate_one`), non più il blocco `notes` editabile | M | ✅ |
| H1-4 | `LegalReview` mutabile (H4) | admin append-only: `has_delete_permission=False`, righe esistenti congelate, `reviewer=request.user` forzato | S | ✅ |
| H1-5 | invarianti solo in `clean()` (H5/medium) | `CheckConstraint` DB per `valid_to>=valid_from`, ordinamenti età/invalidità; FK `CompensationDataset → LegalSourceVersion` | M | ⏳ (richiede migrazione) |
| H1-6 | `CACHES` non condivisa (H7) | backend Redis condiviso in non-DEBUG (`CACHE_URL`/`REDIS_URL`), LocMemCache in dev/test | S | ✅ |
| H1-7 | `check --deploy` assente in CI | `manage.py check --deploy --fail-level WARNING` nel job `production-checks` (W021 preload silenziata) | S | ✅ |
| H1-8 | provenienza calcolo sottile | record di provenienza per Simulation CALCULATED (version_label + hash riga/formula); righe APPROVED immutabili | M | ⏳ |

> **Canarino obbligatorio**: ogni item di H-1 chiude con IT 35/10/0 = 26.268 /
> 27.353 / 28.439 € verde (live simulation matrix). ✅ verificato 2026-06-19.

---

## 2. Batch H-2 — Trasparenza & i18n pre-go-live (P0/P1)

| ID | Finding | Intervento | Effort |
|---|---|---|---|
| H2-1 | **IT ~67% non tradotto (C1)** | completare `.po` it→fr→ar (funnel+landing+result+disclaimer), `compilemessages`, **gate CI di copertura** | L (bottleneck: traduzione Studio) |
| H2-2 | result page senza `confidence`/`missing_documents` (H2) | renderizzare badge `confidence` e l'array `missing_documents` dell'engine (oggi scartato in `cases/views.py:236-238`) **oppure** allineare la copy di home/methodology | M |
| H2-3 | no canonical/OG su home & pagine (H10) | spostare `canonical` + Open Graph in `base.html` (helper già in `apps/core/seo.py`) | M |
| H2-4 | FAQ senza schema.org (medium) | `build_faq_page_json_ld()` su case-type landing, source-bound/promise-free | S |
| H2-5 | switcher CSP (H1) | ✅ **FATTO** (audit §6) — aggiungere test browser sotto CSP enforced | XS |

---

## 3. Batch H-3 — Staging deployabile (P1/P2, infra)

| ID | Finding | Intervento | Effort |
|---|---|---|---|
| H3-1 | no TLS/proxy in staging (H8) | reverse-proxy + TLS (Caddy, già nel runbook) o gate esplicito su proxy esterno | M |
| H3-2 | `legal_data` montato RW (H8) | split mount: `legal_data/sources` **read-only**, `exports` writable | S |
| H3-3 | Redis+Celery assenti in staging (H9) | aggiungere i service al compose staging **oppure** system check che blocca async senza broker | S |
| H3-4 | healthcheck su `/` (medium) | `HEALTHCHECK` Docker su `/healthz/` (DB-free) | XS |
| H3-5 | no Manifest static storage (medium) | `STORAGES` whitenoise `CompressedManifestStaticFilesStorage` in non-DEBUG | S |
| H3-6 | backup/restore docs-only (medium) | automazione backup + off-site + restore-test datato; Sentry `CeleryIntegration` | M |

---

## 4. Batch H-4 — Back-office Studio (P1/P2)

| ID | Finding | Intervento | Effort |
|---|---|---|---|
| H4-1 | mandate by-hand bypassa il servizio (H6) | `mandate_signed`/`status` readonly + azione admin che chiama `mark_mandate_signed` | S |
| H4-2 | no export lead (medium) | azione export CSV/XLSX PII-safe (whitelist colonne, skip anonimizzati, log `PrivacyAuditEvent`) | M |
| H4-3 | no lead-360 (medium) | pannelli read-only su LeadAdmin: range Simulation + `sources_snapshot` + ConsentRecord | M |
| H4-4 | priorità mai valorizzata (medium) | derivare urgenza alla creazione + filtro range su importo simulazione | M |
| H4-5 | `cms_content` stub (medium) | decidere: implementare modelli CMS traducibili **oppure** documentare il deferral e togliere l'app vuota dallo scope | L |

---

## 5. Batch H-5 — Test & QA (P2)

| ID | Finding | Intervento | Effort |
|---|---|---|---|
| H5-1 | nessun Playwright reale | smoke pack browser IT (wizard happy path, consent client-side, result) sul server Lighthouse CI | M |
| H5-2 | golden IT da fixture, non da dataset approved | test di determinismo che ricomputa 26.268/27.353/28.439 dal seed approved committato | S |
| H5-3 | coverage PDF sottile | test `apps/reports`: disclaimer presente, no banned-wording, **no importo EUR** per giurisdizioni review-gated | M |
| H5-4 | `--reuse-db` senza drift-check | `makemigrations --check`; `.gitattributes binary` per artefatti `legal_data` | S |

---

## 6. P0-MVP-1 — Primo caso non-IT verde (bloccato da Studio)

Invariato rispetto a `LOCAL_NEXT_STEPS.md`: serve un ramo qualunque tra
FR road accident / BE road accident / MA inheritance / TN inheritance, **dopo**
firma del relativo review package. Sequenza per ramo:
1. Studio compila il checklist → GO/NO-GO.
2. Import dataset approved (seed read-only, post-GO).
3. Calculator REAL (override `_compute_with_sources`).
4. Wizard pubblico dietro feature flag.
5. Test E2E verde + staging deploy.

Nessun codice dev può sbloccare questo P0 senza la firma Studio.

---

## 7. Sequenza consigliata (next 30/60/90)

- **0–30 gg**: Batch **H-1** completo (hardening difesa-in-profondità) + H2-5
  (✅) + H2-3/H2-4 (SEO). In parallelo lo Studio avvia traduzione IT (H2-1) e
  review FR.
- **30–60 gg**: Batch **H-3** (staging deployabile) + H2-1 IT completato +
  H2-2 (result transparency) + H4-1 (mandate).
- **60–90 gg**: **P0-MVP-1** (primo paese non-IT post-firma) + Batch **H-5**
  (Playwright + determinismo + coverage PDF) + H-4 back-office.
- **90+ gg**: go-live gate (`STUDIO_*` valorizzati, firme, `check --deploy`
  verde), poi rollout per paese dietro feature flag.

---

## 8. Out-of-scope (invariato)

Da `LOCAL_NEXT_STEPS.md` §6 / `ROADMAP_PRIORITIZED.md` §9: calcolatori
pluri-giurisdizione automatici, integrazione real-time assicuratori, pagamenti,
app nativa, casi che richiedono perizia medica obbligatoria (restano scaffold
con `missing_documents`). Area cliente/upload/firma incarico = P5.
