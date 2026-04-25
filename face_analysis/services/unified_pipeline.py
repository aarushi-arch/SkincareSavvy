"""
Unified Skin Analysis Pipeline
================================
Single entry point that runs all three models in the correct order:

  1. MediaPipe  — detect face, get bounding box
  2. YOLO       — detect localised concern regions on the face crop
  3. MobileNet  — classify overall skin type + concern severity on the face crop

This replaces the need to call cnn.py and yolo_pipeline.py separately.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np


# ── Singleton model holders (loaded once per process) ────────────────────────

class _Models:
    """Lazy-loaded model container — initialised on first use."""

    def __init__(self) -> None:
        self._ready = False

        # MediaPipe
        self.face_detector = None

        # YOLO
        self.yolo = None
        self._yolo_loaded = False

        # MobileNet (skin type + concerns)
        self.skin_type_model    = None
        self.skin_concern_model = None
        self.skin_type_classes:    list[str] = []
        self.skin_concern_classes: list[str] = []

    # ── MediaPipe ─────────────────────────────────────────────────────────────

    def _init_mediapipe(self) -> None:
        try:
            import mediapipe as mp
            self.face_detector = mp.solutions.face_detection.FaceDetection(
                model_selection=0,
                min_detection_confidence=0.3,
            )
            print("[Pipeline] MediaPipe FaceDetection ready")
        except Exception as e:
            print(f"[Pipeline] MediaPipe init failed: {e}")

    # ── YOLO ──────────────────────────────────────────────────────────────────

    def load_yolo(self) -> None:
        if self._yolo_loaded:
            return
        try:
            from ultralytics import YOLO
            from face_analysis.models import YOLOModel

            record = YOLOModel.objects.filter(is_active=True).first()
            if record and record.model_file:
                self.yolo = YOLO(record.model_file.path)
                print(f"[Pipeline] YOLO loaded: {record.name}")
            else:
                self.yolo = YOLO("yolov8n.pt")
                print("[Pipeline] YOLO fallback: yolov8n.pt")
        except ImportError:
            print("[Pipeline] ultralytics not installed")
        except Exception as e:
            print(f"[Pipeline] YOLO load error: {e}")
        self._yolo_loaded = True

    def reload_yolo(self) -> None:
        self._yolo_loaded = False
        self.yolo = None
        self.load_yolo()

    def reload_mobilenet(self) -> None:
        """Force reload MobileNet — call this if models were updated in DB."""
        self.skin_type_model    = None
        self.skin_concern_model = None
        self.skin_type_classes    = []
        self.skin_concern_classes = []
        self._load_mobilenet()

    # ── MobileNet ─────────────────────────────────────────────────────────────

    def _load_mobilenet(self) -> None:
        import tensorflow as tf
        from face_analysis.models import CNNModel

        # Compatible custom objects — handles quantization metadata in older models
        class _DenseCompat(tf.keras.layers.Dense):
            def __init__(self, *args, quantization_config=None, **kwargs):
                super().__init__(*args, **kwargs)
            def get_config(self):
                cfg = super().get_config()
                cfg.pop('quantization_config', None)
                return cfg

        custom_objects = {'quantization_config': None, 'Dense': _DenseCompat}

        # ── Skin type — from local file ───────────────────────────────────────
        try:
            base = Path(__file__).resolve().parent.parent / "models" / "ml"
            model_path  = base / "skin_type_mobilenet_final.h5"
            labels_path = base / "class_labels (1).json"

            if model_path.exists():
                self.skin_type_model = tf.keras.models.load_model(
                    str(model_path), custom_objects=custom_objects, compile=False
                )
                print(f"[Pipeline] Skin-type model loaded from {model_path.name}")
            else:
                print(f"[Pipeline] Skin-type model NOT found at {model_path}")

            if labels_path.exists():
                with open(labels_path) as f:
                    data = json.load(f)
                self.skin_type_classes = (
                    [k for k, v in sorted(data.items(), key=lambda x: x[1])]
                    if isinstance(data, dict) else data
                )
                print(f"[Pipeline] Skin-type classes: {self.skin_type_classes}")
        except Exception as e:
            print(f"[Pipeline] Skin-type model error: {e}")

        # ── Skin concerns — from DB ───────────────────────────────────────────
        try:
            record = CNNModel.objects.filter(model_type="skin_concerns", is_active=True).first()
            if not record:
                print("[Pipeline] No active skin_concerns model in DB")
                return
            if not record.model_file:
                print("[Pipeline] Skin-concerns model record has no file")
                return

            print(f"[Pipeline] Loading skin-concerns model: {record.name} → {record.model_file.path}")

            # First attempt — with custom objects
            try:
                self.skin_concern_model = tf.keras.models.load_model(
                    record.model_file.path,
                    custom_objects=custom_objects,
                    compile=False,
                )
            except Exception as e1:
                print(f"[Pipeline] First load attempt failed ({e1}), trying safe_mode=False")
                self.skin_concern_model = tf.keras.models.load_model(
                    record.model_file.path,
                    custom_objects=custom_objects,
                    compile=False,
                    safe_mode=False,
                )

            raw = record.class_names
            self.skin_concern_classes = (
                [k for k, v in sorted(raw.items(), key=lambda x: x[1])]
                if isinstance(raw, dict) else (raw if isinstance(raw, list) else [])
            )
            print(f"[Pipeline] Skin-concern model loaded — classes: {self.skin_concern_classes}")

        except Exception as e:
            print(f"[Pipeline] Skin-concern model FAILED to load: {e}")
            import traceback
            traceback.print_exc()

    # ── Bootstrap ─────────────────────────────────────────────────────────────

    def ensure_ready(self) -> None:
        if self._ready:
            return
        self._init_mediapipe()
        self.load_yolo()
        self._load_mobilenet()
        # Only mark ready if at least one model loaded successfully
        self._ready = True
        if self.skin_concern_model is None:
            print("[Pipeline] WARNING: skin_concern_model is None after load attempt")


_models = _Models()


# ── Helper functions ──────────────────────────────────────────────────────────

def _detect_face(image_bgr: np.ndarray) -> dict:
    """Run MediaPipe and return face bbox with padding."""
    if _models.face_detector is None:
        return {"face_present": False, "bbox": None}

    h, w = image_bgr.shape[:2]
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    results = _models.face_detector.process(rgb)

    if not results.detections:
        return {"face_present": False, "bbox": None}

    best = max(results.detections, key=lambda d: d.score[0])
    rel  = best.location_data.relative_bounding_box

    PAD = 30
    x1 = max(0,     int(rel.xmin * w) - PAD)
    y1 = max(0,     int(rel.ymin * h) - PAD)
    x2 = min(w,     int((rel.xmin + rel.width)  * w) + PAD)
    y2 = min(h,     int((rel.ymin + rel.height) * h) + PAD)

    return {"face_present": True, "bbox": [x1, y1, x2, y2]}


def _run_yolo(face_crop: np.ndarray, orig_x1: int, orig_y1: int,
              orig_w: int, orig_h: int, conf: float = 0.20) -> list[dict]:
    """Run YOLO on 640×640 face crop and map boxes back to original frame."""
    if _models.yolo is None:
        return []

    crop_h, crop_w = face_crop.shape[:2]
    face_640 = cv2.resize(face_crop, (640, 640))
    cv2.imwrite("debug_face.jpg", face_640)

    results = _models.yolo(face_640, verbose=False, conf=conf)[0]
    sx = crop_w / 640.0
    sy = crop_h / 640.0

    detections = []
    for box in results.boxes:
        bx1, by1, bx2, by2 = map(int, box.xyxy[0].tolist())
        confidence = float(box.conf[0])
        cls_id     = int(box.cls[0])
        label      = results.names.get(cls_id, str(cls_id))

        # 640-space → crop-space → original-frame-space
        ox1 = max(0,      orig_x1 + int(bx1 * sx))
        oy1 = max(0,      orig_y1 + int(by1 * sy))
        ox2 = min(orig_w, orig_x1 + int(bx2 * sx))
        oy2 = min(orig_h, orig_y1 + int(by2 * sy))

        if ox2 <= ox1 or oy2 <= oy1:
            continue

        detections.append({
            "label":      label,
            "confidence": round(confidence, 4),
            "box":        [ox1, oy1, ox2, oy2],
        })

    return detections


def _run_mobilenet(face_crop: np.ndarray) -> dict:
    """Run MobileNet skin-type + skin-concern classification on the face crop."""
    result: dict[str, Any] = {}

    face_rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)

    # Skin type
    if _models.skin_type_model and _models.skin_type_classes:
        try:
            shape = _models.skin_type_model.input_shape
            h, w  = (shape[1], shape[2]) if shape and len(shape) >= 3 else (224, 224)
            h, w  = h or 224, w or 224
            inp   = cv2.resize(face_rgb, (w, h)).astype(np.float32) / 255.0
            inp   = np.expand_dims(inp, 0)
            preds = _models.skin_type_model.predict(inp, verbose=0)[0]
            top   = np.argsort(preds)[-3:][::-1]
            result["skin_type"] = {
                "predictions": [
                    {"class": _models.skin_type_classes[i], "confidence": float(preds[i])}
                    for i in top
                ]
            }
        except Exception as e:
            result["skin_type"] = {"error": str(e)}

    # Skin concerns
    if _models.skin_concern_model and _models.skin_concern_classes:
        try:
            shape = _models.skin_concern_model.input_shape
            h, w  = (shape[1], shape[2]) if shape and len(shape) >= 3 else (224, 224)
            h, w  = h or 224, w or 224
            inp   = cv2.resize(face_rgb, (w, h)).astype(np.float32) / 255.0
            inp   = np.expand_dims(inp, 0)
            preds = _models.skin_concern_model.predict(inp, verbose=0)[0]
            top   = np.argsort(preds)[-3:][::-1]
            result["skin_concerns"] = {
                "predictions": [
                    {"class": _models.skin_concern_classes[i], "confidence": float(preds[i])}
                    for i in top
                ]
            }
        except Exception as e:
            result["skin_concerns"] = {"error": str(e)}

    return result


def _severity_from_count(n: int) -> str:
    if n == 0:   return "None"
    if n <= 2:   return "Mild"
    if n <= 6:   return "Moderate"
    return "Severe"


# ── Public API ────────────────────────────────────────────────────────────────

def analyze(image_input: bytes | np.ndarray, yolo_conf: float = 0.20) -> dict[str, Any]:
    """
    Full unified pipeline:
      MediaPipe → face crop → YOLO → MobileNet → merged result

    Args:
        image_input: raw bytes or BGR numpy array
        yolo_conf:   YOLO confidence threshold (default 0.20)

    Returns:
        {
          "status":        "success" | "no_face" | "error",
          "face_bbox":     [x1,y1,x2,y2] | None,
          "yolo": {
              "detections":     [{label, confidence, box}, ...],
              "concern_counts": {label: count},
              "top_concern":    str | None,
              "severity":       "None"|"Mild"|"Moderate"|"Severe",
          },
          "mobilenet": {
              "skin_type":     {predictions: [...]},
              "skin_concerns": {predictions: [...]},
          },
          "image_base64":  str,   # original image as JPEG base64
        }
    """
    _models.ensure_ready()

    # ── Decode input ──────────────────────────────────────────────────────────
    if isinstance(image_input, bytes):
        nparr     = np.frombuffer(image_input, np.uint8)
        image_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    else:
        image_bgr = image_input

    if image_bgr is None:
        return {"status": "error", "error": "Could not decode image"}

    img_h, img_w = image_bgr.shape[:2]

    # ── Step 1: MediaPipe face detection ──────────────────────────────────────
    face_result = _detect_face(image_bgr)
    if not face_result["face_present"]:
        print("[Pipeline] No face detected")
        _, buf = cv2.imencode(".jpg", image_bgr)
        return {
            "status":       "no_face",
            "error":        "No face detected. Please use a clear, well-lit photo.",
            "face_bbox":    None,
            "image_base64": base64.b64encode(buf).decode(),
        }

    fx1, fy1, fx2, fy2 = face_result["bbox"]
    print(f"[Pipeline] Face bbox: [{fx1},{fy1},{fx2},{fy2}]")

    # ── Step 2: Crop face ─────────────────────────────────────────────────────
    face_crop = image_bgr[fy1:fy2, fx1:fx2]
    if face_crop.size == 0:
        return {"status": "error", "error": "Face crop failed"}

    # ── Step 3: YOLO on face crop ─────────────────────────────────────────────
    yolo_detections = _run_yolo(face_crop, fx1, fy1, img_w, img_h, conf=yolo_conf)
    concern_counts: dict[str, int] = {}
    for d in yolo_detections:
        lbl = d["label"].lower()
        concern_counts[lbl] = concern_counts.get(lbl, 0) + 1

    top_concern = max(concern_counts, key=concern_counts.get) if concern_counts else None
    severity    = _severity_from_count(len(yolo_detections))
    print(f"[Pipeline] YOLO: {len(yolo_detections)} detections, severity={severity}")

    # ── Step 4: MobileNet on face crop ────────────────────────────────────────
    mobilenet_result = _run_mobilenet(face_crop)
    print(f"[Pipeline] MobileNet done")

    # ── Step 5: Encode original image for display ─────────────────────────────
    _, buf = cv2.imencode(".jpg", image_bgr)
    image_b64 = base64.b64encode(buf).decode()

    return {
        "status":    "success",
        "face_bbox": [fx1, fy1, fx2, fy2],
        "yolo": {
            "detections":     yolo_detections,
            "concern_counts": concern_counts,
            "top_concern":    top_concern,
            "severity":       severity,
            "total_regions":  len(yolo_detections),
        },
        "mobilenet":    mobilenet_result,
        "image_base64": image_b64,
    }
