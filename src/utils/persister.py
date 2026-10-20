"""Deterministic script persistence helpers."""

import re
import unicodedata
from datetime import datetime
from pathlib import Path

from src.utils.file_io import atomic_write


def save_script(
    scripts_dir: Path | str,
    post_format: str,
    topic: str,
    content: str,
    *,
    moment: datetime | None = None,
) -> Path:
    """Save a script as scripts/YYYY-MM-DD_<format>_<slug>.md without overwriting."""
    directory = Path(scripts_dir)
    directory.mkdir(parents=True, exist_ok=True)

    current = moment or datetime.now()
    stem = f"{current.date().isoformat()}_{post_format}_{slugify(topic)}"
    path = directory / f"{stem}.md"

    suffix = 2
    while path.exists():
        path = directory / f"{stem}_{suffix}.md"
        suffix += 1

    atomic_write(path, content.strip() + "\n")
    return path


def save_discarded(
    discarded_dir: Path | str,
    post_format: str,
    topic: str,
    content: str,
    *,
    moment: datetime | None = None,
) -> Path:
    """Save an aborted draft for later human review."""
    directory = Path(discarded_dir)
    directory.mkdir(parents=True, exist_ok=True)

    current = moment or datetime.now()
    stamp = current.strftime("%Y-%m-%d_%H%M%S")
    path = directory / f"{stamp}_{post_format}_{slugify(topic)}.md"
    atomic_write(path, content.strip() + "\n")
    return path


def slugify(value: str, limit: int = 50) -> str:
    """Convert a topic into a filesystem-safe slug."""
    text = unicodedata.normalize("NFKD", value)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    text = re.sub(r"_+", "_", text)
    return (text[:limit].rstrip("_")) or "sin_titulo"
