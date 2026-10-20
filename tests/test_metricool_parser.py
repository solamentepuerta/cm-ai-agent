"""Unit tests for the deterministic Metricool parser."""

from pathlib import Path

import pytest

from src.utils.metricool_parser import (
    MetricoolParseError,
    parse_metricool_csv,
    parse_metricool_text,
    to_compact_json,
)

SPANISH_HEADER = (
    "Red social,Fecha de publicación,Publicación,Alcance,Visualizaciones,"
    "Me gusta,Comentarios,Compartidos,Guardados,Retención"
)

SPANISH_CSV = f"""Reporte Metricool; exportado 2026-10-19
{SPANISH_HEADER}
Instagram,18/10/2026,El gancho directo confrontativo,10000,12000,800,120,90,240,68%
Instagram,17/10/2026,Consejos para planificar tu lunes,9000,10000,90,10,5,12,35%
TikTok,16/10/2026,Tres errores al medir engagement,15000,18000,"1.200",150,300,"1.500",72%
"""

ENGLISH_CSV = """Platform,Date,Post,Reach,Views,Likes,Comments,Shares,Saves,Retention
Facebook,2026-10-15,Hook test A,5000,6000,"1,000",50,20,80,40%
Facebook,2026-10-14,Hook test B,4000,4500,100,5,2,3,10%
"""


def test_parse_spanish_headers_with_preamble() -> None:
    payload = parse_metricool_text(SPANISH_CSV, source_name="metricool_instagram_week42")
    assert payload.posts_analyzed == 3

    winner = payload.top_posts[0]
    assert winner.title == "Tres errores al medir engagement"
    assert winner.date == "2026-10-16"
    assert winner.engagement_rate == pytest.approx(21.0)
    assert winner.retention_rate == pytest.approx(72.0)

    second = payload.top_posts[1]
    assert second.title == "El gancho directo confrontativo"
    assert second.date == "2026-10-18"
    assert second.engagement_rate == pytest.approx(12.5)
    assert second.retention_rate == pytest.approx(68.0)

    assert payload.bottom_posts[0].title == "Consejos para planificar tu lunes"
    assert payload.averages.engagement_rate > 0


def test_parse_english_headers_and_thousands_separator() -> None:
    payload = parse_metricool_text(ENGLISH_CSV, source_name="export_facebook")
    assert payload.posts_analyzed == 2
    winner = payload.top_posts[0]
    assert winner.platform == "Facebook"
    assert winner.likes == 1000
    assert winner.reach == 5000


def test_platform_inferred_from_filename(tmp_path: Path) -> None:
    source = tmp_path / "metricool_tiktok_week42.csv"
    source.write_text(SPANISH_CSV, encoding="utf-8")
    payload = parse_metricool_csv(source)
    assert payload.posts_analyzed == 3


def test_interactions_column_is_treated_as_count() -> None:
    csv = "Fecha,Publicación,Alcance,Interacciones\n18/10/2026,Post con interacciones,1000,150\n"
    payload = parse_metricool_text(csv)
    assert payload.top_posts[0].engagement_rate == 15.0


def test_engagement_rate_column_is_used_when_no_counts() -> None:
    csv = 'Fecha,Publicación,Alcance,Tasa de engagement\n18/10/2026,Post con tasa,1000,"4,5%"\n'
    payload = parse_metricool_text(csv)
    assert payload.top_posts[0].engagement_rate == 4.5


def test_export_word_does_not_imply_x_platform() -> None:
    csv = "Fecha,Publicación,Alcance,Me gusta,Comentarios\n18/10/2026,Post sin red,1000,100,10\n"
    payload = parse_metricool_text(csv, source_name="export_week42")
    assert payload.top_posts[0].platform == "unknown"


def test_compact_json_has_no_whitespace() -> None:
    payload = parse_metricool_text(ENGLISH_CSV)
    compact = to_compact_json(payload)
    assert '": ' not in compact
    assert ', "' not in compact
    assert '"posts_analyzed":2' in compact


def test_invalid_csv_raises() -> None:
    with pytest.raises(MetricoolParseError):
        parse_metricool_text("foo,bar\n1,2\n")


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(MetricoolParseError):
        parse_metricool_csv(tmp_path / "missing.csv")


def test_versioned_sample_csv_parses() -> None:
    sample = Path(__file__).resolve().parents[1] / "data" / "metricool_sample_week42.csv"
    payload = parse_metricool_csv(sample)

    assert payload.posts_analyzed == 3
    assert payload.top_posts[0].title == "Tres errores al medir engagement"
    assert payload.top_posts[0].engagement_rate == 21.0
    assert payload.top_posts[0].retention_rate == 72.0
