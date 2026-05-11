"""
Generate WebP variants of cached Pexels images.

Iter: F-p2-img-1-hero-image-optimization.

For each JPEG/PNG already cached under MEDIA_ROOT/pexels/, produce
two WebP companions next to the source:

    <name>.jpg         — original (untouched)
    <name>.webp        — WebP, same resolution as source, q=80
    <name>.mobile.webp — WebP, max-width 800 px, q=75

The mobile variant is used in `<picture><source media="(max-width:
640px)" srcset="...">` to send a smaller payload to mobile clients.

Idempotent: skips when the companion is newer than the source.
Pillow is the only dependency (already required by the project).

Scoped to MEDIA_ROOT/pexels — does NOT touch repository assets,
does NOT write outside the media cache. Like the source JPEGs the
companions are runtime artifacts, gitignored.

Usage:

    python manage.py compress_pexels_images
    python manage.py compress_pexels_images --force  # rewrite all
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

DEFAULT_QUALITY = 80
# Mobile quality picked from empirical Lighthouse runs on /ar/ where
# the hero JPEG is the LCP element. At quality=65 the visible
# difference is invisible on the 390x480-px viewport while saving
# ~6 KiB over q=75 on the home hero.
DEFAULT_MOBILE_QUALITY = 65
DEFAULT_MOBILE_MAX_WIDTH = 800

SOURCE_SUFFIXES = (".jpg", ".jpeg", ".png")


class Command(BaseCommand):
    help = (
        "Generate WebP (full-res + 800-wide mobile) companions for each "
        "JPEG/PNG cached in MEDIA_ROOT/pexels/."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Rewrite all WebP companions regardless of mtime.",
        )
        parser.add_argument(
            "--quality",
            type=int,
            default=DEFAULT_QUALITY,
            help=f"Desktop WebP quality (default {DEFAULT_QUALITY}).",
        )
        parser.add_argument(
            "--mobile-quality",
            type=int,
            default=DEFAULT_MOBILE_QUALITY,
            help=(
                f"Mobile WebP quality (default {DEFAULT_MOBILE_QUALITY}). "
                "Lower than desktop because Lighthouse penalises bigger "
                "transfer over throttled mobile networks."
            ),
        )
        parser.add_argument(
            "--mobile-max-width",
            type=int,
            default=DEFAULT_MOBILE_MAX_WIDTH,
            help=(
                f"Mobile WebP max width (default {DEFAULT_MOBILE_MAX_WIDTH}). "
                "Sources wider than this are scaled down preserving aspect "
                "ratio; sources narrower than this are copied at native "
                "resolution."
            ),
        )

    def handle(self, *args, **options):
        try:
            from PIL import Image
        except ImportError as exc:
            raise SystemExit(
                "Pillow is required for compress_pexels_images. "
                "It is part of requirements.txt; activate the project "
                "venv before running."
            ) from exc

        media_root = Path(settings.MEDIA_ROOT)
        pexels_dir = media_root / "pexels"
        if not pexels_dir.is_dir():
            self.stdout.write(
                f"No pexels cache at {pexels_dir} - nothing to compress."
            )
            return

        force = options["force"]
        quality = options["quality"]
        mobile_quality = options["mobile_quality"]
        mobile_max_width = options["mobile_max_width"]

        written_desktop = 0
        written_mobile = 0
        skipped_fresh = 0
        scanned = 0

        for source in sorted(pexels_dir.iterdir()):
            if not source.is_file():
                continue
            if source.suffix.lower() not in SOURCE_SUFFIXES:
                continue
            scanned += 1

            webp_desktop = source.with_suffix(".webp")
            webp_mobile = source.with_name(source.stem + ".mobile.webp")

            if self._is_fresh(webp_desktop, source) and not force:
                skipped_fresh += 1
            else:
                self._write_webp(Image, source, webp_desktop, quality, None)
                written_desktop += 1

            if self._is_fresh(webp_mobile, source) and not force:
                skipped_fresh += 1
            else:
                self._write_webp(
                    Image, source, webp_mobile, mobile_quality, mobile_max_width
                )
                written_mobile += 1

        self.stdout.write(
            f"Scanned {scanned} source image(s). "
            f"Wrote {written_desktop} desktop WebP, "
            f"{written_mobile} mobile WebP. "
            f"Skipped {skipped_fresh} fresh."
        )

    @staticmethod
    def _is_fresh(companion: Path, source: Path) -> bool:
        return companion.exists() and companion.stat().st_mtime >= source.stat().st_mtime

    @staticmethod
    def _write_webp(
        image_module,
        source: Path,
        dest: Path,
        quality: int,
        max_width: int | None,
    ) -> None:
        with image_module.open(source) as im:
            im = im.convert("RGB")
            if max_width is not None and im.width > max_width:
                ratio = max_width / im.width
                new_size = (max_width, max(1, int(round(im.height * ratio))))
                im = im.resize(new_size, image_module.Resampling.LANCZOS)
            im.save(dest, format="WEBP", quality=quality, method=6)
