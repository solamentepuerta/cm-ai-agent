"""Unit tests for atomic file I/O utilities."""

from pathlib import Path

from src.utils.file_io import append_atomic, atomic_write, read_file


def test_atomic_write_creates_parent_directories(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "deeper" / "file.md"
    atomic_write(target, "hola mundo")
    assert target.read_text(encoding="utf-8") == "hola mundo"


def test_read_file_returns_default_when_missing(tmp_path: Path) -> None:
    assert read_file(tmp_path / "missing.md", default="fallback") == "fallback"


def test_append_atomic_appends_and_creates(tmp_path: Path) -> None:
    target = tmp_path / "tasks.md"
    append_atomic(target, "linea 1\n")
    append_atomic(target, "linea 2\n")
    assert target.read_text(encoding="utf-8") == "linea 1\nlinea 2\n"


def test_no_tmp_files_left_behind(tmp_path: Path) -> None:
    target = tmp_path / "file.md"
    atomic_write(target, "contenido")
    leftovers = [p.name for p in tmp_path.iterdir() if p.suffix == ".tmp"]
    assert leftovers == []
