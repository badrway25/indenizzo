"""
Generate Open Graph / Twitter Card PNG 1200×630 images for the
public site.

Iter: F-product-og-images-pass1.

Reads:
- `media/pexels/pexels_manifest.json` — Pexels images cached locally.
- `config/pexels_image_overrides.json` — frozen photo_id per slot.

Writes:
- `static/img/og/og-country-default.png`
- `static/img/og/og-italy.png`
- `static/img/og/og-france.png`
- `static/img/og/og-belgium.png`
- `static/img/og/og-morocco.png`
- `static/img/og/og-tunisia.png`

Style:
- Background = downsized Pexels photo (frozen photo_id, validated).
- Dark ink overlay gradient for legibility.
- Studio wordmark + country title + country-specific subtitle.
- Palette: ink-950 / sand-50 / gold-500.
- NO Pexels attribution visible (license requires it but we keep
  attribution only in the manifest).
- NO numeric claim (importi).
- NO "approved/calculated" wording for FR/BE/MA/TN.

Usage:
    python scripts/generate_og_images.py

The script is read-only WRT DB and never calls Pexels (no network,
no API key required). Idempotent.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------------------------
# Layout / palette
# ---------------------------------------------------------------------------

OG_W, OG_H = 1200, 630

INK_950 = (7, 23, 47)  # dark navy
INK_900 = (12, 32, 70)
SAND_50 = (250, 246, 239)
GOLD_500 = (184, 131, 54)
GOLD_400 = (203, 163, 107)

# Map: output-filename slug → spec for the overlay.
COUNTRY_SLUG_TO_MANIFEST_KEY = {
    "italy": "country_landing::IT",
    "france": "country_landing::FR",
    "belgium": "country_landing::BE",
    "morocco": "country_landing::MA",
    "tunisia": "country_landing::TN",
}

COUNTRY_DISPLAY = {
    "italy": "Italy",
    "france": "France",
    "belgium": "Belgium",
    "morocco": "Morocco",
    "tunisia": "Tunisia",
}

COUNTRY_SUBTITLE = {
    "italy": "Indicative compensation simulation",
    "france": "Legal review for French compensation sources",
    "belgium": "Legal review for Belgian compensation sources",
    "morocco": "International inheritance legal review",
    "tunisia": "International inheritance legal review",
}

DEFAULT_BACKGROUND_KEY = "home_hero::GLOBAL"
DEFAULT_SUBTITLE = "Indicative compensation simulations & inheritance reviews"
WORDMARK = "STUDIO LEGALE INTERNAZIONALE BADRANE"


# ---------------------------------------------------------------------------
# Font discovery
# ---------------------------------------------------------------------------


def _find_font(candidates: list[str]) -> str | None:
    """Cerca font in font-paths comuni cross-platform. Ritorna path o None."""
    search_dirs: list[Path] = []
    if sys.platform.startswith("win"):
        search_dirs.append(Path("C:/Windows/Fonts"))
    search_dirs.extend(
        [
            Path("/usr/share/fonts"),
            Path("/usr/local/share/fonts"),
            Path("/Library/Fonts"),
            Path.home() / "Library" / "Fonts",
        ]
    )
    for c in candidates:
        for d in search_dirs:
            if not d.exists():
                continue
            for f in d.rglob(c):
                return str(f)
    return None


def _load_fonts() -> tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]:
    """
    (titlefont 76, subtitlefont 30, eyebrowfont 22).

    Preferenze:
    - serif → Cormorant Garamond / Georgia / Times New Roman
    - sans → Inter / Arial
    """
    title_path = _find_font(
        ["CormorantGaramond-SemiBold.ttf", "Georgia.ttf", "georgia.ttf", "times.ttf", "Times.ttc"]
    )
    sans_path = _find_font(["Inter-SemiBold.ttf", "arial.ttf", "Arial.ttf", "DejaVuSans.ttf"])
    eyebrow_path = _find_font(["Inter-SemiBold.ttf", "arial.ttf", "Arial.ttf", "DejaVuSans.ttf"])
    title = ImageFont.truetype(title_path, 76) if title_path else ImageFont.load_default()
    subtitle = ImageFont.truetype(sans_path, 30) if sans_path else ImageFont.load_default()
    eyebrow = ImageFont.truetype(eyebrow_path, 22) if eyebrow_path else ImageFont.load_default()
    return title, subtitle, eyebrow


# ---------------------------------------------------------------------------
# Compositing
# ---------------------------------------------------------------------------


def _open_background(local_path: Path) -> Image.Image:
    """Apre l'immagine sorgente, la ridimensiona e la cropa a 1200×630."""
    img = Image.open(local_path).convert("RGB")
    # Cover crop al ratio 1200×630.
    target_ratio = OG_W / OG_H
    src_ratio = img.width / img.height
    if src_ratio > target_ratio:
        # img più largo → crop laterale
        new_w = int(img.height * target_ratio)
        left = (img.width - new_w) // 2
        img = img.crop((left, 0, left + new_w, img.height))
    else:
        new_h = int(img.width / target_ratio)
        top = (img.height - new_h) // 2
        img = img.crop((0, top, img.width, top + new_h))
    img = img.resize((OG_W, OG_H), Image.LANCZOS)
    # Subtle blur to make text more readable on busy backgrounds.
    img = img.filter(ImageFilter.GaussianBlur(radius=1.2))
    return img


def _apply_overlay(img: Image.Image) -> Image.Image:
    """Applica gradient ink overlay diagonale per leggibilità testo."""
    overlay = Image.new("RGBA", (OG_W, OG_H), (0, 0, 0, 0))
    # Dark gradient bottom-left → transparent top-right
    for y in range(OG_H):
        # Linear: stronger at bottom
        alpha = int(190 * (y / OG_H) ** 1.4 + 60)
        alpha = max(60, min(220, alpha))
        for_strip = (INK_950[0], INK_950[1], INK_950[2], alpha)
        ImageDraw.Draw(overlay).line([(0, y), (OG_W, y)], fill=for_strip, width=1)
    composed = img.convert("RGBA")
    composed.alpha_composite(overlay)
    # Add a left-to-right darker pad on the bottom 60% for headline area.
    side_pad = Image.new("RGBA", (OG_W, OG_H), (0, 0, 0, 0))
    pad_draw = ImageDraw.Draw(side_pad)
    pad_draw.rectangle(
        [(0, int(OG_H * 0.30)), (int(OG_W * 0.78), OG_H)],
        fill=(*INK_950, 130),
    )
    composed.alpha_composite(side_pad)
    return composed.convert("RGB")


def _draw_text(img: Image.Image, *, eyebrow_text: str, title: str, subtitle: str) -> None:
    """Disegna wordmark eyebrow, country title, subtitle."""
    title_font, subtitle_font, eyebrow_font = _load_fonts()
    draw = ImageDraw.Draw(img)

    # Eyebrow (gold, letterspaced, top-left area but actually mid-left).
    eyebrow_y = 380
    draw.text((80, eyebrow_y), eyebrow_text, font=eyebrow_font, fill=GOLD_400)
    # Gold horizontal accent line under eyebrow.
    draw.line(
        [(80, eyebrow_y + 38), (160, eyebrow_y + 38)],
        fill=GOLD_500,
        width=3,
    )

    # Title (serif, big, sand-50).
    draw.text((80, eyebrow_y + 56), title, font=title_font, fill=SAND_50)

    # Subtitle (sans, smaller, sand-50/85).
    # Wrap at ~55 chars — heuristic for our subtitles which are <60 chars.
    draw.text(
        (80, eyebrow_y + 56 + 90),
        subtitle,
        font=subtitle_font,
        fill=(SAND_50[0], SAND_50[1], SAND_50[2]),
    )

    # Top-right: small wordmark line ("studiolegalebadrane.it") + brand mark.
    # Discreet so it doesn't compete with the headline.
    domain_font = subtitle_font
    domain = "studiolegalebadrane.it"
    bbox = draw.textbbox((0, 0), domain, font=domain_font)
    domain_w = bbox[2] - bbox[0]
    draw.text(
        (OG_W - domain_w - 60, 60),
        domain,
        font=domain_font,
        fill=GOLD_400,
    )


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _media_root() -> Path:
    return _project_root() / "media"


def _static_og_dir() -> Path:
    d = _project_root() / "static" / "img" / "og"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _read_manifest() -> dict[str, dict]:
    p = _media_root() / "pexels" / "pexels_manifest.json"
    if not p.exists():
        return {}
    return json.load(p.open(encoding="utf-8"))


def _write_png(img: Image.Image, path: Path) -> dict:
    img.save(path, "PNG", optimize=True)
    raw = path.read_bytes()
    return {
        "path": str(path),
        "size_bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "width": img.width,
        "height": img.height,
    }


def _generate_one(
    manifest: dict[str, dict],
    *,
    output_filename: str,
    manifest_key: str,
    eyebrow_text: str,
    title: str,
    subtitle: str,
) -> dict:
    entry = manifest.get(manifest_key)
    if not entry:
        raise SystemExit(
            f"[og] manifest key not found: {manifest_key!r}. "
            "Run `python manage.py fetch_pexels_site_images --all --force` first."
        )
    local_rel = entry.get("local_path", "")
    if not local_rel:
        raise SystemExit(f"[og] manifest entry {manifest_key!r} missing local_path.")
    local_abs = _media_root() / local_rel
    if not local_abs.exists():
        raise SystemExit(
            f"[og] local image missing: {local_abs}. Refetch via "
            f"`python manage.py fetch_pexels_site_images --slot <key> --force`."
        )

    bg = _open_background(local_abs)
    composed = _apply_overlay(bg)
    _draw_text(composed, eyebrow_text=eyebrow_text, title=title, subtitle=subtitle)
    out = _static_og_dir() / output_filename
    return _write_png(composed, out)


def main() -> None:
    manifest = _read_manifest()
    if not manifest:
        raise SystemExit(
            "[og] media/pexels/pexels_manifest.json missing or empty. "
            "Run `python manage.py fetch_pexels_site_images --all` first."
        )

    results: list[dict] = []

    # Default
    results.append(
        _generate_one(
            manifest,
            output_filename="og-country-default.png",
            manifest_key=DEFAULT_BACKGROUND_KEY,
            eyebrow_text=WORDMARK,
            title="Indicative simulations",
            subtitle=DEFAULT_SUBTITLE,
        )
    )

    # 5 country-specific
    for slug, mkey in COUNTRY_SLUG_TO_MANIFEST_KEY.items():
        results.append(
            _generate_one(
                manifest,
                output_filename=f"og-{slug}.png",
                manifest_key=mkey,
                eyebrow_text=WORDMARK,
                title=COUNTRY_DISPLAY[slug],
                subtitle=COUNTRY_SUBTITLE[slug],
            )
        )

    # Print summary.
    print("Generated OG images:")
    for r in results:
        print(
            f"  {r['path']}  {r['width']}x{r['height']}  "
            f"size={r['size_bytes']:,}B  sha256={r['sha256'][:16]}..."
        )


if __name__ == "__main__":
    main()
