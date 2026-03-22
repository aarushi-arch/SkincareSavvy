## Skin Concerns Model - TensorFlow Compatibility Issue

### Problem
The skin concerns model file was saved with a newer version of Keras/TensorFlow that includes `quantization_config` parameter. Your current TensorFlow version does not recognize this parameter, so the model cannot load.

**Error:**
```
ValueError: Unrecognized keyword arguments passed to Dense: {'quantization_config': None}
```

### Solution

You have 2 options:

#### Option 1: Re-export the Model (RECOMMENDED)
If you have access to the training code:

```python
import tensorflow as tf

# Load the model with the newer TensorFlow that created it
model = tf.keras.models.load_model('your_model_path.h5')

# Save it in a compatible format
model.save('skin_concerns_compatible.h5', save_format='h5')
```

Then upload the compatible version to Django Admin.

#### Option 2: Upgrade TensorFlow (Quick Fix)
Update your TensorFlow to the latest version:

```bash
pip install --upgrade tensorflow
```

Then clear the models cache and restart:
```bash
python manage.py runserver
```

#### Option 3: Use TensorFlow Lite Format
Convert the model to TensorFlow Lite format (.tflite) which has better compatibility:

```python
import tensorflow as tf

# Load original model
model = tf.keras.models.load_model('your_model_path.h5')

# Convert to TFLite
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()

# Save
with open('skin_concerns.tflite', 'wb') as f:
    f.write(tflite_model)
```

### Temporary Workaround
While you fix the model, facial analysis will work but show:
- ✓ Skin Type correctly
- ✗ No skin concerns detected (will use simulation fallback)

This allows the application to continue functioning.

### After Fixing the Model

1. Go to Django Admin → Face Analysis → CNN Models
2. Edit the SkinConcernsMobileNetV2 model
3. Delete the old model file
4. Upload the compatible model file
5. Save
6. Run `python manage.py runserver`
7. Test with a face image
