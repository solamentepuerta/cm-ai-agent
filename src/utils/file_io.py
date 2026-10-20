"""Atomic and safe file I/O operations for local Markdown and configuration state."""

import os
import tempfile
from pathlib import Path


def atomic_write(target_path: Path | str, content: str, encoding: str = "utf-8") -> None:
    """Atomically write text content to target path using a temporary file."""
    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    temp_file = tempfile.NamedTemporaryFile(
        "w",
        dir=path.parent,
        delete=False,
        encoding=encoding,
    )
    temp_path = Path(temp_file.name)
    try:
        temp_file.write(content)
        temp_file.flush()
        temp_file.close()
        os.replace(temp_path, path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise


def read_file(path: Path | str, default: str = "", encoding: str = "utf-8") -> str:
    """Read file content with UTF-8 encoding, returning default if file does not exist."""
    target = Path(path)
    if not target.exists():
        return default
    with open(target, encoding=encoding) as f:
        return f.read()


def append_atomic(target_path: Path | str, content_to_append: str, encoding: str = "utf-8") -> None:
    """Atomically append content to an existing file, creating it if not present."""
    target = Path(target_path)
    existing = read_file(target, default="", encoding=encoding)
    new_content = existing + content_to_append
    atomic_write(target, new_content, encoding=encoding)
