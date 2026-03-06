from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel

from visionscore.models import ImageMeta
from visionscore.pipeline.loader import LoadedImage


class BaseAnalyzer(ABC):
    """Abstract base for all VisionScore analyzers."""

    @abstractmethod
    def analyze(self, image: LoadedImage, metadata: ImageMeta | None = None) -> BaseModel:
        ...
