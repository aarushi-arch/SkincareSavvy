import pandas as pd
import re
import os
import traceback

# Path to the CSV file
csv_path = 'recommendations/notebooks/updated_products_with_images.csv'
# Intermediate file
output_path = 'recommendations/notebooks/updated_products_with_images_npr.csv'

log_file = 'debug_log.txt'

def log(msg):
    with open(log_file, 'a') as f:
        f.write(str(msg) + '\n')

try:
    if os.path.exists(log_file):
        os.remove(log_file)

    if not os.path.exists(csv_path):
        log(f"Error: {csv_path} not found.")
    else:
        log(f"Reading {csv_path}...")
        # Use low_memory=False to avoid DtypeWarning
        df = pd.read_csv(csv_path, low_memory=False)
        log(f"Read {len(df)} rows.")

        def convert_to_npr(price_str):
            if pd.isna(price_str) or not str(price_str).strip():
                return price_str
            
            # Check if already starts with Rs. to avoid double conversion
            if str(price_str).startswith('Rs.'):
                return price_str
            
            # Find numeric values
            numbers = re.findall(r'[\d\.]+', str(price_str))
            if numbers:
                try:
                    val = float(numbers[0])
                    # Using 135 as the conversion rate
                    npr_val = int(val * 135)
                    return f"Rs. {npr_val:,}"
                except:
                    return price_str
            return price_str

        log("Converting prices...")
        df['price'] = df['price'].apply(convert_to_npr)

        log(f"Attempting to overwrite {csv_path}...")
        try:
            df.to_csv(csv_path, index=False)
            log("Successfully overwritten original CSV.")
            print(f"Successfully updated prices to NPR in {csv_path}")
        except Exception as e:
            log(f"Overwrite failed: {e}. Saving to intermediate file {output_path} instead.")
            df.to_csv(output_path, index=False)
            log(f"Saved to {output_path}")
            print(f"FAILED to update original CSV: {e}. Saved to {output_path} instead.")

except Exception as e:
    log(f"CRITICAL ERROR: {e}")
    log(traceback.format_exc())
    print(f"CRITICAL ERROR: {e}")
