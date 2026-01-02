"""
Simple test script to verify face detection (without TensorFlow models).
"""
import cv2
import mediapipe as mp
import numpy as np

print("=" * 60)
print("Testing Face Detection (MediaPipe Only)")
print("=" * 60)

# Initialize MediaPipe
print("\n1. Initializing MediaPipe FaceDetection...")
try:
    mp_face_detection = mp.solutions.face_detection
    face_detector = mp_face_detection.FaceDetection(
        model_selection=1,
        min_detection_confidence=0.6
    )
    print("   [OK] MediaPipe FaceDetection initialized")
except Exception as e:
    print(f"   [ERROR] Failed: {e}")
    exit(1)

print("\n2. Initializing MediaPipe FaceMesh...")
try:
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.6
    )
    print("   [OK] MediaPipe FaceMesh initialized")
except Exception as e:
    print(f"   [ERROR] Failed: {e}")
    exit(1)

# Load test image
print("\n3. Loading test image...")
choice = input("   [a] Webcam or [b] File path? ").strip().lower()

if choice == 'a':
    print("   Opening webcam... Press SPACE to capture")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("   [ERROR] Could not open webcam")
        exit(1)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        cv2.imshow('Press SPACE to capture', frame)
        
        key = cv2.waitKey(1)
        if key == 27:  # ESC
            cap.release()
            cv2.destroyAllWindows()
            exit(0)
        elif key == 32:  # SPACE
            image_bgr = frame
            cap.release()
            cv2.destroyAllWindows()
            break
else:
    path = input("   Enter image path: ").strip()
    image_bgr = cv2.imread(path)
    if image_bgr is None:
        print(f"   [ERROR] Failed to load: {path}")
        exit(1)

print(f"   [OK] Image loaded: {image_bgr.shape}")

# Test face detection
print("\n4. Testing face detection...")
h, w, _ = image_bgr.shape
rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
results = face_detector.process(rgb)

if not results.detections:
    print("   [ERROR] No face detected")
    exit(1)

if len(results.detections) > 1:
    print(f"   [WARNING] Multiple faces detected: {len(results.detections)}")
else:
    print("   [OK] One face detected")

detection = results.detections[0]
confidence = detection.score[0]
print(f"   Confidence: {confidence:.2%}")

# Crop face
print("\n5. Cropping face...")
bbox = detection.location_data.relative_bounding_box
x = int(bbox.xmin * w)
y = int(bbox.ymin * h)
width = int(bbox.width * w)
height = int(bbox.height * h)

x = max(0, x)
y = max(0, y)
width = min(w - x, width)
height = min(h - y, height)

face_crop = image_bgr[y:y+height, x:x+width]
print(f"   [OK] Face cropped: {face_crop.shape}")

# Show result
print("\n6. Displaying result...")
cv2.imshow('Cropped Face - Press any key to close', face_crop)
cv2.waitKey(0)
cv2.destroyAllWindows()

print("\n" + "=" * 60)
print("[SUCCESS] Face Detection Test Complete!")
print("=" * 60)
print("\nNext step: The cropped face will be:")
print("  1. Converted BGR -> RGB")
print("  2. Resized to 224x224")
print("  3. Normalized (division by 255)")
print("  4. Fed to CNN for prediction")
