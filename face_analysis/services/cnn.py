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

    
    # MODEL LOADING
    
    def load_models_from_db(self) -> None:
        """Load active models from the database (only once)."""
        if self._models_loaded:
            return

        # SKIN CONCERNS 
        concerns = CNNModel.objects.filter(
            model_type="skin_concerns",
            is_active=True
        ).first()

        if concerns and concerns.model_file:
            try:
                self.skin_concerns_model = tf.keras.models.load_model(
                    concerns.model_file.path
                )
                self.skin_concerns_classes = self._parse_class_names(concerns)
                print("Skin concerns model loaded")
            except Exception as e:
                print(f"Skin concerns model load failed: {e}")

        # SKIN TYPES 
        skin_types = CNNModel.objects.filter(
            model_type="skin_types",
            is_active=True
        ).first()

        if skin_types and skin_types.model_file:
            try:
                self.skin_types_model = tf.keras.models.load_model(
                    skin_types.model_file.path
                )
                self.skin_types_classes = self._parse_class_names(skin_types)
                print("Skin types model loaded")
            except Exception as e:
                print(f"Skin types model load failed: {e}")

        self._models_loaded = True

    
    # CLASS NAME HANDLING (FIXES Class_0 BUG)
    
    def _parse_class_names(self, model: CNNModel) -> list[str]:
        """
        Converts JSON class file into ordered class list.

        Supports:
        - {"acne": 0, "pores": 1}
        - ["acne", "pores"]
        """
        raw = model.class_names

        if isinstance(raw, dict):
            # Convert index-mapped dict → ordered list
            return [k for k, v in sorted(raw.items(), key=lambda x: x[1])]

        if isinstance(raw, list):
            return raw

        return []

    
    # PREPROCESSING
    
    def preprocess(
        self,
        image_bytes: bytes | np.ndarray,
    ) -> np.ndarray:
        """
        Preprocess image according to model input size.
        """
        # Detect input size dynamically
        if self.skin_concerns_model is not None:
            h, w = self.skin_concerns_model.input_shape[1:3]
        elif self.skin_types_model is not None:
            h, w = self.skin_types_model.input_shape[1:3]
        else:
            h, w = (224, 224)

        return preprocess_image(
            image_bytes,
            target_size=(h, w),
            normalize=True,
        )

    
    # PREDICTIONS
    
    def predict_skin_type(
        self,
        processed: np.ndarray,
        top_k: int = 3
    ) -> dict[str, Any]:
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

    def predict_skin_concerns(
        self,
        processed: np.ndarray,
        top_k: int = 3
    ) -> dict[str, Any]:
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

    
    # MAIN ENTRY POINT
    
    def analyze(self, image_bytes: bytes | np.ndarray) -> dict[str, Any]:
        """
        Run full analysis (skin type + concerns).
        """
        self.load_models_from_db()

        processed = self.preprocess(image_bytes)

        return {
            "skin_type": self.predict_skin_type(processed),
            "skin_concerns": self.predict_skin_concerns(processed),
        }
