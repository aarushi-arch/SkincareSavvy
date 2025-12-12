# CNN Model Training Guide

This guide explains how to train CNN models for skin type and skin concern classification.

## Dataset Preparation

### 1. Organize Your Dataset

Place your datasets in the following structure:

```
face_analysis/datasets/
  skin_types/
    train/
      dry/
      oily/
      combination/
      normal/
      sensitive/
    validation/
      (same structure)
    test/
      (same structure)
  
  skin_concerns/
    train/
      acne/
      wrinkles/
      dark_spots/
      dryness/
      redness/
      texture/
    validation/
      (same structure)
    test/
      (same structure)
```

### 2. Dataset Requirements

- Images should be in common formats (jpg, png, jpeg)
- Recommended image size: 224x224 or 256x256 pixels
- Ensure balanced datasets across all classes
- Use train/validation/test split (e.g., 70/15/15 or 80/10/10)

## Training Models

### Using Django Management Command

The easiest way to train models is using the Django management command:

#### Train Skin Types Model

```bash
python manage.py train_cnn \
  --dataset-type skin_types \
  --dataset-path face_analysis/datasets/skin_types \
  --output-dir face_analysis/models \
  --base-model mobilenet \
  --epochs 50 \
  --batch-size 32 \
  --learning-rate 0.001
```

#### Train Skin Concerns Model

```bash
python manage.py train_cnn \
  --dataset-type skin_concerns \
  --dataset-path face_analysis/datasets/skin_concerns \
  --output-dir face_analysis/models \
  --base-model mobilenet \
  --epochs 50 \
  --batch-size 32 \
  --learning-rate 0.001
```

### Command Options

- `--dataset-type`: Type of dataset (`skin_types` or `skin_concerns`)
- `--dataset-path`: Path to dataset directory
- `--output-dir`: Directory to save trained models (default: `face_analysis/models`)
- `--base-model`: Base architecture (`mobilenet`, `resnet50`, `vgg16`, or `custom`)
- `--epochs`: Number of training epochs (default: 50)
- `--batch-size`: Batch size (default: 32)
- `--learning-rate`: Learning rate (default: 0.001)
- `--dropout-rate`: Dropout rate (default: 0.5)
- `--image-size`: Image size as height width (default: 224 224)

### Using Python Script

You can also train models programmatically:

```python
from pathlib import Path
from face_analysis.training.trainer import CNNTrainer

# Create trainer
trainer = CNNTrainer(
    dataset_path=Path("face_analysis/datasets/skin_types"),
    model_type="skin_types",
    output_dir=Path("face_analysis/models"),
    base_model="mobilenet",
    epochs=50,
    batch_size=32,
)

# Prepare data
train_gen, val_gen, test_gen = trainer.prepare_data()

# Build model
trainer.build_model()

# Train
trainer.train(train_gen, val_gen)

# Evaluate
test_results = trainer.evaluate(test_gen)
print(f"Test accuracy: {test_results[1]:.4f}")

# Save
trainer.save_model()
trainer.save_training_history()
```

## Model Architectures

### Available Base Models

1. **MobileNetV2** (default)
   - Lightweight, fast inference
   - Good for mobile/web deployment
   - Lower accuracy than deeper models

2. **ResNet50**
   - Deeper architecture
   - Higher accuracy
   - Slower inference

3. **VGG16**
   - Classic architecture
   - Good baseline
   - Moderate size

4. **Custom CNN**
   - Lightweight custom architecture
   - Good for small datasets
   - Fast training

## Output Files

After training, the following files will be saved:

- `{model_type}_best_model.keras`: Best model during training
- `{model_type}_final_model.keras`: Final model after training
- `{model_type}_class_names.json`: Class names mapping
- `{model_type}_training_log.csv`: Training metrics log
- `{model_type}_history.json`: Training history

## Tips for Better Results

1. **Data Augmentation**: Enabled by default to increase dataset diversity
2. **Early Stopping**: Prevents overfitting by stopping when validation accuracy stops improving
3. **Learning Rate Scheduling**: Automatically reduces learning rate when loss plateaus
4. **Class Balance**: Ensure balanced datasets for better performance
5. **Image Quality**: Use high-quality, well-lit images
6. **Transfer Learning**: Pre-trained ImageNet weights are used by default

## Monitoring Training

Training progress is logged to:
- Console output (real-time)
- CSV file: `{model_type}_training_log.csv`
- JSON history: `{model_type}_history.json`

You can visualize training progress using TensorBoard or by plotting the CSV data.

