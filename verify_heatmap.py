import os
import sys
import django
from django.conf import settings
from io import BytesIO
from PIL import Image

# Setup Django environment
sys.path.append(r"c:\Users\Hp\Desktop\SkincareSavvy")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SkincareSavvy.settings")
django.setup()

import numpy as np
from face_analysis.services.cnn import FaceAnalysisPipeline

def verify():
    print("Initializing pipeline...")
    pipeline = FaceAnalysisPipeline()
    
    # Create dummy image
    img = Image.new('RGB', (300, 300), color='white')
    buf = BytesIO()
    img.save(buf, format='JPEG')
    image_bytes = buf.getvalue()
    
    print("Running analysis...")
    try:
        # We need to make sure the skin concerns model is actually loaded and has a conv layer that can be found.
        # This might fail if the dummy model in the environment doesn't look like a standard CNN or if the file doesn't exist.
        # But we are testing the CODE logic.
        
        result = pipeline.analyze(image_bytes)
        
        if "skin_concerns" in result:
            concerns = result["skin_concerns"]
            if "predictions" in concerns:
                preds = concerns["predictions"]
                print(f"Got {len(preds)} skin concern predictions.")
                
                heatmap_count = 0
                for p in preds:
                    if 'heatmap' in p:
                        heatmap_count += 1
                        # Verify it looks like base64
                        if len(p['heatmap']) > 100:
                            print(f"  - {p['class']}: Heatmap generated (length {len(p['heatmap'])})")
                        else:
                            print(f"  - {p['class']}: Heatmap present but suspiciously short")
                    else:
                        print(f"  - {p['class']}: NO heatmap")
                
                if heatmap_count > 0:
                    print("SUCCESS: At least one heatmap generated.")
                else:
                    print("WARNING: No heatmaps generated. Check if model has conv layers or if loading failed.")
            else:
                 print("No predictions list in skin_concerns result.")
        else:
             print("No skin_concerns in result.")

    except Exception as e:
        print(f"FAILURE: Analysis crashed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify()
