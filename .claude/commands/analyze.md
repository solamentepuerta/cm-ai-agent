---
description: Analiza un CSV de Metricool y entrega el reporte semanal táctico.
argument-hint: [ruta del CSV]
---

Analiza las métricas del periodo. Entrada: `$ARGUMENTS` (ruta opcional; si se omite se usa el
CSV más reciente de `data/`).

1. Ejecuta `python -m src analyze <ruta-o-vacío>`. Sin `--summary` devuelve JSON compacto.
   Si falla, explica el error y pide un CSV válido; no inventes datos.
2. Lee `prompts/analyst.md` y `brand_context.md`.
3. Interpreta exclusivamente el JSON. No recalcules métricas.
4. Entrega la plantilla obligatoria: ganador, peor rendimiento y 3 ajustes concretos.
5. Si falta un dato, dilo.

$ARGUMENTS
