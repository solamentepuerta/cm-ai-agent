"""Shared schemas and format definitions for the deterministic toolkit."""

from typing import Literal

from pydantic import BaseModel, Field

PostFormat = Literal["video_corto", "carrusel", "hilo_x", "video_largo", "story"]

FORMAT_LABELS: dict[str, str] = {
    "video_corto": "Video Corto (Reel / TikTok / Shorts)",
    "carrusel": "Carrusel (Instagram / LinkedIn)",
    "hilo_x": "Hilo de X (Twitter)",
    "video_largo": "Video Largo (YouTube)",
    "story": "Story",
}


class BrandProfile(BaseModel):
    """Structured brand profile accepted by the renderer."""

    identity: str = Field(description="Quién es la marca y a quién le habla")
    target_audience: str = Field(description="Público objetivo en una frase")
    tone_attributes: list[str] = Field(description="Atributos de voz y ritmo")
    blacklist: list[str] = Field(description="Palabras y frases prohibidas")
    format_rules: dict[str, list[str]] = Field(
        description="Reglas por formato: video_corto, carrusel, hilo_x, video_largo, story"
    )
    style_examples: list[str] = Field(
        default_factory=list,
        description="Patrones observados en los posts de ejemplo",
    )
