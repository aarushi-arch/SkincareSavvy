"""CNN pipeline for face analysis."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from tensorflow import keras

from face_analysis.utils.image_utils import preprocess_image


class FaceAnalysisPipeline:
    """
    CNN pipeline for face analysis (skin types and skin concerns).
    """

    def __init__(
        self,
        skin_types_model_path: Path | str | None = None,
        skin_concerns_model_path: Path | str | None = None,
        models_dir: Path | str | None = None,
    ) -> None:
        """
        Initialize the pipeline with trained models.

        Args:
            skin_types_model_path: Path to skin types model
            skin_concerns_model_path: Path to skin concerns model
            models_dir: Directory containing models (will auto-detect if not specified)
        """
        if models_dir:
            models_dir = Path(models_dir)
            if skin_types_model_path is None:
                skin_types_model_path = models_dir / "skin_types_final_model.keras"
            if skin_concerns_model_path is None:
                skin_concerns_model_path = models_dir / "skin_concerns_final_model.keras"

        self.skin_types_model_path = Path(skin_types_model_path) if skin_types_model_path else None
        self.skin_concerns_model_path = Path(skin_concerns_model_path) if skin_concerns_model_path else None

        self.skin_types_model: keras.Model | None = None
        self.skin_concerns_model: keras.Model | None = None
        self.skin_types_classes: list[str] = []
        self.skin_concerns_classes: list[str] = []

        # Load models if paths are provided
        if self.skin_types_model_path and self.skin_types_model_path.exists():
            self.load_skin_types_model()
        if self.skin_concerns_model_path and self.skin_concerns_model_path.exists():
            self.load_skin_concerns_model()

    def load_skin_types_model(self):
        """Load the skin types classification model."""
        if self.skin_types_model_path and self.skin_types_model_path.exists():
            self.skin_types_model = keras.models.load_model(str(self.skin_types_model_path))
            # Load class names
            class_names_path = self.skin_types_model_path.parent / "skin_types_class_names.json"
            if class_names_path.exists():
                with open(class_names_path) as f:
                    self.skin_types_classes = json.load(f)
        else:
            raise FileNotFoundError(f"Skin types model not found at {self.skin_types_model_path}")

    def load_skin_concerns_model(self):
        """Load the skin concerns classification model."""
        if self.skin_concerns_model_path and self.skin_concerns_model_path.exists():
            self.skin_concerns_model = keras.models.load_model(str(self.skin_concerns_model_path))
            # Load class names
            class_names_path = self.skin_concerns_model_path.parent / "skin_concerns_class_names.json"
            if class_names_path.exists():
                with open(class_names_path) as f:
                    self.skin_concerns_classes = json.load(f)
        else:
            raise FileNotFoundError(f"Skin concerns model not found at {self.skin_concerns_model_path}")

    def preprocess(self, image_bytes: bytes | np.ndarray, target_size: tuple[int, int] = (224, 224)) -> np.ndarray:
        """
        Convert raw image bytes to a normalized NumPy array suitable for model input.

        Args:
            image_bytes: Raw image bytes or numpy array
            target_size: Target image size (height, width)

        Returns:
            Preprocessed image array
        """
        return preprocess_image(image_bytes, target_size=target_size, normalize=True)

    def predict_skin_type(self, processed: np.ndarray, top_k: int = 3) -> dict[str, Any]:
        """
        Predict skin type from preprocessed image.

        Args:
            processed: Preprocessed image array
            top_k: Number of top predictions to return

        Returns:
            Dictionary with predictions
        """
        if self.skin_types_model is None:
            raise ValueError("Skin types model not loaded. Call load_skin_types_model() first.")

        predictions = self.skin_types_model.predict(processed, verbose=0)[0]
        top_indices = np.argsort(predictions)[-top_k:][::-1]

        results = {
            "predictions": [
                {
                    "class": self.skin_types_classes[idx] if idx < len(self.skin_types_classes) else f"class_{idx}",
                    "confidence": float(predictions[idx]),
                }
                for idx in top_indices
            ],
            "top_prediction": {
                "class": self.skin_types_classes[top_indices[0]] if top_indices[0] < len(self.skin_types_classes) else "unknown",
                "confidence": float(predictions[top_indices[0]]),
            },
        }

        return results

    def predict_skin_concerns(self, processed: np.ndarray, top_k: int = 3) -> dict[str, Any]:
        """
        Predict skin concerns from preprocessed image.

        Args:
            processed: Preprocessed image array
            top_k: Number of top predictions to return

        Returns:
            Dictionary with predictions
        """
        if self.skin_concerns_model is None:
            raise ValueError("Skin concerns model not loaded. Call load_skin_concerns_model() first.")

        predictions = self.skin_concerns_model.predict(processed, verbose=0)[0]
        top_indices = np.argsort(predictions)[-top_k:][::-1]

        results = {
            "predictions": [
                {
                    "class": self.skin_concerns_classes[idx] if idx < len(self.skin_concerns_classes) else f"class_{idx}",
                    "confidence": float(predictions[idx]),
                }
                for idx in top_indices
            ],
            "top_prediction": {
                "class": self.skin_concerns_classes[top_indices[0]] if top_indices[0] < len(self.skin_concerns_classes) else "unknown",
                "confidence": float(predictions[top_indices[0]]),
            },
        }

        return results

    def analyze(self, image_bytes: bytes | np.ndarray) -> dict[str, Any]:
        """
        Analyze image for both skin type and skin concerns.

        Args:
            image_bytes: Raw image bytes or numpy array

        Returns:
            Dictionary with both skin type and skin concerns predictions
        """
        processed = self.preprocess(image_bytes)

        results = {}

        if self.skin_types_model is not None:
            results["skin_type"] = self.predict_skin_type(processed)
        else:
            results["skin_type"] = {"error": "Model not loaded"}

        if self.skin_concerns_model is not None:
            results["skin_concerns"] = self.predict_skin_concerns(processed)
        else:
            results["skin_concerns"] = {"error": "Model not loaded"}

        return results

