"""
Read-only check del database backend attivo.

Iter: F-local-product-hardening-pass4-postgres-prep.

Uso:
    .venv/Scripts/python.exe scripts/staging/check_database_backend.py

Stampa:
- engine Django attivo (es. `django.db.backends.sqlite3`,
  `django.db.backends.postgresql`);
- vendor connection (es. `sqlite`, `postgresql`);
- database name (path file SQLite o nome DB Postgres);
- DEBUG flag corrente;
- count migrazioni applicate.

Politica exit code:
- vendor=sqlite → ritorna 0 ma stampa WARNING (è OK in dev, non OK in
  produzione; il chiamante decide).
- vendor=postgresql → stampa OK.
- vendor sconosciuto → ritorna 1.

NON modifica DB, NON applica migrate, NON crea record.
"""

from __future__ import annotations

import os
import pathlib
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _bootstrap_django() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import django

    django.setup()


def main() -> int:
    _bootstrap_django()
    from django.conf import settings
    from django.db import connection
    from django.db.migrations.loader import MigrationLoader

    engine = connection.settings_dict.get("ENGINE", "?")
    vendor = connection.vendor
    name = connection.settings_dict.get("NAME", "?")
    debug = bool(getattr(settings, "DEBUG", False))

    loader = MigrationLoader(connection)
    applied_count = len(loader.applied_migrations)

    print("=" * 64)
    print("DATABASE BACKEND CHECK (read-only)")
    print("=" * 64)
    print(f"engine:             {engine}")
    print(f"vendor:             {vendor}")
    print(f"name:               {name}")
    print(f"DEBUG:              {debug}")
    print(f"applied migrations: {applied_count}")
    print()

    if vendor == "postgresql":
        print("[OK] Postgres backend attivo. Coerente con CLAUDE.md per produzione.")
        return 0
    if vendor == "sqlite":
        print(
            "[WARNING] Backend = SQLite. OK per sviluppo locale; CLAUDE.md richiede "
            "Postgres in produzione. Configurare DATABASE_URL=postgres://… per "
            "lo staging/prod prima del deploy."
        )
        return 0
    print(f"[ERROR] vendor sconosciuto: {vendor!r}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
