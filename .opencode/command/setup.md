---
description: Inicializa o actualiza brand_context.md mediante entrevista y validación determinista.
agent: build
---

Configura la marca del proyecto.

1. Si `$ARGUMENTS` pide cambios, parte de `brand_context.md`. Si no existe, empieza de cero.
2. Entrevista al usuario (usa la herramienta `question` si está disponible; si no, pregunta en
   el chat). Necesitas: público objetivo, tono no negociable, objetivo de la cuenta,
   plataformas, reglas no negociables y 3-5 publicaciones con mejor rendimiento.
3. Lee `prompts/setup.md` antes de construir el perfil.
4. Escribe un JSON de `BrandProfile` en `scripts/drafts/brand-profile.json` y ejecuta:

   ```bash
   python -m src brand render scripts/drafts/brand-profile.json
   ```

   Alternativa: escribe `brand_context.md` directamente con estas secciones:
   `# Identity & Audience`, `# Global Blacklist`, `# Voice & Tone Attributes`,
   `# Format Rules` (con `##` para los 5 formatos) y, opcionalmente, `# Style Examples`.
5. Valida:

   ```bash
   python -m src brand check
   ```

   Si el exit code es `1` o `missing` no está vacío, corrige y repite. `ok: true` es obligatorio.
6. Borra `scripts/drafts/brand-profile.json` si lo creaste.
7. Responde con un resumen breve: identidad, blacklist y reglas por formato.

No inventes ejemplos ni métricas. Si el usuario no aporta posts, dilo y usa solo la entrevista.

$ARGUMENTS
