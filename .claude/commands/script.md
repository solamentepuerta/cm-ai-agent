---
description: Crea un guion con borrador, review determinista, reintentos y guardado.
argument-hint: [tema] [Hook: gancho exacto]
---

Crea un guion usando el toolkit. Entrada: `$ARGUMENTS` (tema; puede incluir `Hook: ...`).

1. Si falta el formato, pregunta; por defecto usa `video_corto`. Si falta el tema, pídelo.
   Separa un `Hook: ...` si viene en los argumentos.
2. Verifica `brand_context.md`; si no existe, ejecuta el flujo de `/setup` primero.
3. Lee `brand_context.md`, `prompts/drafter.md` y `prompts/reviewer.md`.
4. Redacta en `scripts/drafts/pending-<slug>.md`: texto plano, sin direcciones de escena,
   timestamps ni títulos markdown. El gancho, si existe, es la primera línea exacta.
5. Audita con `python -m src review --format <formato> --draft <ruta> [--hook "<gancho>"]`.
   Un exit code `1` con `passed: false` es un rechazo normal del review.
6. Si falla, aplica `retry_instruction` y reescribe. Máximo 2 reintentos.
7. Tras 2 fallos, pide intervención humana:
   - Aceptar: `python -m src save ... --force` solo con aceptación explícita.
   - Feedback: un último intento y nueva revisión.
   - Abortar: `python -m src discard --format <formato> --topic "<tema>" --draft <ruta>`.
8. Si pasa, guarda con `python -m src save --format <formato> --topic "<tema>" --draft <ruta>
   [--hook "<gancho>"] [--source "<fuente>"]`.
9. Borra el pendiente y muestra ruta + `task_id`. No inventes datos.

$ARGUMENTS
