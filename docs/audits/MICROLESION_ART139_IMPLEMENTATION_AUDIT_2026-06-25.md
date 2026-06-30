# Italy art. 139 microlesions — implementation audit (P7)

**Phase**: P7 · 2026-06-25. Serious extraction attempt + precise blocker, per
the brief ("non dire più 'manca fonte ufficiale' senza prova").

## What was VERIFIED from official sources

Fetched the **official Gazzetta Ufficiale** text of art. 139 D.Lgs. 209/2005
(`gazzettaufficiale.it/atto/serie_generale/caricaArticolo?...idArticolo=139`):

- **Structure (verified):** danno biologico permanente per lesioni ≤9% is
  computed as `valore_primo_punto × coefficiente(P) × punti × demoltiplicatore_età`,
  where the importo grows "in misura più che proporzionale".
- **Age reduction (verified, in the article text):**
  `demoltiplicatore = 1 − 0,005 × (età − 11 + 1)` — i.e. −0,5% per year of age
  from the 11th year: `1 − (età − 10) × 0,005` for età ≥ 10.
- **Danno biologico temporaneo (verified, art. 139 co.1 lett. b):** a fixed
  daily amount for inabilità assoluta (100%); for inabilità temporanea < 100%,
  the liquidation is **proportional** to the recognised daily percentage.
- **2025 monetary values (provided by the owner; consistent with D.M. MIMIT
  18/07/2025, G.U. n.176 del 31/07/2025, decorrenza aprile 2025):**
  - valore del primo punto = **€ 963,40**
  - inabilità temporanea assoluta = **€ 56,18 / giorno**

## What is BLOCKED (and why — not generic prudence)

**The per-percentage progression coefficients** `coefficiente(P)` for P = 1…9 are
the missing piece. They are NOT in the official article text:

- art. 139 **comma 6** is the *legal definition* of danno biologico (psycho-
  physical integrity), **not** a coefficient table — verified from the Gazzetta
  fetch.
- The "più che proporzionale" coefficients derive from the **tabella delle
  menomazioni** (D.M. Salute 3/7/2003 + the calculation method), which is NOT
  reproduced in art. 139 itself and is **not extractable** from an accessible
  official primary source (Normattiva/Gazzetta `caricaArticolo` are
  JavaScript-rendered; the D.M. MIMIT 2025 PDF publishes only the *monetary
  update*, not the progression).
- The only sources that publish the explicit 9 coefficient values are
  **secondary/commercial** (Brocardi/Altalex/calculator sites) — **forbidden as
  a validation source** by the project rules.

➡️ Implementing the permanent micro with **guessed** intermediate coefficients
would violate the cardinal rule "non inventare dati legali". An **ITT-only**
engine was rejected on its own: presenting only the temporary component for a
case that also has permanent damage would **understate** the total and mislead.

## Implementation-ready spec (the moment the table is verified)

When the verbatim, official, non-blog **9 coefficients** are obtained (or the
full per-% 2025 importo table), implementation is mechanical (no architecture
change):

1. `LegalSource` (approved): CAP art. 139 + D.M. MIMIT 18/07/2025
   (G.U. n.176/2025), official URLs + the PDF hash.
2. `CompensationDataset` (approved, `case_type=road_accident_micro`) with
   `CompensationTableRow`s: the primo-punto value, the ITT daily value, and the
   9 progression coefficients (each as a row with its `point_value`/coefficient).
3. New `amount_rule` in `apps.compensation.services.SUPPORTED_AMOUNT_RULES`:
   `italy_art139_micro_v1` = `primo_punto × coeff(P) × P × (1 − (età−10)×0.005)`
   for the permanent part **+** `(itt_assoluta_days + Σ itt_parziale_days × q) ×
   56.18` for the temporary part.
4. `ItalyRoadAccidentMicrolesionCalculator` registered for
   `(IT-NATIONAL, road_accident_micro)`; the wizard routes **1–9% → art. 139**,
   **≥10% → TUN art. 138** (the existing engine).
5. **Canary tests** (deterministic): e.g. P=9, età=35, 0 ITT → fixed €; ITT-only
   (P=0, 30 days assoluta) → 30 × 56,18 = **€ 1 685,40**; boundary 10% → routes
   to TUN; 0% → INSUFFICIENT; >9% → not micro.
6. Fail-closed: any missing coefficient row → UNAVAILABLE, never a guessed €.

**Exactly what I need from you:** the official, verbatim **9 progression
coefficients** of art. 139 (or the full 2025 per-percentage importo table) from
a primary source (Gazzetta PDF / D.M. Salute tabella menomazioni / IVASS), so
nothing is invented.
