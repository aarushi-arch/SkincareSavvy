# Virtual Try-On Feature

## Overview
The Virtual Try-On feature allows users to visualize where to apply skincare products on their face using MediaPipe face landmark detection. When viewing a product detail page, users can click the "Try On" button to see green highlighted zones on their previously uploaded face image.

## How It Works

### 1. Face Analysis
- Users first upload their face image through the face analysis page (`/face-analysis/`)
- The system stores the analyzed image in the session for later use
- This image is then available for the try-on feature

### 2. Product Detail Page
- Each product detail page now has a "Try On" button
- When clicked, it fetches the user's stored face image
- The system uses MediaPipe to detect facial landmarks
- Based on the product category, specific zones are highlighted

### 3. Zone Mapping
Different product categories map to different facial zones:

| Category | Zones |
|----------|-------|
| Eye Care / Eye Cream | Left eye, Right eye |
| Moisturizer / Sunscreen | Full face |
| Serum | Left cheek, Right cheek |
| Spot Treatment | Nose |
| Acne Treatment | Nose, Forehead, Chin |
| Cleanser / Face Wash / Toner | Full face |
| Mask / Face Mask / Exfoliator | Full face |
| Lip Care / Lip Balm | Lips |

## Technical Implementation

### Files Created/Modified

1. **recommendations/skincare_zones.py** (NEW)
   - Core logic for MediaPipe face landmark detection
   - Zone mapping for different product categories
   - Image processing and overlay generation

2. **recommendations/views.py** (MODIFIED)
   - Added `tryon_zones()` view endpoint
   - Handles POST requests with product category
   - Returns base64 encoded image with zones

3. **recommendations/urls.py** (MODIFIED)
   - Added route: `/recommendations/tryon-zones/`

4. **recommendations/templates/recommendations/product_detail.html** (MODIFIED)
   - Added "Try On" button
   - Added modal for displaying the visualization
   - Added JavaScript for handling the try-on interaction

5. **face_analysis/views.py** (ALREADY STORES IMAGE)
   - Already stores analyzed image in session as `last_analysis_image`

### Dependencies
- OpenCV (cv2)
- MediaPipe
- NumPy
- Django sessions

### API Endpoint

**POST** `/recommendations/tryon-zones/`

Request body:
```json
{
  "category": "eye care"
}
```

Response:
```json
{
  "image_base64": "base64_encoded_image_data",
  "zones": [
    {
      "label": "Left Eye",
      "points": [[x1, y1], [x2, y2], ...]
    }
  ]
}
```

Error response:
```json
{
  "error": "No face image found. Please complete a face analysis first."
}
```

## User Flow

1. User completes face analysis at `/face-analysis/`
2. System stores the analyzed face image in session
3. User browses recommended products
4. User clicks "View Description" on a product card
5. On product detail page, user clicks "Try On" button
6. Modal opens showing their face with green zones indicating where to apply the product
7. User can close the modal and continue browsing

## Testing

Run the test script:
```bash
python test_tryon_zones.py
```

This will test the zone detection on different product categories using the `debug_face.jpg` image.

## Future Enhancements

1. **Multiple Face Images**: Allow users to upload multiple images and select which one to use
2. **AR Try-On**: Real-time webcam try-on with live zone highlighting
3. **Product Color Overlay**: Show actual product color instead of green
4. **Animation**: Animate the application process
5. **Before/After**: Show side-by-side comparison
6. **Save Try-On**: Allow users to save their try-on images
7. **Share**: Social media sharing of try-on results

## Troubleshooting

### "No face image found" error
- User needs to complete face analysis first
- Session may have expired (default Django session timeout)
- Solution: Redirect user to face analysis page

### "No face detected in the image" error
- The stored image doesn't contain a detectable face
- MediaPipe couldn't find facial landmarks
- Solution: Ask user to upload a clearer face image

### Zones not appearing correctly
- Check product category mapping in `CATEGORY_ZONE_MAP`
- Verify landmark indices are correct
- Test with different face images

## Performance Considerations

- MediaPipe processing takes ~100-300ms per image
- Images are cached in session (memory usage consideration)
- Consider implementing image compression for session storage
- For high traffic, consider moving to Redis sessions

## Security Notes

- Images are stored in session (server-side)
- Base64 encoding used for transmission
- CSRF protection enabled on endpoint
- Consider adding rate limiting for production
