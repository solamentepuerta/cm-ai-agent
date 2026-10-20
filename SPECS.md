# AI Community Manager Assistant — Technical Specifications (v0.2)

## 1. System Overview

Toolkit determinista para que OpenCode o Claude Code actúen como Community Manager Assistant.
El agente host es el LLM y el orquestador; el repositorio no contiene cliente LLM, API keys ni
llamadas a modelos.

Prioridades: **Zero AI Sound** (blacklist y reglas auditadas con código), **bajo consumo de
contexto** (parsing local), **control humano** (máximo 2 reintentos) y **estado en archivos**
(sin base de datos ni historial de chat).

## 2. Architecture

```text
Host agent (OpenCode / Claude Code)
├── AGENTS.md / CLAUDE.md
├── slash commands (.opencode/command, .claude/commands)
├── prompts/*.md
└── python -m src <command>
    ├── brand check|render
    ├── review
    ├── save|discard
    ├── analyze
    ├── scripts list
    ├── tasks list|add|done
    ├── formats
    └── doctor
```

El agente nunca reimplementa parsing, reviews, persistencia ni tareas: invoca el CLI.

## 3. State Files

### `brand_context.md`

Generado por `/setup` y validado por `brand check`. Secciones obligatorias: `# Identity &
Audience`, `# Global Blacklist` (≥8 términos recomendados), `# Voice & Tone Attributes` y
`# Format Rules` con un `##` para `video_corto`, `carrusel`, `hilo_x`, `video_largo` y `story`.
`# Style Examples` es opcional.

### `tasks.md`

```text
- [ ] [TASK-20261020-001] **EDIT** — Producir y publicar Video Corto: Tema
  - Formato: Video Corto (Reel / TikTok / Shorts)
  - Archivo: scripts/2026-10-20_video_corto_tema.md
  - Notas: Guion aprobado. Revisar, producir y publicar el contenido.
```

Solo se modifica mediante `python -m src tasks ...`.

### `scripts/`

`scripts/YYYY-MM-DD_<formato>_<slug>.md` para aprobados; `scripts/drafts/` para temporales y
descartes (ignorado por Git).

## 4. Command Contracts

Todos los comandos se ejecutan desde la raíz. Las rutas se resuelven desde `config.yaml` o desde
la raíz si no existe.

- `formats`: lista los cinco formatos y sus etiquetas.
- `doctor`: muestra Python y existencia de brand context, tasks, data, scripts y prompts.

### `brand check`

```json
{
  "ok": true,
  "blacklist_terms": 18,
  "formats": {"video_corto": 3, "carrusel": 3, "hilo_x": 3, "video_largo": 3, "story": 3},
  "missing": [],
  "warnings": []
}
```

Exit `0` si `ok` es `true`; `1` si falta alguna sección.

### `brand render <json|-> [--out PATH]`

Lee un `BrandProfile` JSON, normaliza las claves de formato y escribe `brand_context.md`.
Devuelve `path` y el resultado de `brand check`.

### `review --format <fmt> --draft <path|-> [--hook <texto>] [--summary]`

```json
{
  "format": "video_corto",
  "passed": false,
  "hook_matches": true,
  "blacklist_violations": ["desata"],
  "stage_direction_violations": ["[Música épica]"],
  "warnings": ["El guion supera ~220 palabras..."],
  "metrics": {"words": 120, "characters": 700, "lines": 8, "blocks": 1},
  "retry_instruction": "Elimina los términos de la blacklist: 'desata'."
}
```

`passed = true` exige: sin blacklist, sin stage directions y hook verbatim si se aportó. Los
`warnings` son advertencias de formato y no bloquean.

### `save --format <fmt> --topic <tema> --draft <path|-> [--hook] [--source] [--force] [--no-task]`

Vuelve a ejecutar `review`. Si falla devuelve `saved: false` y exit `1`; `--force` solo se usa
tras aceptación humana explícita. Si guarda, escribe el script y crea una tarea `EDIT` salvo
`--no-task`. Devuelve `path`, `task_id` y el review.

### `discard --format <fmt> --topic <tema> --draft <path|->`

Guarda en `scripts/drafts/` sin crear tarea.

### `analyze [path] [--top N] [--summary]`

Parsea el CSV de Metricool con Pandas, normaliza columnas ES/EN, detecta encabezado y separador,
calcula engagement/retención/promedios y devuelve JSON compacto. Sin ruta usa el CSV más reciente
de `data/`. La ruta relativa se busca primero en el cwd y luego en `data_dir`.

### `scripts list`

Lista los `.md` de `scripts/` con nombre, ruta, tamaño y fecha de modificación.

### `tasks`

`tasks list [--all] [--json]`, `tasks add "<descripción>" [--type] [--deadline] [--notes]` y
`tasks done <id>`.

## 5. Review Rules

1. **Blacklist:** búsqueda determinista, case/accent-insensitive, con límites de palabra.
2. **Hook verbatim:** comparación exacta contra la primera línea no vacía.
3. **Stage directions:** corchetes, líneas de producción (`Música:`, `Cámara:`, etc.) y
   timestamps al inicio de línea.
4. **Warnings por formato:** longitud de video corto/largo, separadores de carrusel, límite de
   280 caracteres por tweet e interacción en story.
5. **CTA/tono:** los evalúa el agente leyendo `brand_context.md`; no hay heurística fiable.

## 6. Agent Workflows

- `/setup`: entrevista → `BrandProfile` JSON o Markdown → `brand render` → `brand check` hasta
  `ok: true`.
- `/script`: entradas → borrador en `scripts/drafts/pending-<slug>.md` → `review` → reintentos
  (máx. 2) → intervención humana si falla → `save` o `discard`.
- `/repurpose`: `scripts list` → fuente → formatos destino → ciclo de `/script` → `save --source`.
- `/analyze`: `analyze` → leer `prompts/analyst.md` → interpretar solo el JSON → reporte.
- `/tasks`: `tasks list|add|done`; nunca editar `tasks.md` a mano.

## 7. Error Handling

- Errores de dominio (`BrandContextError`, `MetricoolParseError`, archivos ausentes) devuelven
  JSON `{"error": "..."}` y exit `1`.
- Un review fallido también devuelve exit `1`, pero con JSON estructurado; es un resultado
  esperado, no un fallo de infraestructura.
- `save` sin `--force` no escribe nada si el review falla.

## 8. Testing

```bash
pytest -q
ruff check src tests
ruff format --check src tests
mypy src
```

Cobertura: config, file I/O, tareas, parser Metricool, brand context, review determinista,
persistencia y CLI (stdin, `--force`, `--json` y errores).
