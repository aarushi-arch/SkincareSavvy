"""Utility to split dataset folders into train/test/validation."""
from __future__ import annotations

import random
import shutil
from pathlib import Path
from typing import Tuple


class DatasetSplitter:
    """Split dataset folders into train, validation, and test sets."""

    def __init__(
        self,
        source_dir: Path | str,
        output_dir: Path | str | None = None,
        train_ratio: float = 0.7,
        val_ratio: float = 0.15,
        test_ratio: float = 0.15,
        seed: int = 42,
    ):
        """
        Initialize the dataset splitter.

        Args:
            source_dir: Source directory containing class folders
            output_dir: Output directory (if None, reorganizes in place)
            train_ratio: Ratio for training set (default: 0.7)
            val_ratio: Ratio for validation set (default: 0.15)
            test_ratio: Ratio for test set (default: 0.15)
            seed: Random seed for reproducibility
        """
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir) if output_dir else self.source_dir
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.seed = seed

        # Validate ratios
        total = train_ratio + val_ratio + test_ratio
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Ratios must sum to 1.0, got {total}")

        random.seed(seed)

    def get_image_files(self, directory: Path) -> list[Path]:
        """Get all image files from a directory."""
        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff"}
        image_files = []
        for ext in image_extensions:
            image_files.extend(directory.glob(f"*{ext}"))
            image_files.extend(directory.glob(f"*{ext.upper()}"))
        return sorted(image_files)

    def split_class_folder(
        self,
        class_folder: Path,
        class_name: str,
        output_base: Path,
    ) -> Tuple[int, int, int]:
        """
        Split a single class folder into train/val/test.

        Args:
            class_folder: Path to the class folder
            class_name: Name of the class
            output_base: Base output directory

        Returns:
            Tuple of (train_count, val_count, test_count)
        """
        # Get all image files
        image_files = self.get_image_files(class_folder)
        total_images = len(image_files)

        if total_images == 0:
            print(f"Warning: No images found in {class_folder}")
            return 0, 0, 0

        # Shuffle images
        random.shuffle(image_files)

        # Calculate split indices
        train_end = int(total_images * self.train_ratio)
        val_end = train_end + int(total_images * self.val_ratio)

        # Split files
        train_files = image_files[:train_end]
        val_files = image_files[train_end:val_end]
        test_files = image_files[val_end:]

        # Create output directories
        train_dir = output_base / "train" / class_name
        val_dir = output_base / "validation" / class_name
        test_dir = output_base / "test" / class_name

        train_dir.mkdir(parents=True, exist_ok=True)
        val_dir.mkdir(parents=True, exist_ok=True)
        test_dir.mkdir(parents=True, exist_ok=True)

        # Copy files
        for file in train_files:
            shutil.copy2(file, train_dir / file.name)

        for file in val_files:
            shutil.copy2(file, val_dir / file.name)

        for file in test_files:
            shutil.copy2(file, test_dir / file.name)

        return len(train_files), len(val_files), len(test_files)

    def reorganize_dataset(self, keep_original: bool = False) -> dict:
        """
        Reorganize dataset from class-based structure to train/val/test structure.

        Args:
            keep_original: Whether to keep original class folders

        Returns:
            Dictionary with split statistics
        """
        if not self.source_dir.exists():
            raise ValueError(f"Source directory does not exist: {self.source_dir}")

        # Get all class folders (directories in source_dir)
        class_folders = [d for d in self.source_dir.iterdir() if d.is_dir()]

        if not class_folders:
            raise ValueError(f"No class folders found in {self.source_dir}")

        # Filter out train/validation/test if they exist
        class_folders = [
            d for d in class_folders
            if d.name not in ["train", "validation", "test", "val"]
        ]

        if not class_folders:
            raise ValueError("No class folders found (excluding train/validation/test)")

        print(f"Found {len(class_folders)} class folders:")
        for cf in class_folders:
            print(f"  - {cf.name}")

        # Create output structure
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "train").mkdir(exist_ok=True)
        (self.output_dir / "validation").mkdir(exist_ok=True)
        (self.output_dir / "test").mkdir(exist_ok=True)

        # Split each class
        statistics = {
            "classes": {},
            "total": {"train": 0, "validation": 0, "test": 0},
        }

        for class_folder in class_folders:
            class_name = class_folder.name
            print(f"\nSplitting {class_name}...")

            train_count, val_count, test_count = self.split_class_folder(
                class_folder,
                class_name,
                self.output_dir,
            )

            statistics["classes"][class_name] = {
                "train": train_count,
                "validation": val_count,
                "test": test_count,
                "total": train_count + val_count + test_count,
            }

            statistics["total"]["train"] += train_count
            statistics["total"]["validation"] += val_count
            statistics["total"]["test"] += test_count

            print(f"  Train: {train_count}, Validation: {val_count}, Test: {test_count}")

        # Remove original class folders if not keeping them
        if not keep_original:
            print("\nRemoving original class folders...")
            for class_folder in class_folders:
                shutil.rmtree(class_folder)
                print(f"  Removed {class_folder}")

        print("\n" + "=" * 50)
        print("Split Summary:")
        print(f"Total Train: {statistics['total']['train']}")
        print(f"Total Validation: {statistics['total']['validation']}")
        print(f"Total Test: {statistics['total']['test']}")
        print(f"Grand Total: {sum(statistics['total'].values())}")
        print("=" * 50)

        return statistics

