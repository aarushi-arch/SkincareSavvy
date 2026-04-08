import ultralytics
import torch
import cv2
import sys

def check_env():
    print("--- Environment Status ---")
    print(f"Python: {sys.version}")
    print(f"Ultralytics: {ultralytics.__version__}")
    print(f"Torch: {torch.__version__}")
    print(f"OpenCV: {cv2.__version__}")
    
    cuda_available = torch.cuda.is_available()
    print(f"CUDA available: {cuda_available}")
    if cuda_available:
        print(f"GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("Running on CPU")
    
    try:
        from ultralytics import YOLO
        # Just try to instantiate, don't necessarily download/run if we don't need to
        # but a simple load check is good.
        print("YOLO class imported successfully.")
    except Exception as e:
        print(f"Error importing YOLO: {e}")
    
    print("-----------------------")

if __name__ == "__main__":
    check_env()
