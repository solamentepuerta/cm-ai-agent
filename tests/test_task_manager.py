"""Unit tests for the deterministic task manager."""

from datetime import datetime
from pathlib import Path

from src.utils.task_manager import TaskManager, render_task


def _manager(tmp_path: Path) -> TaskManager:
    return TaskManager(tmp_path / "tasks.md")


def test_append_task_generates_sequential_ids(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    fixed = datetime(2026, 10, 20, 9, 0)

    first = manager.append_task("EDIT", "Editar Reel", task_id=manager.next_task_id(fixed))
    second = manager.append_task(
        "PUBLISH", "Publicar carrusel", task_id=manager.next_task_id(fixed)
    )

    assert first.task_id == "TASK-20261020-001"
    assert second.task_id == "TASK-20261020-002"


def test_parse_roundtrip_preserves_metadata(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    manager.append_task(
        "EDIT",
        "Grabar y editar Reel",
        deadline="2026-10-21 14:00",
        notes="Subtítulos dinámicos",
        content_format="Video Corto",
        source_path="scripts/2026-10-20_reel.md",
        task_id="TASK-20261020-001",
    )

    tasks = manager.parse()
    assert len(tasks) == 1
    task = tasks[0]
    assert task.task_id == "TASK-20261020-001"
    assert task.task_type == "EDIT"
    assert task.deadline == "2026-10-21 14:00"
    assert task.notes == "Subtítulos dinámicos"
    assert task.content_format == "Video Corto"
    assert task.source_path == "scripts/2026-10-20_reel.md"
    assert not task.completed


def test_mark_task_done_sets_checkbox_and_timestamp(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    manager.append_task("EDIT", "Editar Reel", task_id="TASK-20261020-001")

    updated = manager.mark_task_done(
        "TASK-20261020-001",
        completed_at=datetime(2026, 10, 21, 10, 30),
    )

    assert updated is not None
    assert updated.completed
    assert updated.completed_at == "2026-10-21 10:30"
    content = (tmp_path / "tasks.md").read_text(encoding="utf-8")
    assert "- [x] [TASK-20261020-001]" in content
    assert "Fecha completado: 2026-10-21 10:30" in content


def test_list_open_tasks_excludes_completed(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    manager.append_task("EDIT", "Uno", task_id="TASK-20261020-001")
    manager.append_task("PUBLISH", "Dos", task_id="TASK-20261020-002")
    manager.mark_task_done("TASK-20261020-001")

    open_tasks = manager.list_open_tasks()
    assert [task.task_id for task in open_tasks] == ["TASK-20261020-002"]


def test_mark_task_done_returns_none_for_unknown_id(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    assert manager.mark_task_done("TASK-20261020-999") is None


def test_render_task_includes_extra_metadata() -> None:
    from src.utils.task_manager import TaskItem

    task = TaskItem(
        task_id="TASK-20261020-001",
        task_type="EDIT",
        description="Cortar video",
        deadline="Mañana 10:00",
        extra={"Prioridad": "Alta"},
    )
    rendered = render_task(task)
    assert "**EDIT** — Cortar video" in rendered
    assert "  - Prioridad: Alta" in rendered
