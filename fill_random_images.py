import pandas as pd
import random
import os

# Path to the CSV file
file_path = "recommendations/notebooks/updated_products_with_images_npr.csv"

# Load your CSV
if not os.path.exists(file_path):
    print(f"Error: {file_path} not found.")
    exit(1)

df = pd.read_csv(file_path)

IMAGE_COLUMN = "image_url"

# Identify empty image slots
def is_empty(val):
    return pd.isna(val) or str(val).strip() == "" or not str(val).startswith("http")

# Get a pool of valid image URLs
valid_images = df[IMAGE_COLUMN].dropna().tolist()
valid_images = [img for img in valid_images if isinstance(img, str) and img.startswith("http")]

if not valid_images:
    print("No valid images found to use as placeholders!")
    exit(1)

print(f"Found {len(valid_images)} valid images to use as a pool.")

# Fill empty slots
empty_indices = df[df[IMAGE_COLUMN].apply(is_empty)].index
print(f"Filling {len(empty_indices)} empty slots...")

for index in empty_indices:
    # Use a random choice from the valid pool
    random_img = random.choice(valid_images)
    df.at[index, IMAGE_COLUMN] = random_img

# Save back to CSV
df.to_csv(file_path, index=False)

print(f"✅ Successfully filled {len(empty_indices)} rows with random images.")
