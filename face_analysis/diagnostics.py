"""Diagnostic script to check skin concerns model status."""
import os
import sys
import django

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SkincareSavvy.settings')
django.setup()

from face_analysis.models import CNNModel
from face_analysis.services.cnn import FaceAnalysisPipeline

print("\n" + "="*60)
print("SKIN CONCERNS MODEL DIAGNOSTIC")
print("="*60)

# 1. Check database for models
print("\n[1] Checking Database Models...")
all_models = CNNModel.objects.all()
print(f"Total models in DB: {len(all_models)}")

for model in all_models:
    status = "[ACTIVE]" if model.is_active else "[inactive]"
    print(f"\n  {status} {model.name}")
    print(f"    Type: {model.model_type}")
    print(f"    Model file: {'[OK]' if model.model_file else '[MISSING]'}")
    print(f"    Class names file: {'[OK]' if model.class_names_file else '[MISSING]'}")
    if model.class_names_file:
        try:
            names = model.class_names
            count = len(names) if isinstance(names, (list, dict)) else 0
            display = str(names)[:50] if names else "None"
            print(f"    Classes loaded: {count} - {display}...")
        except Exception as e:
            print(f"    Classes error: {e}")

# 2. Check active models
print("\n[2] Active Models...")
skin_types = CNNModel.objects.filter(model_type='skin_types', is_active=True).first()
skin_concerns = CNNModel.objects.filter(model_type='skin_concerns', is_active=True).first()

print(f"Skin Types: {skin_types.name if skin_types else '[NONE]'}")
print(f"Skin Concerns: {skin_concerns.name if skin_concerns else '[NONE]'}")

if skin_concerns:
    print(f"\n  Skin Concerns Model Details:")
    print(f"  - Model file exists: {bool(skin_concerns.model_file)}")
    print(f"  - Class names file exists: {bool(skin_concerns.class_names_file)}")
    print(f"  - Class names data: {skin_concerns.class_names}")

# 3. Test pipeline loading
print("\n[3] Testing Pipeline Loading...")
pipeline = FaceAnalysisPipeline()
pipeline.load_models_from_db()

print(f"[OK] Pipeline initialized")
print(f"  Skin types model loaded: {pipeline.skin_types_model is not None}")
print(f"  Skin concerns model loaded: {pipeline.skin_concerns_model is not None}")
print(f"  Skin types classes: {len(pipeline.skin_types_classes)} - {pipeline.skin_types_classes}")
print(f"  Skin concerns classes: {len(pipeline.skin_concerns_classes)} - {pipeline.skin_concerns_classes}")

# 4. Recommendations
print("\n[4] Recommendations...")
if not skin_concerns:
    print("[ERROR] No active skin concerns model!")
    print("  -> Go to Django Admin and:")
    print("     1. Create or select a CNN Model with type 'Skin Concerns'")
    print("     2. Upload the model file (.h5 or .keras)")
    print("     3. Upload the class_names_file (JSON)")
    print("     4. Check the 'is_active' checkbox")
    print("     5. Save")
elif not skin_concerns.class_names_file:
    print("[ERROR] Skin concerns model missing class_names_file!")
    print("  -> Go to Django Admin:")
    print("     1. Edit the skin concerns model")
    print("     2. Upload the class_names_file (JSON)")
    print("     3. Save")
elif not skin_concerns.class_names:
    print("[ERROR] Skin concerns model class_names cannot be read!")
    print("  -> Check that the class_names_file is a valid JSON file")
    print("  -> Format should be either:")
    print("     - Dict: {\"acne\": 0, \"wrinkles\": 1}")
    print("     - List: [\"acne\", \"wrinkles\"]")
elif pipeline.skin_concerns_model is None:
    print("[ERROR] Skin concerns model failed to load!")
    print("  -> The model file might be incompatible with current TensorFlow version")
    print("  -> Check Django logs for error details")
elif pipeline.skin_concerns_classes:
    print("[OK] Skin concerns model is ready!")
    print(f"  Classes: {pipeline.skin_concerns_classes}")
else:
    print("[?] Unknown issue - check logs above")

print("\n" + "="*60 + "\n")
