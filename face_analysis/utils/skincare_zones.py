"""
MediaPipe FaceMesh zone overlay.
Maps product categories to facial zones and draws coloured blobs.
"""
from __future__ import annotations
import cv2
import numpy as np

try:
    import mediapipe as mp
    _face_mesh = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True, max_num_faces=1, refine_landmarks=True,
        min_detection_confidence=0.5,
    )
    _AVAILABLE = True
except Exception:
    _face_mesh = None
    _AVAILABLE = False

# ── Landmark index groups ─────────────────────────────────────────────────────
_ZONES = {
    "eye care": {
        "left":  [33, 133, 160, 159, 158, 157, 173, 144, 145, 153],
        "right": [362, 385, 387, 263, 373, 380, 398, 384, 381, 382],
        "color": (0, 220, 120),   # green
        "label": "Eye Care",
    },
    "moisturiser": {
        "full": [10, 338, 297, 332, 284, 251, 389, 356, 454, 323,
                 361, 288, 397, 365, 379, 378, 400, 377, 152, 148,
                 176, 149, 150, 136, 172, 58, 132, 93, 234, 127,
                 162, 21, 54, 103, 67, 109],
        "color": (100, 200, 255),
        "label": "Moisturiser",
    },
    "serum": {
        "left_cheek":  [50, 123, 117, 111, 187, 205, 36, 142],
        "right_cheek": [280, 352, 345, 340, 411, 425, 266, 371],
        "color": (180, 100, 255),
        "label": "Serum",
    },
    "sunscreen": {
        "full": [10, 338, 297, 332, 284, 251, 389, 356, 454, 323,
                 361, 288, 397, 365, 379, 378, 400, 377, 152, 148,
                 176, 149, 150, 136, 172, 58, 132, 93, 234, 127,
                 162, 21, 54, 103, 67, 109],
        "color": (0, 200, 255),
        "label": "Sunscreen",
    },
    "cleanser": {
        "full": [10, 338, 297, 332, 284, 251, 389, 356, 454, 323,
                 361, 288, 397, 365, 379, 378, 400, 377, 152, 148,
                 176, 149, 150, 136, 172, 58, 132, 93, 234, 127,
                 162, 21, 54, 103, 67, 109],
        "color": (80, 180, 80),
        "label": "Cleanser",
    },
    "toner": {
        "forehead": [10, 151, 9, 8, 107, 55, 285, 336],
        "color": (255, 180, 50),
        "label": "Toner",
    },
    "mask": {
        "full": [10, 338, 297, 332, 284, 251, 389, 356, 454, 323,
                 361, 288, 397, 365, 379, 378, 400, 377, 152, 148,
                 176, 149, 150, 136, 172, 58, 132, 93, 234, 127,
                 162, 21, 54, 103, 67, 109],
        "color": (200, 80, 200),
        "label": "Mask",
    },
}

# Fallback for unknown categories — full face
_DEFAULT_ZONE = {
    "full": [10, 338, 297, 332, 284, 251, 389, 356, 454, 323,
             361, 288, 397, 365, 379, 378, 400, 377, 152, 148,
             176, 149, 150, 136, 172, 58, 132, 93, 234, 127,
             162, 21, 54, 103, 67, 109],
    "color": (0, 220, 120),
    "label": "Apply here",
}


def _pts(landmarks, indices: list[int], w: int, h: int) -> np.ndarray:
    return np.array(
        [(int(landmarks[i].x * w), int(landmarks[i].y * h)) for i in indices],
        dtype=np.int32,
    )


def _blob(img: np.ndarray, points: np.ndarray, color: tuple, label: str) -> None:
    if len(points) < 3:
        return
    overlay = img.copy()
    cv2.fillPoly(overlay, [points], color)
    cv2.addWeighted(overlay, 0.40, img, 0.60, 0, img)
    # Outline
    cv2.polylines(img, [points], True, color, 2, cv2.LINE_AA)
    # Label
    cx = int(points[:, 0].mean())
    cy = int(points[:, 1].mean())
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
    cv2.rectangle(img, (cx - tw//2 - 4, cy - th - 4), (cx + tw//2 + 4, cy + 4),
                  (0, 0, 0), -1)
    cv2.putText(img, label, (cx - tw//2, cy),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)


def draw_zone(image_bgr: np.ndarray, category: str) -> np.ndarray | None:
    """
    Run MediaPipe FaceMesh and draw the zone blob for the given product category.
    Returns annotated BGR image or None if no face detected.
    """
    if not _AVAILABLE or _face_mesh is None:
        return None

    h, w = image_bgr.shape[:2]
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    results = _face_mesh.process(rgb)

    if not results.multi_face_landmarks:
        return None

    lm = results.multi_face_landmarks[0].landmark
    out = image_bgr.copy()

    zone = _ZONES.get(category.lower().strip(), _DEFAULT_ZONE)
    color = zone["color"]
    label = zone["label"]

    # Draw each sub-region
    for key, indices in zone.items():
        if key in ("color", "label"):
            continue
        pts = _pts(lm, indices, w, h)
        _blob(out, pts, color, label)

    return out
