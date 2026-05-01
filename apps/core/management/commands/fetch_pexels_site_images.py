"""
`manage.py fetch_pexels_site_images` — populate Pexels image cache.

Iter base: F-product-pexels-image-integration.
Pass curation-1: aggiunti `--slot`, `--photo-id`, `--audit`; lettura
`config/pexels_image_overrides.json`.

Esegue le query (override-aware) definite in
`apps.core.pexels.SITE_IMAGE_SLOTS` + override e scarica una foto per
slot in `media/pexels/`. Aggiorna il manifest JSON con metadata +
attribution.

**Usage**:

    # vedi cosa farebbe senza scaricare
    python manage.py fetch_pexels_site_images --dry-run --all

    # audit del manifest corrente (zero rete)
    python manage.py fetch_pexels_site_images --audit

    # scarica solo una slot specifica
    python manage.py fetch_pexels_site_images --slot wizard_start_hero

    # pin manuale di una foto specifica per la slot
    python manage.py fetch_pexels_site_images --slot country_landing_MA --photo-id 12345678

    # ri-scarica anche se presente
    python manage.py fetch_pexels_site_images --all --force

**Sicurezza**: niente API key viene stampata, neppure in errori.
Senza `PEXELS_API_KEY` il comando esce con `CommandError`
leggibile e nessun side effect distruttivo.
"""

from __future__ import annotations

from dataclasses import asdict

from django.core.management.base import BaseCommand, CommandError

from apps.core import pexels


class Command(BaseCommand):
    help = "Scarica immagini Pexels per le slot del sito e aggiorna il manifest."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra cosa verrebbe scaricato senza salvare nulla.",
        )
        parser.add_argument(
            "--audit",
            action="store_true",
            help="Stampa il manifest corrente + status per slot. NIENTE rete, NIENTE API key richiesta.",
        )
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--country",
            help="Limita ad uno dei country code ISO (IT/FR/BE/MA/TN).",
        )
        group.add_argument(
            "--all",
            action="store_true",
            help="Tutte le slot definite in SITE_IMAGE_SLOTS.",
        )
        group.add_argument(
            "--slot",
            help=(
                "Override: scarica una sola slot per chiave override "
                "(es. 'home_hero', 'country_landing_IT', "
                "'wizard_morocco_inheritance_hero')."
            ),
        )
        parser.add_argument(
            "--photo-id",
            type=int,
            default=None,
            help="Pin manuale: scarica esattamente questo Pexels photo ID per la slot scelta.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Riscarica anche se l'entry è già nel manifest.",
        )
        parser.add_argument(
            "--per-page",
            type=int,
            default=None,
            help="Override per_page della query Pexels (default: settings).",
        )
        parser.add_argument(
            "--orientation",
            default=None,
            help="Override orientation (default: settings, normalmente 'landscape').",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        do_audit: bool = options["audit"]
        country: str | None = options.get("country")
        do_all: bool = options["all"]
        slot_key: str | None = options.get("slot")
        photo_id: int | None = options.get("photo_id")
        force: bool = options["force"]
        per_page: int | None = options["per_page"]
        orientation: str | None = options["orientation"]

        if do_audit:
            self._audit()
            return

        if not (country or do_all or slot_key):
            raise CommandError("Specify --country <ISO>, --all, --slot <NAME>, or --audit.")

        if photo_id is not None and not slot_key:
            raise CommandError("--photo-id requires --slot to identify the destination slot.")

        # Sanity: API key richiesta se vogliamo davvero scaricare.
        # Audit + dry-run = OK senza key.
        if not dry_run:
            try:
                pexels._api_key()
            except pexels.PexelsAPIKeyMissing as exc:
                raise CommandError(str(exc)) from exc

        slots = self._select_slots(country=country, do_all=do_all, slot_key=slot_key)
        if not slots:
            raise CommandError(f"No slots match country={country!r} slot={slot_key!r}.")

        if dry_run:
            self.stdout.write(self.style.NOTICE("DRY RUN — nessun download."))

        overrides = pexels.load_overrides()
        manifest = pexels.load_manifest()
        updated = 0
        skipped = 0
        for slot in slots:
            mkey = pexels.manifest_slot_key(slot["purpose"], slot.get("country"))
            ovkey = pexels.override_lookup_key(slot["purpose"], slot.get("country"))
            over = overrides.get(ovkey, {}) or {}
            effective_query = over.get("query") or slot["query"]
            existing = manifest.get(mkey)
            self.stdout.write(
                f"\n[{mkey}]"
                f"  query={effective_query!r}"
                f"  existing={'yes' if existing else 'no'}"
                f"  override={'yes' if over else 'no'}"
            )
            if existing and not force:
                self.stdout.write("  -> skip (use --force to redownload)")
                skipped += 1
                continue
            if dry_run:
                self.stdout.write("  -> would search Pexels (dry-run, no fetch)")
                continue
            try:
                entry = pexels.fetch_one_slot(
                    slot,
                    force=force,
                    orientation=orientation,
                    per_page=per_page,
                    pinned_photo_id=photo_id,
                    overrides=overrides,
                )
            except pexels.PexelsAPIError as exc:
                self.stdout.write(self.style.WARNING(f"  ! Pexels error: {exc}"))
                continue
            if entry is None:
                self.stdout.write(self.style.WARNING("  ! no candidates returned"))
                continue
            pexels.upsert_manifest_entry(manifest, entry)
            updated += 1
            self.stdout.write(
                f"  [ok] photo {entry.photo_id}  -> {entry.local_path}\n"
                f"    {pexels.attribution_for_entry(asdict(entry))}\n"
                f"    {entry.pexels_url}\n"
                f"    alt: {entry.alt[:80]}"
            )

        if not dry_run and updated:
            pexels.save_manifest(manifest)

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"Done. updated={updated} skipped={skipped} dry_run={dry_run}")
        )

    # ------------------------------------------------------------------
    # Audit (read-only, no network)
    # ------------------------------------------------------------------

    def _audit(self) -> None:
        """Stampa stato corrente: per ogni slot, presenza nel manifest +
        match con override + dimensioni + photo_id. Niente API key
        richiesta. Niente rete. Mai stampa la API key."""
        overrides = pexels.load_overrides()
        manifest = pexels.load_manifest()
        self.stdout.write(self.style.NOTICE("AUDIT — Pexels manifest snapshot (no network).\n"))
        for slot in pexels.SITE_IMAGE_SLOTS:
            purpose = slot["purpose"]
            country = slot.get("country")
            mkey = pexels.manifest_slot_key(purpose, country)
            ovkey = pexels.override_lookup_key(purpose, country)
            entry = manifest.get(mkey)
            over = overrides.get(ovkey, {}) or {}
            line = f"[{mkey}] override={'yes' if over else 'no'}"
            if entry:
                line += (
                    f"  photo_id={entry.get('photo_id')}"
                    f"  size={entry.get('width')}x{entry.get('height')}"
                    f"  file={entry.get('local_path')}"
                )
                self.stdout.write(line)
                if entry.get("pexels_url"):
                    self.stdout.write(f"    url: {entry.get('pexels_url')}")
                if entry.get("alt"):
                    self.stdout.write(f"    alt: {entry.get('alt')[:90]}")
            else:
                line += "  status=MISSING"
                self.stdout.write(self.style.WARNING(line))
            if over.get("editorial_notes"):
                self.stdout.write(f"    notes: {over['editorial_notes']}")
            self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Audit done. {len(manifest)} entries in manifest."))

    # ------------------------------------------------------------------
    # Slot resolution
    # ------------------------------------------------------------------

    def _select_slots(self, *, country: str | None, do_all: bool, slot_key: str | None):
        if do_all:
            return list(pexels.SITE_IMAGE_SLOTS)
        if slot_key:
            # `slot_key` può essere `purpose` (per slot global) o
            # `purpose_<COUNTRY_ISO>` (per slot country-specific).
            for s in pexels.SITE_IMAGE_SLOTS:
                if pexels.override_lookup_key(s["purpose"], s.get("country")) == slot_key:
                    return [s]
            return []
        target_iso = (country or "").upper()
        return [s for s in pexels.SITE_IMAGE_SLOTS if (s.get("country") or "") == target_iso]
