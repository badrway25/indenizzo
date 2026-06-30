# Source approvals for engine expansion (P8)

**Phase**: P8 · 2026-06-25. Records the owner-approved official sources/data that
unblock internal technical implementation, with prudent public output +
disclaimer. Implemented engines read ALL numeric values from approved DB rows —
nothing is hardcoded in the engine.

## 1. Italy — microlesions art. 139 CAP — APPROVED & IMPLEMENTED

- **Official source:** Gazzetta Ufficiale, art. 139 Codice delle Assicurazioni
  Private (D.Lgs. 209/2005); annual monetary update **D.M. MIMIT 18/07/2025**
  (G.U. n.176 del 31/07/2025, decorrenza aprile 2025).
- **Approved data:**
  - invalidity 1–9%;
  - comma-6 progression coefficients: 1→1.0, 2→1.1, 3→1.2, 4→1.3, 5→1.5,
    6→1.7, 7→1.9, 8→2.1, 9→2.3;
  - age reduction: −0,5% per year of age from the 11th year
    (`1 − max(0, età−10)×0,005`, floored at 0);
  - ITT: a daily amount for inabilità assoluta, proportional for partial;
  - 2025 values: **primo punto € 963,40**, **ITT assoluta € 56,18/giorno**.
- **Implemented:** engine `italy_art139_micro_v1` (case_type
  `road_accident_microlesions`):
  `permanente = primo_punto × coeff(P) × P × demolt_età`;
  `temporaneo = giorni_ITT_assoluta × 56,18 (+ parziali × 0,5)`.
  Canary (verified to the cent): 1%@35 → €842,98; 9%@35 → €17 449,58; 5%@35 →
  €6 322,31; età 10 → nessuna riduzione; età 11 → ×0,995; 30 gg ITT → €1 685,40.
- **Allowed public output:** tabular biological-damage estimate for compatible
  road-accident micropermanenti, with the official-source drawer + the standard
  disclaimer. Fail-closed for 0% and ≥10% (≥10% routes to the TUN art. 138).
- **Excluded:** personalizzazione +20% (judicial), danno morale extra (shown as
  *not included*), causal link, fault — never auto-computed.

## 2. Italy — medical-liability biological damage — APPROVED & IMPLEMENTED

- **Official source:** L. 8/3/2017 n. 24 (Gelli-Bianco) art. 7 → the biological
  damage from healthcare activity is liquidated on the artt. 138/139 CAP tables.
- **Implemented:** case_type `medical_liability_biological_damage`: 1–9% → art.
  139 micro; ≥10% → the approved TUN art. 138 — presented under L. 24/2017.
- **Limit (strong public disclaimer):** "Stima TABELLARE del danno biologico,
  NON valutazione completa della responsabilità sanitaria." It does NOT compute
  colpa, nesso causale, perdita di chance, danno morale extra, danno patrimoniale
  or overall liability.
- **Canary:** medical 5% → €6 322,31 (= road micro 5%); medical 10% → TUN
  26268/27353/28439. TUN canary unchanged.

## 3. What stays excluded (see FOR_CHATGPT_APPROVAL)

- INAIL indemnity tables (D.M. 2000 / D.M. 45-2019) — table not extracted.
- Morocco Dahir 1984 barème — scanned PDF (no text layer), multi-factor method.
- FR/BE/TN — no official computable government tariff (référentiels only).
- Prescription remains internal & non-numeric (never public).
