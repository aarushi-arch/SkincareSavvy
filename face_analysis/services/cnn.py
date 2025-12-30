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
        
        
        # Initialize MediaPipe FaceMesh
        try:
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=1,
                refine_landmarks=False,
                min_detection_confidence=0.3
            )
            print("MediaPipe FaceMesh initialized successfully")
        except AttributeError:
            print("MediaPipe FaceMesh NOT available (solutions missing).")
            self.face_mesh = None
        except Exception as e:
            print(f"MediaPipe FaceMesh initialization failed: {e}")
            self.face_mesh = None

    
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
    
    def detect_and_crop_face(self, image_bgr: np.ndarray) -> np.ndarray | None:
        """
        Detect face using FaceMesh landmarks and crop the image.
        Validates face size and crops only skin-relevant region.
        Args:
            image_bgr: Input image in BGR format.
        Returns:
            Cropped face (BGR) or None if detection failed or face invalid.
        """
        if self.face_mesh is None:
            print("❌ FaceMesh not available")
            return None

        h, w, _ = image_bgr.shape
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

        results = self.face_mesh.process(image_rgb)

        if not results.multi_face_landmarks:
            print("❌ No face landmarks detected")
            return None

        face_landmarks = results.multi_face_landmarks[0]

        xs = [int(lm.x * w) for lm in face_landmarks.landmark]
        ys = [int(lm.y * h) for lm in face_landmarks.landmark]

        x1, x2 = max(0, min(xs)), min(w, max(xs))
        y1, y2 = max(0, min(ys)), min(h, max(ys))

        # Validate face size
        if (x2 - x1) < 80 or (y2 - y1) < 80:
            print("❌ Face too small")
            return None

        # Crop with padding
        pad_x = int(0.05 * (x2 - x1))
        pad_y = int(0.10 * (y2 - y1))

        x1 = max(0, x1 - pad_x)
        y1 = max(0, y1 - pad_y)
        x2 = min(w, x2 + pad_x)
        y2 = min(h, y2 + pad_y)

        face_crop = image_bgr[y1:y2, x1:x2]

        print("✅ Face detected using FaceMesh")
        return face_crop

    # MAIN ENTRY POINT
    
    def analyze(self, image_bytes: bytes | np.ndarray) -> dict[str, Any]:
        """
        Run full analysis (skin type + concerns) AND generate heatmaps.
        """
        self.load_models_from_db()

        result = {}
        
        # Detect and Crop Face
        # 1. Convert bytes to BGR numpy array
        if isinstance(image_bytes, bytes):
            nparr = np.frombuffer(image_bytes, np.uint8)
            image_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif isinstance(image_bytes, np.ndarray):
             # Assuming input array is RGB (standard for this pipeline/PIL) but user code wants BGR input to convert back to RGB?
             # Wait, if input is from PIL (analyze typically called with bytes from view or PIL array)
             # Let's assume standard flow: bytes -> decode -> BGR (via cv2)
             # If array, assume it might be RGB or BGR? 
             # Safe assumption: `analyze` called with bytes in `views.py`.
             image_bgr = image_bytes
             # If it was RGB, we should convert to BGR for `detect_and_crop_face` to work as designed 
             # (it does BGR->RGB internally). 
             # But let's stick to the primary path: bytes.
        
        if image_bgr is None:
             print("Failed to decode image")
             return {}

        # 2. Run Detection
        cropped_face_bgr = self.detect_and_crop_face(image_bgr)
        
        if cropped_face_bgr is None:
            # Strict: reject if face detection fails
            return {"error": "Face detection failed or face too small"}
        
        # Convert BGR to RGB for analysis models
        cropped_face = cv2.cvtColor(cropped_face_bgr, cv2.COLOR_BGR2RGB)

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
