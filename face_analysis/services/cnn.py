"""CNN pipeline for face analysis."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import tensorflow as tf
import keras

from face_analysis.models import CNNModel # Import CNN model stored in database
from face_analysis.utils.image_utils import preprocess_image # For consistent preprocessing
from face_analysis.utils.gradcam import generate_multi_skin_concern_heatmaps # For heatmap generation

import cv2 # For image processing and face detection
import mediapipe as mp # For advanced face detection and landmark recognition


class FaceAnalysisPipeline:
    """
    CNN pipeline for face analysis (skin types and skin concerns).
    Loads Active models from the database.
    """

    def __init__(self) -> None:
        self.skin_types_model: keras.Model | None = None
        self.skin_concerns_model: keras.Model | None = None
        self.skin_types_classes: list[str] = []
        self.skin_concerns_classes: list[str] = []
        self._models_loaded = False
        
        
        # Initialize MediaPipe FaceDetection (better for face detection)
        try:
            self.mp_face_detection = mp.solutions.face_detection
            self.face_detector = self.mp_face_detection.FaceDetection(
                model_selection=1,          # Best for selfies/close-up images
                min_detection_confidence=0.6
            )
            print("MediaPipe FaceDetection initialized successfully")
        except Exception as e:
            print(f"MediaPipe FaceDetection initialization failed: {e}")
            self.face_detector = None
        
        # Initialize MediaPipe FaceMesh (for eye landmark detection)
        try:
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.6
            )
            print("MediaPipe FaceMesh initialized successfully")
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
                # Try to load with custom objects to handle version mismatches
                self.skin_concerns_model = tf.keras.models.load_model(
                    concerns.model_file.path,
                    custom_objects=self._compatible_custom_objects(),
                    compile=False,
                )
                self.skin_concerns_classes = self._parse_class_names(concerns)
                
                # Validate class names were loaded
                if not self.skin_concerns_classes:
                    print(f"[WARNING] Skin concerns model '{concerns.name}' loaded, but class_names is empty!")
                    print(f"  - Has class_names_file: {bool(concerns.class_names_file)}")
                    if concerns.class_names_file:
                        print(f"  - File path: {concerns.class_names_file.path}")
                    print(f"  - Raw class_names data: {concerns.class_names}")
                    # Unload the model if classes are missing
                    self.skin_concerns_model = None
                else:
                    print(f"[OK] Skin concerns model loaded with {len(self.skin_concerns_classes)} classes")
            except Exception as e:
                print(f"[ERROR] Skin concerns model load failed: {e}")
                # Try a second attempt with compatibility mode + custom object wrappers
                try:
                    print("[INFO] Attempting to load with compatibility mode (custom layer wrappers)...")
                    self.skin_concerns_model = tf.keras.models.load_model(
                        concerns.model_file.path,
                        custom_objects=self._compatible_custom_objects(),
                        compile=False,
                        safe_mode=False,
                    )
                    self.skin_concerns_classes = self._parse_class_names(concerns)
                    print(f"[OK] Skin concerns model loaded in compatibility mode")
                except Exception as e2:
                    print(f"[ERROR] Compatibility mode also failed: {e2}")
                    self.skin_concerns_model = None
        else:
            if concerns:
                print(f"[ERROR] Skin concerns model '{concerns.name}' found but model_file is missing")
            else:
                print(f"[WARNING] No active skin concerns model found")

        # SKIN TYPES - LOAD FROM LOCAL FILE
        try:
            base_path = Path(__file__).resolve().parent.parent / "models" / "ml"
            model_path = base_path / "skin_type_mobilenet_final.h5"
            labels_path = base_path / "class_labels (1).json"

            if model_path.exists():
                self.skin_types_model = tf.keras.models.load_model(str(model_path))
                print(f"[OK] Skin types model loaded from {model_path}")
            else:
                print(f"[ERROR] Skin types model not found at {model_path}")

            if labels_path.exists():
                with open(labels_path, "r") as f:
                    labels_data = json.load(f)
                    # Handle dict {"Combination": 0, ...} -> ["Combination", ...]
                    if isinstance(labels_data, dict):
                        # Sort by value to ensure correct order
                        self.skin_types_classes = [k for k, v in sorted(labels_data.items(), key=lambda x: x[1])]
                    elif isinstance(labels_data, list):
                        self.skin_types_classes = labels_data
                    print(f"[OK] Skin types classes loaded: {self.skin_types_classes}")
            else:
                 print(f"[ERROR] Skin types labels not found at {labels_path}")

        except Exception as e:
            print(f"[ERROR] Skin types model load failed: {e}")

        if not self.skin_types_model or not self.skin_concerns_model:
            print("[WARNING] CNN models incomplete. Some analysis features may not be available until all models are active.")
            
        self._models_loaded = True

    
    # CLASS NAME HANDLING 
    
    def _compatible_custom_objects(self) -> dict:
        """Provide fallback custom objects for legacy models containing quantization metadata."""
        class DenseCompat(tf.keras.layers.Dense):
            def __init__(self, *args, quantization_config=None, **kwargs):
                super().__init__(*args, **kwargs)

            def get_config(self):
                cfg = super().get_config()
                # Some older saved models include this field (TFLite conversion metadata)
                if 'quantization_config' in cfg:
                    cfg.pop('quantization_config')
                return cfg

        return {
            'quantization_config': None,
            'Dense': DenseCompat,
        }

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
        h, w = (128, 128)

        if target_model is not None:
            try:
                shape = target_model.input_shape
                # shape might be (None, 128, 128, 3)
                if shape and len(shape) >= 3:
                     h, w = shape[1:3]
            except Exception:
                pass
        
        # Ensure we have valid dimensions
        if h is None or w is None:
             h, w = (128, 128)

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

        return { # Return list of top predictions with class names and confidence
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
        
        if not self.skin_concerns_classes:
            return {"error": "Skin concerns model loaded but classes are missing. Check class_names_file in Django Admin.", "predictions": []}

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

    
    
    # FACE DETECTION & PREPROCESSING
    
    
    def detect_face(self, image_bgr: np.ndarray):
        """
        Detects face using MediaPipe FaceDetection.
        
        Args:
            image_bgr: Input image in BGR format
            
        Returns:
            MediaPipe detection results or None
        """
        if self.face_detector is None:
            print("FaceDetection not available")
            return None
            
        rgb_image = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        results = self.face_detector.process(rgb_image)
        return results

    def validate_face(self, image_bgr: np.ndarray, results) -> tuple[bool, str]:
        """
        Validates detected face.
        
        Args:
            image_bgr: Input image in BGR format
            results: MediaPipe detection results
            
        Returns:
            Tuple of (is_valid, message)
        """
        if results is None or not results.detections:
            return False, "No face detected. Please upload a clear selfie with your face visible."

        if len(results.detections) > 1:
            return False, "Multiple faces detected. Please upload an image with only one face."

        detection = results.detections[0]
        confidence = detection.score[0]

        if confidence < 0.6:
            return False, f"Low confidence face detection ({confidence:.2%}). Please use a clearer image."

        h, w, _ = image_bgr.shape
        bbox = detection.location_data.relative_bounding_box
        face_width = bbox.width * w
        face_height = bbox.height * h

        if face_width < 100 or face_height < 100:
            return False, "Face too small. Please move closer or use a higher resolution image."

        return True, "Valid face detected"

    def crop_face(self, image_bgr: np.ndarray, detection) -> np.ndarray | None:
        """
        Crops face region from image.
        
        Args:
            image_bgr: Input image in BGR format
            detection: MediaPipe detection object
            
        Returns:
            Cropped face image or None
        """
        h, w, _ = image_bgr.shape
        bbox = detection.location_data.relative_bounding_box

        x = int(bbox.xmin * w)
        y = int(bbox.ymin * h)
        width = int(bbox.width * w)
        height = int(bbox.height * h)

        # Clamp values
        x = max(0, x)
        y = max(0, y)
        width = min(w - x, width)
        height = min(h - y, height)

        face_img = image_bgr[y:y + height, x:x + width]
        
        if face_img.size == 0:
            return None
            
        return face_img

    def validate_face_landmarks(self, face_img: np.ndarray) -> bool:
        """
        Confirms presence of real facial landmarks using FaceMesh.
        Rejects non-faces (objects, cartoons, printed photos, etc.).
        
        Args:
            face_img: Face image in BGR format
            
        Returns:
            True if valid face landmarks detected, False otherwise
        """
        if self.face_mesh is None:
            print("FaceMesh not available, skipping landmark validation")
            return False

        rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)

        return bool(results.multi_face_landmarks)

    def mask_eyes(self, face_img: np.ndarray) -> np.ndarray:
        """
        Masks both eyes using MediaPipe FaceMesh landmarks.
        This excludes eyes from skin analysis.
        
        Args:
            face_img: Face image in BGR format
            
        Returns:
            Face image with eyes masked (blacked out)
        """
        if self.face_mesh is None:
            print("FaceMesh not available, skipping eye masking")
            return face_img
        
        h, w, _ = face_img.shape
        rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            print("No face landmarks detected for eye masking")
            return face_img

        # Eye landmark indices from MediaPipe FaceMesh
        LEFT_EYE = [33, 133, 160, 159, 158, 157, 173]
        RIGHT_EYE = [362, 263, 387, 386, 385, 384, 398]

        # Create white mask (255 = keep, 0 = remove)
        mask = np.ones((h, w), dtype=np.uint8) * 255

        for landmarks in results.multi_face_landmarks:
            for eye in [LEFT_EYE, RIGHT_EYE]:
                points = []
                for idx in eye:
                    lm = landmarks.landmark[idx]
                    points.append((int(lm.x * w), int(lm.y * h)))

                points = np.array(points, dtype=np.int32)
                # Fill eye region with 0 (will be masked out)
                cv2.fillPoly(mask, [points], 0)

        # Apply mask to face image
        masked_face = cv2.bitwise_and(face_img, face_img, mask=mask)
        print("Eyes masked successfully")
        return masked_face

    def normalize_lighting(self, face_img: np.ndarray) -> np.ndarray:
        """
        Normalizes lighting using LAB color space.
        
        Args:
            face_img: Face image in BGR format
            
        Returns:
            Lighting-normalized image
        """
        lab = cv2.cvtColor(face_img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # Equalize the L-channel
        l = cv2.equalizeHist(l)

        lab = cv2.merge((l, a, b))
        normalized = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        return normalized

    def denoise_image(self, face_img: np.ndarray) -> np.ndarray:
        """
        Reduces noise while preserving skin texture.
        
        Args:
            face_img: Face image in BGR format
            
        Returns:
            Denoised image
        """
        return cv2.bilateralFilter(face_img, d=9, sigmaColor=75, sigmaSpace=75)

    def prepare_for_cnn(self, face_img: np.ndarray, target_size: tuple[int, int] = (224, 224)) -> np.ndarray:
        """
        Resizes and normalizes image for CNN.
        
        Args:
            face_img: Face image in BGR format
            target_size: Target size for CNN input
            
        Returns:
            Preprocessed image ready for CNN
        """
        face_img = cv2.resize(face_img, target_size)
        face_img = face_img.astype(np.float32) / 255.0
        return face_img

    def skincare_preprocess(self, image_bgr: np.ndarray) -> tuple[np.ndarray | None, str]:
        """
        Minimal preprocessing that MATCHES training preprocessing.
        Uses face detection only for validation and cropping.
        """
        print("Step 1: Detecting face in uploaded image...")
        results = self.detect_face(image_bgr)

        valid, message = self.validate_face(image_bgr, results)
        if not valid:
            print(f"{message}")
            return None, message

        print(f"{message}")

        detection = results.detections[0]
        face = self.crop_face(image_bgr, detection)

        if face is None or face.size == 0:
            return None, "Face crop failed"

        # NEW: Landmark validation
        print("Step 2: Validating facial landmarks...")
        if not self.validate_face_landmarks(face):
            return None, "No real human face detected. Please upload a clear selfie."
        
        print("Facial landmarks validated successfully")

        # IMPORTANT:
        # NO eye masking
        # NO lighting normalization
        # NO denoising
        # These were NOT used during training

        print("Face cropped successfully (no visual modification applied)")
        return face, "Ready for CNN"

    # MAIN ENTRY POINT
    
    def analyze(self, image_bytes: bytes | np.ndarray) -> dict[str, Any]:
        """
        Run full analysis (skin type + concerns) AND generate heatmaps.
        """
        self.load_models_from_db()

        result = {}
        
        
        # Step 1: Convert bytes to BGR numpy array
        if isinstance(image_bytes, bytes):
            nparr = np.frombuffer(image_bytes, np.uint8)
            image_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif isinstance(image_bytes, np.ndarray):
            # Assume it's already a BGR array from cv2
            image_bgr = image_bytes
        
        if image_bgr is None:
            print("Failed to decode image")
            return {"error": "Invalid image format"}

        # Step 2: Run comprehensive preprocessing pipeline
        cropped_face_bgr, status_message = self.skincare_preprocess(image_bgr)
        
        if cropped_face_bgr is None:
            # Face preprocessing failed → return error
            return {"error": status_message}
        
        # If both models are missing, return a clear error (no simulation results)
        if not self.skin_types_model and not self.skin_concerns_model:
            return {
                "error": "No active skin models are available. Please upload and activate skin type and skin concerns models in the admin dashboard.",
            }
        
        # Convert BGR to RGB for CNN models (they expect RGB)
        cropped_face_rgb = cv2.cvtColor(cropped_face_bgr, cv2.COLOR_BGR2RGB)

        if self.skin_types_model:
            processed_types = self.preprocess(cropped_face_rgb, target_model=self.skin_types_model)
            result["skin_type"] = self.predict_skin_type(processed_types)
        
        if self.skin_concerns_model:
            processed_concerns = self.preprocess(cropped_face_rgb, target_model=self.skin_concerns_model)
            
            # Predict concerns
            concerns_result = self.predict_skin_concerns(processed_concerns)
            
            # Check if predictions have errors
            if concerns_result.get("error"):
                print(f"✗ Skin concerns prediction error: {concerns_result['error']}")
                result["skin_concerns"] = concerns_result
            else:
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

                    heatmap_result = generate_multi_skin_concern_heatmaps(
                        self.skin_concerns_model,
                        cropped_face_rgb, # Passing the cropped RGB array
                        self.skin_concerns_classes,
                        target_size=target_size
                    )

                    # Debug info
                    print("Heatmap generation result keys:", heatmap_result.keys() if isinstance(heatmap_result, dict) else type(heatmap_result))

                    # Attach combined heatmap and detected concerns
                    if isinstance(heatmap_result, dict):
                        result["combined_heatmap"] = heatmap_result.get('combined_heatmap')
                        result["detected_concerns_from_heatmap"] = heatmap_result.get('detected_concerns', [])
                        result["individual_heatmaps"] = heatmap_result.get('individual_heatmaps', {})

                    # Keep individual predictions (without per-class heatmap attachments)
                    result["skin_concerns"] = concerns_result
                except Exception as e:
                    print(f"Heatmap generation failed: {e}")
                    # Fallback to just predictions
                    result["skin_concerns"] = concerns_result
        else:
            print("[WARNING] Skin concerns model not loaded. Skin concerns predictions will be empty.")
            result["skin_concerns"] = {"predictions": []}
            result["flags"] = {
                "acne": False,
                "wrinkles": False,
                "pores": False,
                "darkspots": False,
                "blackheads": False,
            }
            result["detected_concerns"] = []

        print(result)

        # Ensure image is present for display
        import base64
        _, buffer = cv2.imencode(".jpg", image_bgr)
        result["image_base64"] = base64.b64encode(buffer).decode("utf-8")

        return result
