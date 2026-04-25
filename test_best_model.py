"""
Test best_model.pt — verifies the active YOLO model loads and runs inference.

Usage:
    python test_best_model.py                          # uses default dataset image
    python test_best_model.py --image path/to/img.jpg  # your own image
    python test_best_model.py --image path/to/img.jpg --conf 0.15
"""
import os
import sys
import argparse
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SkincareSavvy.settings")
django.setup()

import cv2
import numpy as np
from pathlib import Path


def run(image_path: str, conf: float) -> None:
    # ── 1. Load model from DB ─────────────────────────────────────────────────
    print("=" * 60)
    print("STEP 1: Loading active YOLO model from DB")
    from face_analysis.models import YOLOModel
    from ultralytics import YOLO

    record = YOLOModel.objects.filter(is_active=True).first()
    if not record:
        print("  ERROR: No active YOLO model found in DB.")
        print("  → Go to Django Admin → YOLO Models and set one as active.")
        return

    model_path = Path(record.model_file.path)
    print(f"  Name : {record.name}")
    print(f"  File : {model_path}")
    print(f"  Exists: {model_path.exists()}")

    if not model_path.exists():
        print("  ERROR: Model file not found on disk.")
        return

    try:
        model = YOLO(str(model_path))
        print(f"  Loaded OK — task: {model.task}")
        print(f"  Classes: {model.names}")
    except Exception as e:
        print(f"  ERROR loading model: {e}")
        return

    # ── 2. Load test image ────────────────────────────────────────────────────
    print()
    print("STEP 2: Loading test image")

    if not image_path:
        # Fall back to a dataset image
        fallback = Path("face_analysis/datasets/skin_concerns/test/acne")
        if fallback.exists():
            imgs = list(fallback.glob("*.jpg"))
            if imgs:
                image_path = str(imgs[0])
        if not image_path:
            # Try any jpg in root
            jpgs = list(Path(".").glob("*.jpg"))
            image_path = str(jpgs[0]) if jpgs else None

    if not image_path or not Path(image_path).exists():
        print("  ERROR: No test image found. Pass --image path/to/image.jpg")
        return

    img = cv2.imread(image_path)
    if img is None:
        print(f"  ERROR: Could not read {image_path}")
        return

    print(f"  Image : {image_path}")
    print(f"  Shape : {img.shape}")

    # ── 3. MediaPipe face detection ───────────────────────────────────────────
    print()
    print("STEP 3: MediaPipe face detection")
    from face_analysis.utils.face_check import detect_face

    face_result = detect_face(img)
    print(f"  Face present : {face_result['face_present']}")
    print(f"  Face bbox    : {face_result['bbox']}")

    if not face_result["face_present"]:
        print("  WARNING: No face detected — running YOLO on full image anyway")
        face_crop = img
        fx1, fy1 = 0, 0
    else:
        fx1, fy1, fx2, fy2 = face_result["bbox"]
        PAD = 30
        h, w = img.shape[:2]
        fx1 = max(0, fx1 - PAD); fy1 = max(0, fy1 - PAD)
        fx2 = min(w, fx2 + PAD); fy2 = min(h, fy2 + PAD)
        face_crop = img[fy1:fy2, fx1:fx2]
        print(f"  Crop shape   : {face_crop.shape}")

    # ── 4. YOLO inference on face crop ────────────────────────────────────────
    print()
    print(f"STEP 4: YOLO inference (conf={conf})")

    face_640 = cv2.resize(face_crop, (640, 640))
    results = model(face_640, verbose=False, conf=conf)[0]

    print(f"  Boxes detected : {len(results.boxes)}")

    if len(results.boxes) == 0:
        print("  No detections. Try lowering --conf (e.g. --conf 0.10)")
    else:
        crop_h, crop_w = face_crop.shape[:2]
        sx, sy = crop_w / 640.0, crop_h / 640.0

        for i, box in enumerate(results.boxes):
            bx1, by1, bx2, by2 = map(int, box.xyxy[0].tolist())
            conf_val = float(box.conf[0])
            cls_id   = int(box.cls[0])
            label    = results.names.get(cls_id, str(cls_id))

            # Map back to original frame
            ox1 = fx1 + int(bx1 * sx)
            oy1 = fy1 + int(by1 * sy)
            ox2 = fx1 + int(bx2 * sx)
            oy2 = fy1 + int(by2 * sy)

            print(f"  [{i+1}] {label:20s}  conf={conf_val:.3f}  box=[{ox1},{oy1},{ox2},{oy2}]")

            # Draw on original image
            cv2.rectangle(img, (ox1, oy1), (ox2, oy2), (0, 200, 80), 2)
            cv2.putText(img, f"{label} {conf_val:.2f}",
                        (ox1, max(oy1 - 6, 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 80), 2)

    # Draw face bbox
    if face_result["face_present"]:
        cv2.rectangle(img, (fx1, fy1), (fx2, fy2), (0, 229, 255), 2)

    # ── 5. Save output ────────────────────────────────────────────────────────
    out_path = "test_best_model_output.jpg"
    cv2.imwrite(out_path, img)
    print()
    print(f"STEP 5: Output saved → {out_path}")
    print("=" * 60)
    print(f"SUMMARY: {len(results.boxes)} detection(s) with model '{record.name}'")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test best_model.pt YOLO model")
    parser.add_argument("--image", type=str, default=None, help="Path to test image")
    parser.add_argument("--conf",  type=float, default=0.20, help="Confidence threshold (default 0.20)")
    args = parser.parse_args()
    run(args.image, args.conf)
