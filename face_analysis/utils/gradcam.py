import cv2
import numpy as np
import tensorflow as tf
import base64
from io import BytesIO
from PIL import Image
from face_analysis.utils.image_utils import preprocess_image
from face_analysis.utils.heatmap_generator import (
    generate_facial_mesh_with_problem_areas,
    generate_simplified_mesh_overlay,
    generate_minimal_white_indicators,
    convert_heatmap_to_base64
)

def get_gradcam_heatmap(model, img_array, class_index, last_conv_layer_name):
    """
    Generates Grad-CAM heatmap for a specific class.
    """
    grad_model = tf.keras.models.Model(
        model.input, [model.get_layer(last_conv_layer_name).output, model.output]
    )

    with tf.GradientTape() as tape:
        conv_outputs, predictions = grad_model(img_array)
        if isinstance(predictions, list):
             predictions = predictions[0]
        loss = predictions[:, class_index]

    grads = tape.gradient(loss, conv_outputs)
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

    conv_outputs = conv_outputs[0]
    conv_outputs = conv_outputs * pooled_grads
    heatmap = tf.reduce_mean(conv_outputs, axis=-1)

    heatmap = tf.maximum(heatmap, 0)
    
    # Safe normalization to avoid division by zero
    max_val = tf.math.reduce_max(heatmap)
    if max_val > 0:
        heatmap /= max_val
        
    return heatmap.numpy()

def overlay_heatmap_with_dots(img_rgb, heatmap, dot_threshold=0.6):
    """
    Deprecated: Use generate_minimal_white_indicators instead.
    Kept for backwards compatibility.
    
    Draws prominent dots where the model strongly focuses.
    """
    h, w, _ = img_rgb.shape
    heatmap = cv2.resize(heatmap, (w, h))

    output = img_rgb.copy()

    # Find strong activation points
    ys, xs = np.where(heatmap > dot_threshold)

    for (x, y) in zip(xs, ys):
        # Dot size depends on intensity
        radius = int(2 + heatmap[y, x] * 4)
        cv2.circle(output, (x, y), radius, (0, 0, 255), -1)

    return output

def image_to_base64(img_array):
    """
    Converts numpy image to base64 string.
    """
    img = Image.fromarray(img_array)
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def find_last_conv_layer(model):
    """
    Finds the last convolutional layer in the model.
    """
    for layer in reversed(model.layers):
        if 'conv' in layer.name:
            return layer.name
    raise ValueError("No convolution layer found.")

def generate_multi_skin_concern_heatmaps(model, img_bytes, class_names, last_conv_layer_name=None, target_size=(224, 224), alpha=0.3, threshold=0.6):
    """
    Generate Grad-CAM heatmaps for all classes of interest with minimal white indicators.
    Adapted to accept image bytes directly instead of path for efficiency.
    
    Args:
        model: Keras skin concern model
        img_bytes: Input image (bytes or numpy array)
        class_names: List of skin concern class names
        last_conv_layer_name: Name of last conv layer in model (optional, auto-detected if None)
        alpha: Transparency for heatmap overlay (lower = more subtle, default 0.3)
        threshold: Threshold for high-attention areas (default 0.6)

    Returns:
        List of dictionaries with heatmaps
    """
    if last_conv_layer_name is None:
        last_conv_layer_name = find_last_conv_layer(model)

    # Load original image
    if isinstance(img_bytes, bytes):
        pil_img = Image.open(BytesIO(img_bytes)).convert('RGB')
        img_rgb = np.array(pil_img)
    elif isinstance(img_bytes, np.ndarray):
        img_rgb = img_bytes
    else:
        raise ValueError("Unsupported image type provided to GradCAM generator")
    
    # Preprocess for model using shared utility
    # returns (1, H, W, 3)
    img_array = preprocess_image(img_bytes, target_size=target_size, normalize=True)
    
    # Predict all skin concerns
    preds = model.predict(img_array, verbose=0)[0]

    heatmaps = []

    for i, class_name in enumerate(class_names):
        try:
            # Generate Grad-CAM heatmap for this class
            heatmap = get_gradcam_heatmap(model, img_array, i, last_conv_layer_name)
            
            # Generate visualization with facial mesh overlay and problem areas
            heatmap_visualization = generate_facial_mesh_with_problem_areas(
                original_image=img_rgb,
                heatmap=heatmap,
                threshold=threshold,
                    mesh_color=(180, 180, 180),      # Professional light gray mesh lines (BGR format)
                    problem_color=(80, 80, 220),     # Professional red for problem areas (BGR format - R=220 becomes B=220)
                mesh_thickness=1,                # Thin professional lines
                problem_thickness=2              # Slightly thicker for problem areas - clear visibility
            )

            # Convert to base64
            heatmap_base64 = convert_heatmap_to_base64(heatmap_visualization)

            # Append to results
            heatmaps.append({
                'class': class_name,
                'confidence': float(preds[i]),
                'heatmap': heatmap_base64  # This is the base64-encoded visualization
            })
        except Exception as e:
            print(f"Error generating heatmap for {class_name}: {e}")

    return heatmaps
