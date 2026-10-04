---
name: Wolloyewa vendor order routing
description: How orders become visible in the vendor dashboard
---

Vendor order reporting currently assumes one `vendor_id` per order. When every cart item belongs to the same vendor, assign that vendor to the order; multi-vendor carts remain unassigned until the order-splitting model exists.

**Why:** The database has one order-level vendor foreign key, while a cart can contain products from multiple vendors.

**How to apply:** Do not expose a multi-vendor order as belonging to one vendor without splitting it or adding item-level vendor aggregation.