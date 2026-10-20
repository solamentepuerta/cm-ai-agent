---
description: Inicializa o actualiza brand_context.md mediante entrevista y validación determinista.
argument-hint: [cambios opcionales]
---

Configura la marca del proyecto.

1. Si `$ARGUMENTS` pide cambios, parte de `brand_context.md`. Si no existe, empieza de cero.
2. Entrevista al usuario: público objetivo, tono no negociable, objetivo de la cuenta,
   plataformas, reglas no negociables y 3-5 publicaciones con mejor rendimiento.
3. Lee `prompts/setup.md` antes de construir el perfil.
4. Escribe un JSON de `BrandProfile` en `scripts/drafts/brand-profile.json` y ejecuta
   `python -m src brand render scripts/drafts/brand-profile.json`. Alternativa: escribe
   `brand_context.md` directamente con las secciones obligatorias.
5. Ejecuta `python -m src brand check`. Si el exit code es `1` o `missing` no está vacío,
   corrige y repite hasta obtener `ok: true`.
6. Borra el JSON temporal y resume identidad, blacklist y reglas por formato.

No inventes ejemplos ni métricas.

$ARGUMENTS
