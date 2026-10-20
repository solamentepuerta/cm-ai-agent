"""Deterministic task engine for the persistent human action tracker (tasks.md)."""

import re
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from src.utils.file_io import atomic_write, read_file

TASKS_HEADER = "# Human Action Items\n\n"
TASK_ID_PREFIX = "TASK"

TASK_LINE_RE = re.compile(
    r"^- \[(?P<checked>[ xX])\] \[(?P<task_id>TASK-\d{8}-\d{3})\] "
    r"\*\*(?P<task_type>[A-Z_]+)\*\* — (?P<description>.+)$"
)
METADATA_LINE_RE = re.compile(r"^\s{2,}- (?P<key>[^:]+):\s?(?P<value>.*)$")

_DEADLINE_KEYS = {"deadline", "fecha límite", "fecha limite"}
_NOTES_KEYS = {"notas", "notes"}
_FORMAT_KEYS = {"formato", "format"}
_COMPLETED_KEYS = {"fecha completado", "completado", "completed at"}
_SOURCE_KEYS = {"archivo", "source", "source path", "ruta"}


class TaskItem(BaseModel):
    """A single human action item parsed from tasks.md."""

    task_id: str
    task_type: str
    description: str
    completed: bool = False
    deadline: str | None = None
    notes: str | None = None
    content_format: str | None = None
    completed_at: str | None = None
    source_path: str | None = None
    extra: dict[str, str] = Field(default_factory=dict)


class TaskManager:
    """Reads, appends and completes tasks in a local Markdown file."""

    def __init__(self, tasks_path: Path | str) -> None:
        self.path = Path(tasks_path)

    def _read(self) -> str:
        content = read_file(self.path, default="")
        if not content.strip():
            return TASKS_HEADER
        return content

    def _write(self, content: str) -> None:
        atomic_write(self.path, content)

    def parse(self) -> list[TaskItem]:
        """Parse every task entry from the Markdown file."""
        return _parse_tasks(self._read())

    def list_open_tasks(self) -> list[TaskItem]:
        """Return only tasks that are still pending."""
        return [task for task in self.parse() if not task.completed]

    def get_task(self, task_id: str) -> TaskItem | None:
        """Look up a single task by its identifier."""
        for task in self.parse():
            if task.task_id == task_id:
                return task
        return None

    def next_task_id(self, moment: datetime | None = None) -> str:
        """Generate the next sequential ID for the current day."""
        current = moment or datetime.now()
        date_prefix = current.strftime("%Y%m%d")
        pattern = re.compile(rf"^{TASK_ID_PREFIX}-{date_prefix}-(\d{{3}})$")

        highest = 0
        for task in self.parse():
            match = pattern.match(task.task_id)
            if match:
                highest = max(highest, int(match.group(1)))

        return f"{TASK_ID_PREFIX}-{date_prefix}-{highest + 1:03d}"

    def append_task(
        self,
        task_type: str,
        description: str,
        deadline: str | None = None,
        notes: str | None = None,
        content_format: str | None = None,
        source_path: str | None = None,
        task_id: str | None = None,
    ) -> TaskItem:
        """Append a new pending task and persist it atomically."""
        new_task = TaskItem(
            task_id=task_id or self.next_task_id(),
            task_type=task_type.upper(),
            description=description.strip(),
            deadline=deadline,
            notes=notes,
            content_format=content_format,
            source_path=source_path,
        )

        content = self._read()
        if not content.endswith("\n"):
            content += "\n"
        content += "\n" + render_task(new_task) + "\n"
        self._write(content)
        return new_task

    def add_manual(self, description: str) -> TaskItem:
        """Add a manually requested task with the generic MANUAL type."""
        return self.append_task(task_type="MANUAL", description=description)

    def mark_task_done(
        self,
        task_id: str,
        completed_at: datetime | None = None,
    ) -> TaskItem | None:
        """Mark a task complete, inserting a timestamp. Returns None if not found."""
        content = self._read()
        lines = content.splitlines()

        for index, line in enumerate(lines):
            match = TASK_LINE_RE.match(line)
            if not match or match.group("task_id") != task_id:
                continue

            if match.group("checked").lower() == "x":
                return self.get_task(task_id)

            lines[index] = line.replace("- [ ]", "- [x]", 1)
            moment = (completed_at or datetime.now()).strftime("%Y-%m-%d %H:%M")
            lines = _upsert_metadata(lines, index, "Fecha completado", moment)
            new_content = "\n".join(lines).rstrip("\n") + "\n"
            self._write(new_content)
            return self.get_task(task_id)

        return None


def _upsert_metadata(lines: list[str], header_index: int, key: str, value: str) -> list[str]:
    """Insert or replace a metadata bullet inside the task block."""
    end = header_index + 1
    while end < len(lines) and METADATA_LINE_RE.match(lines[end]):
        end += 1

    completed_re = re.compile(rf"^\s{{2,}}- {re.escape(key)}:", re.IGNORECASE)
    for index in range(header_index + 1, end):
        if completed_re.match(lines[index]):
            lines[index] = f"  - {key}: {value}"
            return lines

    lines.insert(end, f"  - {key}: {value}")
    return lines


def _parse_tasks(content: str) -> list[TaskItem]:
    """Parse a tasks.md document into structured TaskItem objects."""
    lines = content.splitlines()
    tasks: list[TaskItem] = []

    for index, line in enumerate(lines):
        match = TASK_LINE_RE.match(line)
        if not match:
            continue

        task = TaskItem(
            task_id=match.group("task_id"),
            task_type=match.group("task_type"),
            description=match.group("description").strip(),
            completed=match.group("checked").lower() == "x",
        )

        cursor = index + 1
        while cursor < len(lines):
            metadata = METADATA_LINE_RE.match(lines[cursor])
            if not metadata:
                break
            _assign_metadata(task, metadata.group("key").strip(), metadata.group("value").strip())
            cursor += 1

        tasks.append(task)

    return tasks


def _assign_metadata(task: TaskItem, key: str, value: str) -> None:
    """Map a free-form metadata key onto the corresponding TaskItem field."""
    normalized = key.casefold()
    if normalized in _DEADLINE_KEYS:
        task.deadline = value
    elif normalized in _NOTES_KEYS:
        task.notes = value
    elif normalized in _FORMAT_KEYS:
        task.content_format = value
    elif normalized in _COMPLETED_KEYS:
        task.completed_at = value
    elif normalized in _SOURCE_KEYS:
        task.source_path = value
    else:
        task.extra[key] = value


def render_task(task: TaskItem) -> str:
    """Render a TaskItem using the canonical tasks.md block format."""
    checkbox = "x" if task.completed else " "
    lines = [
        f"- [{checkbox}] [{task.task_id}] **{task.task_type}** — {task.description}",
    ]
    if task.content_format:
        lines.append(f"  - Formato: {task.content_format}")
    if task.deadline:
        lines.append(f"  - Deadline: {task.deadline}")
    if task.source_path:
        lines.append(f"  - Archivo: {task.source_path}")
    if task.notes:
        lines.append(f"  - Notas: {task.notes}")
    if task.completed_at:
        lines.append(f"  - Fecha completado: {task.completed_at}")
    for key, value in task.extra.items():
        lines.append(f"  - {key}: {value}")
    return "\n".join(lines)
