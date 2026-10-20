"""Deterministic Metricool CSV parser: cleans data before any LLM sees it."""

from __future__ import annotations

import csv
import re
import unicodedata
from collections.abc import Iterable
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field


class MetricoolParseError(ValueError):
    """Raised when a CSV cannot be interpreted as a Metricool export."""


class PostSummary(BaseModel):
    """Condensed metrics for a single post."""

    platform: str
    date: str | None = None
    title: str
    reach: int = 0
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    engagement_rate: float = 0.0
    retention_rate: float | None = None


class PeriodAverages(BaseModel):
    """Aggregated averages for the analyzed period."""

    engagement_rate: float = 0.0
    retention_rate: float | None = None
    reach: int = 0
    views: int = 0


class AnalysisPayload(BaseModel):
    """Compact payload sent to the Analyst LLM (~400 tokens)."""

    posts_analyzed: int
    averages: PeriodAverages
    top_posts: list[PostSummary] = Field(default_factory=list)
    bottom_posts: list[PostSummary] = Field(default_factory=list)


_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "platform": ("red social", "red", "platform", "network", "canal"),
    "date": ("fecha de publicacion", "fecha publicacion", "fecha", "date", "published"),
    "title": ("publicacion", "post", "contenido", "copy", "titulo", "title", "caption", "texto"),
    "reach": ("alcance", "reach", "impresiones", "impressions"),
    "views": (
        "visualizaciones",
        "reproducciones",
        "views",
        "vistas",
        "video views",
        "reproducciones de video",
    ),
    "likes": ("me gusta", "likes", "reacciones", "reactions"),
    "comments": ("comentarios", "comments"),
    "shares": ("compartidos", "veces compartido", "shares", "compartir"),
    "saves": ("guardados", "saves", "favoritos", "saved"),
    "clicks": ("clics en el enlace", "clics", "clicks", "link clicks"),
    "interactions": ("interacciones", "interactions", "total interactions"),
    "retention": (
        "tasa de retencion",
        "retencion",
        "retention rate",
        "retention",
        "retencion media",
    ),
    "completion": (
        "tasa de finalizacion",
        "finalizacion",
        "completion rate",
        "completion",
        "completion rate",
    ),
    "engagement": (
        "tasa de engagement",
        "engagement rate",
        "engagement",
        "interaction rate",
    ),
}

_ALL_ALIASES = tuple(
    sorted(
        {alias for aliases in _COLUMN_ALIASES.values() for alias in aliases},
        key=len,
        reverse=True,
    )
)


def parse_metricool_csv(path: Path | str, top_n: int = 3) -> AnalysisPayload:
    """Parse a Metricool CSV file into a compact deterministic payload."""
    target = Path(path)
    if not target.exists():
        raise MetricoolParseError(f"No existe el archivo de métricas: {target}")

    frame = _read_with_header_detection(target)
    return _build_payload(frame, source_name=target.stem, top_n=top_n)


def parse_metricool_text(text: str, source_name: str = "", top_n: int = 3) -> AnalysisPayload:
    """Parse CSV content already loaded into memory (useful for tests)."""
    frame = _detect_and_read(StringIO(text))
    return _build_payload(frame, source_name=source_name, top_n=top_n)


def to_compact_json(payload: AnalysisPayload) -> str:
    """Serialize the payload without whitespace to minimize tokens."""
    return payload.model_dump_json()


def _read_with_header_detection(path: Path) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(path, encoding=encoding) as handle:
                return _detect_and_read(handle)
        except (UnicodeDecodeError, pd.errors.ParserError) as exc:
            last_error = exc
    raise MetricoolParseError(f"No se pudo leer el CSV: {last_error}")


def _detect_and_read(handle: Any) -> pd.DataFrame:
    text = handle.read()
    if not text.strip():
        raise MetricoolParseError("El CSV está vacío.")

    lines = text.splitlines()
    best_score = -1
    best_separator = ","
    best_header = 0

    for separator in (",", ";", "\t", "|"):
        for index, line in enumerate(lines[:25]):
            try:
                cells = next(csv.reader([line], delimiter=separator))
            except csv.Error:
                continue
            score = _score_row(cells)
            if score > best_score:
                best_score = score
                best_separator = separator
                best_header = index

    if best_score < 2:
        raise MetricoolParseError("No se reconocieron columnas de métricas en el CSV.")

    return pd.read_csv(
        StringIO(text),
        header=0,
        skiprows=best_header,
        dtype=str,
        skip_blank_lines=True,
        keep_default_na=False,
        sep=best_separator,
        engine="python",
        on_bad_lines="skip",
    )


def _score_row(row: Iterable[Any]) -> int:
    score = 0
    for cell in row:
        normalized = _normalize_header(str(cell))
        if not normalized:
            continue
        if any(alias == normalized or alias in normalized for alias in _ALL_ALIASES):
            score += 1
    return score


def _normalize_header(value: str) -> str:
    text = unicodedata.normalize("NFKD", value)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _resolve_column(
    columns: Iterable[Any],
    aliases: tuple[str, ...],
    excluded: set[str] | None = None,
) -> str | None:
    excluded = excluded or set()
    normalized = {
        str(column): _normalize_header(str(column))
        for column in columns
        if str(column) not in excluded
    }

    for alias in aliases:
        for original, norm in normalized.items():
            if norm == alias:
                return original
    for alias in aliases:
        for original, norm in normalized.items():
            if alias in norm:
                return original
    return None


def _build_payload(frame: pd.DataFrame, source_name: str, top_n: int) -> AnalysisPayload:
    if frame.empty:
        raise MetricoolParseError("El CSV no contiene filas de datos.")

    columns = list(frame.columns)
    resolved: dict[str, str | None] = {}
    excluded: set[str] = set()

    for field in ("date", "platform", "title"):
        column = _resolve_column(columns, _COLUMN_ALIASES[field], excluded)
        resolved[field] = column
        if column:
            excluded.add(column)

    for field in (
        "reach",
        "views",
        "likes",
        "comments",
        "shares",
        "saves",
        "clicks",
        "interactions",
        "retention",
        "completion",
        "engagement",
    ):
        resolved[field] = _resolve_column(columns, _COLUMN_ALIASES[field], excluded)

    has_interactions = any(
        resolved[field]
        for field in ("likes", "comments", "shares", "saves", "clicks", "interactions")
    )
    if not has_interactions and not resolved["engagement"]:
        raise MetricoolParseError(
            "No se encontraron columnas de interacciones ni de engagement en el CSV."
        )

    platform_hint = _infer_platform(source_name)
    posts: list[PostSummary] = []

    for position, (_, row) in enumerate(frame.iterrows(), start=1):
        title = _cell(row, resolved["title"]) or f"Post {position}"
        platform = _cell(row, resolved["platform"]) or platform_hint
        reach = _to_int(row, resolved["reach"])
        views = _to_int(row, resolved["views"])
        likes = _to_int(row, resolved["likes"])
        comments = _to_int(row, resolved["comments"])
        shares = _to_int(row, resolved["shares"])
        saves = _to_int(row, resolved["saves"])
        total_interactions = _to_int(row, resolved["interactions"])

        denominator = reach or views
        if has_interactions and denominator > 0:
            interactions = total_interactions or (likes + comments + shares + saves)
            engagement = round(interactions / denominator * 100, 2)
        else:
            engagement = _parse_rate(_cell(row, resolved["engagement"])) or 0.0

        retention = _parse_rate(_cell(row, resolved["retention"]))
        if retention is None:
            retention = _parse_rate(_cell(row, resolved["completion"]))

        posts.append(
            PostSummary(
                platform=platform,
                date=_parse_date(_cell(row, resolved["date"])),
                title=_truncate(title, 280),
                reach=reach,
                views=views,
                likes=likes,
                comments=comments,
                shares=shares,
                saves=saves,
                engagement_rate=engagement,
                retention_rate=retention,
            )
        )

    ranked = sorted(
        posts,
        key=lambda post: (post.engagement_rate, post.retention_rate or 0.0, post.reach),
        reverse=True,
    )

    return AnalysisPayload(
        posts_analyzed=len(posts),
        averages=_averages(posts),
        top_posts=ranked[:top_n],
        bottom_posts=list(reversed(ranked[-top_n:])),
    )


def _averages(posts: list[PostSummary]) -> PeriodAverages:
    count = len(posts)
    if count == 0:
        return PeriodAverages()

    retentions = [post.retention_rate for post in posts if post.retention_rate is not None]
    return PeriodAverages(
        engagement_rate=round(sum(post.engagement_rate for post in posts) / count, 2),
        retention_rate=(round(sum(retentions) / len(retentions), 2) if retentions else None),
        reach=round(sum(post.reach for post in posts) / count),
        views=round(sum(post.views for post in posts) / count),
    )


def _cell(row: pd.Series[Any], column: str | None) -> str:
    if not column:
        return ""
    value = row.get(column, "")
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null", "-", "n/a"}:
        return ""
    return text


def _to_int(row: pd.Series[Any], column: str | None) -> int:
    number = _parse_number(_cell(row, column))
    return int(round(number)) if number is not None else 0


def _parse_rate(raw: str) -> float | None:
    if not raw:
        return None
    number = _parse_number(raw)
    if number is None:
        return None
    if "%" in raw:
        return round(number, 2)
    if 0 < number <= 1:
        return round(number * 100, 2)
    return round(number, 2)


def _parse_number(raw: str) -> float | None:
    if not raw:
        return None

    cleaned = raw.replace("\u00a0", "").replace(" ", "").replace("%", "")
    negative = cleaned.startswith("-")
    cleaned = cleaned.lstrip("+-")

    if not cleaned:
        return None

    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        if re.fullmatch(r"\d{1,3}(,\d{3})+", cleaned):
            cleaned = cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", cleaned):
        cleaned = cleaned.replace(".", "")

    try:
        value = float(cleaned)
    except ValueError:
        return None
    return -value if negative else value


def _parse_date(raw: str) -> str | None:
    if not raw:
        return None
    if re.match(r"^\d{4}-\d{2}-\d{2}", raw):
        return raw[:10]
    parsed = pd.to_datetime(raw, errors="coerce", dayfirst=True)
    if pd.isna(parsed):
        return raw
    return str(parsed.date())


def _infer_platform(source_name: str) -> str:
    normalized = source_name.casefold()
    for platform in ("instagram", "facebook", "tiktok", "youtube", "linkedin", "twitter"):
        if platform in normalized:
            return "x" if platform == "twitter" else platform
    if re.search(r"(?<![a-z0-9])x(?![a-z0-9])", normalized):
        return "x"
    return "unknown"


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"
