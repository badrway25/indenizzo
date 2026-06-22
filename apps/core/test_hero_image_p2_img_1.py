"""
Tests F-p2-img-1-hero-image-optimization.

Static + light-integration smoke tests for the hero-image WebP
optimisation. They do NOT call Lighthouse and do NOT fetch
Pexels — they verify:

 1. compress_pexels_images management command exists + imports
    Pillow lazily;
 2. command is scoped to MEDIA_ROOT/pexels (never .venv, never repo);
 3. command is idempotent (skips fresh companions);
 4. _pexels_hero returns webp_src / webp_src_mobile only when the
    companion files exist on disk;
 5. home.html emits <picture> + <source type="image/webp">;
 6. home.html emits <link rel="preload" as="image"> for the hero;
 7. _premium_hero_image partial also uses <picture>;
 8. no external image domain anywhere in templates touched;
 9. CSP still has no 'unsafe-inline' / 'unsafe-eval';
10. / and /ar/ render 200, with the expected dir + picture tags.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOME_HTML = REPO_ROOT / "templates" / "public" / "home.html"
HERO_PARTIAL = REPO_ROOT / "templates" / "partials" / "_premium_hero_image.html"
SETTINGS_PY = REPO_ROOT / "config" / "settings.py"
COMPRESS_CMD = REPO_ROOT / "apps" / "core" / "management" / "commands" / "compress_pexels_images.py"
VIEWS_PY = REPO_ROOT / "apps" / "core" / "views.py"
RUNNER_DESKTOP = REPO_ROOT / "scripts" / "run_lighthouse_local.sh"
RUNNER_MOBILE = REPO_ROOT / "scripts" / "run_lighthouse_mobile_local.sh"


# ---------------------------------------------------------------------------
# 1. Management command — exists + imports + sensible defaults
# ---------------------------------------------------------------------------


def test_compress_pexels_images_command_exists():
    assert COMPRESS_CMD.exists()


def test_compress_pexels_images_module_is_importable():
    from apps.core.management.commands import compress_pexels_images  # noqa: F401


def test_compress_pexels_images_defaults_are_sensible():
    from apps.core.management.commands import compress_pexels_images as mod

    # Quality bounds: desktop in [75, 95], mobile in [55, 80].
    assert 75 <= mod.DEFAULT_QUALITY <= 95
    assert 55 <= mod.DEFAULT_MOBILE_QUALITY <= 80
    # Mobile width should be small enough to actually be smaller than
    # the typical 1920-wide hero.
    assert mod.DEFAULT_MOBILE_MAX_WIDTH <= 1024


# ---------------------------------------------------------------------------
# 2-3. Scoped to MEDIA_ROOT/pexels, idempotent
# ---------------------------------------------------------------------------


def test_compress_pexels_images_is_scoped_to_pexels_dir(tmp_path, settings):
    """The command must walk only MEDIA_ROOT/pexels — never the repo
    tree, never .venv. Drive it against an empty tmp_path to confirm
    the early-return behaviour."""
    settings.MEDIA_ROOT = str(tmp_path)
    from apps.core.management.commands.compress_pexels_images import Command

    cmd = Command()
    out = io.StringIO()
    cmd.stdout = out
    cmd.handle(force=False, quality=80, mobile_quality=65, mobile_max_width=800)
    assert "nothing to compress" in out.getvalue()


def test_compress_pexels_images_is_idempotent(tmp_path, settings):
    """Run twice on the same tmp tree: the second run must skip
    fresh companions."""
    pillow = pytest.importorskip("PIL.Image")
    settings.MEDIA_ROOT = str(tmp_path)
    pexels = tmp_path / "pexels"
    pexels.mkdir()
    # Make a tiny 32x32 PNG (will be re-encoded as WebP).
    img = pillow.new("RGB", (32, 32), color=(0, 30, 60))
    img.save(pexels / "demo.png", format="PNG")

    from apps.core.management.commands.compress_pexels_images import Command

    cmd = Command()
    cmd.stdout = io.StringIO()
    cmd.handle(force=False, quality=80, mobile_quality=65, mobile_max_width=800)
    assert (pexels / "demo.webp").exists()
    assert (pexels / "demo.mobile.webp").exists()

    # Second pass: must skip both companions (fresh).
    out2 = io.StringIO()
    cmd.stdout = out2
    cmd.handle(force=False, quality=80, mobile_quality=65, mobile_max_width=800)
    assert "Skipped 2 fresh" in out2.getvalue()


# ---------------------------------------------------------------------------
# 4. _pexels_hero contract
# ---------------------------------------------------------------------------


def test_pexels_hero_returns_none_when_no_entry(tmp_path, settings, rf):
    settings.MEDIA_ROOT = str(tmp_path)
    from apps.core.views import _pexels_hero

    req = rf.get("/", HTTP_HOST="127.0.0.1")
    # No manifest entry exists for this purpose -> None.
    result = _pexels_hero(req, "this_purpose_does_not_exist")
    assert result is None


def test_pexels_hero_emits_webp_keys_only_when_files_exist(tmp_path, settings, rf, monkeypatch):
    """Stub `get_image_for_slot` to return a known entry; place / omit
    the WebP companions on disk; check `_pexels_hero`'s output."""
    settings.MEDIA_ROOT = str(tmp_path)
    pexels = tmp_path / "pexels"
    pexels.mkdir()
    # The source JPEG must exist for the contract to apply.
    (pexels / "hero.jpg").write_bytes(b"\xff\xd8\xff\xe0")

    fake_entry = {"local_path": "pexels/hero.jpg", "alt": "stub"}
    from apps.core import views as views_module

    monkeypatch.setattr(
        "apps.core.pexels.get_image_for_slot",
        lambda *a, **kw: fake_entry,
    )

    req = rf.get("/", HTTP_HOST="127.0.0.1")

    # No WebP companions yet -> webp_src / webp_src_mobile NOT in result.
    result = views_module._pexels_hero(req, "home_hero")
    assert result is not None
    assert "src" in result
    assert "webp_src" not in result
    assert "webp_src_mobile" not in result

    # Add desktop WebP only.
    (pexels / "hero.webp").write_bytes(b"\x52\x49\x46\x46")
    result = views_module._pexels_hero(req, "home_hero")
    assert "webp_src" in result
    assert "webp_src_mobile" not in result

    # Add mobile WebP too.
    (pexels / "hero.mobile.webp").write_bytes(b"\x52\x49\x46\x46")
    result = views_module._pexels_hero(req, "home_hero")
    assert "webp_src" in result
    assert "webp_src_mobile" in result


@pytest.fixture
def rf():
    from django.test import RequestFactory

    return RequestFactory()


# ---------------------------------------------------------------------------
# 5-7. Template wiring
# ---------------------------------------------------------------------------


def test_home_html_uses_picture_with_webp_source():
    text = HOME_HTML.read_text(encoding="utf-8")
    assert "<picture>" in text
    assert 'type="image/webp"' in text
    # The mobile media query for the smaller variant must be present.
    assert "max-width: 640px" in text


def test_home_html_emits_hero_preload():
    text = HOME_HTML.read_text(encoding="utf-8")
    assert 'rel="preload"' in text
    assert 'as="image"' in text
    assert "imagesrcset=" in text  # responsive preload form
    assert 'fetchpriority="high"' in text


def test_secondary_hero_partial_uses_picture_with_webp_source():
    text = HERO_PARTIAL.read_text(encoding="utf-8")
    assert "<picture>" in text
    assert 'type="image/webp"' in text
    # Below-the-fold: must stay lazy + decoding async.
    assert 'loading="lazy"' in text
    assert 'decoding="async"' in text


# ---------------------------------------------------------------------------
# 8. No external image domain leaks into the touched files
# ---------------------------------------------------------------------------


_EXTERNAL_PATTERNS = (
    "images.pexels.com",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "cdnjs.cloudflare.com",
    "googletagmanager.com",
)


def test_no_external_image_domain_in_home_html():
    text = HOME_HTML.read_text(encoding="utf-8")
    for needle in _EXTERNAL_PATTERNS:
        assert needle not in text


def test_no_external_image_domain_in_hero_partial():
    text = HERO_PARTIAL.read_text(encoding="utf-8")
    for needle in _EXTERNAL_PATTERNS:
        assert needle not in text


# ---------------------------------------------------------------------------
# 9. CSP didn't regress
# ---------------------------------------------------------------------------


def test_csp_has_no_unsafe_inline_or_eval():
    text = SETTINGS_PY.read_text(encoding="utf-8")
    assert "'unsafe-inline'" not in text
    assert "'unsafe-eval'" not in text


# ---------------------------------------------------------------------------
# 10. Live HTTP smoke: / and /ar/ still render correctly
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_home_renders_with_picture(client):
    from apps.legal_sources.legal_data_test_support import skip_if_no_pexels_webp

    # The hero <picture>/<img> markup is emitted only when the Pexels WebP
    # companions exist on disk (gitignored media; absent on a fresh CI
    # checkout — where the home renders no hero image at all). Skip the
    # hero-markup assertions when the media is absent.
    resp = client.get("/", HTTP_HOST="127.0.0.1")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert 'dir="ltr"' in html
    skip_if_no_pexels_webp()
    assert "<picture>" in html
    # The <img> inside <picture> must not rely on JS.
    assert "<img " in html


@pytest.mark.django_db
def test_ar_home_renders_with_picture_and_rtl(client):
    from apps.legal_sources.legal_data_test_support import skip_if_no_pexels_webp

    resp = client.get("/ar/", HTTP_HOST="127.0.0.1")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert 'dir="rtl"' in html
    skip_if_no_pexels_webp()
    assert "<picture>" in html


# ---------------------------------------------------------------------------
# Lighthouse runners call the new command
# ---------------------------------------------------------------------------


def test_desktop_runner_calls_compress_pexels_images():
    assert "compress_pexels_images" in RUNNER_DESKTOP.read_text(encoding="utf-8")


def test_mobile_runner_calls_compress_pexels_images():
    assert "compress_pexels_images" in RUNNER_MOBILE.read_text(encoding="utf-8")
