import os
import sys
import django
from django.conf import settings

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SkincareSavvy.settings")
django.setup()

import numpy as np
import cv2
from face_analysis.services.cnn import FaceAnalysisPipeline

def verify():
    pipeline = FaceAnalysisPipeline()
    
    # Path to a sample image
    # Using one found in datasets
    # Adjust path if needed
    image_path = r"face_analysis\datasets\skin_types\validation\oily\oily_f957ae954a160ea5081d_jpg.rf.d241c93c139a8a739f6706147411ef9e.jpg"
    
    if not os.path.exists(image_path):
        print(f"Image not found at {image_path}")
        # Try finding any jpg recursively if this specific one fails?
        # For now assume it exists based on search results
        return

    print(f"Testing with image: {image_path}")
    
    with open(image_path, "rb") as f:
        image_bytes = f.read()
        
    # Test 1: Detect and Crop
    print("\n--- Testing detect_and_crop_face ---")
    
    # Manually decode to BGR for this specific test
    nparr = np.frombuffer(image_bytes, np.uint8)
    image_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    cropped_bgr = pipeline.detect_and_crop_face(image_bgr)
    
    if cropped_bgr is not None:
        print(f"Cropped shape: {cropped_bgr.shape}")
        cv2.imwrite("debug_cropped.jpg", cropped_bgr) # Save as BGR directly
        print("Saved debug_cropped.jpg")
    else:
        print("Detection failed (returned None).")
    
    # Test 2: Full Analyze
    print("\n--- Testing analyze ---")
    try:
        result = pipeline.analyze(image_bytes)
        print("Analysis successful!")
        print("Keys:", result.keys())
        if "skin_type" in result:
             print("Skin Type:", result["skin_type"])
        if "skin_concerns" in result:
             print("Skin Concerns keys:", result["skin_concerns"].keys())
             if "predictions" in result["skin_concerns"]:
                 preds = result["skin_concerns"]["predictions"]
                 print(f"Num predictions: {len(preds)}")
                 if preds and "heatmap" in preds[0]:
                     print("Heatmap present in top prediction.")
    except Exception as e:
        print(f"Analysis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify()
