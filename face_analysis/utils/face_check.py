"""
Lightweight MediaPipe face presence check.
Initialized once at module load — reused across all requests.
"""
import cv2
import mediapipe as mp

_mp_face = mp.solutions.face_detection

# model_selection=0 → short-range (webcam/selfie), faster than model 1
_detector = _mp_face.FaceDetection(
    model_selection=0,
    min_detection_confidence=0.5,
)


def is_face_present(frame_bgr) -> bool:
    """Return True if at least one face is detected in the BGR frame."""
    # Resize to 640×480 before detection for consistent speed
    small = cv2.resize(frame_bgr, (640, 480))
    rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
    results = _detector.process(rgb)
    return bool(results.detections)
