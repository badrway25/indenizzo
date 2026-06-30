"""
Pexels API client + manifest cache (F-product-pexels-image-integration).

Sorgente immagini professionali per home + country landing. Strategia:

- **Mai dal browser**: tutte le chiamate Pexels avvengono SOLO da
  comando admin (`fetch_pexels_site_images`) o da script offline.
  Il rendering pubblico legge unicamente file locali + manifest JSON.
- **Mai esposta la API key**: la key è letta da
  `settings.PEXELS_API_KEY` (env-only). Niente log, niente HTML,
  niente errori che la stampino, niente attribution che la includa.
- **Fail-safe**: senza key, il modulo solleva `PexelsAPIKeyMissing`
  e i caller hanno l'onere di gestire il fallback. Il rendering
  pubblico (`apps/core/views.py`) NON chiama questo modulo
  direttamente: legge solo il manifest, che può essere assente.
- **Attribution obbligatoria**: la licenza Pexels richiede di citare
  fotografo + link Pexels quando si usa la foto. Lo serviamo come
  campo "Photo by X on Pexels" nei template.
- **Cache locale**: `media/pexels/<purpose>__<country>__<photo_id>.jpg`
  (auto-gitignored via `media/`). Il manifest siede a
  `media/pexels/pexels_manifest.json` e mappa
  (purpose, country) → entry locale.

Niente dipendenza pesante: usiamo `requests` (già nel venv).
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configurazione & errori
# ---------------------------------------------------------------------------


class PexelsAPIKeyMissing(RuntimeError):
    """`PEXELS_API_KEY` vuota: nessuna chiamata Pexels è permessa."""


class PexelsAPIError(RuntimeError):
    """Errore HTTP non recuperabile (401/403/429/5xx)."""


@dataclass(frozen=True)
class PexelsPhoto:
    """
    Subset minimale di una photo Pexels rilevante per la nostra UI.

    Questi sono gli unici campi che salviamo nel manifest e
    rendiamo nei template. NON salviamo URL remote in
    `og:image`/template HTML: le foto vengono scaricate localmente.
    """

    id: int
    width: int
    height: int
    photographer: str
    photographer_url: str
    pexels_url: str
    alt: str
    src_original: str
    src_large: str
    src_landscape: str

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> PexelsPhoto:
        src = payload.get("src") or {}
        return cls(
            id=int(payload["id"]),
            width=int(payload.get("width", 0)),
            height=int(payload.get("height", 0)),
            photographer=str(payload.get("photographer") or "Unknown"),
            photographer_url=str(payload.get("photographer_url") or ""),
            pexels_url=str(payload.get("url") or ""),
            alt=str(payload.get("alt") or ""),
            src_original=str(src.get("original") or ""),
            src_large=str(src.get("large2x") or src.get("large") or ""),
            src_landscape=str(src.get("landscape") or src.get("large") or ""),
        )


@dataclass
class ManifestEntry:
    """Una entry locale del manifest cache."""

    purpose: str
    country_code: str | None
    query: str
    local_path: str
    photo_id: int
    photographer: str
    photographer_url: str
    pexels_url: str
    alt: str
    width: int
    height: int
    downloaded_at: str
    sha256: str
    extra: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Mapping curato slot → query
# ---------------------------------------------------------------------------

# Tono: istituzionale, architettura/uffici/documenti. Niente incidenti
# stradali, niente persone ferite, niente sensazionalismo. Tutte
# preferenze landscape per coerenza con hero/og:image (ratio 16:9 ish).
SITE_IMAGE_SLOTS: list[dict[str, Any]] = [
    # Public landings & navigation
    {"purpose": "home_hero", "country": None, "query": "elegant law office interior"},
    {
        "purpose": "countries_index",
        "country": None,
        "query": "international legal documents office",
    },
    # Country landing pages (5)
    {"purpose": "country_landing", "country": "IT", "query": "Rome courthouse architecture"},
    {"purpose": "country_landing", "country": "FR", "query": "Paris courthouse architecture"},
    {"purpose": "country_landing", "country": "BE", "query": "Brussels courthouse architecture"},
    {"purpose": "country_landing", "country": "MA", "query": "Morocco architecture courthouse"},
    {"purpose": "country_landing", "country": "TN", "query": "Tunis architecture courthouse"},
    # Methodology + wizard
    {"purpose": "methodology_hero", "country": None, "query": "legal documents desk premium"},
    {"purpose": "wizard_start_hero", "country": None, "query": "law office consultation table"},
    # Wizard country forms (5)
    {
        "purpose": "wizard_italy_road_accident_hero",
        "country": "IT",
        "query": "Italian courthouse architecture",
    },
    {
        "purpose": "wizard_france_road_accident_hero",
        "country": "FR",
        "query": "French courthouse architecture",
    },
    {
        "purpose": "wizard_belgium_road_accident_hero",
        "country": "BE",
        "query": "Belgian courthouse architecture",
    },
    {
        "purpose": "wizard_morocco_inheritance_hero",
        "country": "MA",
        "query": "Moroccan legal documents",
    },
    {
        "purpose": "wizard_tunisia_inheritance_hero",
        "country": "TN",
        "query": "Tunisian architecture courthouse",
    },
    # Contact
    {"purpose": "contact_hero", "country": None, "query": "law office consultation"},
    # P6: section heroes for the content pages that lacked an image.
    {"purpose": "services_hero", "country": None, "query": "professional legal documents desk"},
    {"purpose": "about_hero", "country": None, "query": "law firm office interior"},
    {"purpose": "ta3ouid_hero", "country": None, "query": "Mediterranean architecture legal office"},
    # P7: complete the content-page hero coverage.
    {"purpose": "how_it_works_hero", "country": None, "query": "justice scales detail desk"},
    {"purpose": "faq_hero", "country": None, "query": "law books shelves library"},
    # P32: dedicated heroes for the P28-P31 platform pages (document intelligence,
    # sources library, case types, dossier result, guided router).
    {"purpose": "documents_hero", "country": None, "query": "organised legal documents desk dossier"},
    {"purpose": "sources_hero", "country": None, "query": "law library archive official volumes"},
    {"purpose": "case_types_hero", "country": None, "query": "law books justice scales detail"},
    {"purpose": "result_hero", "country": None, "query": "premium legal report documents desk"},
    {"purpose": "guided_hero", "country": None, "query": "consultation desk legal advisor documents"},
    # P36: home "what do you want to do?" intent cards (section imagery).
    {"purpose": "intent_estimate", "country": None, "query": "balance scales documents desk office"},
    {"purpose": "intent_offer", "country": None, "query": "business contract pen signed desk"},
    {"purpose": "intent_documents", "country": None, "query": "tidy office desk files folders"},
    {"purpose": "intent_law", "country": None, "query": "globe classic law books wood"},
    # P39: internal body imagery (not heroes) — sources library, source document
    # sheet, human result report, and the three service sections + guided path.
    {"purpose": "sources_body", "country": None, "query": "elegant law library wooden bookshelves"},
    {"purpose": "source_document", "country": None, "query": "official documents desk papers folder"},
    {"purpose": "result_report", "country": None, "query": "professional reviewing legal report desk"},
    {"purpose": "services_estimate", "country": None, "query": "balance scales legal documents wooden desk"},
    {"purpose": "services_documents", "country": None, "query": "neat office binders files folders desk"},
    {"purpose": "services_international", "country": None, "query": "world globe law books international desk"},
    {"purpose": "guided_workflow", "country": None, "query": "lawyers reviewing documents law books desk"},
]


def manifest_slot_key(purpose: str, country_code: str | None) -> str:
    """Chiave canonica del manifest per (purpose, country_code)."""
    cc = (country_code or "GLOBAL").upper()
    return f"{purpose}::{cc}"


# ---------------------------------------------------------------------------
# Overrides system (pass curation-1)
# ---------------------------------------------------------------------------

# Path al file JSON con override editoriale per slot.
# Schema: {"slots": {"<purpose>" o "<purpose>_<COUNTRY_ISO>": {...}}}.
# Mai contiene secret; sempre committabile.
_OVERRIDES_PATH = (
    Path(getattr(settings, "BASE_DIR", ".")) / "config" / "pexels_image_overrides.json"
)


def override_lookup_key(purpose: str, country_code: str | None) -> str:
    """Chiave usata nel JSON override per la slot. Es. `country_landing_IT`."""
    if country_code:
        return f"{purpose}_{country_code.upper()}"
    return purpose


def load_overrides() -> dict[str, dict[str, Any]]:
    """
    Legge `config/pexels_image_overrides.json`. Ritorna `{}` se assente o
    corrotto: il fetch deve restare possibile senza override.
    """
    if not _OVERRIDES_PATH.exists():
        return {}
    try:
        with _OVERRIDES_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.warning("Pexels overrides unreadable, ignoring.")
        return {}
    slots = data.get("slots") if isinstance(data, dict) else None
    return slots if isinstance(slots, dict) else {}


def slot_override(
    purpose: str,
    country_code: str | None,
    overrides: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Ritorna l'override per la slot, o `{}` se non definito."""
    overrides = overrides if overrides is not None else load_overrides()
    return overrides.get(override_lookup_key(purpose, country_code), {}) or {}


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def pexels_cache_dir() -> Path:
    """Directory di cache (media/pexels/). Creata on-demand."""
    base = Path(getattr(settings, "MEDIA_ROOT", "media")) / "pexels"
    base.mkdir(parents=True, exist_ok=True)
    return base


def pexels_manifest_path() -> Path:
    """Path del file manifest JSON."""
    return pexels_cache_dir() / "pexels_manifest.json"


# ---------------------------------------------------------------------------
# Manifest I/O
# ---------------------------------------------------------------------------


def load_manifest() -> dict[str, dict[str, Any]]:
    """
    Legge il manifest. Ritorna `{}` se il file non esiste o è
    corrotto: il sito deve restare servibile anche senza cache.

    NON solleva mai: il render pubblico chiama questo loader e il
    fail-soft è una feature, non un bug.
    """
    path = pexels_manifest_path()
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return data
    except (json.JSONDecodeError, OSError):
        logger.warning("Pexels manifest unreadable, falling back to empty.")
        return {}


def save_manifest(manifest: dict[str, dict[str, Any]]) -> None:
    """Scrive il manifest in modo atomico (tmp + rename)."""
    path = pexels_manifest_path()
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False, sort_keys=True)
    tmp.replace(path)


def manifest_lookup(
    manifest: dict[str, dict[str, Any]],
    *,
    purpose: str,
    country_code: str | None,
) -> dict[str, Any] | None:
    """Ritorna l'entry per la slot, o None."""
    return manifest.get(manifest_slot_key(purpose, country_code))


# ---------------------------------------------------------------------------
# HTTP client (sync, requests)
# ---------------------------------------------------------------------------


def _api_key() -> str:
    """Legge la key dai settings. Solleva se vuota."""
    key = getattr(settings, "PEXELS_API_KEY", "") or ""
    if not key:
        raise PexelsAPIKeyMissing(
            "PEXELS_API_KEY is empty. Set the env var to enable Pexels integration; "
            "without it, the site falls back to local placeholders."
        )
    return key


def _auth_headers() -> dict[str, str]:
    """
    Header Authorization Pexels: la key va inviata RAW, senza
    `Bearer ` prefix (Pexels ha il suo schema custom).
    """
    return {
        "Authorization": _api_key(),
        "User-Agent": "studio-legale-badrane-platform/1.0 (+legaltech, server-side)",
    }


def _base_url() -> str:
    return getattr(settings, "PEXELS_API_BASE_URL", "https://api.pexels.com/v1").rstrip("/")


def _safe_request(method: str, url: str, **kwargs: Any) -> requests.Response:
    """
    Wrapper che converte 401/403/429/5xx in `PexelsAPIError` con
    messaggio utile MA SENZA la API key.
    """
    timeout = kwargs.pop("timeout", 30)
    try:
        resp = requests.request(method, url, timeout=timeout, **kwargs)
    except requests.RequestException as exc:
        # Non includere kwargs.get("headers") nel log: contiene la key.
        logger.warning("Pexels request failed: %s", exc.__class__.__name__)
        raise PexelsAPIError(f"network error contacting Pexels: {exc.__class__.__name__}") from exc

    if resp.status_code == 401:
        raise PexelsAPIError("Pexels rejected the API key (401). Verify PEXELS_API_KEY env.")
    if resp.status_code == 403:
        raise PexelsAPIError("Pexels forbidden (403). Possibly disabled key or quota.")
    if resp.status_code == 429:
        raise PexelsAPIError("Pexels rate-limit hit (429). Retry later.")
    if 500 <= resp.status_code < 600:
        raise PexelsAPIError(f"Pexels server error ({resp.status_code}).")
    if resp.status_code >= 400:
        raise PexelsAPIError(f"Pexels HTTP {resp.status_code}.")
    return resp


def search_photos(
    query: str,
    *,
    orientation: str | None = None,
    per_page: int | None = None,
) -> list[PexelsPhoto]:
    """
    `GET /v1/search?query=...&orientation=...&per_page=...`

    Ritorna la lista di `PexelsPhoto` (vuota se nessun match).
    Solleva `PexelsAPIKeyMissing` se key vuota,
    `PexelsAPIError` su 401/403/429/5xx/network.
    """
    if not query.strip():
        return []
    orientation = orientation or getattr(settings, "PEXELS_DEFAULT_ORIENTATION", "landscape")
    per_page = per_page or getattr(settings, "PEXELS_DEFAULT_PER_PAGE", 10)
    url = f"{_base_url()}/search"
    resp = _safe_request(
        "GET",
        url,
        params={
            "query": query,
            "orientation": orientation,
            "per_page": per_page,
        },
        headers=_auth_headers(),
    )
    payload = resp.json() or {}
    photos = payload.get("photos") or []
    return [PexelsPhoto.from_api(p) for p in photos if isinstance(p, dict)]


def curated_photos(*, per_page: int | None = None) -> list[PexelsPhoto]:
    """`GET /v1/curated?per_page=...` — fallback se la search non rende nulla."""
    per_page = per_page or getattr(settings, "PEXELS_DEFAULT_PER_PAGE", 10)
    url = f"{_base_url()}/curated"
    resp = _safe_request(
        "GET",
        url,
        params={"per_page": per_page},
        headers=_auth_headers(),
    )
    payload = resp.json() or {}
    photos = payload.get("photos") or []
    return [PexelsPhoto.from_api(p) for p in photos if isinstance(p, dict)]


def photo_by_id(photo_id: int) -> PexelsPhoto | None:
    """
    `GET /v1/photos/{id}` — recupera una foto specifica per pin manuale.

    Ritorna None se 404; solleva `PexelsAPIError` su altri errori.
    """
    url = f"{_base_url()}/photos/{int(photo_id)}"
    try:
        resp = _safe_request("GET", url, headers=_auth_headers())
    except PexelsAPIError as exc:
        if "404" in str(exc):
            return None
        raise
    payload = resp.json() or {}
    return PexelsPhoto.from_api(payload) if "id" in payload else None


def _photo_text_blob(photo: PexelsPhoto) -> str:
    """Lower-cased haystack su cui matchare avoid_terms (alt + URL)."""
    return f"{photo.alt or ''} {photo.pexels_url or ''}".lower()


def select_best_photo(
    query: str,
    *,
    country_code: str | None = None,  # noqa: ARG001 — riservato a heuristiche future
    purpose: str | None = None,  # noqa: ARG001
    orientation: str | None = None,
    per_page: int | None = None,
    avoid_terms: list[str] | None = None,
) -> PexelsPhoto | None:
    """
    Sceglie la foto "migliore" per la slot. Heuristic:

    1. landscape con altezza ≥ 600px;
    2. NESSUNO degli `avoid_terms` (case-insensitive) compare in
       `photo.alt` né in `photo.pexels_url`;
    3. fallback alla prima foto della search se nessuna soddisfa.

    Restituisce None se zero risultati totali.
    """
    photos = search_photos(query, orientation=orientation, per_page=per_page)
    if not photos:
        return None
    avoid = [t.lower() for t in (avoid_terms or []) if t]

    def is_landscape_min(p: PexelsPhoto) -> bool:
        return p.height >= 600 and p.width >= p.height

    def passes_avoid(p: PexelsPhoto) -> bool:
        if not avoid:
            return True
        blob = _photo_text_blob(p)
        return not any(term in blob for term in avoid)

    # Pass 1: landscape + passes avoid.
    for photo in photos:
        if is_landscape_min(photo) and passes_avoid(photo):
            return photo
    # Pass 2: any photo passing avoid.
    for photo in photos:
        if passes_avoid(photo):
            return photo
    # Pass 3: fallback (avoid filter would empty the list).
    return photos[0]


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


def _safe_filename(purpose: str, country_code: str | None, photo_id: int) -> str:
    """`country_landing__IT__1234567.jpg` — solo ASCII, no spazi."""
    cc = (country_code or "global").lower()
    purpose_clean = re.sub(r"[^a-z0-9_]", "_", purpose.lower())
    return f"{purpose_clean}__{cc}__{int(photo_id)}.jpg"


def download_pexels_photo(
    photo: PexelsPhoto,
    *,
    target_path: Path,
    timeout: int = 30,
) -> dict[str, Any]:
    """
    Scarica `photo.src_landscape` (o fallback) sul disco.

    Ritorna metadata: `{"local_path": str, "sha256": str,
    "size_bytes": int}`. Niente API key necessaria per il download
    (Pexels CDN è pubblico).
    """
    src = photo.src_landscape or photo.src_large or photo.src_original
    if not src:
        raise PexelsAPIError(f"photo {photo.id} has no usable src URL")
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Niente Authorization sul CDN (la key NON va inviata fuori da api.pexels.com).
    try:
        resp = requests.get(src, timeout=timeout, stream=True)
    except requests.RequestException as exc:
        raise PexelsAPIError(f"CDN error: {exc.__class__.__name__}") from exc
    if resp.status_code != 200:
        raise PexelsAPIError(f"CDN returned HTTP {resp.status_code} for photo {photo.id}")

    sha = hashlib.sha256()
    size = 0
    with target_path.open("wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if not chunk:
                continue
            f.write(chunk)
            sha.update(chunk)
            size += len(chunk)
    return {
        "local_path": str(target_path),
        "sha256": sha.hexdigest(),
        "size_bytes": size,
    }


# ---------------------------------------------------------------------------
# Orchestration helpers per il management command
# ---------------------------------------------------------------------------


def fetch_one_slot(
    slot: dict[str, Any],
    *,
    force: bool = False,
    orientation: str | None = None,
    per_page: int | None = None,
    pinned_photo_id: int | None = None,
    overrides: dict[str, dict[str, Any]] | None = None,
) -> ManifestEntry | None:
    """
    Esegue search + download per una slot e ritorna la `ManifestEntry`.

    Logica override (pass curation-1):
    1. Se `pinned_photo_id` è esplicito, usa direttamente
       `photo_by_id(pinned_photo_id)`.
    2. Altrimenti, se l'override JSON ha `photo_id` valorizzato, idem.
    3. Altrimenti, search con la `query` dell'override (se presente)
       o con quella di default della slot. Applica `avoid_terms` per
       filtrare risultati fuori contesto.

    Caller del comando si occupa di aggiornare il manifest e stampare
    attribution.
    """
    purpose = slot["purpose"]
    country = slot.get("country")
    default_query = slot["query"]

    over = slot_override(purpose, country, overrides=overrides)
    query = over.get("query") or default_query
    avoid_terms = over.get("avoid_terms") or []
    pin_from_override = over.get("photo_id")
    pin = pinned_photo_id if pinned_photo_id is not None else pin_from_override

    if pin:
        photo = photo_by_id(int(pin))
    else:
        photo = select_best_photo(
            query,
            country_code=country,
            purpose=purpose,
            orientation=orientation,
            per_page=per_page,
            avoid_terms=avoid_terms,
        )
    if photo is None:
        return None

    fname = _safe_filename(purpose, country, photo.id)
    target = pexels_cache_dir() / fname
    if target.exists() and not force:
        sha = _hash_file(target)
        size = target.stat().st_size
    else:
        meta = download_pexels_photo(photo, target_path=target)
        sha = meta["sha256"]
        size = meta["size_bytes"]

    return ManifestEntry(
        purpose=purpose,
        country_code=country,
        query=query,
        local_path=(Path("pexels") / fname).as_posix(),
        photo_id=photo.id,
        photographer=photo.photographer,
        photographer_url=photo.photographer_url,
        pexels_url=photo.pexels_url,
        alt=photo.alt,
        width=photo.width,
        height=photo.height,
        downloaded_at=datetime.now(UTC).isoformat(),
        sha256=sha,
        extra={"size_bytes": size},
    )


def _hash_file(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


def upsert_manifest_entry(
    manifest: dict[str, dict[str, Any]],
    entry: ManifestEntry,
) -> None:
    """Modifica `manifest` in-place inserendo/sovrascrivendo la entry."""
    key = manifest_slot_key(entry.purpose, entry.country_code)
    manifest[key] = asdict(entry)


# ---------------------------------------------------------------------------
# Lookup pubblico per views/template (read-only, no rete)
# ---------------------------------------------------------------------------


def get_image_for_country_landing(country_code: str) -> dict[str, Any] | None:
    """
    Ritorna la entry manifest per la country landing del paese,
    oppure None. Non chiama mai Pexels.

    `country_code` è in lowercase (`"italy"`, `"france"`, ecc.) come
    nel context del template; lo convertiamo a ISO upper per la
    chiave manifest.
    """
    iso = _country_to_iso(country_code)
    manifest = load_manifest()
    return manifest_lookup(manifest, purpose="country_landing", country_code=iso)


def get_image_for_slot(
    purpose: str,
    country_code: str | None = None,
) -> dict[str, Any] | None:
    """
    Lookup generico read-only del manifest per qualunque slot del
    sito (home_hero, methodology_hero, wizard_*_hero, contact_hero, …).

    Niente rete. Ritorna None se la entry manca: il template deve
    avere un fallback elegante.
    """
    manifest = load_manifest()
    return manifest_lookup(manifest, purpose=purpose, country_code=country_code)


_COUNTRY_LOWER_TO_ISO = {
    "italy": "IT",
    "france": "FR",
    "belgium": "BE",
    "morocco": "MA",
    "tunisia": "TN",
}


def _country_to_iso(country_code: str) -> str:
    """`'italy'` → `'IT'`, già ISO se già upper-case."""
    return _COUNTRY_LOWER_TO_ISO.get(country_code.lower(), country_code.upper())


def attribution_for_entry(entry: dict[str, Any]) -> str:
    """
    Stringa attribution conforme a Pexels license:
    `"Photo by <photographer> on Pexels"`.
    """
    name = (entry.get("photographer") or "Unknown").strip()
    return f"Photo by {name} on Pexels"


def media_url_for_entry(entry: dict[str, Any]) -> str:
    """
    URL servibile dell'immagine locale (relativo a `MEDIA_URL`).
    Es: `/media/pexels/country_landing__it__123.jpg`.
    """
    media_url = getattr(settings, "MEDIA_URL", "/media/").rstrip("/")
    local = entry.get("local_path", "").lstrip("/")
    # `local_path` è già `pexels/<fname>` rispetto a MEDIA_ROOT.
    return f"{media_url}/{quote(local)}"
