# AI Community Manager Assistant — Roadmap

## Fase 0: Toolkit base y tooling

- [x] **0.1.** Estructura `src/`, `prompts/`, `scripts/`, `data/` y entorno Python 3.11+.
- [x] **0.2.** `ruff`, `mypy` y `pytest` configurados.
- [x] **0.3.** `config.yaml` solo con rutas; sin API keys ni secretos.

## Fase 1: Capa determinista

- [x] **1.1.** File I/O atómico.
- [x] **1.2.** Motor de tareas `TASK-YYYYMMDD-XXX` y parser de `tasks.md`.
- [x] **1.3.** Parser de Metricool (encabezado, separador, alias ES/EN, engagement, promedios).
- [x] **1.4.** Brand context: blacklist, reglas por formato, render y validación estructural.

## Fase 2: Review y persistencia

- [x] **2.1.** Review determinista: blacklist, gancho verbatim, stage directions y warnings.
- [x] **2.2.** Guardado de guiones con nombres deterministas y sin sobrescritura.
- [x] **2.3.** Creación automática de tareas `EDIT` y descarte de borradores.

## Fase 3: CLI agent-native

- [x] **3.1.** `python -m src formats|doctor`.
- [x] **3.2.** `brand check|render`.
- [x] **3.3.** `review|save|discard`.
- [x] **3.4.** `analyze|scripts list|tasks list|add|done`.
- [x] **3.5.** Salidas JSON, exit codes y errores accionables.

## Fase 4: Integración con hosts

- [x] **4.1.** `AGENTS.md` para OpenCode.
- [x] **4.2.** `CLAUDE.md` para Claude Code.
- [x] **4.3.** Slash commands en `.opencode/command/`.
- [x] **4.4.** Slash commands en `.claude/commands/`.
- [x] **4.5.** Prompts de Drafter, Reviewer, Analyst y Setup reorientados al agente host.

## Fase 5: Validación

- [x] **5.1.** Tests unitarios de toda la capa determinista.
- [x] **5.2.** Tests de integración del CLI (stdin, `--force`, JSON, errores).
- [x] **5.3.** Smoke test de `/setup`, `/script`, `/repurpose` y `/analyze` con los comandos
  documentados.
- [ ] **5.4.** Validación con un CSV real de Metricool distinto al sample.
- [ ] **5.5.** Medición de consumo de contexto del host en una semana de trabajo real.

## Futuro

- [ ] Exportación de reportes de analytics a Markdown.
- [ ] Plantillas de calendario editorial.
- [ ] Validación adicional de reglas por formato (slots de story, checklists de carrusel).
