import cv2
import numpy as np
import tensorflow as tf
import keras
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
    grad_model = keras.Model(
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

def generate_multi_skin_concern_heatmaps(
    model,
    img_bytes,
    class_names,
    last_conv_layer_name=None,
    target_size=None,
    confidence_threshold=0.30,   # only show meaningful concerns
    activation_threshold=0.45,   # remove weak heatmap noise
    alpha=0.25                   # subtle overlay
):
    """
    Improved Grad-CAM visualization with:
    - Noise reduction
    - Strong activation filtering
    - Smoother, more professional look
    - Individual heatmaps for each detected concern
    """

    if last_conv_layer_name is None:
        last_conv_layer_name = find_last_conv_layer(model)

    # Load original image
    if isinstance(img_bytes, bytes):
        pil_img = Image.open(BytesIO(img_bytes)).convert("RGB")
        img_rgb = np.array(pil_img)
    elif isinstance(img_bytes, np.ndarray):
        img_rgb = img_bytes
    else:
        raise ValueError("Unsupported image type provided")

    # Determine target size if not provided
    if target_size is None:
        try:
            # model.input_shape might be (None, 128, 128, 3)
            shape = model.input_shape
            if shape and len(shape) >= 3:
                # Some models have (None, H, W, C), others (H, W, C)
                if len(shape) == 4:
                    target_size = shape[1:3]
                else:
                    target_size = shape[0:2]
        except Exception:
            pass
            
    if target_size is None:
        target_size = (224, 224) # Final fallback

    print(f"DEBUG: Grad-CAM using target_size={target_size}")

    # Preprocess image
    img_array = preprocess_image(img_bytes, target_size=target_size, normalize=True)

    # Get predictions
    preds = model.predict(img_array, verbose=0)[0]

    combined_heatmap = None
    total_weight = 0.0
    detected_concerns = []
    individual_heatmaps = {}  # Store individual heatmaps

    orig_h, orig_w = img_rgb.shape[:2]

    for i, class_name in enumerate(class_names):
        confidence = float(preds[i])

        # Only visualize meaningful predictions
        if confidence < confidence_threshold:
            continue

        try:
            heatmap = get_gradcam_heatmap(
                model, img_array, i, last_conv_layer_name
            )

            heatmap = cv2.resize(heatmap, (orig_w, orig_h))

            # Boost contrast
            heatmap = np.power(heatmap, 1.8)

            # Remove weak activations
            heatmap[heatmap < activation_threshold] = 0

            # Smooth heatmap
            heatmap = cv2.GaussianBlur(heatmap, (21, 21), 0)

            # Weight by confidence
            heatmap_weighted = heatmap * confidence

            # Create individual heatmap visualization
            colored_individual_heatmap = cv2.applyColorMap(
                (heatmap * 255).astype(np.uint8),
                cv2.COLORMAP_INFERNO
            )
            
            original_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
            individual_overlay = cv2.addWeighted(original_bgr, 1 - alpha, colored_individual_heatmap, alpha, 0)
            individual_overlay_rgb = cv2.cvtColor(individual_overlay, cv2.COLOR_BGR2RGB)
            
            # Convert to base64
            individual_base64 = convert_heatmap_to_base64(individual_overlay_rgb)
            individual_heatmaps[class_name] = individual_base64

            if combined_heatmap is None:
                combined_heatmap = heatmap_weighted
            else:
                combined_heatmap += heatmap_weighted

            total_weight += confidence
            detected_concerns.append({
                "name": class_name,
                "confidence": int(confidence * 100),
                "heatmap": individual_base64
            })

        except Exception as e:
            print(f"GradCAM error for {class_name}: {e}")

    if combined_heatmap is None:
        combined_heatmap = np.zeros((orig_h, orig_w), dtype=np.float32)

    combined_heatmap /= max(total_weight, 1e-6)
    combined_heatmap = np.clip(combined_heatmap, 0, 1)

    # Apply modern colormap
    colored_heatmap = cv2.applyColorMap(
        (combined_heatmap * 255).astype(np.uint8),
        cv2.COLORMAP_INFERNO  # better than JET
    )

    # Blend with original image
    original_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    overlay_bgr = cv2.addWeighted(original_bgr, 1 - alpha, colored_heatmap, alpha, 0)

    overlay_rgb = cv2.cvtColor(overlay_bgr, cv2.COLOR_BGR2RGB)

    combined_base64 = convert_heatmap_to_base64(overlay_rgb)

    return {
        "combined_heatmap": combined_base64,
        "detected_concerns": detected_concerns,
        "individual_heatmaps": individual_heatmaps,
    }
