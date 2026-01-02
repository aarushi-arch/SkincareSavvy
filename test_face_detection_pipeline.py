"""
Test script to verify face detection preprocessing pipeline.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SkincareSavvy.settings')
django.setup()

import cv2
import numpy as np
from face_analysis.services.cnn import FaceAnalysisPipeline

def test_preprocessing():
    """Test the face detection and preprocessing pipeline."""
    
    print("=" * 60)
    print("Testing Face Detection Preprocessing Pipeline")
    print("=" * 60)
    
    # Initialize pipeline
    print("\n1. Initializing pipeline...")
    pipeline = FaceAnalysisPipeline()
    
    # Create a test image (you can replace this with an actual image path)
    print("\n2. Attempting to load test image...")
    
    # Option 1: Use webcam to capture an image
    print("   Would you like to:")
    print("   a) Capture from webcam")
    print("   b) Use an existing image file")
    
    choice = input("   Enter choice (a/b): ").strip().lower()
    
    if choice == 'a':
        print("   Opening webcam...")
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("   ❌ Could not open webcam")
            return
        
        print("   Press SPACE to capture, ESC to cancel")
        while True:
            ret, frame = cap.read()
            if not ret:
                print("   ❌ Failed to grab frame")
                break
            
            cv2.imshow('Webcam - Press SPACE to capture', frame)
            
            key = cv2.waitKey(1)
            if key == 27:  # ESC
                print("   Cancelled")
                cap.release()
                cv2.destroyAllWindows()
                return
            elif key == 32:  # SPACE
                image_bgr = frame
                cap.release()
                cv2.destroyAllWindows()
                break
    else:
        image_path = input("   Enter image path: ").strip()
        if not os.path.exists(image_path):
            print(f"   ❌ Image not found: {image_path}")
            return
        
        image_bgr = cv2.imread(image_path)
        if image_bgr is None:
            print(f"   ❌ Failed to load image: {image_path}")
            return
    
    print(f"   ✅ Image loaded: {image_bgr.shape}")
    
    # Test preprocessing
    print("\n3. Testing preprocessing pipeline...")
    print("-" * 60)
    
    face_crop, status_message = pipeline.skincare_preprocess(image_bgr)
    
    print("-" * 60)
    
    if face_crop is None:
        print(f"\n❌ Preprocessing failed: {status_message}")
        return
    
    print(f"\n✅ Preprocessing successful!")
    print(f"   Status: {status_message}")
    print(f"   Cropped face shape: {face_crop.shape}")
    
    # Display result
    print("\n4. Displaying cropped face...")
    cv2.imshow('Cropped Face (Press any key to close)', face_crop)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    print("\n" + "=" * 60)
    print("✅ Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_preprocessing()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
