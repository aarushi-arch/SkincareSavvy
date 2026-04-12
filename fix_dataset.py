import pandas as pd

df = pd.read_csv('recommendations/notebooks/updated_products_with_images_npr.csv')
before = len(df)

# Remove non-skincare products that slipped in
df = df[~df['product_name'].str.lower().str.contains('livon hair|hair gain|hair tonic', na=False)]
df.to_csv('recommendations/notebooks/updated_products_with_images_npr.csv', index=False)

sunscreen_count = len(df[df['product_type'] == 'Sunscreen'])
print(f"Removed {before - len(df)} non-skincare row(s)")
print(f"Total rows     : {len(df)}")
print(f"Sunscreen rows : {sunscreen_count}")
print()
print(df[df['product_type'] == 'Sunscreen'][['product_name', 'price', 'rating']].to_string(index=False))
