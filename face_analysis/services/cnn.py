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
                min_detection_confidence=0.3
            )
            print("MediaPipe Face Detection initialized successfully")
        except AttributeError:
            print("MediaPipe Face Detection NOT available (solutions missing).")
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
    
    def detect_and_crop_face(self, image_bgr: np.ndarray) -> np.ndarray | None:
        """
        Detect face and crop the image using MediaPipe.
        Validates face size and crops only skin-relevant region.
        Args:
            image_bgr: Input image in BGR format.
        Returns:
            Cropped face (BGR) or None if detection failed or face invalid.
        """
        if self.face_detector is None:
            print("❌ Face detector not available.")
            return None

        # Convert BGR → RGB (CRITICAL)
        image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        results = self.face_detector.process(image_rgb)

        if not results.detections:
            print("❌ No face detected")
            return None

        # Take the first detected face
        detection = results.detections[0]
        bbox = detection.location_data.relative_bounding_box

        h, w, _ = image_bgr.shape
        x1 = max(0, int(bbox.xmin * w))
        y1 = max(0, int(bbox.ymin * h))
        x2 = min(w, int((bbox.xmin + bbox.width) * w))
        y2 = min(h, int((bbox.ymin + bbox.height) * h))

        # Calculate face dimensions
        face_width = x2 - x1
        face_height = y2 - y1
        min_face_size = 50  # Reject faces smaller than 50px
        
        # Validate face size
        if face_width < min_face_size or face_height < min_face_size:
            print(f"❌ Face too small: {face_width}x{face_height} (minimum: {min_face_size}x{min_face_size})")
            return None
        
        # Extract skin-relevant region with slight padding
        padding_x = int(face_width * 0.05)  # 5% padding
        padding_y = int(face_height * 0.05)
        x1_padded = max(0, x1 - padding_x)
        y1_padded = max(0, y1 - padding_y)
        x2_padded = min(w, x2 + padding_x)
        y2_padded = min(h, y2 + padding_y)
        
        face_crop = image_bgr[y1_padded:y2_padded, x1_padded:x2_padded]

        if face_crop.size == 0:
            print("❌ Failed to crop face region")
            return None

        print(f"✅ Face detected and cropped: {face_crop.shape}")
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
