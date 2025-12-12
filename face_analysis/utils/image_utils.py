"""Image preprocessing utilities."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image


def load_image(image_path: Path | str) -> np.ndarray:
    """Load an image from file path."""
    img = Image.open(image_path)
    return np.array(img)


def preprocess_image(
    image: np.ndarray | Image.Image | bytes,
    target_size: tuple[int, int] = (224, 224),
    normalize: bool = True,
) -> np.ndarray:
    """
    Preprocess image for CNN input.

    Args:
        image: Input image (numpy array, PIL Image, or bytes)
        target_size: Target size (height, width)
        normalize: Whether to normalize to [0, 1]

    Returns:
        Preprocessed image as numpy array
    """
    # Convert bytes to PIL Image
    if isinstance(image, bytes):
        image = Image.open(BytesIO(image))

    # Convert PIL Image to numpy array
    if isinstance(image, Image.Image):
        image = np.array(image)

    # Ensure RGB
    if len(image.shape) == 2:  # Grayscale
        image = np.stack([image] * 3, axis=-1)
    elif image.shape[2] == 4:  # RGBA
        image = image[:, :, :3]

    # Resize
    pil_image = Image.fromarray(image)
    pil_image = pil_image.resize(target_size, Image.Resampling.LANCZOS)
    image = np.array(pil_image)

    # Normalize
    if normalize:
        image = image.astype(np.float32) / 255.0

    # Add batch dimension
    image = np.expand_dims(image, axis=0)

    return image


def save_image(image: np.ndarray, output_path: Path | str):
    """Save image to file."""
    if image.dtype != np.uint8:
        image = (image * 255).astype(np.uint8)
    img = Image.fromarray(image)
    img.save(output_path)

