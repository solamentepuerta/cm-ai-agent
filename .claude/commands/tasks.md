---
description: Lista, añade o completa tareas humanas en tasks.md.
argument-hint: [list | done <id> | add <descripción>]
---

Gestiona el tablero de tareas humanas. Entrada: `$ARGUMENTS`.

- Sin argumentos o `list`: `python -m src tasks list`
- `done <id>`: `python -m src tasks done <id>`
- `add <descripción>`: `python -m src tasks add "<descripción>"`

Usa `--json` si necesitas procesar la salida. No edites `tasks.md` manualmente.

$ARGUMENTS
