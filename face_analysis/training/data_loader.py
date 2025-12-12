"""Data loading utilities for CNN training."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Generator, Tuple

import numpy as np
from PIL import Image
from tensorflow import keras


class SkinDatasetLoader:
    """Loader for skin type and skin concern datasets."""

    def __init__(
        self,
        dataset_path: Path | str,
        image_size: Tuple[int, int] = (224, 224),
        batch_size: int = 32,
        validation_split: float = 0.2,
        test_split: float = 0.1,
    ):
        """
        Initialize the dataset loader.

        Args:
            dataset_path: Path to the dataset directory
            image_size: Target image size (height, width)
            batch_size: Batch size for training
            validation_split: Fraction of data to use for validation
            test_split: Fraction of data to use for testing
        """
        self.dataset_path = Path(dataset_path)
        self.image_size = image_size
        self.batch_size = batch_size
        self.validation_split = validation_split
        self.test_split = test_split
        self.class_names = []
        self.num_classes = 0

    def get_class_names(self) -> list[str]:
        """Get class names from dataset directory structure."""
        train_path = self.dataset_path / "train"
        if not train_path.exists():
            raise ValueError(f"Train directory not found at {train_path}")

        class_names = sorted([d.name for d in train_path.iterdir() if d.is_dir()])
        self.class_names = class_names
        self.num_classes = len(class_names)
        return class_names

    def create_data_generators(
        self,
        augment: bool = True,
    ) -> Tuple[keras.utils.Sequence, keras.utils.Sequence, keras.utils.Sequence]:
        """
        Create data generators for train, validation, and test sets.

        Args:
            augment: Whether to apply data augmentation to training set

        Returns:
            Tuple of (train_gen, val_gen, test_gen)
        """
        train_path = self.dataset_path / "train"
        val_path = self.dataset_path / "validation"
        test_path = self.dataset_path / "test"

        # Data augmentation for training
        train_datagen = keras.preprocessing.image.ImageDataGenerator(
            rescale=1.0 / 255.0,
            rotation_range=20,
            width_shift_range=0.2,
            height_shift_range=0.2,
            horizontal_flip=True,
            zoom_range=0.2,
            fill_mode="nearest",
        ) if augment else keras.preprocessing.image.ImageDataGenerator(
            rescale=1.0 / 255.0
        )

        # No augmentation for validation and test
        val_test_datagen = keras.preprocessing.image.ImageDataGenerator(
            rescale=1.0 / 255.0
        )

        # Create generators
        train_gen = train_datagen.flow_from_directory(
            train_path,
            target_size=self.image_size,
            batch_size=self.batch_size,
            class_mode="categorical",
            shuffle=True,
        )

        val_gen = val_test_datagen.flow_from_directory(
            val_path,
            target_size=self.image_size,
            batch_size=self.batch_size,
            class_mode="categorical",
            shuffle=False,
        )

        test_gen = val_test_datagen.flow_from_directory(
            test_path,
            target_size=self.image_size,
            batch_size=self.batch_size,
            class_mode="categorical",
            shuffle=False,
        )

        # Update class names from generator
        self.class_names = list(train_gen.class_indices.keys())
        self.num_classes = len(self.class_names)

        return train_gen, val_gen, test_gen

    def get_dataset_info(self) -> dict:
        """Get information about the dataset."""
        train_path = self.dataset_path / "train"
        val_path = self.dataset_path / "validation"
        test_path = self.dataset_path / "test"

        info = {
            "classes": self.get_class_names(),
            "num_classes": len(self.get_class_names()),
            "train_samples": 0,
            "val_samples": 0,
            "test_samples": 0,
            "class_distribution": {},
        }

        # Count samples per class
        for class_name in info["classes"]:
            train_class_path = train_path / class_name
            val_class_path = val_path / class_name
            test_class_path = test_path / class_name

            train_count = len(list(train_class_path.glob("*"))) if train_class_path.exists() else 0
            val_count = len(list(val_class_path.glob("*"))) if val_class_path.exists() else 0
            test_count = len(list(test_class_path.glob("*"))) if test_class_path.exists() else 0

            info["class_distribution"][class_name] = {
                "train": train_count,
                "validation": val_count,
                "test": test_count,
            }
            info["train_samples"] += train_count
            info["val_samples"] += val_count
            info["test_samples"] += test_count

        return info

