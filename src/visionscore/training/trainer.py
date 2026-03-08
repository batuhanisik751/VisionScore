from __future__ import annotations

import csv
import random
import time
from pathlib import Path

import torch
import torch.nn as nn
from PIL import Image
from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

from visionscore.analyzers.aesthetic import NIMAModel

# ImageNet normalization (must match inference preprocessing)
_IMAGENET_MEAN = [0.485, 0.456, 0.406]
_IMAGENET_STD = [0.229, 0.224, 0.225]


# ---------------------------------------------------------------------------
# Loss function
# ---------------------------------------------------------------------------


def emd_loss(predicted: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Earth Mover's Distance loss for probability distributions.

    Computes the squared difference between cumulative distribution functions.
    Standard loss for NIMA aesthetic score training.
    """
    cdf_pred = torch.cumsum(predicted.float(), dim=-1)
    cdf_target = torch.cumsum(target.float(), dim=-1)
    return torch.mean((cdf_pred - cdf_target) ** 2)


# ---------------------------------------------------------------------------
# Score distribution
# ---------------------------------------------------------------------------


def _score_to_distribution(score: float, sigma: float = 1.5) -> torch.Tensor:
    """Convert a scalar rating (1-10) to a 10-bin soft target distribution."""
    buckets = torch.arange(1, 11, dtype=torch.float32)
    weights = torch.exp(-((buckets - score) ** 2) / (2 * sigma**2))
    return weights / weights.sum()


# ---------------------------------------------------------------------------
# CSV loader
# ---------------------------------------------------------------------------

_HEADER_NAMES = {"filename", "file", "image", "name", "path"}


def load_ratings(
    csv_path: Path, image_dir: Path, scale: str = "ava"
) -> list[tuple[str, float]]:
    """Load image ratings from a CSV file.

    Args:
        csv_path: Path to CSV with ``filename,score`` columns.
        image_dir: Directory containing the referenced images.
        scale: ``"ava"`` for 1-10 scores, ``"visionscore"`` for 0-100.

    Returns:
        List of ``(filename, ava_score)`` tuples.

    Raises:
        ValueError: On invalid scores or missing image files.
    """
    ratings: list[tuple[str, float]] = []

    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        for row_num, row in enumerate(reader, 1):
            if len(row) < 2:
                continue

            filename = row[0].strip()
            score_str = row[1].strip()

            # Skip header row
            if row_num == 1 and filename.lower() in _HEADER_NAMES:
                continue

            try:
                score = float(score_str)
            except ValueError:
                raise ValueError(
                    f"Row {row_num}: invalid score '{score_str}' for '{filename}'"
                )

            # Convert scale
            if scale == "visionscore":
                if not 0 <= score <= 100:
                    raise ValueError(
                        f"Row {row_num}: score {score} out of range 0-100 "
                        f"for visionscore scale"
                    )
                score = score * 9.0 / 100.0 + 1.0
            else:
                if not 1 <= score <= 10:
                    raise ValueError(
                        f"Row {row_num}: score {score} out of range 1-10 for AVA scale"
                    )

            # Verify image exists
            if not (image_dir / filename).is_file():
                raise ValueError(
                    f"Row {row_num}: image '{filename}' not found in {image_dir}"
                )

            ratings.append((filename, score))

    if not ratings:
        raise ValueError(f"No valid ratings found in {csv_path}")

    return ratings


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------


class NIMARatingDataset(Dataset):
    """PyTorch dataset for NIMA fine-tuning from user-rated images."""

    def __init__(
        self,
        image_dir: Path,
        ratings: list[tuple[str, float]],
        augment: bool = True,
    ) -> None:
        self.image_dir = image_dir
        self.ratings = ratings

        if augment:
            self.transform = transforms.Compose([
                transforms.Resize(256),
                transforms.RandomCrop(224),
                transforms.RandomHorizontalFlip(),
                transforms.RandomRotation(10),
                transforms.ColorJitter(
                    brightness=0.2, contrast=0.2, saturation=0.2, hue=0.05
                ),
                transforms.ToTensor(),
                transforms.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
            ])
        else:
            self.transform = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
            ])

    def __len__(self) -> int:
        return len(self.ratings)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        filename, score = self.ratings[idx]
        img = Image.open(self.image_dir / filename).convert("RGB")
        tensor = self.transform(img)
        target = _score_to_distribution(score)
        return tensor, target


# ---------------------------------------------------------------------------
# Config / Result models
# ---------------------------------------------------------------------------


class TrainingConfig(BaseModel):
    """Configuration for NIMA fine-tuning."""

    image_dir: Path
    csv_path: Path
    output_path: Path = Field(
        default_factory=lambda: Path.home() / ".visionscore" / "models" / "nima_finetuned.pth"
    )
    base_weights: Path | None = None
    epochs: int = 20
    batch_size: int = 16
    learning_rate: float = 1e-4
    val_split: float = 0.2
    full_finetune: bool = False
    augment: bool = True
    scale: str = "ava"
    device: str = "auto"
    seed: int = 42


class TrainingResult(BaseModel):
    """Result summary from a training run."""

    output_path: str
    epochs_trained: int
    best_epoch: int
    best_val_loss: float
    final_train_loss: float
    final_val_loss: float
    training_time_seconds: float
    total_images: int
    train_images: int
    val_images: int
    device: str


# ---------------------------------------------------------------------------
# Trainer
# ---------------------------------------------------------------------------


class NIMAAestheticTrainer:
    """Fine-tune the NIMA aesthetic model on a user-provided rated dataset."""

    def __init__(
        self, config: TrainingConfig, console: Console | None = None
    ) -> None:
        self.config = config
        self.console = console or Console()
        self._device = self._resolve_device(config.device)

    @staticmethod
    def _resolve_device(device: str) -> torch.device:
        if device != "auto":
            return torch.device(device)
        if torch.cuda.is_available():
            return torch.device("cuda")
        if torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")

    def _prepare_model(self) -> NIMAModel:
        model = NIMAModel()

        # Load base weights if available
        if self.config.base_weights and self.config.base_weights.is_file():
            state_dict = torch.load(
                self.config.base_weights,
                map_location=self._device,
                weights_only=True,
            )
            # Handle weights saved without base_model. prefix
            if any(
                k.startswith("features.") or k.startswith("classifier.")
                for k in state_dict
            ):
                state_dict = {f"base_model.{k}": v for k, v in state_dict.items()}
            model.load_state_dict(state_dict)

        # Freeze backbone unless full fine-tuning
        if not self.config.full_finetune:
            for param in model.base_model.features.parameters():
                param.requires_grad = False

        model.to(self._device)
        return model

    def _split_data(
        self, ratings: list[tuple[str, float]]
    ) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
        """Deterministic train/val split."""
        data = list(ratings)
        rng = random.Random(self.config.seed)
        rng.shuffle(data)
        split_idx = max(1, int(len(data) * (1 - self.config.val_split)))
        return data[:split_idx], data[split_idx:]

    def _run_epoch(
        self,
        model: nn.Module,
        loader: DataLoader,
        optimizer: torch.optim.Optimizer | None = None,
        train: bool = True,
    ) -> float:
        """Run one training or validation epoch. Returns average loss."""
        if train:
            model.train()
        else:
            model.eval()

        total_loss = 0.0
        count = 0

        context = torch.enable_grad() if train else torch.no_grad()
        with context:
            for images, targets in loader:
                images = images.to(self._device)
                targets = targets.to(self._device)

                predictions = model(images)
                loss = emd_loss(predictions, targets)

                if train and optimizer is not None:
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()

                total_loss += loss.item() * images.size(0)
                count += images.size(0)

        return total_loss / count if count > 0 else 0.0

    def _save_checkpoint(self, model: NIMAModel, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), path)

    def train(self) -> TrainingResult:
        """Run the full training pipeline."""
        start = time.perf_counter()

        # Load and split data
        ratings = load_ratings(
            self.config.csv_path, self.config.image_dir, self.config.scale
        )
        train_data, val_data = self._split_data(ratings)

        self.console.print(
            f"[bold]Training NIMA[/bold] | "
            f"{len(train_data)} train, {len(val_data)} val | "
            f"Device: {self._device}"
        )

        # Build datasets and loaders
        train_ds = NIMARatingDataset(
            self.config.image_dir, train_data, augment=self.config.augment
        )
        val_ds = NIMARatingDataset(
            self.config.image_dir, val_data, augment=False
        )
        pin = self._device.type == "cuda"
        train_loader = DataLoader(
            train_ds, batch_size=self.config.batch_size, shuffle=True,
            num_workers=0, pin_memory=pin,
        )
        val_loader = DataLoader(
            val_ds, batch_size=self.config.batch_size, shuffle=False,
            num_workers=0, pin_memory=pin,
        )

        # Prepare model and optimizer
        model = self._prepare_model()
        trainable = [p for p in model.parameters() if p.requires_grad]
        optimizer = torch.optim.Adam(trainable, lr=self.config.learning_rate)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, patience=3, factor=0.5
        )

        best_val_loss = float("inf")
        best_epoch = 0
        final_train_loss = 0.0
        final_val_loss = 0.0

        # Training loop
        table = Table(title="Training Progress")
        table.add_column("Epoch", justify="right", style="dim")
        table.add_column("Train Loss", justify="right")
        table.add_column("Val Loss", justify="right")
        table.add_column("LR", justify="right", style="dim")
        table.add_column("", style="green")

        for epoch in range(1, self.config.epochs + 1):
            train_loss = self._run_epoch(model, train_loader, optimizer, train=True)
            val_loss = self._run_epoch(model, val_loader, train=False)
            scheduler.step(val_loss)

            marker = ""
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_epoch = epoch
                self._save_checkpoint(model, self.config.output_path)
                marker = "best"

            lr = optimizer.param_groups[0]["lr"]
            table.add_row(
                str(epoch),
                f"{train_loss:.6f}",
                f"{val_loss:.6f}",
                f"{lr:.2e}",
                marker,
            )

            final_train_loss = train_loss
            final_val_loss = val_loss

        self.console.print(table)

        # Save final model alongside best
        final_path = self.config.output_path.with_stem(
            self.config.output_path.stem + "_final"
        )
        self._save_checkpoint(model, final_path)

        elapsed = round(time.perf_counter() - start, 2)

        result = TrainingResult(
            output_path=str(self.config.output_path),
            epochs_trained=self.config.epochs,
            best_epoch=best_epoch,
            best_val_loss=round(best_val_loss, 6),
            final_train_loss=round(final_train_loss, 6),
            final_val_loss=round(final_val_loss, 6),
            training_time_seconds=elapsed,
            total_images=len(ratings),
            train_images=len(train_data),
            val_images=len(val_data),
            device=str(self._device),
        )

        # Summary
        self.console.print()
        summary = Table(title="Training Complete")
        summary.add_column("Metric", style="cyan")
        summary.add_column("Value", style="white")
        summary.add_row("Best Epoch", str(result.best_epoch))
        summary.add_row("Best Val Loss", f"{result.best_val_loss:.6f}")
        summary.add_row("Final Train Loss", f"{result.final_train_loss:.6f}")
        summary.add_row("Final Val Loss", f"{result.final_val_loss:.6f}")
        summary.add_row("Time", f"{result.training_time_seconds:.1f}s")
        summary.add_row("Saved To", result.output_path)
        self.console.print(summary)

        return result
