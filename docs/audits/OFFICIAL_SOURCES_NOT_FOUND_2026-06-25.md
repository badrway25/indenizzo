# Official sources — not found / to confirm

**Phase**: P5 · 2026-06-25. Companion to
`PUBLIC_SERVICE_OFFICIAL_COVERAGE_2026-06-25.md`. Lists only what a serious
search on **official** portals did NOT yield as a *primary national* source.
None of these blocks the public site (every affected section stays fail-closed
with an assisted-pathway pathway and premium copy) — they are items for the
Studio / owner to confirm.

> Official portals only (Gazzetta Ufficiale, Normattiva, MIMIT, INAIL, IVASS,
> EUR-Lex, Ministero della Giustizia, Camera/Senato). NOT used: blogs, Altalex,
> Brocardi, Wikipedia, private firms, SEO portals.

---

## 1. Parental / death damages — no official national statutory table

- **Section:** `death` (Loss of a relative / danno da perdita del rapporto
  parentale).
- **Searched for:** a primary, official, *national* statutory table of amounts
  (analogous to the TUN for road-accident bodily injury).
- **Portals consulted:** Gazzetta Ufficiale, Normattiva (Codice Civile, leggi
  collegate), Ministero della Giustizia.
- **What is missing:** there is **no official national statutory table** that
  quantifies parental/loss-of-relationship damages. The de-facto reference is the
  **Tabelle del Tribunale di Milano** — *court practice*, catalogued in the DB as
  `needs_review`, **not a primary national source** and not an approved public
  formula.
- **What I need you to confirm:** whether the Studio wants to (a) keep this area
  fully assisted (current, recommended), or (b) treat the Milano tables as an
  internal working reference (never a public automatic number).

## 2. Italian instrument article *bodies* — JS-rendered / compressed

- **Sections:** road_accident (CAP 138-139), medical (Gelli art. 7),
  work_injury (T.U. INAIL 112), defective product (Consumo 114-127), insurance
  offer (CAP 145/148).
- **Limit (technical, not "not found"):** the *instruments* and official URLs are
  confirmed, but the consolidated *article bodies* are not auto-extractable
  (Normattiva / Gazzetta `caricaArticolo` are JavaScript-rendered; the IVASS CAP
  PDF text layer is FlateDecode-compressed).
- **What I need you to confirm:** the current consolidated text of each cited
  article via the official portal (or Gazzetta PDF with an extractor/OCR) before
  any of them is ever turned into a public automatic output. Default stays
  **NO-GO / fail-closed**.

## 3. MIMIT uplift coefficients (road accident)

- **Section:** road_accident.
- **Status:** D.M. MIMIT 18/07/2025 & 10/12/2025 are catalogued (`needs_review`)
  with official `mimit.gov.it` URLs but the *uplift coefficients* are not modelled
  in the approved engine. The public calculation uses only the **approved TUN
  2025** dataset.
- **What I need you to confirm:** whether the MIMIT updates should be promoted to
  `approved` and folded into the engine (a calculator change — out of P5 scope).
