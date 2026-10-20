"""Unit tests for deterministic script persistence."""

from datetime import datetime
from pathlib import Path

from src.utils.persister import save_discarded, save_script, slugify


def test_slugify_normalizes_accents_and_symbols() -> None:
    assert slugify("Tres errores al medir engagement") == "tres_errores_al_medir_engagement"
    assert slugify("¿Qué está pasando?") == "que_esta_pasando"
    assert slugify("---") == "sin_titulo"


def test_save_script_avoids_overwriting(tmp_path: Path) -> None:
    moment = datetime(2026, 10, 20, 12, 0)
    first = save_script(tmp_path / "scripts", "video_corto", "Tema", "Uno", moment=moment)
    second = save_script(tmp_path / "scripts", "video_corto", "Tema", "Dos", moment=moment)

    assert first.name == "2026-10-20_video_corto_tema.md"
    assert second.name == "2026-10-20_video_corto_tema_2.md"
    assert first.read_text(encoding="utf-8") == "Uno\n"


def test_save_discarded_uses_timestamp(tmp_path: Path) -> None:
    moment = datetime(2026, 10, 20, 12, 34, 56)
    path = save_discarded(tmp_path, "story", "Tema", "Borrador", moment=moment)

    assert path.name == "2026-10-20_123456_story_tema.md"
    assert path.read_text(encoding="utf-8") == "Borrador\n"
