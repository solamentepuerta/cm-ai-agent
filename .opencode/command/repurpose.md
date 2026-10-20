---
description: Adapta un guion guardado o pegado a uno o varios formatos destino.
agent: build
---

Reutiliza contenido existente. Entrada: `$ARGUMENTS` (opcional: ruta del guion fuente).

1. Lista los guiones disponibles:

   ```bash
   python -m src scripts list
   ```

2. Pregunta al usuario qué guion quiere usar o si prefiere pegar el texto. Pide los formatos
   destino (puede ser más de uno).
3. Verifica `brand_context.md`; si falta, ejecuta `/setup`.
4. Lee el guion fuente, `brand_context.md`, `prompts/drafter.md` y `prompts/reviewer.md`.
5. Para cada formato destino, ejecuta el mismo ciclo que `/script`:
   - Redacta `scripts/drafts/pending-<slug>-<formato>.md`.
   - `python -m src review --format <formato> --draft ...`
   - Máximo 2 reintentos; después, intervención humana.
   - Guarda con `python -m src save ... --source "<ruta-o-referencia>"`.
6. Limpia los pendientes y resume rutas + `task_id` de cada formato.

Conserva el argumento central del guion fuente; no copies literalmente si el formato no lo permite.
No inventes métricas ni testimonios.

$ARGUMENTS
