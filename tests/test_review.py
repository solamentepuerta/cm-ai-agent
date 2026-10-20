"""Unit tests for the deterministic draft review gate."""

import pytest

from src.review import review_draft

BRAND = """# Global Blacklist

- `desata`
- `en el mundo de`
"""


def test_clean_draft_with_verbatim_hook_passes() -> None:
    report = review_draft(
        "El 90% mide mal el alcance.\nCuerpo directo.\nComenta MÉTRICAS.",
        "video_corto",
        BRAND,
        "El 90% mide mal el alcance.",
    )
    assert report.passed is True
    assert report.hook_matches is True
    assert report.blacklist_violations == []
    assert report.stage_direction_violations == []
    assert report.retry_instruction is None


def test_blacklist_and_hook_failures_are_reported() -> None:
    report = review_draft(
        "Otro gancho.\nDesata tu potencial en el mundo de los datos.",
        "video_corto",
        BRAND,
        "El gancho exacto.",
    )
    assert report.passed is False
    assert report.hook_matches is False
    assert "desata" in report.blacklist_violations
    assert "en el mundo de" in report.blacklist_violations
    assert "gancho del usuario" in str(report.retry_instruction)


def test_stage_directions_and_timestamps_fail() -> None:
    draft = "[Música épica]\n00:00 Gancho\nCuerpo.\n[Cámara lenta]"
    report = review_draft(draft, "video_corto", BRAND)
    assert report.passed is False
    assert len(report.stage_direction_violations) >= 3


def test_production_line_without_brackets_fails() -> None:
    report = review_draft("Gancho\nMúsica: tensa\nCuerpo", "video_corto", BRAND)
    assert report.passed is False
    assert any("Música" in item for item in report.stage_direction_violations)


def test_carrusel_warns_without_slides() -> None:
    report = review_draft("Un texto corrido sin separadores.", "carrusel", BRAND)
    assert report.passed is True
    assert any("láminas" in warning for warning in report.warnings)


def test_hilo_warns_when_tweet_exceeds_limit() -> None:
    report = review_draft("x" * 300, "hilo_x", BRAND)
    assert report.passed is True
    assert any("280" in warning for warning in report.warnings)


def test_story_warns_without_interaction() -> None:
    report = review_draft("Hoy lanzamos algo nuevo.", "story", BRAND)
    assert any("interacción" in warning for warning in report.warnings)


def test_story_with_question_has_no_interaction_warning() -> None:
    report = review_draft("¿Probamos esto?", "story", BRAND)
    assert not any("interacción" in warning for warning in report.warnings)


def test_empty_draft_raises() -> None:
    with pytest.raises(ValueError):
        review_draft("   ", "video_corto", BRAND)
