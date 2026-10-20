# Claude Code Instructions

@AGENTS.md

## Notas específicas de Claude Code

- Los slash commands están en `.claude/commands/` (`/setup`, `/script`, `/repurpose`,
  `/analyze`, `/tasks`). Úsalos como punto de entrada.
- Usa `Read`, `Write`, `Edit`, `Glob`, `Grep` y `Bash` para operar el toolkit. No hagas
  llamadas HTTP a APIs de modelos ni pidas API keys.
- Para ejecutar las herramientas: `python -m src ...`. En Windows, si el venv no está activo:
  `.\.venv\Scripts\python -m src ...`.
- Los borradores temporales van en `scripts/drafts/` y se borran al terminar.
- Si un comando devuelve exit code `1` con un JSON `passed: false`, se trata de un rechazo
  normal del review: aplica `retry_instruction`; no es un fallo de infraestructura.
- Tras 2 reintentos fallidos, pide intervención humana antes de usar `--force`.
