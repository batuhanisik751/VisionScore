from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel

from visionscore.models import ImageMeta
from visionscore.pipeline.loader import LoadedImage
from visionscore.plugins.info import PluginInfo


class BaseAnalyzer(ABC):
    """Abstract base for all VisionScore analyzers."""

    plugin_info: ClassVar[PluginInfo | None] = None

    @abstractmethod
    def analyze(self, image: LoadedImage, metadata: ImageMeta | None = None) -> BaseModel: ...
