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

    # Build a single combined, confidence-weighted heatmap
    combined_heatmap = None
    total_weight = 0.0
    detected_concerns = []

    orig_h, orig_w = img_rgb.shape[:2]

    for i, class_name in enumerate(class_names):
        try:
            heatmap = get_gradcam_heatmap(model, img_array, i, last_conv_layer_name)

            # Confidence for this class
            confidence = float(preds[i])

            # Resize to original image size and weight by confidence
            heatmap = cv2.resize(heatmap, (orig_w, orig_h))
            heatmap = heatmap * confidence

            if combined_heatmap is None:
                combined_heatmap = heatmap
            else:
                combined_heatmap += heatmap

            total_weight += confidence

            # Consider it a detected concern if confidence passes a small threshold
            if confidence >= 0.10:
                detected_concerns.append(class_name)

        except Exception as e:
            print(f"Error generating heatmap for {class_name}: {e}")

    # Normalize combined heatmap
    if combined_heatmap is None:
        combined_heatmap = np.zeros((orig_h, orig_w), dtype=np.float32)

    combined_heatmap = combined_heatmap / max(total_weight, 1e-6)
    combined_heatmap = np.clip(combined_heatmap, 0.0, 1.0)

    # Colorize and overlay on original image
    colored_heatmap = cv2.applyColorMap((combined_heatmap * 255).astype(np.uint8), cv2.COLORMAP_JET)

    # Ensure we have BGR for overlay; original is RGB -> convert to BGR
    original_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    overlay_bgr = cv2.addWeighted(original_bgr, 0.6, colored_heatmap, 0.4, 0)

    # Convert overlay back to RGB for consistent downstream handling
    overlay_rgb = cv2.cvtColor(overlay_bgr, cv2.COLOR_BGR2RGB)

    # Convert to base64
    combined_base64 = convert_heatmap_to_base64(overlay_rgb)

    return {
        'combined_heatmap': combined_base64,
        'detected_concerns': detected_concerns,
    }
