---
description: Crea un guion con borrador, review determinista, reintentos y guardado.
agent: build
---

Crea un guion usando el toolkit. Entrada: `$ARGUMENTS` (tema; puede incluir `Hook: ...`).

1. Si falta el formato, pregunta. Si el usuario no especifica, usa `video_corto`. Si falta el
   tema, pide un tema o ángulo concreto. Separa un `Hook: ...` si viene en los argumentos.
2. Verifica que exista `brand_context.md`. Si no existe, ejecuta el flujo de `/setup` primero.
3. Lee `brand_context.md`, `prompts/drafter.md` y `prompts/reviewer.md`.
4. Redacta el guion en `scripts/drafts/pending-<slug>.md`:
   - Texto plano, sin títulos markdown, sin direcciones de escena ni timestamps.
   - Si hay gancho, debe ser la primera línea exacta, sin cambios.
   - Respeta las reglas del formato y la blacklist.
5. Audita el borrador:

   ```bash
   python -m src review --format <formato> --draft scripts/drafts/pending-<slug>.md --hook "<gancho>"
   ```

   Omite `--hook` si no hay gancho. Un exit code `1` con `passed: false` es un rechazo normal.
6. Si `passed: false`, reescribe aplicando `retry_instruction`. Máximo 2 reintentos.
7. Si tras 2 reintentos sigue fallando, pide intervención humana:
   - **Aceptar:** `python -m src save ... --force` (solo con aceptación explícita).
   - **Feedback manual:** incorpora el feedback en un último intento y vuelve a revisar.
   - **Abortar:** `python -m src discard --format <formato> --topic "<tema>" --draft <ruta>`.
8. Si `passed: true`, guarda:

   ```bash
   python -m src save --format <formato> --topic "<tema>" --draft scripts/drafts/pending-<slug>.md --hook "<gancho>"
   ```

   Añade `--source <ruta>` si estás reutilizando un guion.
9. Borra el pendiente, muestra la ruta guardada y el `task_id`. No inventes datos ni métricas.

$ARGUMENTS
