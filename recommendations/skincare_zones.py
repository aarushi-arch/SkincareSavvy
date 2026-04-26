"""
Skincare zone mapping using MediaPipe face landmarks.
Maps product categories to specific facial zones.
"""
import cv2
import mediapipe as mp
import numpy as np
import base64

mp_face_mesh = mp.solutions.face_mesh

# ---------- FACE ZONES ----------
LEFT_EYE = [33, 133, 160, 159, 158, 157]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]
LEFT_CHEEK = [50, 123, 117, 111, 187]
RIGHT_CHEEK = [280, 352, 345, 340, 411]
FOREHEAD = [10, 151, 9, 8, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162]
NOSE = [1, 2, 5, 4, 6, 168, 197, 195, 5, 4, 1, 19, 94, 2]
CHIN = [199, 175, 152, 377, 400, 378, 379, 365, 397, 288, 361, 323, 454, 356, 389, 251, 284, 332, 297, 338]
FULL_FACE = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]

# Category to zone mapping
CATEGORY_ZONE_MAP = {
    "eye care": [("LEFT_EYE", LEFT_EYE), ("RIGHT_EYE", RIGHT_EYE)],
    "eye cream": [("LEFT_EYE", LEFT_EYE), ("RIGHT_EYE", RIGHT_EYE)],
    "moisturizer": [("FULL_FACE", FULL_FACE)],
    "moisturiser": [("FULL_FACE", FULL_FACE)],
    "sunscreen": [("FULL_FACE", FULL_FACE)],
    "serum": [("LEFT_CHEEK", LEFT_CHEEK), ("RIGHT_CHEEK", RIGHT_CHEEK)],
    "face serum": [("LEFT_CHEEK", LEFT_CHEEK), ("RIGHT_CHEEK", RIGHT_CHEEK)],
    "spot treatment": [("NOSE", NOSE)],
    "acne treatment": [("NOSE", NOSE), ("FOREHEAD", FOREHEAD), ("CHIN", CHIN)],
    "cleanser": [("FULL_FACE", FULL_FACE)],
    "face wash": [("FULL_FACE", FULL_FACE)],
    "toner": [("FULL_FACE", FULL_FACE)],
    "mask": [("FULL_FACE", FULL_FACE)],
    "face mask": [("FULL_FACE", FULL_FACE)],
    "exfoliator": [("FULL_FACE", FULL_FACE)],
    "lip care": [("LIPS", [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291])],
    "lip balm": [("LIPS", [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291])],
}


def get_points(landmarks, indices, w, h):
    """Extract landmark points as numpy array."""
    return np.array(
        [(int(landmarks[i].x * w), int(landmarks[i].y * h)) for i in indices],
        dtype=np.int32
    )


def get_zones_for_category(category):
    """Get zone definitions for a product category."""
    category_lower = category.lower().strip()
    
    # Try exact match first
    if category_lower in CATEGORY_ZONE_MAP:
        return CATEGORY_ZONE_MAP[category_lower]
    
    # Try partial match
    for key, zones in CATEGORY_ZONE_MAP.items():
        if key in category_lower or category_lower in key:
            return zones
    
    # Default to full face
    return [("FULL_FACE", FULL_FACE)]


def apply_skincare_zones(image_bytes, category):
    """
    Apply skincare zones to an image based on product category.
    
    Args:
        image_bytes: Image as bytes
        category: Product category string
        
    Returns:
        dict with:
            - image_base64: Base64 encoded result image
            - zones: List of zone data (label, points)
            - error: Error message if failed
    """
    try:
        # Decode image
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return {"error": "Could not decode image"}
        
        h, w, _ = image.shape
        zones_data = []
        
        with mp_face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True
        ) as face_mesh:
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb)
            
            if not results.multi_face_landmarks:
                return {"error": "No face detected in the image"}
            
            landmarks = results.multi_face_landmarks[0].landmark
            
            # Get zones for this category
            zones = get_zones_for_category(category)
            
            # Draw each zone
            for zone_label, zone_indices in zones:
                points = get_points(landmarks, zone_indices, w, h)
                
                # Draw semi-transparent green overlay
                overlay = image.copy()
                cv2.fillPoly(overlay, [points], (0, 255, 0))
                image = cv2.addWeighted(overlay, 0.35, image, 0.65, 0)
                
                # Store zone data for frontend
                zones_data.append({
                    "label": zone_label.replace("_", " ").title(),
                    "points": points.tolist()
                })
        
        # Encode result as base64
        _, buffer = cv2.imencode('.jpg', image)
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return {
            "image_base64": image_base64,
            "zones": zones_data
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"Failed to process image: {str(e)}"}
