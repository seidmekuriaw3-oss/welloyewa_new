---
name: Wolloyewa admin routing architecture
description: How all admin_* Telegram callbacks are routed, and the multi-step text-input state system
---

## Routing architecture

Single `^admin_` pattern in dispatcher → `dashboard.admin_callback` (the central router).

**Static callbacks** use a long `elif action ==` chain.

**Dynamic (parameterised) callbacks** are checked with `action.startswith()` BEFORE the static chain:
- `admin_cat_edit_<id>` → `start_edit_category(cat_id)`
- `admin_cat_del_confirm_<id>` → `do_delete_category(cat_id)` ← must be BEFORE `admin_cat_del_`
- `admin_cat_del_<id>` → `confirm_delete_category(cat_id)` (shows confirm panel)
- `admin_cat_pick_<id>` → `do_create_product_with_category(cat_id)` (final step of add-product)
- `admin_approve_product_<id>` → `do_approve_product(product_id)` (sets status="active")
- `admin_reject_product_<id>` → `do_reject_product(product_id)` (sets status="rejected")
- `admin_suspend_user_<id>` → `confirm_suspend_user(uid)` (shows confirm panel)
- `admin_confirm_suspend_<id>` → `do_suspend_user(uid)`
- `admin_unsuspend_user_<id>` → `do_unsuspend_user(uid)` (sets status="active")
- `admin_approve_vendor_<id>` → `do_approve_vendor(vid, admin_id)` ← needs admin_id arg
- `admin_reject_vendor_<id>` → `do_reject_vendor(vid, reason="Admin rejection")` ← needs reason arg
- `admin_view_order_<id>` → `show_order_detail(oid)` with status-change buttons
- `admin_set_status_<oid>_<status>` → parse with `.split("_", 1)` → `do_change_order_status(oid, status)`

## Multi-step text input (admin_input.py)

States stored in `context.user_data["admin_state"]`:
- `add_product_name` → `add_product_price` → `add_product_stock` → shows category picker (inline buttons `admin_cat_pick_<id>`)
- `add_category_name` → creates category immediately
- `edit_category_name` → updates category (id stored in `user_data["admin_cat_id"]`)

Dispatcher: admin MessageHandler is in group=0, general text handler is in group=1. The admin handler self-gates with `_is_admin()` and returns early for non-admins.

## Service call signatures (critical)

- `VendorService.approve_vendor(vendor_id, admin_id)` — 2 args required
- `VendorService.reject_vendor(vendor_id, reason)` — reason is a string, required
- `ProductCreate(sku=..., ...)` — sku is required; auto-generated as `{NAME_BASE}-{UUID6}` in add-product flow

## Per-entity action buttons

Products: each pending product row has `admin_approve_product_{id}` + `admin_reject_product_{id}`
Users: each user row has `admin_suspend_user_{id}` or `admin_unsuspend_user_{id}`
Vendors: each unapproved vendor row has `admin_approve_vendor_{id}` + `admin_reject_vendor_{id}`
Orders: each order row has `admin_view_order_{id}`; detail screen has `admin_set_status_{id}_{status}` per valid transition

## CSV export

`export_sales_csv` and `export_users_csv` in reports.py use `io.BytesIO` + utf-8-sig BOM encoding → `context.bot.send_document()`
