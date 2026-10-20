---
description: Adapta un guion guardado o pegado a uno o varios formatos destino.
argument-hint: [ruta del guion fuente]
---

Reutiliza contenido existente. Entrada: `$ARGUMENTS` (ruta opcional).

1. Ejecuta `python -m src scripts list` y muestra los guiones disponibles.
2. Pregunta qué guion usar o si prefiere pegar texto. Pide los formatos destino.
3. Verifica `brand_context.md`; si falta, ejecuta `/setup`.
4. Lee el guion fuente, `brand_context.md`, `prompts/drafter.md` y `prompts/reviewer.md`.
5. Para cada formato, repite el ciclo de `/script`: borrador pendiente, `review`, máximo 2
   reintentos, intervención humana si hace falta, y `save --source "<ruta-o-referencia>"`.
6. Limpia pendientes y resume rutas + `task_id`.

Conserva el argumento central. No inventes métricas ni testimonios.

$ARGUMENTS
