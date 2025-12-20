import cv2
import numpy as np
import tensorflow as tf
import base64
from io import BytesIO
from PIL import Image

def get_gradcam_heatmap(model, img_array, class_index, last_conv_layer_name):
    """
    Generates Grad-CAM heatmap for a specific class.
    """
    grad_model = tf.keras.models.Model(
        [model.inputs], [model.get_layer(last_conv_layer_name).output, model.output]
    )

    with tf.GradientTape() as tape:
        conv_outputs, predictions = grad_model(img_array)
        loss = predictions[:, class_index]

    grads = tape.gradient(loss, conv_outputs)
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

    conv_outputs = conv_outputs[0]
    heatmap = conv_outputs @ pooled_grads[..., tf.newaxis]
    heatmap = tf.squeeze(heatmap)

    heatmap = tf.maximum(heatmap, 0) / tf.math.reduce_max(heatmap)
    return heatmap.numpy()

def overlay_heatmap(img_rgb, heatmap, alpha=0.4):
    """
    Overlays heatmap on original image.
    """
    # Resize heatmap to image size
    heatmap = cv2.resize(heatmap, (img_rgb.shape[1], img_rgb.shape[0]))
    
    # Colorize
    heatmap = np.uint8(255 * heatmap)
    heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
    
    # Overlay
    superimposed_img = heatmap * alpha + img_rgb * (1 - alpha)  # Be careful with types
    superimposed_img = np.clip(superimposed_img, 0, 255).astype(np.uint8)
    
    return superimposed_img

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

def generate_multi_skin_concern_heatmaps(model, img_bytes, class_names, last_conv_layer_name=None):
    """
    Generate Grad-CAM heatmaps for all classes of interest.
    Adapted to accept image bytes directly instead of path for efficiency.
    
    Args:
        model: Keras skin concern model
        img_bytes: Input image bytes
        class_names: List of skin concern class names
        last_conv_layer_name: Name of last conv layer in model (optional, auto-detected if None)

    Returns:
        List of dictionaries with heatmaps
    """
    if last_conv_layer_name is None:
        last_conv_layer_name = find_last_conv_layer(model)

    # 1️⃣ Load original image
    # We use PIL to read bytes, then convert to numpy for CV2 operations
    pil_img = Image.open(BytesIO(img_bytes)).convert('RGB')
    img_rgb = np.array(pil_img)
    
    # Preprocess for model
    img_resized = cv2.resize(img_rgb, (128, 128))
    img_array = np.expand_dims(img_resized / 255.0, axis=0)
    
    # 2️⃣ Predict all skin concerns
    preds = model.predict(img_array, verbose=0)[0]

    heatmaps = []

    # Limit to e.g. top 3 or all? User said "all classes of interest".
    # Let's do all classes but maybe sort them or just return all.
    # The snippet loops over class_names.
    
    for i, class_name in enumerate(class_names):
        # Only generate heatmap if confidence is somewhat relevant? 
        # Or just generate for all as requested.
        
        # 3️⃣ Generate Grad-CAM heatmap for this class
        try:
            heatmap = get_gradcam_heatmap(model, img_array, i, last_conv_layer_name)
            
            # Use resized image for overlay to match model input size visual
            # OR overlay on original? 
            # User snippet: `img_resized = ...; superimposed_img = overlay_heatmap(img_rgb, heatmap)`
            # Note: img_rgb is the ORIGINAL size in snippet? Yes: `cv2.imread(img_path)`.
            # So overlay_heatmap receives original size image and small heatmap.
            # My overlay_heatmap resizes heatmap to img_rgb size. Correct.
            
            superimposed_img = overlay_heatmap(img_rgb, heatmap)

            # 4️⃣ Convert to base64
            heatmap_base64 = image_to_base64(superimposed_img)

            # 5️⃣ Append to results
            heatmaps.append({
                'class': class_name,
                'confidence': float(preds[i]),
                'heatmap_img': heatmap_base64
            })
        except Exception as e:
            print(f"Error generating heatmap for {class_name}: {e}")

    return heatmaps
