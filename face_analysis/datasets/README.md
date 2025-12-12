# Dataset Structure

Place your training datasets in the following structure:

## Skin Types Dataset
```
datasets/
  skin_types/
    train/
      dry/
        image1.jpg
        image2.jpg
        ...
      oily/
        image1.jpg
        image2.jpg
        ...
      combination/
        image1.jpg
        image2.jpg
        ...
      normal/
        image1.jpg
        image2.jpg
        ...
      sensitive/
        image1.jpg
        image2.jpg
        ...
    validation/
      dry/
        ...
      oily/
        ...
      combination/
        ...
      normal/
        ...
      sensitive/
        ...
    test/
      dry/
        ...
      oily/
        ...
      combination/
        ...
      normal/
        ...
      sensitive/
        ...
```

## Skin Concerns Dataset
```
datasets/
  skin_concerns/
    train/
      acne/
        image1.jpg
        image2.jpg
        ...
      wrinkles/
        image1.jpg
        image2.jpg
        ...
      dark_spots/
        image1.jpg
        image2.jpg
        ...
      dryness/
        image1.jpg
        image2.jpg
        ...
      redness/
        image1.jpg
        image2.jpg
        ...
      texture/
        image1.jpg
        image2.jpg
        ...
    validation/
      (same structure as train)
    test/
      (same structure as train)
```

## Notes
- Images should be in common formats (jpg, png, jpeg)
- Recommended image size: 224x224 or 256x256 pixels
- Ensure balanced datasets across all classes
- Use train/validation/test split (e.g., 70/15/15 or 80/10/10)

