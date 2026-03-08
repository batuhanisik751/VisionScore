from __future__ import annotations

from pathlib import Path

import pytest
import torch
from PIL import Image

from visionscore.analyzers.aesthetic import NIMAModel
from visionscore.training.trainer import (
    NIMAAestheticTrainer,
    NIMARatingDataset,
    TrainingConfig,
    _score_to_distribution,
    emd_loss,
    load_ratings,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tiny_dataset(tmp_path: Path) -> tuple[Path, Path]:
    """Create 5 synthetic 64x64 JPEG images and a ratings CSV."""
    image_dir = tmp_path / "images"
    image_dir.mkdir()

    scores = [2.0, 4.0, 6.0, 8.0, 9.0]
    lines: list[str] = []
    for i, score in enumerate(scores):
        img = Image.new("RGB", (64, 64), (i * 50, 100, 200 - i * 30))
        name = f"img_{i}.jpg"
        img.save(image_dir / name, "JPEG")
        lines.append(f"{name},{score}")

    csv_path = tmp_path / "ratings.csv"
    csv_path.write_text("\n".join(lines) + "\n")

    return image_dir, csv_path


@pytest.fixture()
def training_config(
    tiny_dataset: tuple[Path, Path], tmp_path: Path
) -> TrainingConfig:
    image_dir, csv_path = tiny_dataset
    return TrainingConfig(
        image_dir=image_dir,
        csv_path=csv_path,
        output_path=tmp_path / "output" / "nima_finetuned.pth",
        base_weights=None,
        epochs=2,
        batch_size=2,
        learning_rate=1e-3,
        val_split=0.2,
        full_finetune=False,
        augment=False,
        scale="ava",
        device="cpu",
        seed=42,
    )


# ---------------------------------------------------------------------------
# TestEMDLoss
# ---------------------------------------------------------------------------


class TestEMDLoss:
    def test_identical_distributions_zero_loss(self) -> None:
        dist = torch.softmax(torch.randn(2, 10), dim=-1)
        loss = emd_loss(dist, dist)
        assert loss.item() < 1e-6

    def test_distant_distributions_high_loss(self) -> None:
        a = torch.zeros(1, 10)
        a[0, 0] = 1.0  # peaked at bucket 1
        b = torch.zeros(1, 10)
        b[0, 9] = 1.0  # peaked at bucket 10
        loss = emd_loss(a, b)
        assert loss.item() > 0.5

    def test_loss_is_differentiable(self) -> None:
        pred = torch.softmax(torch.randn(2, 10, requires_grad=True), dim=-1)
        target = torch.softmax(torch.randn(2, 10), dim=-1)
        loss = emd_loss(pred, target)
        loss.backward()  # should not raise

    def test_loss_symmetric(self) -> None:
        a = torch.softmax(torch.randn(2, 10), dim=-1)
        b = torch.softmax(torch.randn(2, 10), dim=-1)
        assert abs(emd_loss(a, b).item() - emd_loss(b, a).item()) < 1e-6


# ---------------------------------------------------------------------------
# TestScoreToDistribution
# ---------------------------------------------------------------------------


class TestScoreToDistribution:
    def test_distribution_shape(self) -> None:
        dist = _score_to_distribution(5.0)
        assert dist.shape == (10,)

    def test_distribution_sums_to_one(self) -> None:
        dist = _score_to_distribution(7.0)
        assert abs(dist.sum().item() - 1.0) < 1e-5

    def test_distribution_peaks_at_correct_bucket(self) -> None:
        dist = _score_to_distribution(7.0)
        # score=7.0 → bucket index 6 (buckets 1-10, 0-indexed)
        assert dist.argmax().item() == 6


# ---------------------------------------------------------------------------
# TestLoadRatings
# ---------------------------------------------------------------------------


class TestLoadRatings:
    def test_valid_csv(self, tiny_dataset: tuple[Path, Path]) -> None:
        image_dir, csv_path = tiny_dataset
        ratings = load_ratings(csv_path, image_dir, scale="ava")
        assert len(ratings) == 5
        for filename, score in ratings:
            assert 1 <= score <= 10
            assert (image_dir / filename).is_file()

    def test_auto_detect_header(self, tiny_dataset: tuple[Path, Path]) -> None:
        image_dir, csv_path = tiny_dataset
        # Create CSV with header
        original = csv_path.read_text()
        csv_with_header = csv_path.parent / "with_header.csv"
        csv_with_header.write_text("filename,score\n" + original)
        ratings = load_ratings(csv_with_header, image_dir, scale="ava")
        assert len(ratings) == 5

    def test_visionscore_scale_conversion(
        self, tiny_dataset: tuple[Path, Path]
    ) -> None:
        image_dir, csv_path = tiny_dataset
        # Write a CSV with visionscore scale (0-100)
        vs_csv = csv_path.parent / "vs_ratings.csv"
        vs_csv.write_text("img_0.jpg,55.5\n")
        ratings = load_ratings(vs_csv, image_dir, scale="visionscore")
        assert len(ratings) == 1
        # 55.5 * 9/100 + 1 = 5.995
        assert abs(ratings[0][1] - 5.995) < 1e-3

    def test_invalid_score_raises(self, tiny_dataset: tuple[Path, Path]) -> None:
        image_dir, csv_path = tiny_dataset
        bad_csv = csv_path.parent / "bad.csv"
        bad_csv.write_text("img_0.jpg,15.0\n")  # out of 1-10 range
        with pytest.raises(ValueError, match="out of range"):
            load_ratings(bad_csv, image_dir, scale="ava")


# ---------------------------------------------------------------------------
# TestNIMARatingDataset
# ---------------------------------------------------------------------------


class TestNIMARatingDataset:
    def test_dataset_length(self, tiny_dataset: tuple[Path, Path]) -> None:
        image_dir, csv_path = tiny_dataset
        ratings = load_ratings(csv_path, image_dir)
        ds = NIMARatingDataset(image_dir, ratings, augment=False)
        assert len(ds) == 5

    def test_getitem_shape(self, tiny_dataset: tuple[Path, Path]) -> None:
        image_dir, csv_path = tiny_dataset
        ratings = load_ratings(csv_path, image_dir)
        ds = NIMARatingDataset(image_dir, ratings, augment=False)
        img_tensor, target = ds[0]
        assert img_tensor.shape == (3, 224, 224)
        assert target.shape == (10,)

    def test_target_distribution_sums_to_one(
        self, tiny_dataset: tuple[Path, Path]
    ) -> None:
        image_dir, csv_path = tiny_dataset
        ratings = load_ratings(csv_path, image_dir)
        ds = NIMARatingDataset(image_dir, ratings, augment=False)
        _, target = ds[0]
        assert abs(target.sum().item() - 1.0) < 1e-5

    def test_target_peaks_at_correct_bucket(
        self, tiny_dataset: tuple[Path, Path]
    ) -> None:
        image_dir, csv_path = tiny_dataset
        ratings = load_ratings(csv_path, image_dir)
        ds = NIMARatingDataset(image_dir, ratings, augment=False)
        # First image has score 2.0 → bucket index 1
        _, target = ds[0]
        assert target.argmax().item() == 1

    def test_augmentation_disabled_deterministic(
        self, tiny_dataset: tuple[Path, Path]
    ) -> None:
        image_dir, csv_path = tiny_dataset
        ratings = load_ratings(csv_path, image_dir)
        ds = NIMARatingDataset(image_dir, ratings, augment=False)
        img1, _ = ds[0]
        img2, _ = ds[0]
        assert torch.allclose(img1, img2)


# ---------------------------------------------------------------------------
# TestNIMAAestheticTrainer
# ---------------------------------------------------------------------------


class TestNIMAAestheticTrainer:
    def test_train_one_epoch(self, tmp_path: Path, tiny_dataset: tuple[Path, Path]) -> None:
        image_dir, csv_path = tiny_dataset
        config = TrainingConfig(
            image_dir=image_dir,
            csv_path=csv_path,
            output_path=tmp_path / "out" / "model.pth",
            base_weights=None,
            epochs=1,
            batch_size=2,
            learning_rate=1e-3,
            val_split=0.2,
            full_finetune=False,
            augment=False,
            scale="ava",
            device="cpu",
            seed=42,
        )
        trainer = NIMAAestheticTrainer(config)
        result = trainer.train()
        assert result.epochs_trained == 1
        assert result.best_epoch >= 1
        assert result.best_val_loss >= 0
        assert result.total_images == 5

    def test_freeze_backbone(self, training_config: TrainingConfig) -> None:
        training_config.full_finetune = False
        trainer = NIMAAestheticTrainer(training_config)
        model = trainer._prepare_model()
        for p in model.base_model.features.parameters():
            assert not p.requires_grad
        for p in model.base_model.classifier.parameters():
            assert p.requires_grad

    def test_full_finetune_unfreezes(self, training_config: TrainingConfig) -> None:
        training_config.full_finetune = True
        trainer = NIMAAestheticTrainer(training_config)
        model = trainer._prepare_model()
        for p in model.parameters():
            assert p.requires_grad

    def test_checkpoint_saved(
        self, training_config: TrainingConfig
    ) -> None:
        trainer = NIMAAestheticTrainer(training_config)
        trainer.train()
        assert training_config.output_path.is_file()

    def test_finetuned_weights_loadable(
        self, training_config: TrainingConfig
    ) -> None:
        trainer = NIMAAestheticTrainer(training_config)
        trainer.train()

        # Load saved weights into a fresh NIMAModel
        model = NIMAModel()
        state_dict = torch.load(
            training_config.output_path, map_location="cpu", weights_only=True
        )
        model.load_state_dict(state_dict)
        model.eval()

        # Run a forward pass to ensure it works
        x = torch.randn(1, 3, 224, 224)
        with torch.inference_mode():
            out = model(x)
        assert out.shape == (1, 10)
        assert abs(out.sum().item() - 1.0) < 1e-4
