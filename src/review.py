"""Deterministic draft review used by the host agent as a quality gate."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from src.utils.brand_context import (
    extract_blacklist,
    find_blacklist_violations,
    hook_is_verbatim,
)

_STAGE_BRACKET_RE = re.compile(r"\[[^\]\n]{1,80}\]")
_STAGE_LINE_RE = re.compile(
    r"(?im)^\s*(?:[\(\[]\s*(?:música|musica|sfx|efecto de sonido|cámara|camara|plano|"
    r"zoom|corte|transición|transicion|texto en pantalla|voz en off|voiceover)\b.*[\)\]]"
    r"|(?:música|musica|sfx|cámara|camara|plano|zoom|transición|transicion|"
    r"texto en pantalla|voz en off|voiceover)\s*:).*$"
)
_TIMESTAMP_RE = re.compile(r"(?m)^\s*\[?\d{1,2}:\d{2}\]?\s*(?:[-–—:]\s*)?")


class ReviewMetrics(BaseModel):
    """Cheap structural metrics included in the review report."""

    words: int
    characters: int
    lines: int
    blocks: int


class ReviewReport(BaseModel):
    """Structured verdict consumed by the host agent."""

    format: str
    passed: bool
    hook_matches: bool | None = None
    blacklist_violations: list[str] = Field(default_factory=list)
    stage_direction_violations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metrics: ReviewMetrics
    retry_instruction: str | None = None


def review_draft(
    draft: str,
    post_format: str,
    brand_context: str,
    user_hook: str | None = None,
) -> ReviewReport:
    """Run deterministic checks and format-specific advisory heuristics."""
    if not draft.strip():
        raise ValueError("El borrador está vacío.")

    blacklist = find_blacklist_violations(draft, extract_blacklist(brand_context))
    stage_directions = _find_stage_directions(draft)
    hook_matches = hook_is_verbatim(draft, user_hook) if user_hook else None
    warnings = _format_warnings(draft, post_format)
    metrics = ReviewMetrics(
        words=len(re.findall(r"\w+", draft, flags=re.UNICODE)),
        characters=len(draft),
        lines=len([line for line in draft.splitlines() if line.strip()]),
        blocks=len(_split_blocks(draft, post_format)),
    )

    passed = not blacklist and not stage_directions and hook_matches is not False
    return ReviewReport(
        format=post_format,
        passed=passed,
        hook_matches=hook_matches,
        blacklist_violations=blacklist,
        stage_direction_violations=stage_directions,
        warnings=warnings,
        metrics=metrics,
        retry_instruction=_retry_instruction(
            blacklist=blacklist,
            stage_directions=stage_directions,
            hook_matches=hook_matches,
        ),
    )


def _find_stage_directions(draft: str) -> list[str]:
    found: list[str] = []
    for pattern in (_STAGE_BRACKET_RE, _STAGE_LINE_RE, _TIMESTAMP_RE):
        for match in pattern.finditer(draft):
            snippet = match.group(0).strip()
            if snippet and snippet not in found:
                found.append(snippet)
    return found


def _format_warnings(draft: str, post_format: str) -> list[str]:
    words = len(re.findall(r"\w+", draft, flags=re.UNICODE))
    blocks = _split_blocks(draft, post_format)
    warnings: list[str] = []

    if post_format == "video_corto":
        if words > 220:
            warnings.append("El guion supera ~220 palabras; un video corto suele pedir 30-60 s.")
        if words < 20:
            warnings.append("El guion es muy corto para un video con gancho y CTA.")
    elif post_format == "carrusel":
        if len(blocks) < 3 and not re.search(r"(?m)^\s*\d+[.)]\s+", draft):
            warnings.append("No se detectaron láminas separadas con `---` ni una lista numerada.")
    elif post_format == "hilo_x":
        long_blocks = [block for block in blocks if len(block) > 280]
        if long_blocks:
            warnings.append("Hay bloques de más de 280 caracteres; un tweet podría pasarse.")
    elif post_format == "video_largo":
        if words < 150:
            warnings.append("El guion es muy corto para un video largo; desarrolla el argumento.")
    elif post_format == "story":
        if words > 120:
            warnings.append("El story es largo; repártelo en varias pantallas.")
        if "?" not in draft and "encuesta" not in draft.casefold():
            warnings.append("Añade una interacción explícita (pregunta, encuesta o sticker).")

    return warnings


def _split_blocks(draft: str, post_format: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"(?m)^\s*---\s*$", draft) if part.strip()]
    if len(parts) == 1 and post_format == "hilo_x":
        parts = [part.strip() for part in re.split(r"\n\s*\n", draft) if part.strip()]
    return parts


def _retry_instruction(
    *,
    blacklist: list[str],
    stage_directions: list[str],
    hook_matches: bool | None,
) -> str | None:
    parts: list[str] = []
    if blacklist:
        terms = ", ".join(f"'{term}'" for term in blacklist)
        parts.append(f"Elimina los términos de la blacklist: {terms}.")
    if stage_directions:
        parts.append("Elimina direcciones de escena, timestamps y acotaciones de producción.")
    if hook_matches is False:
        parts.append("Coloca el gancho del usuario exactamente como primera línea, sin cambios.")
    return " ".join(parts) or None
