
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SkincareSavvy.settings')
try:
    django.setup()
    print("Django setup success")
    from face_analysis.services.cnn import FaceAnalysisPipeline
    print("FaceAnalysisPipeline import success")
except ImportError as e:
    print(f"ImportError: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"General Error: {e}")
    import traceback
    traceback.print_exc()
