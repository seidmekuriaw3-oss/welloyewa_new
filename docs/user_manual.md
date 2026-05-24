ደስ ብሎኛል! በቅደም ተከተል እንቀጥላለን።

## ፋይል #299: `docs/user_manual.md`

```markdown
# Wolloyewa Store Bot - User Manual

## 📖 ይዘቶች

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Customer Guide](#customer-guide)
4. [Vendor Guide](#vendor-guide)
5. [Admin Guide](#admin-guide)
6. [Frequently Asked Questions](#frequently-asked-questions)
7. [Troubleshooting](#troubleshooting)

---

## Introduction

Wolloyewa Store Bot is Ethiopia's first modern e-commerce Telegram bot that connects buyers with sellers. This manual will guide you through all features available on the platform.

### Key Features

| Feature | Description |
|---------|-------------|
| 🛍️ Product Catalog | Browse products by category |
| 🔍 Search | Find products by name or keyword |
| 🛒 Shopping Cart | Add multiple items before checkout |
| 💳 Payments | Pay via Chapa, Telebirr, or CBE Birr |
| 📦 Order Tracking | Track your orders in real-time |
| ⭐ Reviews | Rate and review products |
| ❤️ Wishlist | Save favorite products |
| 🏪 Vendor Dashboard | Manage products and orders |

---

## Getting Started

### 1. Start the Bot

Open Telegram and search for **@WolloyewaBot** or click this link: [t.me/WolloyewaBot](https://t.me/WolloyewaBot)

Click **Start** or send `/start`

### 2. Main Menu

After starting, you'll see the main menu:

```
🌟 Welcome to Wolloyewa Store!

📁 Categories
🛍️ Products
🔍 Search
🛒 Cart
👤 Profile
📦 My Orders
⭐ Wishlist
❓ Help
```

### 3. Language Selection

The bot supports three languages:
- 🇪🇹 Amharic (አማርኛ) - Default
- 🇬🇧 English
- 🇪🇹 Oromo (Oromiffa)

To change language: Go to **Profile → Change Language**

---

## Customer Guide

### Browsing Products

#### By Category
1. Click **📁 Categories** or send `/menu`
2. Select a category (Electronics, Clothing, Food, etc.)
3. Browse products in that category

#### By Search
1. Click **🔍 Search** or send `/search`
2. Type product name or keyword
3. Filter results by price, category, or rating

### Product Details

Click on any product to see:
- 📷 Product images
- 💰 Price (original and discounted)
- 📦 Stock status
- ⭐ Rating and reviews
- 📝 Description
- 🏪 Vendor information

### Shopping Cart

#### Add to Cart
1. Open a product
2. Click **🛒 Add to Cart**
3. Choose quantity
4. Confirm

#### Manage Cart
- Send `/cart` or click **🛒 Cart**
- Update quantities using +/-
- Remove items with 🗑️
- Clear entire cart

### Checkout Process

1. **Go to Cart** → Click **✅ Checkout**

2. **Select Address**
   - Choose saved address or add new one
   - Enter recipient name and phone

3. **Select Payment Method**
   - 💳 Chapa (Card, Telebirr, CBE Birr)
   - 📱 Telebirr (Direct)
   - 🏦 CBE Birr
   - 💵 Cash on Delivery

4. **Review Order**
   - Check items and totals
   - Confirm order

5. **Payment**
   - Follow payment instructions
   - You'll receive confirmation

### Order Tracking

#### Track Order
- Send `/orders` or click **📦 My Orders**
- Select order to see status

#### Order Status Meanings
| Status | Meaning |
|--------|---------|
| ⏳ Pending | Order received, waiting confirmation |
| ✅ Confirmed | Payment verified |
| 🔄 Processing | Being prepared |
| 🚚 Shipped | On the way |
| 📦 Delivered | Arrived at destination |
| ❌ Cancelled | Order cancelled |

### Reviews & Ratings

#### Leave a Review
1. Go to **My Orders**
2. Select delivered order
3. Click **📝 Write Review**
4. Rate 1-5 stars
5. Write your feedback

#### View Reviews
- Open any product
- Scroll to **Reviews** section

### Wishlist

#### Add to Wishlist
- Open any product
- Click **❤️ Add to Wishlist**

#### Manage Wishlist
- Send `/wishlist`
- Remove items
- Add all to cart

### Profile Management

#### View Profile
- Send `/profile`
- View your information

#### Update Information
- **Phone Number**: Share contact or type manually
- **Email**: Type new email address
- **Language**: Change bot language

---

## Vendor Guide

### Becoming a Vendor

1. Complete customer registration
2. Go to **Profile → Become a Vendor**
3. Submit application with:
   - Business name
   - Business license number
   - TIN number
   - Business address
4. Wait for admin approval (24-48 hours)

### Vendor Dashboard

After approval, access **Vendor Panel**:

```
🏪 Vendor Panel
├── 📦 My Products
├── ➕ Add Product
├── 📋 Orders
├── 📊 Statistics
└── ⚙️ Settings
```

### Managing Products

#### Add Product
1. Go to **Vendor Panel → Add Product**
2. Fill in:
   - Product name (English & Amharic)
   - Description
   - Price
   - Stock quantity
   - Category
   - Images (up to 5)
3. Submit for approval

#### Edit Product
1. Go to **My Products**
2. Select product
3. Click **✏️ Edit**
4. Update information
5. Save changes

#### Manage Stock
- View low stock alerts
- Update quantities in real-time
- Mark products as out of stock

### Processing Orders

1. Go to **Vendor Panel → Orders**
2. View pending orders
3. Update order status:
   - Confirm → Processing → Shipped → Delivered
4. Add tracking number (if applicable)

### Vendor Statistics

View in **Vendor Panel → Statistics**:
- 📊 Daily/weekly/monthly sales
- 💰 Revenue breakdown
- 📦 Top selling products
- ⭐ Average rating

---

## Admin Guide

### Admin Access

Admin commands are only available to users with admin role:

```
🔧 Admin Commands
├── /admin - Open admin panel
├── /stats - View system stats
└── /broadcast - Send mass message
```

### Admin Dashboard

#### Access
1. Send `/admin`
2. Select option from menu

#### Dashboard Sections

**📊 Overview**
- Daily/weekly/monthly sales
- User statistics
- Order status breakdown

**👥 Users**
- View all users
- Search/filter users
- Suspend/activate accounts
- Change user roles

**🏪 Vendors**
- View vendor applications
- Approve/reject vendors
- Monitor vendor performance

**📦 Products**
- Review pending products
- Approve/reject products
- Manage categories
- Feature products

**📋 Orders**
- View all orders
- Update any order status
- Process refunds
- Handle disputes

**📊 Reports**
- Generate sales reports
- Export data (CSV/Excel)
- View analytics

### Broadcasting

Send messages to all users:

1. Send `/broadcast`
2. Select target audience:
   - All users
   - Active users (last 7 days)
   - New users (last 30 days)
   - Vendors only
3. Type your message
4. Confirm and send

### System Management

#### Backup
- Automatic daily backups at 2 AM
- Manual backup: `./scripts/backup.sh`

#### Monitoring
- Check system health: `/health`
- View metrics: `/metrics`
- Monitor logs: `docker-compose logs -f`

---

## Frequently Asked Questions

### General Questions

**Q: How do I contact support?**
A: Send `/feedback` or email support@wolloyewa.com

**Q: Is my personal information safe?**
A: Yes, we use encryption and follow GDPR guidelines.

**Q: What payment methods are accepted?**
A: Chapa, Telebirr, CBE Birr, and Cash on Delivery.

### Order Questions

**Q: How long does delivery take?**
A: 
- Addis Ababa: 2-5 business days
- Other cities: 5-10 business days

**Q: Can I cancel my order?**
A: Yes, before it's shipped. Go to **My Orders → Cancel**.

**Q: How do I return a product?**
A: Within 14 days of delivery, contact support.

**Q: What if I receive a damaged product?**
A: Contact support immediately with photos.

### Payment Questions

**Q: Is payment secure?**
A: Yes, all payments are processed through verified gateways.

**Q: Can I pay with foreign currency?**
A: No, all prices are in Ethiopian Birr (ETB).

**Q: What is Cash on Delivery?**
A: Pay when you receive the product.

### Vendor Questions

**Q: How much does it cost to be a vendor?**
A: Basic plan is free. Premium plans start at 499 ETB/month.

**Q: When do I get paid?**
A: Payments are processed 7 days after delivery.

**Q: Can I have multiple stores?**
A: Yes, with Professional and Enterprise plans.

---

## Troubleshooting

### Common Issues

#### Issue: Bot not responding
**Solution:**
- Check internet connection
- Restart Telegram app
- Send `/start` again

#### Issue: Can't add to cart
**Solution:**
- Check if product is in stock
- Clear cart and try again
- Contact support if issue persists

#### Issue: Payment failed
**Solution:**
- Check balance
- Try different payment method
- Contact your bank
- Try again after 10 minutes

#### Issue: Order not showing
**Solution:**
- Wait 5 minutes and refresh
- Check spam folder for email
- Contact support with order number

#### Issue: Can't login
**Solution:**
- Clear bot data: Settings → Privacy → Clear history
- Restart bot with `/start`
- Re-register if needed

### Error Messages

| Error | Solution |
|-------|----------|
| "Product not found" | Product may be removed or hidden |
| "Insufficient stock" | Product is out of stock |
| "Invalid coupon" | Coupon expired or doesn't exist |
| "Address required" | Add shipping address in profile |
| "Payment timeout" | Try again or use different method |

### Contact Support

If issues persist:

1. **Telegram**: @wolloyewa_support
2. **Email**: support@wolloyewa.com
3. **Phone**: +251-XXX-XXX-XXX

Provide:
- Your user ID (from profile)
- Screenshots if applicable
- Steps to reproduce issue

---

## Tips & Tricks

### 💡 Pro Tips

1. **Save addresses** in profile for faster checkout
2. **Use wishlist** to track price drops
3. **Enable notifications** for order updates
4. **Write detailed reviews** to help other buyers
5. **Follow our channel** for promotions

### 🚀 Keyboard Shortcuts

| Command | Action |
|---------|--------|
| `/start` | Start/restart bot |
| `/menu` | Main menu |
| `/search` | Search products |
| `/cart` | View cart |
| `/orders` | My orders |
| `/profile` | My profile |
| `/wishlist` | My wishlist |
| `/feedback` | Send feedback |
| `/help` | Help menu |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-01-01 | Initial release |
| 1.1.0 | 2024-03-15 | Added wishlist feature |
| 1.2.0 | 2024-06-01 | Multi-language support |
| 1.3.0 | 2024-09-10 | Vendor dashboard |

---

## Support & Feedback

We value your feedback!

- 📝 Send feedback: `/feedback`
- 💬 Join our community: [t.me/wolloyewa_community](https://t.me/wolloyewa_community)
- ⭐ Rate us on Telegram Bot Store

---

**Thank you for choosing Wolloyewa Store Bot!**

© 2024 Wolloyewa Technologies PLC. All rights reserved.
```

