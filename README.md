# AI Community Manager Assistant (Agent-Native Toolkit)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Host: OpenCode / Claude Code](https://img.shields.io/badge/host-OpenCode%20%7C%20Claude%20Code-purple.svg)](https://opencode.ai)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

Toolkit local para que **OpenCode** o **Claude Code** actúen como Community Manager Assistant.
El agente host es el LLM: conversa, redacta y decide. El repositorio aporta **herramientas
deterministas** para validar, parsear, persistir y organizar el trabajo.

**No hay API keys, ni cliente OpenAI, ni LangGraph, ni llamadas a modelos desde el código.**

---

## Qué hace

- **`/setup`**: entrevista al usuario y genera `brand_context.md` validado.
- **`/script`**: redacta un guion, lo audita contra la blacklist y las reglas de formato, y lo
  guarda con una tarea de producción.
- **`/repurpose`**: adapta un guion existente a otros formatos.
- **`/analyze`**: limpia un CSV de Metricool con Python y entrega el JSON que el agente interpreta.
- **`/tasks`**: gestiona tareas humanas en `tasks.md` con IDs `TASK-YYYYMMDD-XXX`.

Todo el estado vive en Markdown y CSV locales. Sin base de datos, sin historial de chat, sin
secretos.

## Cómo funciona

```text
OpenCode / Claude Code (el LLM y el orquestador)
│
├── lee AGENTS.md o CLAUDE.md
├── ejecuta slash commands (.opencode/command o .claude/commands)
├── lee brand_context.md y prompts/*.md
│
└── usa herramientas deterministas:
    ├── python -m src brand check|render
    ├── python -m src review
    ├── python -m src save|discard
    ├── python -m src analyze
    ├── python -m src scripts list
    └── python -m src tasks list|add|done
```

El gancho del usuario se conserva **verbatim** como primera línea. Tras **2 reintentos**
fallidos del ciclo redacción→review, el agente debe pedir intervención humana.

## Instalación

```bash
git clone https://github.com/tu-usuario/community-ai-manager.git
cd community-ai-manager
```

Con `uv` (recomendado):

```bash
uv venv --python 3.11
uv pip install -r requirements.txt
```

O con `venv`:

```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Comprueba el entorno:

```bash
python -m src doctor
```

No hay que configurar ninguna clave. `config.yaml` solo contiene rutas; si no existe, se usan
las de la raíz del repositorio. Puedes copiar la plantilla si quieres personalizarlas:

```bash
cp config.example.yaml config.yaml
```

En Windows PowerShell:

```powershell
Copy-Item config.example.yaml config.yaml
```

## Uso con OpenCode

1. Abre el repositorio con OpenCode.
2. OpenCode carga `AGENTS.md` y descubre los comandos de `.opencode/command/`.
3. Ejecuta `/setup`, `/script`, `/repurpose`, `/analyze` o `/tasks`.

```text
/setup
/script 3 errores al medir engagement. Hook: El 90% mide mal el alcance.
/analyze
/tasks add "Revisar métricas del viernes"
```

## Uso con Claude Code

1. Abre el repositorio con Claude Code.
2. Claude Code carga `CLAUDE.md` (que importa `AGENTS.md`) y los comandos de `.claude/commands/`.
3. Usa los mismos slash commands.

## Herramientas deterministas

### Marca

```bash
python -m src brand check
python -m src brand render scripts/drafts/brand-profile.json
python -m src brand render -        # JSON por stdin
```

`brand check` devuelve JSON con `ok`, `blacklist_terms`, `formats`, `missing` y `warnings`.
`ok: true` exige identidad, blacklist, tono y las cinco secciones de formato.

### Revisión

```bash
python -m src review --format video_corto --draft scripts/drafts/pending.md \
  --hook "Gancho exacto"

python -m src review --format hilo_x --draft -   # borrador por stdin
```

Salida JSON con `passed`, `hook_matches`, `blacklist_violations`,
`stage_direction_violations`, `warnings`, `metrics` y `retry_instruction`.
Exit `0` si pasa; `1` si hay violaciones. Los `warnings` no bloquean.

### Guardar y descartar

```bash
python -m src save --format video_corto --topic "Tema" \
  --draft scripts/drafts/pending.md --hook "Gancho exacto"

python -m src save --format carrusel --topic "Tema" --draft - --source "scripts/fuente.md"
python -m src save ... --force      # solo tras aceptación humana explícita
python -m src discard --format story --topic "Tema" --draft scripts/drafts/pending.md
```

`save` vuelve a ejecutar el review. Crea `scripts/YYYY-MM-DD_<formato>_<slug>.md` y una tarea
`EDIT` en `tasks.md`. `discard` guarda en `scripts/drafts/` y no crea tarea.

### Métricas

```bash
python -m src analyze                                  # CSV más reciente de data/
python -m src analyze data/metricool_sample_week42.csv
python -m src analyze data/week42.csv --top 5
python -m src analyze data/week42.csv --summary        # tabla legible
```

Sin `--summary` imprime JSON compacto. El agente interpreta ese JSON; no recalcula las métricas.

### Scripts y tareas

```bash
python -m src scripts list
python -m src tasks list
python -m src tasks list --all --json
python -m src tasks add "Revisar métricas del viernes"
python -m src tasks done TASK-20261020-001
```

## Estructura

```text
.
├── AGENTS.md                  Instrucciones para OpenCode
├── CLAUDE.md                  Instrucciones para Claude Code (importa AGENTS.md)
├── .opencode/command/         Slash commands de OpenCode
├── .claude/commands/          Slash commands de Claude Code
├── prompts/                   Instrucciones de Drafter, Reviewer, Analyst y Setup
├── src/
│   ├── cli.py                 CLI determinista (`python -m src`)
│   ├── review.py              Blacklist, hook verbatim, stage directions y warnings
│   ├── config.py              Rutas (sin secretos)
│   ├── state.py               Formatos y BrandProfile
│   └── utils/                 Brand context, Metricool, persistencia, tareas y file I/O
├── brand_context.md           Estado de marca (generado por /setup)
├── tasks.md                   Tareas humanas (solo vía CLI)
├── data/                      CSVs de Metricool (incluye un ejemplo)
└── scripts/                   Guiones aprobados y drafts temporales
```

## Desarrollo

```bash
pytest -q
ruff check src tests
ruff format --check src tests
mypy src
```

No uses `ruff format .`: intenta formatear bloques de código dentro de los `.md`.

## Licencia

Distribuido bajo la licencia [MIT](LICENSE).
