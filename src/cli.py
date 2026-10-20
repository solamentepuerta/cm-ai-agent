"""Agent-native CLI: deterministic tools for OpenCode / Claude Code."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from rich.console import Console
from rich.table import Table

from src.config import AppConfig, load_config
from src.review import ReviewReport, review_draft
from src.state import FORMAT_LABELS, BrandProfile
from src.utils.brand_context import (
    BrandContextError,
    check_brand_context,
    load_brand_context,
    render_brand_context,
)
from src.utils.file_io import atomic_write
from src.utils.metricool_parser import AnalysisPayload, parse_metricool_csv, to_compact_json
from src.utils.persister import save_discarded, save_script
from src.utils.task_manager import TaskManager

Handler = Callable[[argparse.Namespace, AppConfig], int]


def main(argv: Sequence[str] | None = None) -> int:
    """Parse arguments, dispatch a deterministic command and map errors to exit codes."""
    _configure_stdio()
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
        handler = cast(Handler, args.func)
        return handler(args, config)
    except (BrandContextError, FileNotFoundError, ValueError, OSError) as exc:
        _print_json({"error": str(exc)})
        return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src",
        description="Herramientas deterministas para el AI Community Manager Assistant.",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Ruta al YAML de configuración (por defecto: config.yaml).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    formats = subparsers.add_parser("formats", help="Lista los formatos soportados.")
    formats.set_defaults(func=_cmd_formats)

    doctor = subparsers.add_parser("doctor", help="Muestra rutas y estado del proyecto.")
    doctor.set_defaults(func=_cmd_doctor)

    brand = subparsers.add_parser("brand", help="Renderiza o valida brand_context.md.")
    brand_sub = brand.add_subparsers(dest="brand_command", required=True)
    brand_check = brand_sub.add_parser("check", help="Valida secciones y cobertura.")
    brand_check.set_defaults(func=_cmd_brand_check)
    brand_render = brand_sub.add_parser("render", help="Renderiza brand_context.md desde JSON.")
    brand_render.add_argument("profile", help="JSON de BrandProfile o '-' para stdin.")
    brand_render.add_argument("--out", help="Ruta de salida (por defecto: paths.brand_context).")
    brand_render.set_defaults(func=_cmd_brand_render)

    review = subparsers.add_parser("review", help="Audita un borrador de forma determinista.")
    review.add_argument("--format", required=True, choices=list(FORMAT_LABELS))
    review.add_argument("--draft", default="-", help="Archivo del borrador o '-' para stdin.")
    review.add_argument("--hook", help="Gancho del usuario que debe aparecer verbatim.")
    review.add_argument("--summary", action="store_true", help="Salida legible en lugar de JSON.")
    review.set_defaults(func=_cmd_review)

    save = subparsers.add_parser("save", help="Guarda un guion aprobado y crea la tarea.")
    save.add_argument("--format", required=True, choices=list(FORMAT_LABELS))
    save.add_argument("--topic", required=True)
    save.add_argument("--draft", default="-", help="Archivo del borrador o '-' para stdin.")
    save.add_argument("--hook", help="Gancho del usuario para validar antes de guardar.")
    save.add_argument("--source", help="Ruta o referencia del guion fuente (repurpose).")
    save.add_argument("--force", action="store_true", help="Guardar aunque el review falle.")
    save.add_argument("--no-task", action="store_true", help="No crear tarea en tasks.md.")
    save.set_defaults(func=_cmd_save)

    discard = subparsers.add_parser(
        "discard", help="Guarda un borrador descartado sin crear tarea."
    )
    discard.add_argument("--format", required=True, choices=list(FORMAT_LABELS))
    discard.add_argument("--topic", required=True)
    discard.add_argument("--draft", default="-", help="Archivo del borrador o '-' para stdin.")
    discard.set_defaults(func=_cmd_discard)

    analyze = subparsers.add_parser("analyze", help="Parsea un CSV de Metricool a JSON compacto.")
    analyze.add_argument(
        "path", nargs="?", help="CSV a analizar; si se omite, usa el más reciente."
    )
    analyze.add_argument("--top", type=int, default=3, help="Número de posts destacados.")
    analyze.add_argument("--summary", action="store_true", help="Salida legible en lugar de JSON.")
    analyze.set_defaults(func=_cmd_analyze)

    scripts = subparsers.add_parser("scripts", help="Gestiona los guiones guardados.")
    scripts_sub = scripts.add_subparsers(dest="scripts_command", required=True)
    scripts_list = scripts_sub.add_parser("list", help="Lista scripts guardados.")
    scripts_list.add_argument("--summary", action="store_true", help="Salida legible.")
    scripts_list.set_defaults(func=_cmd_scripts_list)

    tasks = subparsers.add_parser("tasks", help="Gestiona tareas humanas en tasks.md.")
    tasks_sub = tasks.add_subparsers(dest="tasks_command", required=True)
    tasks_list = tasks_sub.add_parser("list", help="Lista tareas.")
    tasks_list.add_argument("--all", action="store_true", help="Incluye completadas.")
    tasks_list.add_argument("--json", action="store_true", help="Salida JSON.")
    tasks_list.set_defaults(func=_cmd_tasks_list)
    tasks_add = tasks_sub.add_parser("add", help="Añade una tarea manual.")
    tasks_add.add_argument("description", nargs="+")
    tasks_add.add_argument("--type", default="MANUAL", dest="task_type")
    tasks_add.add_argument("--deadline")
    tasks_add.add_argument("--notes")
    tasks_add.set_defaults(func=_cmd_tasks_add)
    tasks_done = tasks_sub.add_parser("done", help="Marca una tarea como completada.")
    tasks_done.add_argument("task_id")
    tasks_done.set_defaults(func=_cmd_tasks_done)

    return parser


def _cmd_formats(args: argparse.Namespace, config: AppConfig) -> int:
    for key, label in FORMAT_LABELS.items():
        print(f"{key}\t{label}")
    return 0


def _cmd_doctor(args: argparse.Namespace, config: AppConfig) -> int:
    paths = config.paths
    payload = {
        "python": sys.version.split()[0],
        "brand_context": _path_status(paths.brand_context),
        "tasks": _path_status(paths.tasks),
        "data_dir": _path_status(paths.data_dir),
        "scripts_dir": _path_status(paths.scripts_dir),
        "prompts_dir": _path_status(paths.prompts_dir),
    }
    _print_json(payload)
    return 0


def _cmd_brand_check(args: argparse.Namespace, config: AppConfig) -> int:
    content = load_brand_context(config.paths.brand_context)
    result = check_brand_context(content)
    _print_json(result.model_dump())
    return 0 if result.ok else 1


def _cmd_brand_render(args: argparse.Namespace, config: AppConfig) -> int:
    raw = (
        sys.stdin.read() if args.profile == "-" else Path(args.profile).read_text(encoding="utf-8")
    )
    profile = BrandProfile.model_validate(json.loads(raw))
    content = render_brand_context(profile)
    out = Path(args.out) if args.out else config.paths.brand_context
    atomic_write(out, content)
    check = check_brand_context(content)
    _print_json({"path": str(out), "check": check.model_dump()})
    return 0 if check.ok else 1


def _cmd_review(args: argparse.Namespace, config: AppConfig) -> int:
    brand_context = load_brand_context(config.paths.brand_context)
    draft = _read_draft(args.draft)
    report = review_draft(draft, args.format, brand_context, args.hook)
    if args.summary:
        _print_review(report)
    else:
        _print_json(report.model_dump())
    return 0 if report.passed else 1


def _cmd_save(args: argparse.Namespace, config: AppConfig) -> int:
    brand_context = load_brand_context(config.paths.brand_context)
    draft = _read_draft(args.draft)
    report = review_draft(draft, args.format, brand_context, args.hook)

    if not report.passed and not args.force:
        _print_json(
            {
                "saved": False,
                "review": report.model_dump(),
                "hint": "Corrige el borrador o usa --force tras la aceptación humana.",
            }
        )
        return 1

    path = save_script(config.paths.scripts_dir, args.format, args.topic, draft)
    task_id: str | None = None
    if not args.no_task:
        label = FORMAT_LABELS.get(args.format, args.format)
        notes = (
            "Guion aprobado. Revisar, producir y publicar el contenido."
            if report.passed
            else "Guardado con --force tras aceptación humana. Revisar las violaciones del review."
        )
        if args.source:
            notes += f" Fuente: {args.source}"
        task = TaskManager(config.paths.tasks).append_task(
            task_type="EDIT",
            description=f"Producir y publicar {label}: {args.topic}",
            content_format=label,
            source_path=str(path).replace("\\", "/"),
            notes=notes,
        )
        task_id = task.task_id

    _print_json(
        {
            "saved": True,
            "path": str(path),
            "task_id": task_id,
            "review": report.model_dump(),
        }
    )
    return 0


def _cmd_discard(args: argparse.Namespace, config: AppConfig) -> int:
    draft = _read_draft(args.draft)
    path = save_discarded(
        config.paths.scripts_dir / "drafts",
        args.format,
        args.topic,
        draft,
    )
    _print_json({"discarded": True, "path": str(path)})
    return 0


def _cmd_analyze(args: argparse.Namespace, config: AppConfig) -> int:
    csv_path = _resolve_csv(args.path, config)
    payload = parse_metricool_csv(csv_path, top_n=args.top)
    if args.summary:
        _print_analysis(payload, csv_path)
    else:
        print(to_compact_json(payload))
    return 0


def _cmd_scripts_list(args: argparse.Namespace, config: AppConfig) -> int:
    directory = config.paths.scripts_dir
    files = sorted(directory.glob("*.md")) if directory.exists() else []
    entries = [
        {
            "name": path.name,
            "path": str(path),
            "bytes": path.stat().st_size,
            "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
        }
        for path in files
    ]
    if args.summary:
        table = Table(title=f"Scripts guardados ({len(entries)})")
        table.add_column("Archivo")
        table.add_column("Bytes", justify="right")
        table.add_column("Modificado")
        for entry in entries:
            table.add_row(str(entry["name"]), str(entry["bytes"]), str(entry["modified"]))
        Console().print(table)
    else:
        _print_json(entries)
    return 0


def _cmd_tasks_list(args: argparse.Namespace, config: AppConfig) -> int:
    manager = TaskManager(config.paths.tasks)
    tasks = manager.parse() if args.all else manager.list_open_tasks()
    if args.json:
        _print_json([task.model_dump() for task in tasks])
        return 0

    table = Table(title=f"Tareas ({len(tasks)})", show_header=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Estado")
    table.add_column("Tipo", style="magenta")
    table.add_column("Descripción")
    table.add_column("Deadline")
    for task in tasks:
        table.add_row(
            task.task_id,
            "x" if task.completed else " ",
            task.task_type,
            task.description,
            task.deadline or "-",
        )
    Console().print(table)
    return 0


def _cmd_tasks_add(args: argparse.Namespace, config: AppConfig) -> int:
    task = TaskManager(config.paths.tasks).append_task(
        task_type=args.task_type,
        description=" ".join(args.description),
        deadline=args.deadline,
        notes=args.notes,
    )
    _print_json({"task_id": task.task_id, "task": task.model_dump()})
    return 0


def _cmd_tasks_done(args: argparse.Namespace, config: AppConfig) -> int:
    task = TaskManager(config.paths.tasks).mark_task_done(args.task_id)
    if task is None:
        raise ValueError(f"No existe la tarea {args.task_id}.")
    _print_json({"done": True, "task": task.model_dump()})
    return 0


def _read_draft(source: str) -> str:
    if source == "-":
        return sys.stdin.read()
    return Path(source).read_text(encoding="utf-8")


def _resolve_csv(raw_path: str | None, config: AppConfig) -> Path:
    if raw_path:
        candidate = Path(raw_path.strip().strip("\"'"))
        if candidate.is_absolute():
            return candidate
        if candidate.exists():
            return candidate
        return config.paths.data_dir / candidate

    files = sorted(
        config.paths.data_dir.glob("*.csv"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not files:
        raise FileNotFoundError(
            f"No hay CSV en '{config.paths.data_dir}'. Exporta métricas desde Metricool primero."
        )
    return files[0]


def _path_status(path: Path) -> dict[str, str | bool]:
    return {"path": str(path), "exists": path.exists()}


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _print_review(report: ReviewReport) -> None:
    console = Console()
    status = "APROBADO" if report.passed else "RECHAZADO"
    style = "green" if report.passed else "red"
    console.print(f"[bold {style}]{status}[/bold {style}] · {report.format}")
    console.print(
        f"Palabras: {report.metrics.words} · Líneas: {report.metrics.lines} · "
        f"Bloques: {report.metrics.blocks} · Hook: {_hook_label(report.hook_matches)}"
    )
    for term in report.blacklist_violations:
        console.print(f"[red]Blacklist:[/red] {term}")
    for snippet in report.stage_direction_violations:
        console.print(f"[red]Producción:[/red] {snippet}")
    for warning in report.warnings:
        console.print(f"[yellow]Aviso:[/yellow] {warning}")
    if report.retry_instruction:
        console.print(f"[bold]Instrucción:[/bold] {report.retry_instruction}")


def _print_analysis(payload: AnalysisPayload, csv_path: Path) -> None:
    console = Console()
    console.print(f"[bold]Métricas:[/bold] {csv_path.name} · {payload.posts_analyzed} posts")
    table = Table(show_header=True, box=None)
    table.add_column("Post")
    table.add_column("Engagement", justify="right")
    table.add_column("Retención", justify="right")
    table.add_column("Alcance", justify="right")
    for post in payload.top_posts:
        table.add_row(
            post.title,
            f"{post.engagement_rate:.2f}%",
            f"{post.retention_rate:.2f}%" if post.retention_rate is not None else "-",
            str(post.reach),
        )
    console.print("[bold]Top posts[/bold]")
    console.print(table)
    averages = f"Promedios: engagement {payload.averages.engagement_rate:.2f}%"
    if payload.averages.retention_rate is not None:
        averages += f" · retención {payload.averages.retention_rate:.2f}%"
    console.print(averages)


def _hook_label(value: bool | None) -> str:
    if value is None:
        return "no aplica"
    return "ok" if value else "no coincide"


def _configure_stdio() -> None:
    """Prefer UTF-8 on Windows so accents and JSON survive redirection."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


if __name__ == "__main__":
    raise SystemExit(main())
