"""
YOLO + MobileNet pipeline.

Flow:
  image bytes
    → YOLO detects skin concern regions (acne, blackheads, etc.)
    → each detected crop is passed to the existing MobileNet CNN
    → results merged and returned
"""
from __future__ import annotations

import base64
from typing import Any

import cv2
import numpy as np

from face_analysis.services.cnn import FaceAnalysisPipeline


class YOLOAnalysisPipeline:
    """
    Wraps YOLO detection + MobileNet classification.
    YOLO model is loaded lazily from the database on first use.
    """

    def __init__(self) -> None:
        self.yolo_model = None
        self._yolo_loaded = False
        # Reuse the existing CNN pipeline for MobileNet inference
        self.cnn = FaceAnalysisPipeline()

    # ── Model loading ────────────────────────────────────────────────────────

    def _load_yolo(self) -> None:
        """Load the active YOLO model from the database."""
        if self._yolo_loaded:
            return

        try:
            from ultralytics import YOLO
            from face_analysis.models import YOLOModel

            record = YOLOModel.objects.filter(is_active=True).first()
            if record and record.model_file:
                self.yolo_model = YOLO(record.model_file.path)
                print(f"[YOLO] Loaded model: {record.name}")
            else:
                # Fall back to YOLOv8n if no model uploaded yet
                print("[YOLO] No active model in DB — falling back to yolov8n")
                self.yolo_model = YOLO("yolov8n.pt")
        except ImportError:
            print("[YOLO] ultralytics not installed. Run: pip install ultralytics")
        except Exception as e:
            print(f"[YOLO] Model load error: {e}")

        self._yolo_loaded = True

    def reload(self) -> None:
        """Force reload of YOLO model (call after uploading a new model)."""
        self._yolo_loaded = False
        self.yolo_model = None
        self._load_yolo()

    # ── Fast real-time detection (YOLO only, no MobileNet) ───────────────────

    def detect_only(self, image_bgr: np.ndarray, conf_threshold: float = 0.20) -> dict[str, Any]:
        """
        MediaPipe face gate → crop face → resize → YOLO on face crop.
        Returns face_bbox (original coords) + YOLO concern boxes (mapped back).
        """
        self._load_yolo()

        if self.yolo_model is None:
            return {
                "error": "No active YOLO model. Upload a .pt file in Django Admin → YOLO Models.",
                "yolo_available": False,
            }

        # ── Step 1: MediaPipe face detection ─────────────────────────────────
        from face_analysis.utils.face_check import detect_face
        face_result = detect_face(image_bgr)

        if not face_result["face_present"]:
            print("[YOLO] No face detected — skipping YOLO inference")
            return {
                "status": "no_face",
                "message": "No face detected",
                "face_bbox": None,
                "yolo_available": True,
                "detections": [],
                "summary": {"concern_counts": {}, "top_concern": None, "total_regions": 0},
            }

        fx1, fy1, fx2, fy2 = face_result["bbox"]
        print(f"[MediaPipe] Face bbox: [{fx1},{fy1},{fx2},{fy2}]")

        # ── Step 2: Add margin + clamp to frame bounds ────────────────────────
        img_h, img_w = image_bgr.shape[:2]
        MARGIN = 30   # px — gives YOLO room around face edges
        fx1 = max(0,     fx1 - MARGIN)
        fy1 = max(0,     fy1 - MARGIN)
        fx2 = min(img_w, fx2 + MARGIN)
        fy2 = min(img_h, fy2 + MARGIN)

        # ── Step 3: Crop face region ──────────────────────────────────────────
        face_crop = image_bgr[fy1:fy2, fx1:fx2]
        if face_crop.size == 0:
            print("[YOLO] Face crop is empty — skipping")
            return {
                "status": "no_face",
                "message": "Face crop failed",
                "face_bbox": [fx1, fy1, fx2, fy2],
                "yolo_available": True,
                "detections": [],
                "summary": {"concern_counts": {}, "top_concern": None, "total_regions": 0},
            }

        # ── Step 4: Resize crop to 640×640 for YOLO ──────────────────────────
        face_640 = cv2.resize(face_crop, (640, 640))
        cv2.imwrite("debug_face.jpg", face_640)
        print(f"[YOLO] Crop {face_crop.shape} → 640×640, conf={conf_threshold}")

        # ── Step 5: YOLO on face crop ─────────────────────────────────────────
        results = self.yolo_model(face_640, verbose=False, conf=conf_threshold)[0]
        print(f"[YOLO] Boxes on face crop: {len(results.boxes)}")

        # Scale factors: 640-space → crop-space → original-frame-space
        crop_h, crop_w = face_crop.shape[:2]
        scale_x = crop_w / 640.0
        scale_y = crop_h / 640.0

        detections = []
        concern_counts: dict[str, int] = {}

        for box in results.boxes:
            bx1, by1, bx2, by2 = map(int, box.xyxy[0].tolist())
            conf   = float(box.conf[0])
            cls_id = int(box.cls[0])
            label  = results.names.get(cls_id, str(cls_id))

            # 640-space → crop-space
            bx1 = int(bx1 * scale_x)
            by1 = int(by1 * scale_y)
            bx2 = int(bx2 * scale_x)
            by2 = int(by2 * scale_y)

            # crop-space → original frame-space
            ox1 = max(0,     fx1 + bx1)
            oy1 = max(0,     fy1 + by1)
            ox2 = min(img_w, fx1 + bx2)
            oy2 = min(img_h, fy1 + by2)

            if ox2 <= ox1 or oy2 <= oy1:
                continue

            detections.append({
                "label":      label,
                "confidence": round(conf, 4),
                "box":        [ox1, oy1, ox2, oy2],
            })
            lbl = label.lower()
            concern_counts[lbl] = concern_counts.get(lbl, 0) + 1

        top_concern = max(concern_counts, key=concern_counts.get) if concern_counts else None

        return {
            "status":         "success",
            "yolo_available": True,
            "face_bbox":      [fx1, fy1, fx2, fy2],
            "detections":     detections,
            "summary": {
                "concern_counts": concern_counts,
                "top_concern":    top_concern,
                "total_regions":  len(detections),
            },
        }

    # ── Detection helpers ────────────────────────────────────────────────────

    def detect_regions(self, image_bgr: np.ndarray) -> list[dict]:
        """
        Run YOLO on the full image and return detected bounding boxes.

        Returns list of:
            {
                "label": str,
                "confidence": float,
                "box": [x1, y1, x2, y2],   # pixel coords
                "crop": np.ndarray,          # BGR crop
            }
        """
        if self.yolo_model is None:
            return []

        results = self.yolo_model(image_bgr, verbose=False)[0]
        detections = []

        h, w = image_bgr.shape[:2]

        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            label = results.names.get(cls_id, str(cls_id))

            # Clamp to image bounds
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            crop = image_bgr[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            detections.append({
                "label": label,
                "confidence": round(conf, 4),
                "box": [x1, y1, x2, y2],
                "crop": crop,
            })

        return detections

    def _crop_to_b64(self, crop: np.ndarray) -> str:
        """Encode a BGR crop to base64 JPEG string for frontend display."""
        _, buf = cv2.imencode(".jpg", crop)
        return base64.b64encode(buf).decode("utf-8")

    # ── Main entry point ─────────────────────────────────────────────────────

    def analyze(self, image_bytes: bytes | np.ndarray) -> dict[str, Any]:
        """
        Full pipeline: YOLO detect → crop → MobileNet classify each crop.

        Returns:
        {
            "yolo_available": bool,
            "detections": [
                {
                    "label": str,           # YOLO class name
                    "yolo_confidence": float,
                    "box": [x1,y1,x2,y2],
                    "crop_b64": str,        # base64 JPEG of the crop
                    "cnn": {                # MobileNet result on this crop
                        "skin_type": {...},
                        "skin_concerns": {...},
                    }
                },
                ...
            ],
            "summary": {
                "concern_counts": {"acne": 3, "blackheads": 1, ...},
                "top_concern": str | None,
                "total_regions": int,
            },
            "annotated_b64": str,   # full image with YOLO boxes drawn
        }
        """
        self._load_yolo()
        self.cnn.load_models_from_db()

        # Decode input
        if isinstance(image_bytes, bytes):
            nparr = np.frombuffer(image_bytes, np.uint8)
            image_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            image_bgr = image_bytes

        if image_bgr is None:
            return {"error": "Invalid image format"}

        if self.yolo_model is None:
            return {
                "error": "No active YOLO model. Upload a .pt file in Django Admin → YOLO Models.",
                "yolo_available": False,
            }

        # ── Step 1: YOLO detection ───────────────────────────────────────────
        detections = self.detect_regions(image_bgr)

        # ── Step 2: MobileNet on each crop ───────────────────────────────────
        annotated = image_bgr.copy()
        results_out = []
        concern_counts: dict[str, int] = {}

        for det in detections:
            crop_bgr = det["crop"]
            x1, y1, x2, y2 = det["box"]

            # Run CNN on this crop (pass as ndarray — analyze() accepts it)
            cnn_result = self.cnn.analyze(crop_bgr)

            # Strip heavy image_base64 from nested result to keep response lean
            cnn_result.pop("image_base64", None)
            cnn_result.pop("face_bbox", None)

            # Tally concern labels from YOLO
            lbl = det["label"].lower()
            concern_counts[lbl] = concern_counts.get(lbl, 0) + 1

            # Draw annotated box on full image
            color = (0, 255, 100)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                annotated,
                f"{det['label']} {det['confidence']:.0%}",
                (x1, max(y1 - 6, 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2,
            )

            results_out.append({
                "label": det["label"],
                "yolo_confidence": det["confidence"],
                "box": det["box"],
                "crop_b64": self._crop_to_b64(crop_bgr),
                "cnn": cnn_result,
            })

        # ── Step 3: Build summary ────────────────────────────────────────────
        top_concern = max(concern_counts, key=concern_counts.get) if concern_counts else None

        _, buf = cv2.imencode(".jpg", annotated)
        annotated_b64 = base64.b64encode(buf).decode("utf-8")

        return {
            "yolo_available": True,
            "detections": results_out,
            "summary": {
                "concern_counts": concern_counts,
                "top_concern": top_concern,
                "total_regions": len(results_out),
            },
            "annotated_b64": annotated_b64,
        }
