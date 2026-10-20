"""Unit tests for brand context rendering and deterministic checks."""

import pytest

from src.state import BrandProfile
from src.utils.brand_context import (
    DEFAULT_BLACKLIST,
    check_brand_context,
    extract_blacklist,
    extract_format_rules,
    find_blacklist_violations,
    hook_is_verbatim,
    normalize_format_rules,
    render_brand_context,
)


def _profile() -> BrandProfile:
    return BrandProfile(
        identity="Marca de productividad para creadores B2B.",
        target_audience="Emprendedores y creadores de contenido",
        tone_attributes=["Directo", "Pragmático"],
        blacklist=["desata", "unleash"],
        format_rules={
            "video_corto": ["30-60 segundos", "Gancho en la primera línea"],
            "carrusel": ["Máximo 35 palabras por lámina"],
            "hilo_x": ["Un argumento por tweet"],
            "video_largo": ["Intro sin rodeos"],
            "story": ["Incluye una encuesta"],
        },
        style_examples=["Frases cortas", "Sin emojis decorativos"],
    )


def test_render_contains_all_sections() -> None:
    rendered = render_brand_context(_profile())
    for heading in (
        "# Identity & Audience",
        "# Global Blacklist",
        "# Voice & Tone Attributes",
        "# Format Rules",
        "# Style Examples",
    ):
        assert heading in rendered
    assert "## Video Corto" in rendered
    assert "## Carrusel" in rendered
    assert "## Hilo de X" in rendered
    assert "## Video Largo" in rendered
    assert "## Story" in rendered


def test_extract_format_rules_for_specific_format() -> None:
    rendered = render_brand_context(_profile())
    rules = extract_format_rules(rendered, "carrusel")
    assert "Máximo 35 palabras" in rules
    assert "30-60 segundos" not in rules


def test_extract_blacklist_includes_custom_and_defaults() -> None:
    rendered = render_brand_context(_profile())
    blacklist = extract_blacklist(rendered)
    assert "desata" in blacklist
    assert "unleash" in blacklist
    assert any(term in blacklist for term in DEFAULT_BLACKLIST)


def test_find_blacklist_violations_is_accent_insensitive() -> None:
    violations = find_blacklist_violations(
        "No te SUMERJAS en el mundo de los datos.",
        ["sumérgete", "en el mundo de"],
    )
    assert "en el mundo de" in violations


def test_hook_is_verbatim_uses_first_non_empty_line() -> None:
    draft = "\nEl 90% mide mal el alcance.\nCuerpo del guion."
    assert hook_is_verbatim(draft, "El 90% mide mal el alcance.")
    assert not hook_is_verbatim(draft, "El 90% mide mal el alcance")


def test_format_rules_fallback_when_missing() -> None:
    rules = extract_format_rules("# Identity\nNada más", "story")
    assert "encuesta" in rules.lower()


@pytest.mark.parametrize(
    "post_format",
    ["video_corto", "carrusel", "hilo_x", "video_largo", "story"],
)
def test_every_format_has_rules(post_format: str) -> None:
    rendered = render_brand_context(_profile())
    assert extract_format_rules(rendered, post_format).strip()


def test_check_brand_context_accepts_rendered_profile() -> None:
    result = check_brand_context(render_brand_context(_profile()))
    assert result.ok is True
    assert result.blacklist_terms >= 2
    assert all(count > 0 for count in result.formats.values())
    assert result.missing == []


def test_check_brand_context_reports_missing_sections() -> None:
    result = check_brand_context("# Identity & Audience\n\nSolo identidad.")
    assert result.ok is False
    assert "blacklist" in result.missing
    assert "tone" in result.missing
    assert "format:video_corto" in result.missing


def test_normalize_format_rules_accepts_labels_and_accents() -> None:
    normalized = normalize_format_rules(
        {
            "Video Corto (Reels / TikTok / Shorts)": ["Gancho"],
            "Carrusel (Instagram / LinkedIn)": ["35 palabras"],
            "Hilo de X (Twitter)": ["Un argumento"],
            "Video Largo (YouTube)": ["Intro directa"],
            "Stories": ["Encuesta"],
        }
    )
    assert set(normalized) == {"video_corto", "carrusel", "hilo_x", "video_largo", "story"}
    assert normalized["story"] == ["Encuesta"]


def test_check_brand_context_accepts_spanish_headings() -> None:
    content = """# Identidad y Audiencia

Marca directa.

# Lista Negra

- `desata`
- `unleash`

# Tono de Voz

- Directo

# Reglas por Formato

## Video Corto (Reel / TikTok)

- Gancho

## Carrusel

- Láminas

## Hilo de X

- Un argumento

## Video Largo

- Intro

## Story

- Encuesta
"""
    result = check_brand_context(content)
    assert result.ok is True
    assert result.blacklist_terms == 2
