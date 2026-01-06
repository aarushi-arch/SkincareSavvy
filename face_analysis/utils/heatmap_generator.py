import cv2
import numpy as np
import base64
from io import BytesIO
import datetime


try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False


def generate_facial_mesh_with_problem_areas(original_image, heatmap, threshold=0.6, 
                                            mesh_color=(200, 200, 200), 
                                            problem_color=(80, 80, 220),
                                            mesh_thickness=1,
                                            problem_thickness=2):
    """
    Generate a facial mesh overlay with highlighted problem areas based on heatmap.
    Similar to the reference image with white mesh lines and red problem indicators.
    
    Args:
        original_image: Original face image (numpy array, RGB)
        heatmap: Attention/activation map from the model (numpy array)
        threshold: Threshold for problem areas (0-1)
        mesh_color: Color for normal mesh lines (BGR format) - default light gray
        problem_color: Color for problem area indicators (BGR format) - default red
        mesh_thickness: Thickness of mesh lines
        problem_thickness: Thickness of problem area lines
    
    Returns:
        Image with facial mesh overlay and problem area indicators
    """
    if not MEDIAPIPE_AVAILABLE:
        print("MediaPipe not available. Falling back to simplified mesh overlay.")
        return generate_simplified_mesh_overlay(original_image, heatmap, threshold, mesh_color, problem_color)
    
    # Initialize MediaPipe Face Mesh
    mp_face_mesh = mp.solutions.face_mesh
    
    # Ensure original image is RGB for MediaPipe
    if len(original_image.shape) == 2:
        original_image = cv2.cvtColor(original_image, cv2.COLOR_GRAY2RGB)
    elif original_image.shape[2] == 4:
        original_image = cv2.cvtColor(original_image, cv2.COLOR_RGBA2RGB)
    
    result = original_image.copy()
    h, w = result.shape[:2]
    
    # Convert to BGR for OpenCV operations
    result_bgr = cv2.cvtColor(result, cv2.COLOR_RGB2BGR)
    
    # Process with MediaPipe Face Mesh
    with mp_face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5
    ) as face_mesh:
        
        # Process the image
        results = face_mesh.process(result)
        
        if results.multi_face_landmarks:
            print(f"✓ Face detected with {len(results.multi_face_landmarks[0].landmark)} landmarks")
            face_landmarks = results.multi_face_landmarks[0]
            
            # Get landmark coordinates
            landmarks = []
            for landmark in face_landmarks.landmark:
                x = int(landmark.x * w)
                y = int(landmark.y * h)
                landmarks.append((x, y))
            
            # Resize and normalize heatmap
            heatmap_resized = cv2.resize(heatmap, (w, h))
            heatmap_normalized = (heatmap_resized - heatmap_resized.min()) / \
                               (heatmap_resized.max() - heatmap_resized.min() + 1e-8)
            
            # Define minimal mesh - clean face outline with key features
            # MediaPipe has 468 landmarks; we'll use the reliable contour points
            MINIMAL_FACE_CONTOUR = [
                # Face jawline and perimeter (indices 0-16 form the face outline)
                (0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (8, 9), (9, 10),
                (10, 11), (11, 12), (12, 13), (13, 14), (14, 15), (15, 16), (16, 0),  # Complete face outline
                # Left eye contour (important for analysis)
                (33, 160), (160, 158), (158, 133), (133, 33),  # Left eye
                # Right eye contour (important for analysis)
                (362, 385), (385, 387), (387, 263), (263, 362),  # Right eye
                # Eyebrows for face reference
                (70, 63), (63, 105),  # Left eyebrow
                (336, 296), (296, 334),  # Right eyebrow
                # Nose center line for reference
                (1, 4), (4, 8), (8, 12), (12, 16),  # Center vertical
                # Mouth contour for reference
                (61, 185), (185, 40), (40, 39), (39, 37), (37, 0),  # Upper mouth
            ]
            
            # Draw minimal mesh connections
            lines_drawn = 0
            debug_draw_info = []
            for connection in MINIMAL_FACE_CONTOUR:
                start_idx = connection[0]
                end_idx = connection[1]
                
                # Validate indices are within bounds
                if start_idx < len(landmarks) and end_idx < len(landmarks) and start_idx >= 0 and end_idx >= 0:
                    start_point = landmarks[start_idx]
                    end_point = landmarks[end_idx]
                    
                    # Check if this connection is in a problem area
                    mid_x = (start_point[0] + end_point[0]) // 2
                    mid_y = (start_point[1] + end_point[1]) // 2
                    
                    # Ensure coordinates are within bounds
                    mid_x = max(0, min(mid_x, w - 1))
                    mid_y = max(0, min(mid_y, h - 1))
                    
                    # Check heatmap value at midpoint
                    is_problem_area = heatmap_normalized[mid_y, mid_x] > threshold
                    
                    # Choose color and thickness based on whether it's a problem area
                    color = problem_color if is_problem_area else mesh_color
                    thickness = problem_thickness if is_problem_area else mesh_thickness
                    
                    # Draw the line with anti-aliasing for clean appearance
                    cv2.line(result_bgr, start_point, end_point, color, thickness, cv2.LINE_AA)
                    # Record debug info for this draw
                    debug_draw_info.append({
                        'start': start_point,
                        'end': end_point,
                        'color': color,
                        'thickness': thickness,
                        'is_problem': bool(is_problem_area)
                    })
                    lines_drawn += 1
            
            print(f"✓ Drew {lines_drawn} mesh lines on face")
            # If no lines drawn, mark a few key landmark points for debugging
            if lines_drawn == 0:
                try:
                    key_indices = [0, 4, 8, 16, 33, 133, 362, 263, 61, 185]
                    marker_color = (0, 0, 255)  # Bright red in BGR
                    for idx in key_indices:
                        if 0 <= idx < len(landmarks):
                            cv2.circle(result_bgr, landmarks[idx], 3, marker_color, -1, cv2.LINE_AA)
                    print(f"No lines drawn — placed debug markers at indices: {key_indices}")
                except Exception as e:
                    print(f"Failed to place debug markers: {e}")
            # Save a debug image and some info to disk for inspection
            try:
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                debug_path = f"media/face_analysis/debug_mesh_{timestamp}.jpg"
                cv2.imwrite(debug_path, result_bgr)
                print(f"Saved debug mesh image to {debug_path}")
                # Print sample debug info
                for i, info in enumerate(debug_draw_info[:8]):
                    print(f"  line[{i}] start={info['start']} end={info['end']} color={info['color']} thickness={info['thickness']} problem={info['is_problem']}")
            except Exception as e:
                print(f"Failed to save debug mesh image: {e}")
        else:
            # No face detected, fall back to simplified mesh
            print("No face detected by MediaPipe. Using simplified mesh overlay instead.")
            result_bgr = cv2.cvtColor(original_image, cv2.COLOR_RGB2BGR)
            result_rgb = generate_simplified_mesh_overlay(original_image, heatmap, threshold, mesh_color, problem_color)
            return result_rgb
    
    # Convert back to RGB
    result_rgb = cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)
    
    return result_rgb


def generate_simplified_mesh_overlay(original_image, heatmap, threshold=0.6,
                                     mesh_color=(200, 200, 200),
                                     problem_color=(80, 80, 220),
                                     num_vertical_lines=8,
                                     num_horizontal_lines=8):
    """
    Generate a simplified geometric mesh overlay (grid-based) with problem areas.
    Lighter weight alternative that doesn't require MediaPipe Face Mesh.
    
    Args:
        original_image: Original face image (numpy array, RGB)
        heatmap: Attention/activation map from the model
        threshold: Threshold for problem areas
        mesh_color: Color for normal mesh (BGR format)
        problem_color: Color for problem areas (BGR format)
        num_vertical_lines: Number of vertical mesh lines
        num_horizontal_lines: Number of horizontal mesh lines
    
    Returns:
        Image with simplified mesh overlay
    """
    if len(original_image.shape) == 2:
        original_image = cv2.cvtColor(original_image, cv2.COLOR_GRAY2RGB)
    elif original_image.shape[2] == 4:
        original_image = cv2.cvtColor(original_image, cv2.COLOR_RGBA2RGB)
    
    result = original_image.copy()
    h, w = result.shape[:2]
    
    # Resize and normalize heatmap
    heatmap_resized = cv2.resize(heatmap, (w, h))
    heatmap_normalized = (heatmap_resized - heatmap_resized.min()) / \
                       (heatmap_resized.max() - heatmap_resized.min() + 1e-8)
    
    # Convert to BGR for OpenCV
    result_bgr = cv2.cvtColor(result, cv2.COLOR_RGB2BGR)
    
    # Draw vertical lines
    for i in range(num_vertical_lines + 1):
        x = int(w * i / num_vertical_lines)
        for y in range(0, h - h // num_horizontal_lines, h // num_horizontal_lines):
            y_end = y + h // num_horizontal_lines
            
            # Sample heatmap along this segment
            segment_values = heatmap_normalized[y:y_end, max(0, x-2):min(w, x+2)]
            is_problem = np.mean(segment_values) > threshold
            
            color = problem_color if is_problem else mesh_color
            thickness = 2 if is_problem else 1
            
            cv2.line(result_bgr, (x, y), (x, y_end), color, thickness, cv2.LINE_AA)
    
    # Draw horizontal lines
    for i in range(num_horizontal_lines + 1):
        y = int(h * i / num_horizontal_lines)
        for x in range(0, w - w // num_vertical_lines, w // num_vertical_lines):
            x_end = x + w // num_vertical_lines
            
            # Sample heatmap along this segment
            segment_values = heatmap_normalized[max(0, y-2):min(h, y+2), x:x_end]
            is_problem = np.mean(segment_values) > threshold
            
            color = problem_color if is_problem else mesh_color
            thickness = 2 if is_problem else 1
            
            cv2.line(result_bgr, (x, y), (x_end, y), color, thickness, cv2.LINE_AA)
    
    result_rgb = cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)
    return result_rgb


def generate_minimal_white_indicators(original_image, heatmap, alpha=0.3, threshold=0.6):
    """
    More minimal version - just white outlines on semi-transparent heatmap.
    
    Args:
        original_image: Original face image (numpy array)
        heatmap: Attention/activation map from the model (numpy array)
        alpha: Transparency for heatmap overlay (lower = more subtle)
        threshold: Threshold for high-attention areas
    
    Returns:
        Combined image with minimal white indicators
    """
    # Ensure original image is RGB
    if len(original_image.shape) == 2:
        original_image = cv2.cvtColor(original_image, cv2.COLOR_GRAY2RGB)
    elif original_image.shape[2] == 4:
        original_image = cv2.cvtColor(original_image, cv2.COLOR_RGBA2RGB)
    
    # Resize heatmap to match original image
    h, w = original_image.shape[:2]
    heatmap_resized = cv2.resize(heatmap, (w, h))
    
    # Normalize heatmap
    heatmap_normalized = (heatmap_resized - heatmap_resized.min()) / (heatmap_resized.max() - heatmap_resized.min() + 1e-8)
    
    # Create subtle colored heatmap
    heatmap_colored = cv2.applyColorMap((heatmap_normalized * 255).astype(np.uint8), cv2.COLORMAP_JET)
    heatmap_colored = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)
    
    # Very subtle blend
    result = cv2.addWeighted(original_image, 1 - alpha, heatmap_colored, alpha, 0)
    
    # Find high-attention areas
    high_attention_mask = heatmap_normalized > threshold
    
    # Clean up the mask
    kernel = np.ones((7, 7), np.uint8)
    high_attention_mask = cv2.morphologyEx(high_attention_mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel)
    high_attention_mask = cv2.dilate(high_attention_mask, kernel, iterations=1)
    
    # Find contours
    contours, _ = cv2.findContours(high_attention_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Draw clean white outlines
    cv2.drawContours(result, contours, -1, (255, 255, 255), 3, cv2.LINE_AA)
    
    return result


def convert_heatmap_to_base64(heatmap_image):
    """
    Convert heatmap image to base64 string for HTML display.
    
    Args:
        heatmap_image: RGB numpy array
        
    Returns:
        base64 encoded string
    """
    # Convert RGB to BGR for OpenCV
    heatmap_bgr = cv2.cvtColor(heatmap_image, cv2.COLOR_RGB2BGR)
    
    # Encode to JPEG
    _, buffer = cv2.imencode('.jpg', heatmap_bgr, [cv2.IMWRITE_JPEG_QUALITY, 95])
    
    # Convert to base64
    heatmap_base64 = base64.b64encode(buffer).decode('utf-8')
    
    return heatmap_base64


def process_skin_concern_with_heatmap(original_image, attention_map, concern_name, alpha=0.3, threshold=0.6):
    """
    Complete example showing how to integrate with your model.
    
    Args:
        original_image: Preprocessed face image (numpy array, RGB)
        attention_map: Attention/activation map from model (numpy array)
        concern_name: Name of the concern being analyzed
        alpha: Transparency for heatmap overlay (0.2-0.4 recommended)
        threshold: Threshold for high-attention areas (0.5-0.7 recommended)
        
    Returns:
        Dictionary with prediction and heatmap
    """
    # Generate heatmap with white indicators
    heatmap_image = generate_minimal_white_indicators(
        original_image=original_image,
        heatmap=attention_map,
        alpha=alpha,
        threshold=threshold
    )
    
    # Convert to base64
    heatmap_base64 = convert_heatmap_to_base64(heatmap_image)
    
    return {
        'concern_name': concern_name,
        'heatmap': heatmap_base64
    }
