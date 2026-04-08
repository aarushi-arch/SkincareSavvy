import os
import django
import cv2
import numpy as np

# 1. Initialize Django
# Make sure the settings module matches your project name
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SkincareSavvy.settings')
django.setup()

from face_analysis.services.yolo_pipeline import YOLOAnalysisPipeline

def run_test():
    print("--- YOLO Test Initialization ---")
    pipeline = YOLOAnalysisPipeline()
    
    # Try to load a sample image (you can change this path)
    # Path to a specific acne image from your project dataset
    image_path = 'face_analysis/datasets/skin_concerns/test/acne/0_before_jpg.rf.db1b0102231c11d9d92d42a9a13c6ffb.jpg'
    
    if not os.path.exists(image_path):
        print(f"Checking for fallback images...")
        jpgs = [f for f in os.listdir('.') if f.lower().endswith('.jpg')]
        if jpgs:
            image_path = jpgs[0]
            print(f"Using image found in root: {image_path}")
        else:
            print("No .jpg images found in the root directory to test with.")
            return

    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not read {image_path}")
        return

    print(f"Running YOLO detection on {image_path}...")
    # Lowering confidence threshold to 0.10 to catch more potential detections
    results = pipeline.detect_only(img, conf_threshold=0.10)
    
    if "error" in results:
        print(f"Pipeline Error: {results['error']}")
    else:
        detections = results.get('detections', [])
        print(f"Result: Found {len(detections)} regions using threshold 0.10.")
        
        if detections:
            print("Annotating image...")
            for i, det in enumerate(detections):
                x1, y1, x2, y2 = det["box"]
                # Draw green box
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                # Draw label
                label_text = f"{det['label']} {det['confidence']:.2f}"
                cv2.putText(img, label_text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                print(f"  [{i}] {det['label']} - Confidence: {det['confidence']:.2f}")
            
            output_file = "test_result_visual.jpg"
            cv2.imwrite(output_file, img)
            print(f"--- SUCCESS: View the results in {output_file} ---")
        else:
            print("No regions found even with 0.10 threshold. Try an image with clearer skin concerns.")
    
    print("--- Test Complete ---")

if __name__ == "__main__":
    run_test()
