"""
Optimize Open Graph PNG images (lossless).

Iter: F-product-og-images-pass2-compress.

Riduce il peso file dei PNG generati da `scripts/generate_og_images.py`
SENZA cambiare:
- dimensioni (devono restare 1200×630);
- contenuto visivo (lossless: ogni pixel resta identico).

Strategia tool:
1. **`oxipng`** (via `pyoxipng`, OPZIONALE) — tool Rust che esplora più
   strategie di filtro+zlib di quanto faccia Pillow. Tipicamente
   riduce 5–15% su PNG già "optimize=True".
2. **Pillow `optimize=True` + `compress_level=9`** — fallback puro,
   già lo standard usato in `generate_og_images.py`. In pratica
   re-encoding di un file già ottimizzato dà 0% di riduzione, quindi
   il fallback è solo un no-op pulito.

`pyoxipng` NON è in `requirements.txt` per evitare di forzare una
dipendenza Rust su tutti gli ambienti. Per usarlo:

    pip install pyoxipng

Senza `pyoxipng`, lo script gira ugualmente ma con 0% di gain (i PNG
sono già stati prodotti con Pillow optimize=True).

---

Modalità:

- (default) ottimizza in place e stampa la tabella before/after/sha256.
- `--check` non scrive: re-esegue l'ottimizzazione in RAM e fallisce
  se almeno un PNG potrebbe essere ulteriormente ridotto, o se le
  dimensioni non sono 1200×630, o se non è un PNG valido.

Idempotente: in modalità default, la prima esecuzione riduce, le
successive sono no-op (sha256 invariato). `--check` quindi passa
sempre dopo la prima esecuzione.

No rete. No DB. No API key.

Usage:
    python scripts/optimize_og_images.py
    python scripts/optimize_og_images.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import io
import sys
from pathlib import Path

from PIL import Image

try:
    import oxipng

    _HAS_OXIPNG = True
except ImportError:  # pragma: no cover - environment-dependent
    _HAS_OXIPNG = False


OG_W, OG_H = 1200, 630


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _og_dir() -> Path:
    return _project_root() / "static" / "img" / "og"


def _is_valid_png(raw: bytes) -> bool:
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return False
    try:
        Image.open(io.BytesIO(raw)).verify()
    except Exception:
        return False
    return True


def _png_size(raw: bytes) -> tuple[int, int]:
    return Image.open(io.BytesIO(raw)).size


def _optimize_bytes(raw: bytes) -> bytes:
    """
    Ritorna i byte PNG ottimizzati (lossless).

    Se `oxipng` non è disponibile, fa re-encoding via Pillow. Per file
    già generati con Pillow optimize=True, questo è un no-op.
    """
    if _HAS_OXIPNG:
        return oxipng.optimize_from_memory(
            raw,
            level=6,
            strip=oxipng.StripChunks.safe(),
            interlace=oxipng.Interlacing.Off,
        )
    img = Image.open(io.BytesIO(raw))
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True, compress_level=9)
    return buf.getvalue()


def _format_row(name: str, before: int, after: int, sha: str) -> str:
    delta_pct = (1 - after / before) * 100 if before else 0.0
    return f"{name:<32}{before:>10,}{after:>10,}{delta_pct:>7.1f}%  {sha[:16]}"


def _run(*, check_only: bool) -> int:
    og_dir = _og_dir()
    pngs = sorted(og_dir.glob("*.png"))
    if not pngs:
        print(f"[og-opt] no PNG found in {og_dir}", file=sys.stderr)
        return 1

    tool = "oxipng" if _HAS_OXIPNG else "Pillow optimize=True (oxipng not installed)"
    mode = "CHECK" if check_only else "OPTIMIZE"
    print(f"[og-opt] mode: {mode}")
    print(f"[og-opt] tool: {tool}")
    print(f"[og-opt] dir:  {og_dir}")
    print()
    print(f"{'file':<32}{'before':>10}{'after':>10}{'delta':>8}  sha256")
    print("-" * 80)

    failures: list[str] = []
    total_before = 0
    total_after = 0

    for p in pngs:
        raw = p.read_bytes()
        before = len(raw)
        total_before += before

        if not _is_valid_png(raw):
            failures.append(f"{p.name}: invalid PNG")
            print(f"[og-opt] FAIL {p.name}: invalid PNG", file=sys.stderr)
            continue

        size = _png_size(raw)
        if size != (OG_W, OG_H):
            failures.append(f"{p.name}: size {size} != ({OG_W}, {OG_H})")
            print(
                f"[og-opt] FAIL {p.name}: size {size} != ({OG_W}, {OG_H})",
                file=sys.stderr,
            )
            continue

        opt = _optimize_bytes(raw)
        after = len(opt)

        if check_only:
            if after < before:
                failures.append(
                    f"{p.name}: could shrink {before}→{after} ({(1-after/before)*100:.1f}%)"
                )
                print(
                    f"[og-opt] FAIL {p.name}: re-optimization would shrink "
                    f"{before:,}→{after:,} bytes",
                    file=sys.stderr,
                )
                total_after += after
            else:
                total_after += before
                print(_format_row(p.name, before, before, hashlib.sha256(raw).hexdigest()))
        else:
            if after < before:
                p.write_bytes(opt)
                total_after += after
                print(_format_row(p.name, before, after, hashlib.sha256(opt).hexdigest()))
            else:
                total_after += before
                print(_format_row(p.name, before, before, hashlib.sha256(raw).hexdigest()))

    print("-" * 80)
    if total_before:
        total_delta = (1 - total_after / total_before) * 100
        print(f"{'TOTAL':<32}{total_before:>10,}{total_after:>10,}{total_delta:>7.1f}%")

    if failures:
        print(f"\n[og-opt] {len(failures)} failure(s):", file=sys.stderr)
        for msg in failures:
            print(f"  - {msg}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify PNG are already optimized; do not write. Exits 1 on regression.",
    )
    args = parser.parse_args()
    return _run(check_only=args.check)


if __name__ == "__main__":
    sys.exit(main())
