# P37 — Official Source Validation Queue (2026-06-29)

Tracks the `approval_needed` sources that could unlock new monetary estimates. A figure
is allowed **only** after a source is legally validated (`usable_for_engine`) AND an
engine + canary test exist. **Nothing here is fabricated**: where a table cannot be
verified with certainty, the platform keeps the document pre-check / summary path.

Legend: ✅ yes · ❌ no · ⚠️ partial / needs legal review.

## INAIL — `it-dm-45-2019` + `it-dlgs-38-2000` (Italy, work injury)
- Official ref: D.M. 12 luglio 2000 / D.Lgs. 38/2000 (danno biologico INAIL); D.M. 45/2019 (indennizzo capitale).
- Status: `approval_needed`. PDF downloaded/committed: ❌ (not committed — heavy/official portal).
- Grade×age table identified: ⚠️ (the structure is known: % invalidità × coefficiente per età), but the exact official coefficients require a verified copy of the table.
- Formula identified: ⚠️ (capitale = grado → indennizzo, modulated by age band).
- Reliable extraction now: ❌ — requires a legally-verified table; OCR of a scanned PDF is not reliable enough to publish a figure.
- Canary available: ❌ (no validated reference values to assert against).
- Can activate engine now: **❌** — would risk inventing coefficients.
- Reason: the indemnity table must be transcribed from the official source and signed off by a legal reviewer before any euro figure is shown. Until then: **pre-check INAIL → summary**.

## Morocco — `ma-dahir-1-84-177` + `ma-acaps-guide` (road accident)
- Official ref: Dahir n° 1-84-177 (capital de référence / barème) + ACAPS indemnification guide.
- Status: `approval_needed`. PDF committed: ❌.
- Table identified: ⚠️ (capital de référence by age/income exists in the Dahir annexes).
- Formula identified: ⚠️ (depends on liability share + capital de référence + AIPP).
- Reliable extraction now: ❌ — annex tables need a verified copy; liability rules need legal framing.
- Canary: ❌. Can activate now: **❌**.
- Reason: barème + liability interaction not verified. Until then: **pre-check Morocco → summary**.

## Tunisia — `tn-code-assurances` (Titre V) + `tn-loi-2005-86` (road accident)
- Official ref: Code des assurances, Titre V (barème d'indemnisation).
- Status: `approval_needed`. PDF committed: ❌.
- Table identified: ⚠️ (the barème Titre V exists with age coefficients).
- Formula identified: ⚠️.
- Reliable extraction now: ❌. Canary: ❌. Can activate now: **❌**.
- Reason: barème not yet transcribed + validated. Until then: **pre-check Tunisia → summary**.

## Belgium — `be-tableau-indicatif` (indicative table)
- Status: `non_binding_practice`. Can activate as sole basis: **❌** — it is explicitly
  *indicative / non-binding*, so it cannot be the basis of a published figure. It may be
  shown as context next to the validated BE engine.

## Summary
**0 new monetary engines can be safely activated in P37.** All candidate sources remain
`approval_needed`/`non_binding_practice`. Activating any would require: (1) a legally
verified copy of the table, (2) transcription + a developer-built engine, (3) canary
tests pinning known reference values, (4) flipping the source to `usable_for_engine`.
That is a controlled legal+dev workstream — not something to fabricate. The platform's
behaviour (pre-check / summary for these) is therefore **correct and unchanged**.

Public copy for these cases stays simple and honest, e.g.:
> "Possiamo preparare i tuoi documenti subito. Per calcolare l'importo serve prima la
> tabella ufficiale di questo paese."
