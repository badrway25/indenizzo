# Release notes — P28→P50 premium public platform (PR #22)

_Date: 2026-06-30 · Merged into `product/staging-readiness-p0` as `edbb462`
(merge commit, `--no-ff`). Source: `feature/p3-public-ux-redesign @ f4ab1e4`.
228 files, +37.8k / −2.6k, 204 commits. Not yet deployed._

## What's in
- **Premium public experience:** hand-written design system (navy/gold/sand),
  full-bleed hero, navbar mega-menu with icons + mobile drawer, refined motion
  (reduced-motion safe). Self-hosted fonts; no CDN.
- **Accessible custom select:** progressive enhancement over native `<select>`
  (ARIA listbox, gold checkmark, full keyboard, value-sync, no-JS fallback).
- **Guided Path Studio:** deterministic recommender (estimate path offered only
  where a validated engine exists — IT injury).
- **Official sources:** library + source detail + PDF/link center + search.
- **Documentation hub** + nine case-type guides + glossary + FAQ.
- **Document AI intake + multi-document dossier** (in-memory, never stored;
  OpenAI feature-flagged OFF by default).
- **Results as human report pages**; **truthful estimate matrix**; **public
  "why no amount" + "what it takes to show an amount"** explanations.
- **Official source harvest** command (allowlisted, robots-respecting, provenance
  manifest only) + **validation packs** (8) + missing-sources gap map.
- **i18n** it/fr/en/ar (0 fuzzy).

## What's NOT in (deliberately)
- **No new estimate engine.** Only IT road / danno biologico / medical produce a
  figure. FR/BE road and IT/MA/TN inheritance return
  `unavailable_requires_legal_validation`.
- No deploy, no production change, no DB run on any server.
- No CDN, no committed heavy PDFs/screenshots, no harvest manifest in the repo.
- No OpenAI calls unless explicitly enabled via env.

## Migrations
3 non-destructive `AlterField` on `case_type` (cases/0005, compensation/0007,
crm/0006). Apply with `migrate` after a DB backup. See the runbook §B.

## Environment
`STUDIO_*` (7) mandatory before go-live (`core.W001` → ERROR under `DEBUG=False`).
Security: `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`,
SSL/HSTS vars, `DATABASE_URL`. OpenAI off unless authorised; Pexels env-only. Full
list in the runbook §C.

## Risks (all non-blocking for staging)
- `STUDIO_*` unset blocks `check` under `DEBUG=False` (configure first).
- Lighthouse **mobile** is opt-in (workflow_dispatch); run before go-live.
- Pre-existing ruff items (10) in P28–P34 files only; the P35–P50 stack adds zero.

## Required QA after deploy
HTTP smoke (`/healthz/` + it/ar routes, zero 5xx); browser smoke (custom select,
documents, sources, documentation, result; mobile 390; RTL); 0 console errors;
matrix truthful; no unvalidated amount. See runbook §G.

## Legal/data
No new estimate is activated without a validated official table **and** a
legally-reviewed canary. `apps/calculators/data/legal_tables/` is empty by design.
The harvest probe confirmed several official domains are reachable but extracted
**no** binding barème — every validation pack stays `needs_legal_review` /
`not_calculable`. Nothing is invented.
