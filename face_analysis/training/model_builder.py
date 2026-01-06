"""CNN model architecture builder for skin analysis."""
from __future__ import annotations

from typing import Optional

import keras
from keras import layers


def build_skin_analysis_cnn(
    num_classes: int,
    input_shape: tuple[int, int, int] = (224, 224, 3),
    base_model: Optional[str] = "mobilenet",
    dropout_rate: float = 0.5,
    learning_rate: float = 0.001,
) -> keras.Model:
    """
    Build a CNN model for skin type or skin concern classification.

    Args:
        num_classes: Number of output classes
        input_shape: Input image shape (height, width, channels)
        base_model: Base model architecture ('mobilenet', 'resnet50', 'vgg16', or 'custom')
        dropout_rate: Dropout rate for regularization
        learning_rate: Learning rate for optimizer

    Returns:
        Compiled Keras model
    """
    inputs = keras.Input(shape=input_shape)

    if base_model == "mobilenet":
        # Use MobileNetV2 as base (lightweight, good for mobile/web)
        base = keras.applications.MobileNetV2(
            input_shape=input_shape,
            include_top=False,
            weights="imagenet",
        )
        base.trainable = True  # Fine-tune the base model
        x = base(inputs, training=True)
        x = layers.GlobalAveragePooling2D()(x)

    elif base_model == "resnet50":
        # Use ResNet50 as base (deeper, more accurate)
        base = keras.applications.ResNet50(
            input_shape=input_shape,
            include_top=False,
            weights="imagenet",
        )
        base.trainable = True
        x = base(inputs, training=True)
        x = layers.GlobalAveragePooling2D()(x)

    elif base_model == "vgg16":
        # Use VGG16 as base
        base = keras.applications.VGG16(
            input_shape=input_shape,
            include_top=False,
            weights="imagenet",
        )
        base.trainable = True
        x = base(inputs, training=True)
        x = layers.GlobalAveragePooling2D()(x)

    else:  # custom CNN
        # Custom lightweight CNN architecture
        x = layers.Conv2D(32, (3, 3), activation="relu")(inputs)
        x = layers.MaxPooling2D(2, 2)(x)
        x = layers.Conv2D(64, (3, 3), activation="relu")(x)
        x = layers.MaxPooling2D(2, 2)(x)
        x = layers.Conv2D(128, (3, 3), activation="relu")(x)
        x = layers.MaxPooling2D(2, 2)(x)
        x = layers.Conv2D(128, (3, 3), activation="relu")(x)
        x = layers.MaxPooling2D(2, 2)(x)
        x = layers.Flatten()(x)

    # Add dense layers
    x = layers.Dense(512, activation="relu")(x)
    x = layers.Dropout(dropout_rate)(x)
    x = layers.Dense(256, activation="relu")(x)
    x = layers.Dropout(dropout_rate)(x)

    # Output layer
    outputs = layers.Dense(num_classes, activation="softmax")(x)

    model = keras.Model(inputs, outputs)

    # Compile model
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
        loss="categorical_crossentropy",
        metrics=["accuracy", "top_k_categorical_accuracy"],
    )

    return model


def build_transfer_learning_model(
    num_classes: int,
    input_shape: tuple[int, int, int] = (224, 224, 3),
    base_model_name: str = "mobilenet",
    freeze_base: bool = False,
    dropout_rate: float = 0.5,
) -> keras.Model:
    """
    Build a transfer learning model with fine-tuning options.

    Args:
        num_classes: Number of output classes
        input_shape: Input image shape
        base_model_name: Base model to use
        freeze_base: Whether to freeze base model weights
        dropout_rate: Dropout rate

    Returns:
        Compiled Keras model
    """
    # Select base model
    base_models = {
        "mobilenet": keras.applications.MobileNetV2,
        "resnet50": keras.applications.ResNet50,
        "vgg16": keras.applications.VGG16,
        "efficientnet": keras.applications.EfficientNetB0,
    }

    if base_model_name not in base_models:
        raise ValueError(f"Unknown base model: {base_model_name}")

    base_model_class = base_models[base_model_name]
    base = base_model_class(
        input_shape=input_shape,
        include_top=False,
        weights="imagenet",
    )

    if freeze_base:
        base.trainable = False
    else:
        # Fine-tune last few layers
        base.trainable = True
        for layer in base.layers[:-10]:
            layer.trainable = False

    # Build model
    inputs = keras.Input(shape=input_shape)
    x = base(inputs, training=not freeze_base)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dense(512, activation="relu")(x)
    x = layers.Dropout(dropout_rate)(x)
    x = layers.Dense(256, activation="relu")(x)
    x = layers.Dropout(dropout_rate)(x)
    outputs = layers.Dense(num_classes, activation="softmax")(x)

    model = keras.Model(inputs, outputs)

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.001),
        loss="categorical_crossentropy",
        metrics=["accuracy", "top_k_categorical_accuracy"],
    )

    return model

