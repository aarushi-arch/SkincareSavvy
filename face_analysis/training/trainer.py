"""Training script for CNN models."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import numpy as np
from tensorflow import keras

from face_analysis.training.data_loader import SkinDatasetLoader
from face_analysis.training.model_builder import build_skin_analysis_cnn


class CNNTrainer:
    """Trainer class for CNN models."""

    def __init__(
        self,
        dataset_path: Path | str,
        model_type: str = "skin_types",  # or "skin_concerns"
        output_dir: Path | str = "models",
        image_size: tuple[int, int] = (224, 224),
        batch_size: int = 32,
        base_model: str = "mobilenet",
        epochs: int = 50,
        learning_rate: float = 0.001,
        dropout_rate: float = 0.5,
    ):
        """
        Initialize the trainer.

        Args:
            dataset_path: Path to dataset directory
            model_type: Type of model ('skin_types' or 'skin_concerns')
            output_dir: Directory to save trained models
            image_size: Image size for training
            batch_size: Batch size
            base_model: Base model architecture
            epochs: Number of training epochs
            learning_rate: Learning rate
            dropout_rate: Dropout rate
        """
        self.dataset_path = Path(dataset_path)
        self.model_type = model_type
        self.output_dir = Path(output_dir)
        self.image_size = image_size
        self.batch_size = batch_size
        self.base_model = base_model
        self.epochs = epochs
        self.learning_rate = learning_rate
        self.dropout_rate = dropout_rate

        self.loader = SkinDatasetLoader(
            dataset_path=self.dataset_path,
            image_size=self.image_size,
            batch_size=self.batch_size,
        )

        self.model: Optional[keras.Model] = None
        self.history: Optional[dict] = None

    def prepare_data(self):
        """Prepare data generators."""
        print(f"Loading dataset from {self.dataset_path}")
        dataset_info = self.loader.get_dataset_info()
        print(f"Dataset info: {json.dumps(dataset_info, indent=2)}")
        return self.loader.create_data_generators(augment=True)

    def build_model(self):
        """Build the CNN model."""
        dataset_info = self.loader.get_dataset_info()
        num_classes = dataset_info["num_classes"]

        print(f"Building {self.base_model} model for {num_classes} classes...")
        self.model = build_skin_analysis_cnn(
            num_classes=num_classes,
            input_shape=(*self.image_size, 3),
            base_model=self.base_model,
            dropout_rate=self.dropout_rate,
            learning_rate=self.learning_rate,
        )

        print("Model architecture:")
        self.model.summary()

        return self.model

    def train(
        self,
        train_gen: keras.utils.Sequence,
        val_gen: keras.utils.Sequence,
        callbacks: Optional[list] = None,
    ):
        """Train the model."""
        if self.model is None:
            raise ValueError("Model not built. Call build_model() first.")

        # Default callbacks
        if callbacks is None:
            callbacks = []

        # Add standard callbacks
        self.output_dir.mkdir(parents=True, exist_ok=True)
        model_save_path = self.output_dir / f"{self.model_type}_best_model.keras"

        callbacks.extend([
            keras.callbacks.ModelCheckpoint(
                str(model_save_path),
                monitor="val_accuracy",
                save_best_only=True,
                verbose=1,
            ),
            keras.callbacks.EarlyStopping(
                monitor="val_accuracy",
                patience=10,
                restore_best_weights=True,
                verbose=1,
            ),
            keras.callbacks.ReduceLROnPlateau(
                monitor="val_loss",
                factor=0.5,
                patience=5,
                min_lr=1e-7,
                verbose=1,
            ),
            keras.callbacks.CSVLogger(
                str(self.output_dir / f"{self.model_type}_training_log.csv"),
            ),
        ])

        print(f"Starting training for {self.epochs} epochs...")
        self.history = self.model.fit(
            train_gen,
            epochs=self.epochs,
            validation_data=val_gen,
            callbacks=callbacks,
            verbose=1,
        )

        return self.history

    def evaluate(self, test_gen: keras.utils.Sequence):
        """Evaluate the model on test set."""
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        print("Evaluating on test set...")
        results = self.model.evaluate(test_gen, verbose=1)
        return results

    def save_model(self, filename: Optional[str] = None):
        """Save the trained model."""
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        if filename is None:
            filename = f"{self.model_type}_final_model.keras"

        model_path = self.output_dir / filename
        self.model.save(str(model_path))
        print(f"Model saved to {model_path}")

        # Save class names
        class_names_path = self.output_dir / f"{self.model_type}_class_names.json"
        with open(class_names_path, "w") as f:
            json.dump(self.loader.class_names, f, indent=2)
        print(f"Class names saved to {class_names_path}")

        return model_path

    def save_training_history(self, filename: Optional[str] = None):
        """Save training history."""
        if self.history is None:
            raise ValueError("No training history available.")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        if filename is None:
            filename = f"{self.model_type}_history.json"

        history_path = self.output_dir / filename
        history_dict = {key: [float(v) for v in values] for key, values in self.history.history.items()}
        with open(history_path, "w") as f:
            json.dump(history_dict, f, indent=2)
        print(f"Training history saved to {history_path}")

        return history_path

