---
description: Analiza un CSV de Metricool y entrega el reporte semanal táctico.
agent: build
---

Analiza las métricas del periodo. Entrada: `$ARGUMENTS` (ruta opcional al CSV; si se omite se
usa el CSV más reciente de `data/`).

1. Ejecuta el parser determinista:

   ```bash
   python -m src analyze <ruta-o-vacío>
   ```

   Sin `--summary` devuelve JSON compacto. Si el comando falla, explica el error y pide un CSV
   válido de Metricool; no inventes datos.
2. Lee `prompts/analyst.md` y `brand_context.md`.
3. Interpreta exclusivamente el JSON. No recalcules métricas ni agregues cifras externas.
4. Entrega el reporte con la plantilla obligatoria:
   - Ganador de la semana (post, métricas del JSON, hipótesis).
   - Peor rendimiento (post, métricas del JSON, qué no repetir).
   - 3 ajustes concretos para la próxima semana.
5. Si falta un dato, dilo explícitamente.

$ARGUMENTS
