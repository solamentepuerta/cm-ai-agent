# AI Community Manager Assistant — Agent Guide

Este repositorio es un **toolkit determinista** para que OpenCode o Claude Code actúen como
Community Manager Assistant. El agente host es el LLM: no hay API key, cliente OpenAI,
LangGraph ni llamadas a modelos desde el proyecto.

## Reglas duras

1. **No agregues ni uses API keys.** No invoques APIs de LLM desde el código. El modelo es el
   agente que está ejecutando esta sesión.
2. **La lógica de negocio vive en `python -m src ...`.** No reimplementes parsing, reviews,
   persistencia ni tareas a mano.
3. **Lee `brand_context.md` antes de redactar.** Si no existe, ejecuta el flujo de `/setup`.
4. **Gancho verbatim:** si el usuario aporta un gancho, debe ser la primera línea exacta.
5. **Máximo 2 reintentos** de Drafter→Reviewer. Después, intervención humana obligatoria.
6. **No inventes métricas, cifras, estudios ni testimonios.** Para `/analyze`, usa únicamente
   el JSON que produce el parser.
7. **No edites `tasks.md` manualmente.** Usa `python -m src tasks ...`.
8. **No guardes un guion sin pasar `review`.** `save` vuelve a validar; usa `--force` solo si
   el humano aceptó explícitamente un borrador con violaciones.
9. **Texto plano:** sin direcciones de escena, música, cámara, timestamps ni acotaciones.
10. **Borra los borradores temporales** cuando termines (`.md` dentro de `scripts/drafts/`).

## Comandos deterministas

Ejecuta desde la raíz del repositorio. Si el venv no está activo en Windows, usa
`.\.venv\Scripts\python -m src ...`.

### Formatos

```bash
python -m src formats
```

### Marca

```bash
python -m src brand check
python -m src brand render scripts/drafts/brand-profile.json
python -m src brand render -            # perfil JSON por stdin
```

`brand check` devuelve JSON. `ok: true` exige identidad, blacklist, tono y las 5 secciones de
formato. Si `missing` no está vacío, corrige `brand_context.md` y repite.

### Revisión de un borrador

```bash
python -m src review --format video_corto --draft scripts/drafts/pending.md \
  --hook "Gancho exacto del usuario" --summary

python -m src review --format carrusel --draft -    # borrador por stdin, salida JSON
```

- Exit `0` + `passed: true`: apto para guardar.
- Exit `1` + `passed: false`: aplica `retry_instruction` y reescribe.
- `warnings` son avisos de formato; no bloquean el guardado.
- `stage_direction_violations` y `blacklist_violations` sí bloquean.

### Guardar / descartar

```bash
python -m src save --format video_corto --topic "Tema" \
  --draft scripts/drafts/pending.md --hook "Gancho exacto"

python -m src save --format carrusel --topic "Tema" --draft - --source "scripts/...md"
python -m src save ... --force --no-task     # solo tras aceptación humana explícita
python -m src discard --format story --topic "Tema" --draft scripts/drafts/pending.md
```

`save` crea `scripts/YYYY-MM-DD_<formato>_<slug>.md` y una tarea `EDIT` en `tasks.md`.
`discard` guarda en `scripts/drafts/` y no crea tarea.

### Métricas

```bash
python -m src analyze                                # CSV más reciente de data/
python -m src analyze data/metricool_sample_week42.csv
python -m src analyze data/week42.csv --top 5
python -m src analyze data/week42.csv --summary      # tabla legible
```

Sin `--summary` imprime JSON compacto. Interpreta ese JSON; no recalcules las métricas.

### Scripts y tareas

```bash
python -m src scripts list
python -m src tasks list
python -m src tasks list --all --json
python -m src tasks add "Revisar métricas del viernes"
python -m src tasks done TASK-20261020-001
```

### Diagnóstico

```bash
python -m src doctor
```

## Flujos

### 1. `/setup`

1. Entrevista al usuario: público objetivo, tono no negociable, objetivo, plataformas,
   no negociables y 3-5 publicaciones de mejor rendimiento.
2. Lee `prompts/setup.md`.
3. Escribe un `BrandProfile` JSON en `scripts/drafts/brand-profile.json` o redacta
   `brand_context.md` directamente con las secciones obligatorias.
4. Ejecuta `python -m src brand render ...` (si usaste JSON) y luego `python -m src brand check`.
5. Corrige hasta que `ok` sea `true`. Responde con un resumen breve.

### 2. `/script`

1. Obtén formato, tema, gancho opcional y CTA/objetivo. `video_corto` es el formato por defecto
   solo si el usuario no especifica otro.
2. Verifica `brand_context.md`; si falta, ejecuta `/setup` primero.
3. Lee `prompts/drafter.md`, `prompts/reviewer.md` y `brand_context.md`.
4. Redacta en `scripts/drafts/pending-<slug>.md` (texto plano).
5. Ejecuta `review` con `--hook` si existe.
6. Si falla, reescribe aplicando `retry_instruction`. Máximo 2 reintentos.
7. Si sigue fallando, ofrece: aceptar, feedback manual para un último intento, o abortar.
   - Abortar: `discard`.
   - Aceptar: `save --force`.
8. Si pasa: `save`.
9. Limpia el pendiente y muestra ruta + `task_id`.

### 3. `/repurpose`

1. `python -m src scripts list`; el usuario elige un script o pega texto.
2. Pide los formatos destino (puede ser más de uno).
3. Para cada formato, ejecuta el mismo ciclo que `/script`, leyendo el guion fuente.
4. Guarda cada resultado con `--source <ruta-o-referencia>`.

### 4. `/analyze`

1. Ejecuta `python -m src analyze [ruta]` (JSON compacto).
2. Lee `prompts/analyst.md` y `brand_context.md`.
3. Entrega el reporte con la plantilla obligatoria: ganador, peor rendimiento y 3 ajustes.
4. Si faltan datos, dilo; no los inventes.

### 5. `/tasks`

- Sin argumentos: lista tareas abiertas.
- `done <id>`: completa una tarea.
- `add <descripción>`: crea una tarea manual.
- Usa `--json` cuando necesites procesar la salida.

## Estructura

```text
AGENTS.md / CLAUDE.md       Instrucciones para los agentes host
.opencode/command/          Slash commands de OpenCode
.claude/commands/           Slash commands de Claude Code
prompts/                    Instrucciones de Drafter, Reviewer, Analyst y Setup
src/cli.py                  CLI determinista
src/review.py               Blacklist, hook verbatim, stage directions y warnings
src/utils/                  Brand context, CSV, persistencia, tareas y file I/O
brand_context.md            Estado de marca (generado por /setup)
tasks.md                    Tareas humanas (solo vía CLI)
data/                       CSVs de Metricool
scripts/                    Guiones aprobados y drafts temporales
```

## Desarrollo

```bash
pytest -q
ruff check src tests
ruff format --check src tests
mypy src
```

No uses `ruff format .`: intenta formatear bloques de código dentro de los `.md`.
