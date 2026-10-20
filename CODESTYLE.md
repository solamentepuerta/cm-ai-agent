# AI Community Manager Assistant — Code Style & Engineering Guidelines

Estándares para el toolkit determinista. El LLM es el agente host (OpenCode/Claude Code); el
código Python no invoca modelos ni guarda secretos.

---

## 1. Python Standards & Tooling

- **Python 3.11+**.
- **Ruff** para lint y formato:
  - Línea máxima: 100 caracteres.
  - Reglas: `E`, `F`, `I`, `B`, `UP`.
  - Formatear solo `src tests` con `ruff format src tests`; nunca `ruff format .` porque
    reformatea bloques Python dentro de los `.md`.
- **mypy `--strict`**: tipar argumentos, retornos y estructuras intermedias.
- Sin dependencias de LLM (`openai`, `langgraph`, `anthropic`, etc.).

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_unused_configs = true
```

---

## 2. Deterministic Core Conventions

- La lógica de negocio vive en `python -m src ...`; los prompts y el agente host no la
  reimplementan.
- Las funciones de dominio reciben y devuelven tipos explícitos (`ReviewReport`, `BrandCheck`,
  `MetricoolReport`, etc.).
- Los comandos CLI devuelven JSON estable; los errores de dominio se convierten en
  `{"error": "..."}` con exit `1`.
- El review es una función pura sobre texto + reglas: sin I/O de red y sin llamadas a modelos.
- La persistencia se concentra en `src/utils/persister.py` y `src/utils/file_io.py`.

---

## 3. Host Agent Conventions

- Las instrucciones del agente viven en `AGENTS.md`, `CLAUDE.md`, `prompts/*.md` y los slash
  commands. No hardcodear prompts largos en Python.
- El agente debe leer `brand_context.md` antes de redactar y usar el CLI para validar, guardar,
  analizar y gestionar tareas.
- Máximo 2 reintentos Drafter→Reviewer. Después, intervención humana obligatoria.
- El gancho del usuario es la primera línea exacta del guion.
- Prohibido inventar métricas, testimonios, estudios o cifras.

---

## 4. Safe File I/O

- Toda escritura de estado (`brand_context.md`, `tasks.md`, `scripts/*.md`) debe ser atómica:
  escribir `.tmp` adyacente y reemplazar con `os.replace()`.
- Crear directorios padres con `mkdir(parents=True, exist_ok=True)`.
- UTF-8 explícito al leer y escribir.
- `scripts/drafts/` es temporal; los guiones aprobados van a `scripts/`.

---

## 5. Token Minimization

- No pasar DataFrames completos al agente: `python -m src analyze` agrega y devuelve JSON
  compacto.
- No repetir `brand_context.md` ni archivos completos en cada turno; leerlos cuando haga falta.
- Preferir salidas estructuradas y resúmenes breves.
- No usar historial de conversación como fuente de verdad; el estado está en archivos.

---

## 6. Testing

```bash
pytest -q
ruff check src tests
ruff format --check src tests
mypy src
```

- Tests unitarios para parsing, review, tareas, persistencia y brand context.
- Tests de integración del CLI incluyendo stdin, `--force`, `--json` y errores.
- Cualquier cambio de contrato CLI debe actualizar `SPECS.md`, `AGENTS.md` y tests.
