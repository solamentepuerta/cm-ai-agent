"""Unit tests for path-only configuration loading."""

from pathlib import Path

import pytest

from src.config import PathsConfig, load_config


def test_default_config_loading_uses_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    cfg = load_config("missing.yaml")
    assert isinstance(cfg.paths, PathsConfig)
    assert cfg.paths.brand_context == (tmp_path / "brand_context.md").resolve()
    assert cfg.paths.prompts_dir == (tmp_path / "prompts").resolve()


def test_yaml_paths_are_resolved_against_config_file(tmp_path: Path) -> None:
    config_file = tmp_path / "custom.yaml"
    config_file.write_text(
        """
paths:
  brand_context: "custom_brand.md"
  tasks: "custom_tasks.md"
  data_dir: "metrics"
""",
        encoding="utf-8",
    )

    cfg = load_config(config_file)

    assert cfg.paths.brand_context == tmp_path / "custom_brand.md"
    assert cfg.paths.tasks == tmp_path / "custom_tasks.md"
    assert cfg.paths.data_dir == tmp_path / "metrics"
    assert cfg.paths.scripts_dir == tmp_path / "scripts"


def test_absolute_paths_are_preserved(tmp_path: Path) -> None:
    absolute = tmp_path / "absolute_brand.md"
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        f'paths:\n  brand_context: "{absolute.as_posix()}"\n',
        encoding="utf-8",
    )

    cfg = load_config(config_file)

    assert cfg.paths.brand_context == absolute
