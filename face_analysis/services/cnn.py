"""CNN pipeline for face analysis."""
from __future__ import annotations

import json
from typing import Any

import numpy as np
import tensorflow as tf
from tensorflow import keras

from face_analysis.models import CNNModel
from face_analysis.utils.image_utils import preprocess_image


class FaceAnalysisPipeline:
    """
    CNN pipeline for face analysis (skin types and skin concerns).
    Loads ACTIVE models from the database.
    """

    def __init__(self) -> None:
        self.skin_types_model: keras.Model | None = None
        self.skin_concerns_model: keras.Model | None = None
        self.skin_types_classes: list[str] = []
        self.skin_concerns_classes: list[str] = []
        self._models_loaded = False

    def load_models_from_db(self) -> None:
        """Load active models from the database (only once)."""
        if self._models_loaded:
            return

        # ---- SKIN CONCERNS MODEL ----
        concerns = CNNModel.objects.filter(
            model_type="skin_concerns",
            is_active=True
        ).first()

        if concerns and concerns.model_file:
            try:
                self.skin_concerns_model = tf.keras.models.load_model(
                    concerns.model_file.path
                )
                self.skin_concerns_classes = concerns.class_names or []
                print("✔ Skin concerns model loaded")
            except Exception as e:
                print(f"❌ Skin concerns model load failed: {e}")

        # ---- SKIN TYPES MODEL ----
        skin_types = CNNModel.objects.filter(
            model_type="skin_types",
            is_active=True
        ).first()

        if skin_types and skin_types.model_file:
            try:
                self.skin_types_model = tf.keras.models.load_model(
                    skin_types.model_file.path
                )
                self.skin_types_classes = skin_types.class_names or []
                print("✔ Skin types model loaded")
            except Exception as e:
                print(f"❌ Skin types model load failed: {e}")

        self._models_loaded = True

    def preprocess(
        self,
        image_bytes: bytes | np.ndarray,
        target_size: tuple[int, int] = (224, 224),
    ) -> np.ndarray:
        return preprocess_image(image_bytes, target_size=target_size, normalize=True)

    def predict_skin_type(self, processed: np.ndarray, top_k: int = 3) -> dict[str, Any]:
        if self.skin_types_model is None:
            return {"error": "Skin types model not loaded"}

        preds = self.skin_types_model.predict(processed, verbose=0)[0]
        top = np.argsort(preds)[-top_k:][::-1]

        return {
            "predictions": [
                {
                    "class": self.skin_types_classes[i],
                    "confidence": float(preds[i]),
                }
                for i in top
            ]
        }

    def predict_skin_concerns(self, processed: np.ndarray, top_k: int = 3) -> dict[str, Any]:
        if self.skin_concerns_model is None:
            return {"error": "Skin concerns model not loaded"}

        preds = self.skin_concerns_model.predict(processed, verbose=0)[0]
        top = np.argsort(preds)[-top_k:][::-1]

        return {
            "predictions": [
                {
                    "class": self.skin_concerns_classes[i],
                    "confidence": float(preds[i]),
                }
                for i in top
            ]
        }

    def analyze(self, image_bytes: bytes | np.ndarray) -> dict[str, Any]:
        self.load_models_from_db()
        processed = self.preprocess(image_bytes)

        return {
            "skin_type": self.predict_skin_type(processed),
            "skin_concerns": self.predict_skin_concerns(processed),
        }
