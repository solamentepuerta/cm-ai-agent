"""Integration tests for the agent-native CLI."""

import json
from io import StringIO
from pathlib import Path

import pytest

from src.cli import main

BRAND_CONTEXT = """# Identity & Audience

Marca de productividad para creadores.

# Global Blacklist

- `desata`
- `en el mundo de`

# Voice & Tone Attributes

- Directo

# Format Rules

## Video Corto (Reel / TikTok / Shorts)

- Gancho en la primera línea.

## Carrusel

- Máximo 35 palabras por lámina.

## Hilo de X

- Un argumento por tweet.

## Video Largo

- Intro sin rodeos.

## Story

- Incluye una encuesta.
"""

SAMPLE_CSV = (
    "Red social,Fecha de publicación,Publicación,Alcance,Me gusta,Comentarios\n"
    "Instagram,18/10/2026,Post ganador,1000,100,10\n"
    "Instagram,17/10/2026,Post flojo,1000,10,1\n"
)

PROFILE_JSON = {
    "identity": "Marca de productividad para creadores.",
    "target_audience": "Creadores B2B",
    "tone_attributes": ["Directo", "Pragmático"],
    "blacklist": ["desata", "en el mundo de"],
    "format_rules": {
        "video_corto": ["Gancho en la primera línea."],
        "carrusel": ["Máximo 35 palabras por lámina."],
        "hilo_x": ["Un argumento por tweet."],
        "video_largo": ["Intro sin rodeos."],
        "story": ["Incluye una encuesta."],
    },
    "style_examples": ["Frases cortas"],
}


def _config(tmp_path: Path) -> Path:
    config = tmp_path / "config.yaml"
    config.write_text(
        """
paths:
  brand_context: "brand_context.md"
  tasks: "tasks.md"
  data_dir: "data"
  scripts_dir: "scripts"
  prompts_dir: "prompts"
""",
        encoding="utf-8",
    )
    (tmp_path / "brand_context.md").write_text(BRAND_CONTEXT, encoding="utf-8")
    (tmp_path / "prompts").mkdir()
    return config


def _json_output(captured: pytest.CaptureFixture[str]) -> object:
    return json.loads(captured.readouterr().out)


def test_review_command_fails_with_blacklist(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = _config(tmp_path)
    draft = tmp_path / "draft.md"
    draft.write_text("Gancho\nDesata tu potencial.", encoding="utf-8")

    code = main(
        ["--config", str(config), "review", "--format", "video_corto", "--draft", str(draft)]
    )

    assert code == 1
    payload = _json_output(capsys)
    assert isinstance(payload, dict)
    assert payload["passed"] is False
    assert "desata" in payload["blacklist_violations"]


def test_review_command_reads_stdin(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr("sys.stdin", StringIO("Gancho\nCuerpo limpio."))

    code = main(["--config", str(config), "review", "--format", "video_corto", "--draft", "-"])

    assert code == 0
    payload = _json_output(capsys)
    assert isinstance(payload, dict)
    assert payload["passed"] is True


def test_save_refuses_failed_review_without_force(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = _config(tmp_path)
    draft = tmp_path / "draft.md"
    draft.write_text("Gancho\nDesata tu potencial.", encoding="utf-8")

    code = main(
        [
            "--config",
            str(config),
            "save",
            "--format",
            "video_corto",
            "--topic",
            "Tema",
            "--draft",
            str(draft),
        ]
    )

    assert code == 1
    payload = _json_output(capsys)
    assert isinstance(payload, dict)
    assert payload["saved"] is False
    assert not (tmp_path / "scripts").exists() or not list((tmp_path / "scripts").glob("*.md"))


def test_save_clean_draft_creates_script_and_task(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = _config(tmp_path)
    draft = tmp_path / "draft.md"
    draft.write_text("El gancho exacto.\nCuerpo limpio.\nComenta MÉTRICAS.", encoding="utf-8")

    code = main(
        [
            "--config",
            str(config),
            "save",
            "--format",
            "video_corto",
            "--topic",
            "3 errores al medir engagement",
            "--draft",
            str(draft),
            "--hook",
            "El gancho exacto.",
        ]
    )

    assert code == 0
    payload = _json_output(capsys)
    assert isinstance(payload, dict)
    assert payload["saved"] is True
    assert Path(str(payload["path"])).exists()
    assert payload["task_id"]

    tasks = (tmp_path / "tasks.md").read_text(encoding="utf-8")
    assert "TASK-" in tasks
    assert "Producir y publicar" in tasks


def test_save_with_force_after_human_acceptance(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = _config(tmp_path)
    draft = tmp_path / "draft.md"
    draft.write_text("Gancho\nDesata tu potencial.", encoding="utf-8")

    code = main(
        [
            "--config",
            str(config),
            "save",
            "--format",
            "video_corto",
            "--topic",
            "Tema",
            "--draft",
            str(draft),
            "--force",
            "--no-task",
        ]
    )

    assert code == 0
    payload = _json_output(capsys)
    assert isinstance(payload, dict)
    assert payload["saved"] is True
    assert payload["task_id"] is None


def test_brand_render_and_check(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = _config(tmp_path)
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps(PROFILE_JSON), encoding="utf-8")
    (tmp_path / "brand_context.md").unlink()

    render_code = main(["--config", str(config), "brand", "render", str(profile)])
    assert render_code == 0
    render_payload = _json_output(capsys)
    assert isinstance(render_payload, dict)
    assert render_payload["check"]["ok"] is True

    check_code = main(["--config", str(config), "brand", "check"])
    assert check_code == 0
    check_payload = _json_output(capsys)
    assert isinstance(check_payload, dict)
    assert check_payload["blacklist_terms"] >= 2


def test_brand_check_fails_for_incomplete_context(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = _config(tmp_path)
    (tmp_path / "brand_context.md").write_text(
        "# Identity & Audience\n\nSolo esto.", encoding="utf-8"
    )

    code = main(["--config", str(config), "brand", "check"])

    assert code == 1
    payload = _json_output(capsys)
    assert isinstance(payload, dict)
    assert payload["ok"] is False
    assert "blacklist" in payload["missing"]


def test_analyze_command_outputs_compact_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = _config(tmp_path)
    data = tmp_path / "data"
    data.mkdir()
    (data / "week42.csv").write_text(SAMPLE_CSV, encoding="utf-8")

    code = main(["--config", str(config), "analyze", "week42.csv"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["posts_analyzed"] == 2
    assert payload["top_posts"][0]["title"] == "Post ganador"


def test_tasks_add_list_and_done(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = _config(tmp_path)

    add_code = main(["--config", str(config), "tasks", "add", "Revisar", "métricas"])
    assert add_code == 0
    added = _json_output(capsys)
    assert isinstance(added, dict)
    task_id = str(added["task_id"])

    list_code = main(["--config", str(config), "tasks", "list", "--json"])
    assert list_code == 0
    listed = _json_output(capsys)
    assert isinstance(listed, list)
    assert len(listed) == 1

    done_code = main(["--config", str(config), "tasks", "done", task_id])
    assert done_code == 0
    done = _json_output(capsys)
    assert isinstance(done, dict)
    assert done["done"] is True


def test_analyze_accepts_cwd_relative_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    data = tmp_path / "data"
    data.mkdir()
    (data / "week42.csv").write_text(SAMPLE_CSV, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    code = main(["--config", str(config), "analyze", "data/week42.csv"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["posts_analyzed"] == 2


def test_invalid_config_returns_json_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = tmp_path / "config.yaml"
    config.write_text("paths: [unclosed", encoding="utf-8")

    code = main(["--config", str(config), "doctor"])

    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert "error" in payload


def test_discard_and_scripts_list(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = _config(tmp_path)
    draft = tmp_path / "draft.md"
    draft.write_text("Borrador descartado.", encoding="utf-8")

    discard_code = main(
        [
            "--config",
            str(config),
            "discard",
            "--format",
            "story",
            "--topic",
            "Tema",
            "--draft",
            str(draft),
        ]
    )
    assert discard_code == 0
    discarded = _json_output(capsys)
    assert isinstance(discarded, dict)
    assert Path(str(discarded["path"])).exists()

    save_code = main(
        [
            "--config",
            str(config),
            "save",
            "--format",
            "story",
            "--topic",
            "Tema",
            "--draft",
            str(draft),
            "--force",
            "--no-task",
        ]
    )
    assert save_code == 0
    _json_output(capsys)

    list_code = main(["--config", str(config), "scripts", "list"])
    assert list_code == 0
    scripts = _json_output(capsys)
    assert isinstance(scripts, list)
    assert len(scripts) == 1
