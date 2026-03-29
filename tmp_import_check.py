
import sys
try:
    import tensorflow as tf
    print(f"TensorFlow version: {tf.__version__}")
except ImportError:
    print("TensorFlow not found")

try:
    import keras
    print(f"Keras version: {keras.__version__}")
except ImportError:
    print("Keras not found")

try:
    from tensorflow import keras as tf_keras
    print("from tensorflow import keras works")
except ImportError:
    print("from tensorflow import keras fails")
