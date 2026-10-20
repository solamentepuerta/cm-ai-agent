"""Brand context rendering, validation and deterministic blacklist checks."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from pydantic import BaseModel, Field

from src.state import FORMAT_LABELS, BrandProfile

DEFAULT_BLACKLIST: tuple[str, ...] = (
    "unlock",
    "unleash",
    "dive into",
    "in the world of",
    "revolutionary",
    "game-changer",
    "desata",
    "desatar",
    "revolucionario",
    "en el mundo de",
    "sumérgete",
    "sumergete",
    "furthermore",
    "in conclusion",
    "en conclusión",
    "en conclusion",
)

_FORMAT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "video_corto": ("video corto", "reel", "tiktok", "short"),
    "carrusel": ("carrusel", "carousel"),
    "hilo_x": ("hilo", "twitter", " hilo de x"),
    "video_largo": ("video largo", "youtube"),
    "story": ("story", "stories", "historias"),
}

_DEFAULT_FORMAT_RULES: dict[str, tuple[str, ...]] = {
    "video_corto": (
        "Duración objetivo 30-60 segundos.",
        "Gancho verbal en la primera línea, sin introducción de contexto.",
        "Un solo argumento central y un CTA claro.",
    ),
    "carrusel": (
        "Máximo 35 palabras por lámina.",
        "Primera lámina con gancho y promesa concreta.",
        "Última lámina con CTA explícito.",
    ),
    "hilo_x": (
        "Primer tweet con gancho autónomo.",
        "Un argumento por tweet, frases cortas.",
        "Cierre con resumen y CTA suave.",
    ),
    "video_largo": (
        "Intro sin rodeos: promete el valor en los primeros 15 segundos.",
        "Checkpoints de retención cada 2-3 minutos.",
        "Cierre con CTA y siguiente paso.",
    ),
    "story": (
        "Tono informal y directo.",
        "Máximo 2 frases por pantalla.",
        "Incluye una interacción (encuesta, sticker, pregunta).",
    ),
}

_FORMAT_KEY_ALIASES: dict[str, tuple[str, ...]] = {
    "video_corto": ("video corto", "reel", "tiktok", "short"),
    "carrusel": ("carrusel", "carousel"),
    "hilo_x": ("hilo", "twitter", "hilo de x"),
    "video_largo": ("video largo", "youtube"),
    "story": ("story", "stories", "historia"),
}


class BrandContextError(RuntimeError):
    """Raised when brand_context.md is missing or unusable."""


class BrandCheck(BaseModel):
    """Result of validating the structure and coverage of brand_context.md."""

    ok: bool
    blacklist_terms: int
    formats: dict[str, int] = Field(default_factory=dict)
    missing: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def load_brand_context(path: Path | str) -> str:
    """Load brand_context.md, failing with an actionable message if absent."""
    target = Path(path)
    if not target.exists():
        raise BrandContextError(f"No existe '{target}'. Ejecuta /setup antes de usar este comando.")
    content = target.read_text(encoding="utf-8").strip()
    if not content:
        raise BrandContextError(f"'{target}' está vacío. Ejecuta /setup para generarlo.")
    return content


def extract_format_rules(brand_context: str, post_format: str) -> str:
    """Extract the rules block for a specific format, with a safe fallback."""
    keywords = _FORMAT_KEYWORDS.get(post_format, ())
    for keywords_set in (keywords, ("format rules", "reglas por formato")):
        body = _extract_section(brand_context, keywords_set)
        if body:
            return body

    fallback = _DEFAULT_FORMAT_RULES.get(post_format, ())
    return "\n".join(f"- {rule}" for rule in fallback)


def extract_blacklist(brand_context: str) -> list[str]:
    """Parse the blacklist section into a list of normalized terms."""
    body = _extract_section(brand_context, ("blacklist", "lista negra"))
    terms = _parse_blacklist(body) if body else []
    return terms or list(DEFAULT_BLACKLIST)


def find_blacklist_violations(draft: str, blacklist: list[str]) -> list[str]:
    """Case/accent-insensitive search for blacklisted terms in a draft."""
    haystack = _normalize(draft)
    violations: list[str] = []

    for term in blacklist:
        needle = _normalize(term)
        if len(needle) < 3:
            continue
        pattern = rf"(?<!\w){re.escape(needle)}(?!\w)"
        if re.search(pattern, haystack):
            violations.append(term)

    return violations


def hook_is_verbatim(draft: str, user_hook: str) -> bool:
    """Check that the user hook is the exact first non-empty line of the draft."""
    first_line = next((line.strip() for line in draft.splitlines() if line.strip()), "")
    return first_line == user_hook.strip()


def normalize_format_rules(rules: dict[str, list[str]]) -> dict[str, list[str]]:
    """Map label-style or accented keys onto the canonical format keys."""
    normalized: dict[str, list[str]] = {}
    for key, values in rules.items():
        canonical = _canonical_format(key)
        cleaned = [str(value).strip() for value in values if str(value).strip()]
        if canonical and cleaned:
            normalized[canonical] = cleaned
    return normalized


def render_brand_context(profile: BrandProfile) -> str:
    """Render a validated BrandProfile into the canonical Markdown file."""
    blacklist = _unique([*profile.blacklist, *DEFAULT_BLACKLIST])
    tone = profile.tone_attributes or ["Directo", "Pragmático", "Sin relleno"]
    rules_by_format = normalize_format_rules(profile.format_rules)

    lines = [
        "# Identity & Audience",
        "",
        profile.identity.strip(),
        "",
        f"**Público objetivo:** {profile.target_audience.strip()}",
        "",
        "# Global Blacklist",
        "",
        "Términos y clichés prohibidos (ES/EN). El Reviewer los audita sin excepción.",
        "",
        *[f"- `{term}`" for term in blacklist],
        "",
        "# Voice & Tone Attributes",
        "",
        *[f"- {attribute}" for attribute in tone],
        "",
        "# Format Rules",
        "",
    ]

    for key, label in FORMAT_LABELS.items():
        rules = rules_by_format.get(key) or list(_DEFAULT_FORMAT_RULES.get(key, ()))
        lines.extend([f"## {label}", ""])
        lines.extend(f"- {rule}" for rule in rules)
        lines.append("")

    if profile.style_examples:
        lines.extend(["# Style Examples", ""])
        lines.extend(f"- {example}" for example in profile.style_examples)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def check_brand_context(brand_context: str) -> BrandCheck:
    """Validate required sections and count usable rules/terms."""
    missing: list[str] = []
    warnings: list[str] = []

    identity = _extract_section(brand_context, ("identity", "audiencia", "público objetivo"))
    if not identity:
        missing.append("identity")

    blacklist_body = _extract_section(brand_context, ("blacklist", "lista negra"))
    blacklist = _parse_blacklist(blacklist_body) if blacklist_body else []
    if not blacklist:
        missing.append("blacklist")
    elif len(blacklist) < 8:
        warnings.append(
            "La blacklist tiene menos de 8 términos; añade clichés específicos del nicho."
        )

    tone = _extract_section(brand_context, ("voice", "tone", "tono"))
    if not tone:
        missing.append("tone")

    formats: dict[str, int] = {}
    for key, keywords in _FORMAT_KEYWORDS.items():
        body = _extract_section(brand_context, keywords)
        count = len(_bullet_lines(body))
        formats[key] = count
        if count == 0:
            missing.append(f"format:{key}")

    return BrandCheck(
        ok=not missing,
        blacklist_terms=len(blacklist),
        formats=formats,
        missing=missing,
        warnings=warnings,
    )


def _parse_blacklist(body: str | None) -> list[str]:
    terms: list[str] = []
    for cleaned in _bullet_lines(body):
        cleaned = cleaned.strip("`*_ ")
        cleaned = re.sub(r"^[\d.)]+\s*", "", cleaned)
        cleaned = cleaned.split("—")[0].split(" - ")[0].strip()
        if cleaned:
            terms.append(cleaned)
    return terms


def _bullet_lines(body: str | None) -> list[str]:
    if not body:
        return []
    lines: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith(("-", "*")):
            content = stripped.lstrip("-*").strip()
        else:
            match = re.match(r"^\d+[.)]\s+(.*)$", stripped)
            content = match.group(1).strip() if match else ""
        if content:
            lines.append(content)
    return lines


def _canonical_format(key: str) -> str | None:
    raw = key.strip().casefold()
    if raw in FORMAT_LABELS:
        return raw
    text = _normalize(key).replace("_", " ")
    for canonical, keywords in _FORMAT_KEY_ALIASES.items():
        if any(keyword in text for keyword in keywords):
            return canonical
    return None


def _extract_section(text: str, keywords: tuple[str, ...]) -> str | None:
    lines = text.splitlines()
    headings = _headings(lines)

    for position, (index, level, title) in enumerate(headings):
        normalized = _normalize(title)
        if not any(keyword in normalized for keyword in keywords):
            continue

        end = len(lines)
        for next_index, next_level, _ in headings[position + 1 :]:
            if next_level <= level:
                end = next_index
                break
        return "\n".join(lines[index + 1 : end]).strip()

    return None


def _headings(lines: list[str]) -> list[tuple[int, int, str]]:
    headings: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        match = re.match(r"^(#{1,6})\s+(.*)$", line.strip())
        if match:
            headings.append((index, len(match.group(1)), match.group(2).strip()))
    return headings


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", value)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text.casefold()).strip()


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        clean = value.strip().strip("`*_ ")
        key = clean.casefold()
        if clean and key not in seen:
            seen.add(key)
            result.append(clean)
    return result
