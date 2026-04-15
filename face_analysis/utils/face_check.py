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
    min_detection_confidence=0.3,   # lower threshold — webcam frames can be blurry
)


def detect_face(frame_bgr):
    """
    Run MediaPipe face detection on a BGR frame.

    Returns:
        {
            "face_present": bool,
            "bbox": [x1, y1, x2, y2] | None   # pixel coords in original frame
        }
    """
    h, w = frame_bgr.shape[:2]

    # Use the frame as-is — no downscale, keep as much detail as possible
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    results = _detector.process(rgb)

    if not results.detections:
        return {"face_present": False, "bbox": None}

    # Take the highest-confidence detection
    best = max(results.detections, key=lambda d: d.score[0])
    rel  = best.location_data.relative_bounding_box

    x1 = max(0, int(rel.xmin * w))
    y1 = max(0, int(rel.ymin * h))
    x2 = min(w, int((rel.xmin + rel.width)  * w))
    y2 = min(h, int((rel.ymin + rel.height) * h))

    return {"face_present": True, "bbox": [x1, y1, x2, y2]}


def is_face_present(frame_bgr) -> bool:
    """Return True if at least one face is detected in the BGR frame."""
    return detect_face(frame_bgr)["face_present"]
