"""Remove orphan attachment files left under ``MEDIA_ROOT/legal_sources``.

Durable hygiene companion to the test-isolation fix in ``conftest.py``. Test
runs that created ``LegalSourceAttachment`` rows before ``MEDIA_ROOT`` was
isolated wrote real PDFs into the repo ``media/`` tree; because Django's
``FileSystemStorage`` appends a random suffix on every name collision, the same
bytes piled up across runs (~28k orphan files / 54 MB observed).

This command lists every file under ``MEDIA_ROOT/legal_sources`` that is NOT
referenced by any live ``LegalSourceAttachment.file`` and (only with
``--delete``) removes it. It is **dry-run by default** and never touches a path
that a DB row points at, so the 8 real attachments stay intact.
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.legal_sources.models import LegalSourceAttachment

_SUBTREE = "legal_sources"


class Command(BaseCommand):
    help = (
        "List (and with --delete remove) orphan files under "
        "MEDIA_ROOT/legal_sources not referenced by any LegalSourceAttachment."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Actually delete the orphan files. Without it the command is a dry-run.",
        )

    def handle(self, *args, **options):
        delete = options["delete"]
        media_root = Path(settings.MEDIA_ROOT)
        base = media_root / _SUBTREE

        # Referenced paths, normalised to absolute resolved paths.
        referenced: set[Path] = set()
        for att in LegalSourceAttachment.objects.exclude(file=""):
            name = att.file.name
            if not name:
                continue
            referenced.add((media_root / name).resolve())

        if not base.is_dir():
            self.stdout.write(
                self.style.WARNING(f"No directory at {base} — nothing to clean.")
            )
            return

        on_disk = [p for p in base.rglob("*") if p.is_file()]
        orphans = [p for p in on_disk if p.resolve() not in referenced]
        kept = len(on_disk) - len(orphans)
        orphan_bytes = sum(p.stat().st_size for p in orphans)

        self.stdout.write(
            f"Scanned {len(on_disk)} files under {base}: "
            f"{kept} referenced, {len(orphans)} orphan "
            f"({orphan_bytes / 1_048_576:.1f} MB)."
        )
        self.stdout.write(f"Referenced (kept): {len(referenced)} DB attachment path(s).")

        if not orphans:
            self.stdout.write(self.style.SUCCESS("No orphans. Tree is clean."))
            return

        if not delete:
            self.stdout.write(
                self.style.WARNING(
                    "DRY-RUN: nothing deleted. Re-run with --delete to remove the "
                    f"{len(orphans)} orphan file(s)."
                )
            )
            return

        removed = 0
        for p in orphans:
            try:
                p.unlink()
                removed += 1
            except OSError as exc:  # pragma: no cover - defensive
                self.stderr.write(f"Could not remove {p}: {exc}")

        # Prune now-empty directories (deepest first), but never the base itself.
        for d in sorted(
            (p for p in base.rglob("*") if p.is_dir()),
            key=lambda p: len(p.parts),
            reverse=True,
        ):
            try:
                next(d.iterdir())
            except StopIteration:
                d.rmdir()
            except OSError:  # pragma: no cover - defensive
                pass

        self.stdout.write(
            self.style.SUCCESS(
                f"Deleted {removed} orphan file(s), freed "
                f"{orphan_bytes / 1_048_576:.1f} MB. Kept {kept} referenced file(s)."
            )
        )
