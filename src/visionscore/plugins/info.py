from __future__ import annotations

from pydantic import BaseModel


class PluginInfo(BaseModel):
    """Metadata for a VisionScore analyzer plugin."""

    name: str
    display_name: str
    version: str = "0.1.0"
    description: str = ""
    score_weight: float = 0.0
    score_field: str = "overall"
