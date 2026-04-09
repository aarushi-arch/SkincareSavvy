import os
import sys
import django
import cv2
import numpy as np

# 1. Initialize Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SkincareSavvy.settings')
django.setup()

from face_analysis.services.yolo_pipeline import YOLOAnalysisPipeline

def run_test(image_path=None):
    print("--- YOLO Test Initialization ---")
    pipeline = YOLOAnalysisPipeline()

    # Accept either:
    #   python test_yolo.py image.jpg
    #   python test_yolo.py --image image.jpg
    if image_path is None:
        if len(sys.argv) > 2 and sys.argv[1] == '--image':
            image_path = sys.argv[2]
        elif len(sys.argv) > 1 and not sys.argv[1].startswith('--'):
            image_path = sys.argv[1]
        else:
            image_path = 'face_analysis/datasets/skin_concerns/test/acne/0_before_jpg.rf.db1b0102231c11d9d92d42a9a13c6ffb.jpg'
            print(f"No image path given — using default: {image_path}")
            print("Usage: python test_yolo.py path/to/your/image.jpg")

    if not os.path.exists(image_path):
        print(f"Error: File not found: {image_path}")
        return

    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not read {image_path}")
        return

    print(f"Running YOLO detection on: {image_path}")
    results = pipeline.detect_only(img, conf_threshold=0.10)

    if "error" in results:
        print(f"Pipeline Error: {results['error']}")
    else:
        detections = results.get('detections', [])
        print(f"Result: Found {len(detections)} regions.")

        if detections:
            print("Annotating image...")
            for i, det in enumerate(detections):
                x1, y1, x2, y2 = det["box"]
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label_text = f"{det['label']} {det['confidence']:.2f}"
                cv2.putText(img, label_text, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                print(f"  [{i}] {det['label']} - Confidence: {det['confidence']:.2f}")

            # Output filename mirrors the input so each test produces a unique file
            base = os.path.splitext(os.path.basename(image_path))[0]
            output_file = f"test_result_{base}.jpg"
            cv2.imwrite(output_file, img)
            print(f"--- SUCCESS: Saved to {output_file} ---")
        else:
            print("No regions found. Try an image with clearer skin concerns.")

    print("--- Test Complete ---")

if __name__ == "__main__":
    run_test()
