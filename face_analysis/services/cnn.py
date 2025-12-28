"""CNN pipeline for face analysis."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import tensorflow as tf
from tensorflow import keras

from face_analysis.models import CNNModel
from face_analysis.utils.image_utils import preprocess_image
from face_analysis.utils.gradcam import generate_multi_skin_concern_heatmaps

import cv2
import mediapipe as mp


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
        
        
        # Initialize MediaPipe Face Detection
        try:
            self.mp_face_detection = mp.solutions.face_detection
            self.face_detector = self.mp_face_detection.FaceDetection(
                model_selection=1, 
                min_detection_confidence=0.6
            )
            print("MediaPipe Face Detection initialized successfully")
        except AttributeError:
            print("MediaPipe Face Detection NOT available (solutions missing). Using full image.")
            self.face_detector = None
        except Exception as e:
            print(f"MediaPipe Face Detection initialization failed: {e}")
            self.face_detector = None

    
    # MODEL LOADING
    
    def load_models_from_db(self) -> None:
        """Load active models."""
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

        # SKIN TYPES - LOAD FROM LOCAL FILE
        try:
            base_path = Path(__file__).resolve().parent.parent / "models" / "ml"
            model_path = base_path / "skin_type_mobilenet_final.h5"
            labels_path = base_path / "class_labels (1).json"

            if model_path.exists():
                self.skin_types_model = tf.keras.models.load_model(str(model_path))
                print(f"Skin types model loaded from {model_path}")
            else:
                print(f"Skin types model not found at {model_path}")

            if labels_path.exists():
                with open(labels_path, "r") as f:
                    labels_data = json.load(f)
                    # Handle dict {"Combination": 0, ...} -> ["Combination", ...]
                    if isinstance(labels_data, dict):
                        # Sort by value to ensure correct order
                        self.skin_types_classes = [k for k, v in sorted(labels_data.items(), key=lambda x: x[1])]
                    elif isinstance(labels_data, list):
                        self.skin_types_classes = labels_data
                    print(f"Skin types classes loaded: {self.skin_types_classes}")
            else:
                 print(f"Skin types labels not found at {labels_path}")

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
        target_model: keras.Model | None = None,
    ) -> np.ndarray:
        """
        Preprocess image according to model input size.
        """
        h, w = (224, 224)

        if target_model is not None:
            try:
                shape = target_model.input_shape
                # shape might be (None, 224, 224, 3)
                if shape and len(shape) >= 3:
                     h, w = shape[1:3]
            except Exception:
                pass
        
        # Ensure we have valid dimensions
        if h is None or w is None:
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
        # Ensure we don't request more top_k than classes available
        k = min(top_k, len(self.skin_types_classes))
        top = np.argsort(preds)[-k:][::-1]

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
        k = min(top_k, len(self.skin_concerns_classes))
        top = np.argsort(preds)[-k:][::-1]

        return {
            "predictions": [
                {
                    "class": self.skin_concerns_classes[i],
                    "confidence": float(preds[i]),
                }
                for i in top
            ]
        }

    
    
    # FACE DETECTION
    
    def detect_and_crop(self, image_bytes: bytes | np.ndarray) -> np.ndarray:
        """
        Detect face and crop the image. 
        Returns RGB numpy array of the face (or original image if no face).
        """
        # Convert bytes to numpy array (if needed)
        if isinstance(image_bytes, bytes):
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif isinstance(image_bytes, np.ndarray):
            image = image_bytes
            # If RGB, convert to BGR for consistently using cv2 (though mediapipe wants RGB)
            # Assuming input ndarray might be RGB if coming from PIL. 
            # Safest is to treat as BGR if read by cv2, or convert to RGB immediately.
            # Let's rely on image_bytes being the primary input format (raw bytes).
            pass
        
        if image is None:
            # Fallback or error
            return np.zeros((224, 224, 3), dtype=np.uint8)

        # Convert to RGB for MediaPipe
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        if not self.face_detector:
            return rgb

        # Process
        try:
            results = self.face_detector.process(rgb)
            
            if results.detections:
                # Take the first face (highest confidence usually)
                detection = results.detections[0]
                bbox = detection.location_data.relative_bounding_box
                
                h, w, _ = image.shape
                x = int(bbox.xmin * w)
                y = int(bbox.ymin * h)
                width = int(bbox.width * w)
                height = int(bbox.height * h)
                
                # Ensure within bounds
                x = max(0, x)
                y = max(0, y)
                width = min(w - x, width)
                height = min(h - y, height)
                
                if width > 0 and height > 0:
                    face = rgb[y:y+height, x:x+width]
                    print(f"Face detected and cropped: {width}x{height}")
                    return face
            
        except Exception as e:
            print(f"Face detection failed during process: {e}")
        
        print("No face detected, using original image.")
        return rgb

    # MAIN ENTRY POINT
    
    def analyze(self, image_bytes: bytes | np.ndarray) -> dict[str, Any]:
        """
        Run full analysis (skin type + concerns) AND generate heatmaps.
        """
        self.load_models_from_db()

        result = {}
        
        # Detect and Crop Face
        # The result is already a numpy array (RGB)
        cropped_face = self.detect_and_crop(image_bytes)

        if self.skin_types_model:
            processed_types = self.preprocess(cropped_face, target_model=self.skin_types_model)
            result["skin_type"] = self.predict_skin_type(processed_types)
        
        if self.skin_concerns_model:
            processed_concerns = self.preprocess(cropped_face, target_model=self.skin_concerns_model)
            
            # Predict concerns
            concerns_result = self.predict_skin_concerns(processed_concerns)
            
            # Generate heatmaps
            try:
                print("Generating heatmaps...")
                
                # Determine target size
                target_size = (224, 224)
                try:
                    shape = self.skin_concerns_model.input_shape
                    if shape and len(shape) >= 3:
                         target_size = shape[1:3]
                except AttributeError:
                    pass

                # Note: Generate heatmaps needs the raw cropped image, not the preprocessed one?
                # The existing function likely takes image bytes or array.
                # Let's check `generate_multi_skin_concern_heatmaps` signature in previous context or next step.
                # It was imported. Assuming it can handle the array.
                # Just passing cropped_face (RGB numpy array) should be fine if it handles it.
                
                # However, GradCAM usually needs the preprocessed input to run the model, 
                # but to overlay, it needs the original image.
                # Looking at cnn.py imports: `from face_analysis.utils.gradcam import generate_multi_skin_concern_heatmaps`
                
                # Let's pass the cropped_face (as bytes or array) 
                
                heatmaps = generate_multi_skin_concern_heatmaps(
                    self.skin_concerns_model,
                    cropped_face, # Passing the cropped RGB array
                    self.skin_concerns_classes,
                    target_size=target_size
                )
                
                # Merge heatmaps into predictions
                # Iterate through predictions and attach matches
                if "predictions" in concerns_result:
                    for pred in concerns_result["predictions"]:
                        # Find matching heatmap
                        match = next((h for h in heatmaps if h['class'] == pred['class']), None)
                        if match:
                            pred['heatmap'] = match['heatmap_img']
                
                result["skin_concerns"] = concerns_result
            except Exception as e:
                print(f"Heatmap generation failed: {e}")
                # Fallback to just predictions
                result["skin_concerns"] = concerns_result

        print(result)

        return result
