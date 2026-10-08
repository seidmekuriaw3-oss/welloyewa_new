## ፋይል #298: `docs/api_docs.md`

```markdown
# Wolloyewa Store Bot - API Documentation

## Base URL

```
https://api.wolloyewa.com/api/v1
```

For local development:
```
http://localhost:8000/api/v1
```

## Authentication

Most endpoints require JWT authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your_access_token>
```

### Get Access Token

```http
POST /users/login
```

**Request Body:**
```json
{
  "telegram_id": 123456789,
  "init_data": "<raw Telegram.WebApp.initData>"
}
```
Send `{"phone_number":"0912345678","password":"..."}` instead for a
phone/password account. A Telegram ID by itself is not accepted as proof of
identity.

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": 1,
    "telegram_id": 123456789,
    "first_name": "John",
    "role": "customer"
  }
}
```

## Endpoints

### Users

#### Register User
```http
POST /users/register
```

**Request Body:**
```json
{
  "telegram_id": 123456789,
  "init_data": "<raw Telegram.WebApp.initData>",
  "username": "john_doe",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "0912345678",
  "email": "john@example.com",
  "language": "am"
}
```

#### Get Current User
```http
GET /users/me
```

**Headers:** `Authorization: Bearer <token>`

#### Update User
```http
PUT /users/me
```

**Request Body:**
```json
{
  "first_name": "Jonathan",
  "phone_number": "0987654321"
}
```

### Products

#### List Products
```http
GET /products?page=1&page_size=20&category=electronics&min_price=100&max_price=5000
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| page | int | Page number (default: 1) |
| page_size | int | Items per page (default: 20, max: 100) |
| category | string | Filter by category |
| vendor_id | int | Filter by vendor |
| min_price | float | Minimum price |
| max_price | float | Maximum price |
| search | string | Search query |

#### Get Product
```http
GET /products/{product_id}
```

#### Create Product (Vendor only)
```http
POST /products
```

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "Smartphone X100",
  "price": 15000.00,
  "stock_quantity": 50,
  "sku": "PHONE001",
  "category": "electronics",
  "description": "Latest smartphone"
}
```

### Orders

#### Create Order
```http
POST /orders
```

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "items": [
    {"product_id": 1, "quantity": 2},
    {"product_id": 2, "quantity": 1}
  ],
  "payment_method": "chapa",
  "shipping_address": "123 Main St, Addis Ababa",
  "shipping_city": "Addis Ababa",
  "shipping_phone": "0912345678",
  "customer_notes": "Leave at gate"
}
```

#### Get My Orders
```http
GET /orders
```

**Headers:** `Authorization: Bearer <token>`

#### Track Order (Public)
```http
GET /orders/track/{order_number}?email=user@example.com
```

### Payments

#### Initiate Payment
```http
POST /payments/initiate
```

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "order_id": 1,
  "payment_method": "chapa",
  "callback_url": "https://example.com/callback"
}
```

#### Verify Payment
```http
GET /payments/verify/{transaction_id}?method=chapa
```

### Analytics

#### Dashboard Summary
```http
GET /analytics/dashboard
```

**Headers:** `Authorization: Bearer <token>`

#### Sales Report
```http
GET /analytics/sales/summary?start_date=2024-01-01&end_date=2024-01-31
```

## Error Responses

### 400 Bad Request
```json
{
  "error": "VALIDATION_ERROR",
  "message": "Invalid phone number format",
  "status_code": 400
}
```

### 401 Unauthorized
```json
{
  "error": "AUTHENTICATION_ERROR",
  "message": "Invalid or expired token",
  "status_code": 401
}
```

### 403 Forbidden
```json
{
  "error": "PERMISSION_DENIED",
  "message": "You don't have permission to perform this action",
  "status_code": 403
}
```

### 404 Not Found
```json
{
  "error": "NOT_FOUND",
  "message": "Product not found",
  "status_code": 404
}
```

### 429 Too Many Requests
```json
{
  "error": "RATE_LIMIT_EXCEEDED",
  "message": "Rate limit exceeded. Please try again in 60 seconds.",
  "status_code": 429,
  "details": {"retry_after": 60}
}
```

## Rate Limits

| Endpoint Type | Limit | Window |
|---------------|-------|--------|
| General API | 60 requests | 1 minute |
| Search | 20 requests | 1 minute |
| Checkout | 10 requests | 1 minute |
| Admin endpoints | 120 requests | 1 minute |

## Webhooks

### Payment Webhooks

Chapa:
```
POST /webhook/chapa
```

Telebirr:
```
POST /webhook/telebirr
```

CBE Birr:
```
POST /webhook/cbe-birr
```

Telegram:
```
POST /webhook/telegram
```

## SDK Examples

### Python
```python
import requests

def login_with_telegram(telegram_user_id, raw_init_data):
    # Pass the exact initData string from Telegram.WebApp.initData.
    response = requests.post(
        "https://api.wolloyewa.com/api/v1/users/login",
        json={"telegram_id": telegram_user_id, "init_data": raw_init_data},
    )
    response.raise_for_status()
    return response.json()["access_token"]

# For phone/password accounts, use this instead:
response = requests.post(
    "https://api.wolloyewa.com/api/v1/users/login",
    json={"phone_number": "0912345678", "password": user_password},
)
token = response.json()["access_token"]

# Get products
headers = {"Authorization": f"Bearer {token}"}
products = requests.get(
    "https://api.wolloyewa.com/api/v1/products",
    headers=headers
)
```

### JavaScript
```javascript
// Telegram Mini App login: pass Telegram's raw signed initData unchanged.
const webApp = window.Telegram?.WebApp;
const telegramUserId = webApp?.initDataUnsafe?.user?.id;
if (!webApp?.initData || !telegramUserId) {
  throw new Error('Open the store inside Telegram to sign in.');
}
const response = await fetch('https://api.wolloyewa.com/api/v1/users/login', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    telegram_id: telegramUserId,
    init_data: webApp.initData
  })
});
const {access_token} = await response.json();

// Get products
const products = await fetch('https://api.wolloyewa.com/api/v1/products', {
  headers: {'Authorization': `Bearer ${access_token}`}
});
```

Phone/password login uses the same endpoint with
`{"phone_number":"0912345678","password":"..."}`. A bare Telegram ID is
rejected. Password recovery uses
`POST /api/v1/users/password-reset/request` followed by
`POST /api/v1/users/password-reset/confirm`.

## Support

For API support, contact:
- Email: api-support@wolloyewa.com
- Telegram: @wolloyewa_api_support
```


ወደ ቀጣዩ ፋይል `docs/deployment.md` እንሂድ?