# Skin Concerns Model Setup Guide

## Problem
Face analysis page shows only skin type, but not skin concerns (acne, wrinkles, pores, etc.).

## Quick Diagnosis

Run this command to see exactly what's wrong:

```bash
python face_analysis/diagnostics.py
```

This will tell you:
- ✓ Which models are active
- ✗ What files are missing
- ✓ Which classes are loaded
- ✗ Why the model isn't loading

## Solution

### Step 1: Check Model Status
Run the diagnostic script first:

```bash
python face_analysis/diagnostics.py
```

### Step 2: Fix Based on Diagnosis

**If no skin concerns model is active:**
1. Go to Django Admin `/admin/`
2. Click **Face Analysis → CNN Models**
3. Create a new model or select an existing one
4. Set **Model Type** to "Skin Concerns"
5. Upload the **Model File** (.h5 or .keras)
6. Upload the **Class Names File** (JSON)
7. Check **is_active**
8. Save

**If model is active but class_names_file is missing:**
1. Go to the model in Django Admin
2. Upload the **Class Names File**
3. Save

**If class_names_file exists but isn't readable:**
1. Verify it's a valid JSON file
2. Format should be one of:
   - **Dict format**: `{"acne": 0, "wrinkles": 1, "pores": 2}`
   - **List format**: `["acne", "wrinkles", "pores"]`
3. Delete and re-upload if corrupted

### Step 3: Verify Pipeline Loads Models
Run the diagnostic again to confirm:

```bash
python face_analysis/diagnostics.py
```

Look for:
```
✓ Skin concerns model loaded: True
✓ Skin concerns classes: 5 - ['acne', 'wrinkles', 'pores', 'dark_spots', 'blackheads']
```

### Step 4: Restart Server
```bash
python manage.py runserver
```

### Step 5: Test
Upload a face image to the face analysis page. You should now see all detected concerns.

## Class Names File Format

Your JSON file should have predictions in order matching your model output.

### Example 1: Dictionary Format
```json
{
  "acne": 0,
  "wrinkles": 1,
  "pores": 2,
  "dark_spots": 3,
  "blackheads": 4
}
```
The numbers are the class indices (must match your model's output order).

### Example 2: List Format
```json
["acne", "wrinkles", "pores", "dark_spots", "blackheads"]
```
Order in the list must match your model's output order.

## Troubleshooting

### Error: "models missing or incomplete"
- Run `python face_analysis/diagnostics.py`
- Check which model is missing
- Upload the missing model file

### Error: "classe names is empty"
- Model is loaded but class_names_file is missing
- Go to Django Admin and upload the class_names_file
- Restart server

### Error: "classes are missing. Check class_names_file in Django Admin"
- The class_names_file exists but can't be read
- Verify it's a valid JSON file
- Try re-uploading it

### No skin concerns shown but no errors
- Run diagnostics: `python face_analysis/diagnostics.py`
- Check if skin_concerns_classes is empty
- Verify the JSON file is correct format

## Manual Activation

If you need to activate a model via command line:

```bash
# Find the model ID
python face_analysis/diagnostics.py

# Then activate it (replace X with the ID)
python manage.py activate_model X
```

## Debug Logging

After uploading a face image, check the server logs for messages like:

```
✓ Skin Type: Oily
✓ Skin Concerns Predictions: 5 predictions received
✓ Detected Concerns (>0.5): ['acne', 'wrinkles']
✓ Main Concern: acne
```

If you see warnings or errors instead, that tells you exactly what's wrong.

## Support Files

- Management command: `python manage.py check_models`
- Diagnostic script: `python face_analysis/diagnostics.py`
- Setup guide: `face_analysis/SKIN_CONCERNS_SETUP.md`

