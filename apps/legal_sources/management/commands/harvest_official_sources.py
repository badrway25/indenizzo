"""
P50: controlled, allowlisted harvest probe for OFFICIAL legal sources.

This complements ``download_international_legal_sources`` (which downloads the
FR/BE/MA/TN packages) by adding a SAFE, official-domain-only reachability +
metadata probe across every (country, category) — including IT INAIL and the new
categories — without touching the database and without committing heavy files.

ABSOLUTE RULES (enforced here):
- **Official domains only**: a target whose host is not in ``ALLOWED_DOMAINS`` is
  refused (never fetched). No blogs, no commercial tables, no private studies.
- **robots.txt is respected**: the path is fetched only if robots allows our
  user-agent; otherwise it is skipped with ``robots_allowed=False``.
- **No aggressive scraping**: one request per target, a transparent User-Agent, a
  timeout, no crawling, no retries beyond one.
- **No CAPTCHA / paywall / login bypass.**
- **No calculation, no engine, no approved data, no canary is created here.** A
  fetched table is *evidence*, not a validated source. Turning it into a public
  monetary estimate requires a legal reviewer to validate the table + fill the
  canary in ``docs/legal_validation/`` — never this command.
- **No heavy files committed**: only a small JSON manifest under the gitignored
  ``media/legal_harvest/`` is written; response bodies are hashed but not stored
  unless small (<= ``MAX_SNAPSHOT_BYTES``) and HTML.

Usage:
    python manage.py harvest_official_sources --dry-run
    python manage.py harvest_official_sources --country IT --category INAIL
    python manage.py harvest_official_sources --country MA --category ROAD
"""

from __future__ import annotations

import hashlib
import json
import urllib.robotparser
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

USER_AGENT = "StudioLegaleBadrane-OfficialSourceHarvest/1.0 (+legaltech research; respects robots.txt)"
TIMEOUT_SECONDS = 20
MAX_SNAPSHOT_BYTES = 512 * 1024  # only hash/snapshot small responses

# Only these official hosts may ever be fetched. Ministries, official gazettes,
# public bodies, national authorities, legislative portals, EU institutions.
ALLOWED_DOMAINS = frozenset({
    "www.normattiva.it", "normattiva.it",
    "www.gazzettaufficiale.it", "gazzettaufficiale.it",
    "www.inail.it", "inail.it",
    "eur-lex.europa.eu",
    "www.sgg.gov.ma", "sgg.gov.ma",
    "www.acaps.ma", "acaps.ma",
    "www.cga.gov.tn", "cga.gov.tn",
    "www.iort.gov.tn", "iort.gov.tn",
    "www.legislation.tn", "legislation.tn",
    "www.legifrance.gouv.fr", "legifrance.gouv.fr",
    "economie.fgov.be", "www.economie.fgov.be",
})

# (country, category, authority, url, doc_type, notes). URLs identified in the
# P40/P44/P47 audits. CATEGORY uses the short public keys used across the harvest.
TARGETS: list[dict[str, str]] = [
    {"country": "IT", "category": "ROAD", "authority": "Normattiva (Cod. Assicurazioni art. 139)",
     "url": "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legislativo:2005-09-07;209",
     "doc_type": "HTML", "notes": "Active engine already (CAP art.139 + TUN); harvest for provenance."},
    {"country": "IT", "category": "INAIL", "authority": "INAIL portal (D.M. 12/07/2000 menomazioni)",
     "url": "https://www.inail.it/", "doc_type": "PDF/HTML",
     "notes": "Indemnity table not machine-extractable from an accessible primary source."},
    {"country": "IT", "category": "INAIL", "authority": "Normattiva (D.Lgs. 38/2000)",
     "url": "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legislativo:2000-02-23;38",
     "doc_type": "HTML", "notes": "Legal basis of danno biologico INAIL."},
    {"country": "MA", "category": "ROAD", "authority": "ACAPS (Dahir 1-84-177 / guide)",
     "url": "https://www.acaps.ma/", "doc_type": "PDF",
     "notes": "Dahir barème is a scanned image (OCR needed); ACAPS guide is non-binding."},
    {"country": "MA", "category": "ROAD", "authority": "SGG (Bulletin Officiel)",
     "url": "https://www.sgg.gov.ma/", "doc_type": "PDF", "notes": "Official gazette for the Dahir."},
    {"country": "MA", "category": "LOSS", "authority": "SGG / Dahir ayants-droit",
     "url": "https://www.sgg.gov.ma/", "doc_type": "PDF",
     "notes": "Ayants-droit shares only inside the road-death barème."},
    {"country": "TN", "category": "ROAD", "authority": "CGA (Code des assurances Titre V)",
     "url": "https://www.cga.gov.tn/", "doc_type": "HTML/PDF",
     "notes": "Binding barème, not yet transcribed/validated."},
    {"country": "TN", "category": "ROAD", "authority": "IORT (Loi 2005-86)",
     "url": "https://www.iort.gov.tn/", "doc_type": "HTML", "notes": "Framework law."},
    {"country": "TN", "category": "LOSS", "authority": "CGA (Titre V décès/ayants-droit)",
     "url": "https://www.cga.gov.tn/", "doc_type": "HTML/PDF",
     "notes": "Death/ayants-droit distribution inside Titre V."},
    {"country": "FR", "category": "ROAD", "authority": "Légifrance (Loi Badinter 85-677)",
     "url": "https://www.legifrance.gouv.fr/", "doc_type": "HTML",
     "notes": "No binding State barème exists; Légifrance blocks non-browser agents (403)."},
    {"country": "BE", "category": "ROAD", "authority": "economie.fgov.be (Loi 21/11/1989)",
     "url": "https://economie.fgov.be/", "doc_type": "HTML",
     "notes": "Only the non-binding Tableau Indicatif; no binding State barème."},
    {"country": "EU", "category": "CROSS_BORDER", "authority": "EUR-Lex (Roma II 864/2007)",
     "url": "https://eur-lex.europa.eu/legal-content/IT/TXT/?uri=CELEX:32007R0864",
     "doc_type": "HTML/PDF", "notes": "Conflict-of-laws only; no tariff by design."},
    {"country": "EU", "category": "SUCCESSION", "authority": "EUR-Lex (Reg. 650/2012)",
     "url": "https://eur-lex.europa.eu/legal-content/IT/TXT/?uri=CELEX:32012R0650",
     "doc_type": "HTML/PDF", "notes": "Applicable-law framing only."},
]


def _manifest_dir() -> Path:
    d = Path(getattr(settings, "MEDIA_ROOT", "media")) / "legal_harvest"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _robots_allows(url: str) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser()
    try:
        resp = requests.get(robots_url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_SECONDS)
        if resp.status_code >= 400:
            return True  # no robots.txt → allowed
        rp.parse(resp.text.splitlines())
        return rp.can_fetch(USER_AGENT, url)
    except requests.RequestException:
        return True  # unreachable robots → do not block the probe; the fetch itself will record the error


class Command(BaseCommand):
    help = "Controlled, allowlisted harvest probe for official legal sources (no DB writes, no heavy commits)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Print the plan; make no network requests.")
        parser.add_argument("--country", type=str, help="Filter by country ISO (IT/MA/TN/FR/BE/EU).")
        parser.add_argument("--category", type=str, help="Filter by category (ROAD/INAIL/LOSS/SUCCESSION/CROSS_BORDER).")

    def handle(self, *args, **opts):
        country = (opts.get("country") or "").upper()
        category = (opts.get("category") or "").upper()
        targets = [
            t for t in TARGETS
            if (not country or t["country"] == country) and (not category or t["category"] == category)
        ]
        if not targets:
            self.stdout.write("No targets match the given filters.")
            return

        if opts.get("dry_run"):
            self.stdout.write(self.style.NOTICE("DRY-RUN — official-source harvest plan (no network):"))
            for t in targets:
                self.stdout.write(f"  [{t['country']}/{t['category']}] {t['authority']}")
                self.stdout.write(f"      url: {t['url']} ({t['doc_type']})")
                self.stdout.write(f"      note: {t['notes']}")
            self.stdout.write(self.style.WARNING(
                "No engine is created by harvesting. A legal reviewer must validate the table "
                "and fill the canary in docs/legal_validation/ before any public estimate."))
            return

        records = []
        for t in targets:
            host = urlparse(t["url"]).netloc
            if host not in ALLOWED_DOMAINS:
                records.append({**self._meta(t), "skipped": "non-official domain (refused)"})
                self.stdout.write(self.style.ERROR(f"REFUSED non-official domain: {host}"))
                continue
            robots_ok = _robots_allows(t["url"])
            rec = {**self._meta(t), "robots_allowed": robots_ok}
            if not robots_ok:
                rec["skipped"] = "robots.txt disallows"
                self.stdout.write(self.style.WARNING(f"robots.txt disallows {t['url']} — skipped"))
                records.append(rec)
                continue
            try:
                resp = requests.get(t["url"], headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
                                    timeout=TIMEOUT_SECONDS, stream=True)
                body = resp.raw.read(MAX_SNAPSHOT_BYTES + 1, decode_content=True) or b""
                rec.update({
                    "http_status": resp.status_code,
                    "content_type": resp.headers.get("Content-Type", ""),
                    "content_length": resp.headers.get("Content-Length", ""),
                    "sha256_first_chunk": hashlib.sha256(body[:MAX_SNAPSHOT_BYTES]).hexdigest()
                    if body else "",
                    "bytes_sampled": min(len(body), MAX_SNAPSHOT_BYTES),
                })
                self.stdout.write(f"[{t['country']}/{t['category']}] {host} -> HTTP {resp.status_code} "
                                  f"{resp.headers.get('Content-Type','')}")
            except requests.RequestException as exc:
                rec["error"] = exc.__class__.__name__
                self.stdout.write(self.style.WARNING(f"[{t['country']}/{t['category']}] {host} -> {exc.__class__.__name__}"))
            records.append(rec)

        manifest = {
            "harvested_with": USER_AGENT,
            "note": "Reachability + provenance probe only. No table is validated and no engine is created here.",
            "records": records,
        }
        path = _manifest_dir() / "harvest_manifest.json"
        path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Wrote provenance manifest -> {path} ({len(records)} records)."))
        self.stdout.write(self.style.WARNING(
            "Reminder: a fetched page is evidence, not a validated source. No public estimate "
            "is enabled until a legal reviewer validates the table and fills the canary."))

    def _meta(self, t: dict) -> dict:
        return {
            "country": t["country"], "category": t["category"], "authority": t["authority"],
            "url": t["url"], "doc_type": t["doc_type"], "notes": t["notes"],
            "fetched_at": datetime.now(UTC).isoformat(),
        }
