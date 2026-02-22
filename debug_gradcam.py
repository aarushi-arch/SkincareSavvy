import os
import sys
import django
import numpy as np
import tensorflow as tf

# Setup Django environment
sys.path.append(r"c:\Users\Hp\Desktop\SkincareSavvy")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SkincareSavvy.settings")
django.setup()

from face_analysis.services.cnn import FaceAnalysisPipeline
from face_analysis.utils.gradcam import find_last_conv_layer, get_gradcam_heatmap, generate_multi_skin_concern_heatmaps

def debug_gradcam():
    pipeline = FaceAnalysisPipeline()
    pipeline.load_models_from_db()
    
    model = pipeline.skin_concerns_model
    if model is None:
        print("Skin concerns model not loaded.")
    output_log = []
    def log(msg):
        print(msg)
        output_log.append(str(msg))

    try:
        pipeline = FaceAnalysisPipeline()
        pipeline.load_models_from_db()
        
        model = pipeline.skin_concerns_model
        if model is None:
            log("Skin concerns model not loaded.")
            return

        log(f"Model Summary:")
        import io
        s = io.StringIO()
        model.summary(print_fn=lambda x: s.write(x + '\n'))
        log(s.getvalue())
        
        log(f"Model Input Shape: {model.input_shape}")
        
        # Determine target size correctly
        target_size = (224, 224)
        if model.input_shape and len(model.input_shape) >= 4:
            target_size = model.input_shape[1:3]
        elif model.input_shape and len(model.input_shape) == 3:
            target_size = model.input_shape[0:2]
            
        log(f"Using target_size: {target_size}")

        log("Searching for last conv layer...")
        try:
            last_conv = find_last_conv_layer(model)
            log(f"Found last conv layer: {last_conv}")
        except Exception as e:
            log(f"Error finding last conv layer: {e}")
            log("Model layers:")
            for layer in model.layers[-10:]:
                log(f"  {layer.name} ({type(layer).__name__})")
            return

        # Create dummy image (numpy array, 0-255)
        img_rgb = np.random.randint(0, 255, (target_size[0], target_size[1], 3), dtype=np.uint8)
        class_names = pipeline.skin_concerns_classes
        
        log(f"Running generate_multi_skin_concern_heatmaps with classes: {class_names}")
        try:
            result = generate_multi_skin_concern_heatmaps(
                model, 
                img_rgb, 
                class_names, 
                confidence_threshold=0.0, # Force all classes
                activation_threshold=0.0  # Force all activations
            )
            log("Success! Result keys: " + str(result.keys()))
            if result.get("combined_heatmap"):
                log("Combined heatmap base64 generated (length: " + str(len(result["combined_heatmap"])) + ")")
            else:
                log("Combined heatmap is None or empty.")
            log("Detected concerns: " + str(result.get("detected_concerns")))
        except Exception as e:
            log(f"Error in generate_multi_skin_concern_heatmaps: {e}")
            import traceback
            log(traceback.format_exc())

    except Exception as top_e:
        log(f"Top level error: {top_e}")
        import traceback
        log(traceback.format_exc())
    finally:
        with open("debug_gradcam_output.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(output_log))

if __name__ == "__main__":
    debug_gradcam()
