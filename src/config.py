"""Configuration management for the agent-native toolkit (paths only, no secrets)."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class PathsConfig(BaseModel):
    """File system paths used by the deterministic tools."""

    brand_context: Path = Field(
        default=Path("brand_context.md"),
        description="Path to brand identity and style file",
    )
    tasks: Path = Field(
        default=Path("tasks.md"),
        description="Path to human action items tracker",
    )
    data_dir: Path = Field(
        default=Path("data"),
        description="Directory for raw Metricool CSV files",
    )
    scripts_dir: Path = Field(
        default=Path("scripts"),
        description="Directory for finalized scripts",
    )
    prompts_dir: Path = Field(
        default=Path("prompts"),
        description="Directory for agent instruction files",
    )


class AppConfig(BaseModel):
    """Root configuration for the toolkit."""

    paths: PathsConfig = Field(default_factory=PathsConfig)


def load_config(config_path: Path | str = "config.yaml") -> AppConfig:
    """Load paths from YAML, resolving relative paths against the config file."""
    target = Path(config_path)
    data: dict[str, Any] = {}
    if target.exists():
        with open(target, encoding="utf-8") as handle:
            try:
                loaded = yaml.safe_load(handle)
            except yaml.YAMLError as exc:
                raise ValueError(f"No se pudo leer '{target}': {exc}") from exc
            if isinstance(loaded, dict):
                data = loaded

    paths = PathsConfig.model_validate(data.get("paths", {}))
    base = target.resolve().parent if target.exists() else Path.cwd()
    resolved = {
        name: (base / value).resolve() if not value.is_absolute() else value
        for name, value in ((name, getattr(paths, name)) for name in PathsConfig.model_fields)
    }
    return AppConfig(paths=PathsConfig(**resolved))
