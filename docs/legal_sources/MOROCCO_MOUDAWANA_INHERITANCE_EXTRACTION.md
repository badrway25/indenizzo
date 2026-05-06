# Moudawana — extraction des articles de succession (pass 1)

Iter: F-morocco-moudawana-livre-iii-mapping-draft-pass1.

- source PDF: `legal_data\sources\morocco\official_downloaded\ma-code-famille-moudawana-fr-pdf.pdf`
- sha256: `932aa556678ff0ceed2e49f57b697d818bc92c60ca42ddcd177b0f60e3c2ce3f`
- size: `227` bytes
- extractor: `stub`
- generated_at: `2026-05-06T16:38:16.434042+00:00`
- articles extracted: `0`

**Extraction blocked:** local PDF is too small (227 bytes) — looks like a synthetic fixture, not the real Moudawana document

The dev environment ships a synthetic fixture in place of the real Moudawana PDF. The extraction returned an empty article list. The mapping draft JSON beside it lists the canonical Moudawana inheritance article numbers anchored on this same approved source slug and tags every rule with `needs_manual_review=true`. Production deployment must replace the synthetic fixture with the real document and re-run this script before the mapping draft can advance.

