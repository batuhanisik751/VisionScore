from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import models

from visionscore.analyzers.base import BaseAnalyzer
from visionscore.models import AestheticScore, ImageMeta
from visionscore.pipeline.loader import LoadedImage

# ImageNet normalization constants
_IMAGENET_MEAN = [0.485, 0.456, 0.406]
_IMAGENET_STD = [0.229, 0.224, 0.225]
_INPUT_SIZE = 224


class NIMAModel(nn.Module):
    """MobileNetV2 backbone with 10-class output for AVA score distribution."""

    def __init__(self) -> None:
        super().__init__()
        base_model = models.mobilenet_v2(weights=None)
        base_model.classifier = nn.Sequential(
            nn.Dropout(p=0.75),
            nn.Linear(1280, 10),
            nn.Softmax(dim=1),
        )
        self.base_model = base_model

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.base_model(x)


class AestheticAnalyzer(BaseAnalyzer):
    """Predict human aesthetic preference using NIMA (MobileNetV2 + AVA)."""

    def __init__(self, model_path: Path | None = None, device: str = "auto") -> None:
        self._model_path = model_path
        self._device = self._resolve_device(device)
        self._model: NIMAModel | None = None

    @staticmethod
    def _resolve_device(device: str) -> torch.device:
        if device != "auto":
            return torch.device(device)
        if torch.cuda.is_available():
            return torch.device("cuda")
        if torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")

    def _load_model(self) -> NIMAModel:
        if self._model is not None:
            return self._model

        if self._model_path is None or not self._model_path.is_file():
            raise FileNotFoundError(
                f"NIMA weights not found at {self._model_path}. "
                "Run: python scripts/download_models.py"
            )

        model = NIMAModel()
        state_dict = torch.load(self._model_path, map_location=self._device, weights_only=True)
        # Handle weights saved without the base_model. prefix wrapper
        if any(k.startswith("features.") or k.startswith("classifier.") for k in state_dict):
            state_dict = {f"base_model.{k}": v for k, v in state_dict.items()}
        model.load_state_dict(state_dict)
        model.to(self._device)
        model.eval()
        self._model = model
        return model

    def _preprocess(self, image: np.ndarray) -> torch.Tensor:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (_INPUT_SIZE, _INPUT_SIZE))
        tensor = torch.from_numpy(resized).float() / 255.0
        tensor = tensor.permute(2, 0, 1)  # HWC -> CHW
        for c in range(3):
            tensor[c] = (tensor[c] - _IMAGENET_MEAN[c]) / _IMAGENET_STD[c]
        return tensor.unsqueeze(0).to(self._device)

    @staticmethod
    def _distribution_to_score(distribution: torch.Tensor) -> tuple[float, float, float]:
        probs = distribution.squeeze().cpu().double()
        buckets = torch.arange(1, 11, dtype=torch.float64)
        mean = (probs * buckets).sum().item()
        std_dev = torch.sqrt((probs * (buckets - mean) ** 2).sum()).item()
        nima_score = (mean - 1) * (100.0 / 9.0)
        confidence = max(0.0, min(1.0, 1.0 - std_dev / 4.5))
        return nima_score, std_dev, confidence

    def analyze(self, image: LoadedImage, metadata: ImageMeta | None = None) -> AestheticScore:
        model = self._load_model()
        tensor = self._preprocess(image.resized)
        with torch.inference_mode():
            distribution = model(tensor)
        nima_score, std_dev, confidence = self._distribution_to_score(distribution)
        return AestheticScore(
            nima_score=round(nima_score, 1),
            std_dev=round(std_dev, 2),
            confidence=round(confidence, 2),
            overall=round(nima_score, 1),
        )
