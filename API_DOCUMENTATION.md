# SkincareSavvy REST API Documentation

## Overview
This document provides a comprehensive overview of all REST API endpoints available in the SkincareSavvy application.

---

## 1. Shop APIs

### Base URL: `/shop/`

#### 1.1 Health Check
- **Endpoint**: `GET /shop/health/`
- **Authentication**: Not required
- **Description**: Check if the shop service is running
- **Response**:
```json
{
  "status": "shop app working"
}
```

#### 1.2 Add to Cart
- **Endpoint**: `POST /shop/add-to-cart/`
- **Authentication**: Required (IsAuthenticated)
- **Description**: Add a product to the user's shopping cart
- **Request Body**:
```json
{
  "product_id": 123,
  "quantity": 1
}
```
- **Success Response** (200):
```json
{
  "message": "Product added to shelf"
}
```
- **Error Responses**:
  - 400: `{"error": "Product ID required"}`
  - 404: `{"error": "Product not found"}`

#### 1.3 PayPal Create Order
- **Endpoint**: `POST /shop/paypal/create-order/`
- **Authentication**: Required
- **Description**: Create a PayPal order for checkout
- **Request Body**:
```json
{
  "product_id": 123  // Optional, if not provided uses cart
}
```
- **Success Response**:
```json
{
  "id": "paypal_order_id"
}
```
- **Error Responses**:
  - 400: `{"error": "Cart is empty"}`
  - 405: `{"error": "POST required"}`
  - 500: `{"error": "error message"}`

#### 1.4 PayPal Capture Order
- **Endpoint**: `POST /shop/paypal/capture-order/`
- **Authentication**: Required
- **Description**: Capture a PayPal payment and create order
- **Request Body**:
```json
{
  "paypal_order_id": "paypal_order_id"
}
```
- **Success Response**:
```json
{
  "status": "success",
  "order_id": 456
}
```
- **Error Responses**:
  - 400: `{"error": "Order ID mismatch or session expired"}`
  - 400: `{"error": "Payment not completed"}`
  - 400: `{"error": "Invalid JSON"}`
  - 405: `{"error": "POST required"}`
  - 500: `{"error": "error message"}`

---

## 2. Face Analysis APIs

### Base URL: `/face-analysis/`

#### 2.1 Realtime Analysis
- **Endpoint**: `POST /face-analysis/realtime-analyze/`
- **Authentication**: Required
- **Description**: Analyze a face image in real-time using dual AI models (YOLO + MobileNet)
- **Request**: Multipart form data with `frame` (image file)
- **Success Response**:
```json
{
  "skin_type": "oily",
  "concerns": [
    {
      "name": "acne",
      "confidence": 85
    }
  ],
  "face_bbox": [x1, y1, x2, y2]
}
```
- **Error Responses**:
  - 400: `{"error": "Could not decode frame"}`
  - 500: `{"error": "error message"}`

#### 2.2 YOLO Detection Only
- **Endpoint**: `POST /face-analysis/yolo-detect/`
- **Authentication**: Required
- **Description**: Run YOLO detection only (faster, for real-time streaming)
- **Request**: Multipart form data with `frame` (image file)
- **Success Response**:
```json
{
  "status": "success",
  "face_bbox": [x1, y1, x2, y2],
  "detections": [
    {
      "label": "acne",
      "confidence": 0.85,
      "box": [x1, y1, x2, y2]
    }
  ]
}
```
- **Error Responses**:
  - 400: `{"error": "Could not decode frame"}`
  - 500: `{"error": "error message"}`

#### 2.3 Unified Analysis
- **Endpoint**: `POST /face-analysis/unified-analyze/`
- **Authentication**: Required
- **Description**: Full unified pipeline analysis (MediaPipe + YOLO + MobileNet)
- **Request**: Multipart form data with `image` (image file)
- **Success Response**:
```json
{
  "status": "success",
  "face_bbox": [x1, y1, x2, y2],
  "yolo": {
    "detections": [...],
    "concern_counts": {...},
    "top_concern": "acne",
    "severity": "Moderate"
  },
  "mobilenet": {
    "skin_type": {...},
    "skin_concerns": {...}
  },
  "image_base64": "base64_encoded_image"
}
```
- **Error Response**:
  - 500: `{"error": "error message"}`

#### 2.4 Get Product Recommendations
- **Endpoint**: `POST /face-analysis/get-recommendations/`
- **Authentication**: Required
- **Description**: Get product recommendations for a specific skin concern
- **Request Body**:
```json
{
  "concern": "acne",
  "allergies": "salicylic acid,benzoyl peroxide"  // Optional
}
```
- **Success Response**:
```json
{
  "success": true,
  "concern": "acne",
  "products": [
    {
      "id": 123,
      "name": "Product Name",
      "brand": "Brand Name",
      "price": 1500,
      "match_score": 95,
      "match_reason": "Strong match for acne treatment",
      "image_url": "https://...",
      "link": "https://...",
      "category": "treatment"
    }
  ]
}
```
- **Error Responses**:
  - 400: `{"error": "No concern specified"}`
  - 400: `{"error": "Invalid concern selected"}`
  - 500: `{"error": "error message"}`

---

## 3. Recommendations APIs

### Base URL: `/recommendations/`

#### 3.1 Get Filtered Options
- **Endpoint**: `POST /recommendations/get-filtered-options/`
- **Authentication**: Not required
- **Description**: Get filtered product options based on criteria
- **Request Body**:
```json
{
  "skin_type": "oily",
  "skin_concern": "acne",
  "category": "moisturizer"
}
```
- **Success Response**:
```json
{
  "notable_effects": ["hydrating", "anti-aging"],
  "product_names": ["Product 1", "Product 2"]
}
```
- **Error Response**:
```json
{
  "error": "error message",
  "notable_effects": [],
  "product_names": []
}
```

#### 3.2 Virtual Try-On Zones
- **Endpoint**: `POST /recommendations/tryon-zones/`
- **Authentication**: Required
- **Description**: Apply virtual skincare product zones to face image
- **Request Body**:
```json
{
  "category": "moisturizer"
}
```
- **Success Response**:
```json
{
  "status": "success",
  "image_base64": "base64_encoded_result",
  "zones_applied": ["forehead", "cheeks", "nose"]
}
```
- **Error Responses**:
  - 400: `{"error": "No face image found. Please complete a face analysis first."}`
  - 500: `{"error": "error message"}`

---

## 4. User Management APIs

### Base URL: `/`

#### 4.1 Add to Shelf
- **Endpoint**: `POST /add-to-shelf/<product_id>/`
- **Authentication**: Required
- **Description**: Add a product to user's personal shelf
- **Response** (AJAX):
```json
{
  "status": "success",
  "message": "Product Name added to your shelf!",
  "created": true,
  "redirect_url": "/shop/my-orders/"
}
```
- **Error Responses**:
  - 404: `{"status": "error", "message": "Product not found"}`
  - 500: `{"status": "error", "message": "Error adding to shelf"}`

---

## 5. Chat APIs

### Base URL: `/chat/`

#### 5.1 Send Message
- **Endpoint**: `POST /chat/user/`
- **Authentication**: Required
- **Description**: Send a chat message (AJAX support)
- **Request**: Form data with `message` field
- **Success Response** (AJAX):
```json
{
  "success": true,
  "message": "message content",
  "timestamp": "2026-05-22T10:30:00Z"
}
```
- **Error Response** (AJAX):
```json
{
  "success": false,
  "error": "Message cannot be empty."
}
```

---

## Authentication

Most APIs require authentication using Django's session-based authentication. For authenticated endpoints:

1. User must be logged in
2. CSRF token must be included in POST requests
3. Session cookie must be present

### CSRF Token
Include CSRF token in request headers:
```
X-CSRFToken: <csrf_token_value>
```

---

## Common Response Codes

- **200 OK**: Request successful
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Permission denied
- **404 Not Found**: Resource not found
- **405 Method Not Allowed**: Wrong HTTP method
- **500 Internal Server Error**: Server error

---

## Rate Limiting

Currently, no rate limiting is implemented. Consider adding rate limiting for production use.

---

## Notes

1. All monetary values are in Nepali Rupees (NPR)
2. Image uploads should be in JPEG or PNG format
3. Maximum file size for image uploads: 10MB
4. Face analysis requires clear, well-lit photos for best results
5. Product recommendations are personalized based on skin analysis results

---

## Example Usage

### JavaScript Fetch Example
```javascript
// Add to Cart
fetch('/shop/add-to-cart/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': getCsrfToken()
  },
  body: JSON.stringify({
    product_id: 123,
    quantity: 1
  })
})
.then(response => response.json())
.then(data => console.log(data));

// Face Analysis
const formData = new FormData();
formData.append('frame', imageFile);

fetch('/face-analysis/realtime-analyze/', {
  method: 'POST',
  headers: {
    'X-CSRFToken': getCsrfToken()
  },
  body: formData
})
.then(response => response.json())
.then(data => console.log(data));
```

### Python Requests Example
```python
import requests

# Login first to get session
session = requests.Session()
session.post('http://localhost:8000/login/', data={
    'username': 'user',
    'password': 'pass'
})

# Add to cart
response = session.post('http://localhost:8000/shop/add-to-cart/', json={
    'product_id': 123,
    'quantity': 1
})
print(response.json())
```

---

## Future API Enhancements

Consider adding:
1. API versioning (e.g., `/api/v1/`)
2. Token-based authentication (JWT)
3. Rate limiting
4. API documentation with Swagger/OpenAPI
5. Pagination for list endpoints
6. Filtering and sorting parameters
7. Batch operations support
8. Webhooks for order status updates
