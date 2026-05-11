"""
Pre-compress local static files (.css, .js) into .gz companions.

Iter: F-p2-perf-1-mobile-performance-pass.

WhiteNoise serves a pre-compressed `<file>.gz` next to `<file>`
when the client sends `Accept-Encoding: gzip`. In dev mode
WhiteNoise does NOT compress on the fly — it only picks up
companions that already exist on disk. Production normally runs
`collectstatic` with a CompressedStaticFilesStorage which does
the same thing as a side-effect; this command is the dev /
Lighthouse-runner equivalent so a developer can opt into
compressed serving without running collectstatic on every change.

The command walks each `STATICFILES_DIRS` root (skipping
`STATIC_ROOT` so we don't compress collected duplicates) plus
each `app/static/` directory discovered by the staticfiles
finders, and writes a `<file>.gz` next to any `.css` or `.js`
whose mtime is newer than the companion's. Existing fresh
`.gz` files are skipped. Files outside the project tree (e.g.
inside `.venv/`) are not touched.

Run from CI right before the Lighthouse stage:

    python manage.py precompress_static

Or pass --force to rewrite all `.gz` companions regardless of
mtime.
"""

from __future__ import annotations

import gzip
import os
import time
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.management.base import BaseCommand

# Only these extensions are worth compressing for our public
# surface. Images / fonts are already binary-optimised.
COMPRESSIBLE_SUFFIXES = (".css", ".js", ".svg", ".json", ".txt", ".map")


class Command(BaseCommand):
    help = "Pre-compress static .css/.js into .gz companions for WhiteNoise."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Rewrite all .gz files regardless of mtime.",
        )

    def handle(self, *args, **options):
        force = options["force"]
        targets = self._collect_targets()
        if not targets:
            self.stdout.write("No compressible static files found.")
            return

        written = 0
        skipped_fresh = 0
        for source in targets:
            gz_path = Path(str(source) + ".gz")
            if not force and gz_path.exists():
                if gz_path.stat().st_mtime >= source.stat().st_mtime:
                    skipped_fresh += 1
                    continue
            self._write_gz(source, gz_path)
            written += 1

        total = len(targets)
        self.stdout.write(
            f"Compressed {written} file(s). Skipped {skipped_fresh} fresh. "
            f"({total} total compressible.)"
        )

    def _collect_targets(self) -> list[Path]:
        """Walk project-owned static dirs and return the source files
        whose extension is in COMPRESSIBLE_SUFFIXES.

        Important: we deliberately do NOT walk the finder list, because
        the AppDirectoriesFinder also surfaces third-party static dirs
        living inside `.venv/` (Django admin, DRF, etc.). Writing `.gz`
        companions next to those would pollute the venv and is the
        wrong place anyway — third-party static gets compressed at
        deploy time via `collectstatic` + WhiteNoise's compressed
        storage. Here we only compress files we own under
        `BASE_DIR/static/` and any explicit `STATICFILES_DIRS`
        entries that point inside `BASE_DIR`.
        """
        base = Path(settings.BASE_DIR).resolve()
        roots: set[Path] = set()
        repo_static = base / "static"
        if repo_static.is_dir():
            roots.add(repo_static)
        for entry in getattr(settings, "STATICFILES_DIRS", []):
            path = entry if isinstance(entry, (str, Path)) else entry[1]
            resolved = Path(path).resolve()
            try:
                resolved.relative_to(base)
            except ValueError:
                # outside the project tree (.venv, site-packages, ...)
                continue
            if resolved.is_dir():
                roots.add(resolved)

        # STATIC_ROOT is *output* — collectstatic populates it. We exclude
        # it here because compressing it would double-compress the same
        # logical file. CI may still call `collectstatic` separately if
        # needed.
        excluded = {Path(settings.STATIC_ROOT).resolve()} if settings.STATIC_ROOT else set()

        targets: list[Path] = []
        for root in sorted(roots):
            if root in excluded:
                continue
            if not root.exists():
                continue
            for f in root.rglob("*"):
                if not f.is_file():
                    continue
                if f.suffix.lower() not in COMPRESSIBLE_SUFFIXES:
                    continue
                # Skip the .gz / .br companions themselves.
                if f.name.endswith(".gz") or f.name.endswith(".br"):
                    continue
                targets.append(f)
        # `finders` is imported for future extensibility (e.g. a
        # --include-third-party flag) but intentionally unused today.
        _ = finders
        return targets

    def _write_gz(self, source: Path, dest: Path) -> None:
        # gzip.open() doesn't accept mtime; wrap an explicit GzipFile
        # so we can pin mtime=0 → deterministic output regardless of
        # when we ran the command (important for reproducible builds).
        data = source.read_bytes()
        with open(dest, "wb") as raw:
            with gzip.GzipFile(
                filename="", fileobj=raw, mode="wb", compresslevel=9, mtime=0
            ) as out:
                out.write(data)
