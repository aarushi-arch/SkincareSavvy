
import os
import sys
import django
import cv2
import numpy as np

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SkincareSavvy.settings')
django.setup()

from face_analysis.services.cnn import FaceAnalysisPipeline

def run_test():
    print("Initializing pipeline...")
    pipeline = FaceAnalysisPipeline()
    
    # Use the debug image if it exists, otherwise create a dummy
    image_path = "debug_cropped.jpg"
    if os.path.exists(image_path):
        print(f"Loading image from {image_path}")
        image_bgr = cv2.imread(image_path)
    else:
        print("Creating dummy image")
        image_bgr = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    
    print("Running analysis...")
    try:
        result = pipeline.analyze(image_bgr)
        if "error" in result:
            print(f"Analysis returned error: {result['error']}")
        else:
            print("Analysis successful!")
            print(f"Skin type: {result.get('skin_type')}")
            print(f"Detected concerns: {result.get('detected_concerns_from_heatmap')}")
    except Exception as e:
        print(f"Analysis failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_test()
