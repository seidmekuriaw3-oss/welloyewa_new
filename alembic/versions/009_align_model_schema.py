"""Align the migrated schema with the SQLAlchemy models.

Revision ID: 009_align_model_schema
Revises: 008_add_missing_user_fields
"""

from alembic import op
import sqlalchemy as sa


revision = "009_align_model_schema"
down_revision = "008_add_missing_user_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "telegram_id", existing_type=sa.BigInteger(), nullable=True)

    op.alter_column(
        "products",
        "category",
        existing_type=sa.Enum(
            "electronics",
            "clothing",
            "food",
            "books",
            "beauty",
            "health",
            "home",
            "sports",
            "toys",
            "other",
            name="product_category",
        ),
        new_column_name="category_type",
        existing_nullable=False,
        nullable=True,
    )
    op.add_column("products", sa.Column("name_am", sa.String(length=255), nullable=True))
    op.add_column("products", sa.Column("description_am", sa.Text(), nullable=True))
    op.add_column("products", sa.Column("category_id", sa.BigInteger(), nullable=True))
    op.add_column("products", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.add_column(
        "products",
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("products", sa.Column("extra_data", sa.JSON(), nullable=True))
    op.create_index(op.f("ix_products_name"), "products", ["name"], unique=False)
    op.create_index(op.f("ix_products_category_id"), "products", ["category_id"], unique=False)
    op.alter_column(
        "products",
        "slug",
        existing_type=sa.String(length=255),
        type_=sa.String(length=280),
        existing_nullable=False,
    )

    op.alter_column(
        "product_images",
        "order",
        existing_type=sa.Integer(),
        new_column_name="display_order",
        existing_nullable=False,
    )
    op.add_column("product_images", sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.execute(
        "UPDATE product_images SET updated_at = created_at WHERE updated_at IS NULL"
    )
    op.alter_column("product_images", "updated_at", nullable=False)

    op.add_column("vendors", sa.Column("total_products", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("vendors", sa.Column("approved_by", sa.BigInteger(), nullable=True))
    op.add_column("vendors", sa.Column("rejected_at", sa.DateTime(), nullable=True))
    op.add_column("vendors", sa.Column("rejection_reason", sa.Text(), nullable=True))
    op.create_index(
        op.f("ix_vendors_business_name"), "vendors", ["business_name"], unique=False
    )

    op.add_column("orders", sa.Column("payment_details", sa.JSON(), nullable=True))
    op.add_column("orders", sa.Column("tracking_carrier", sa.String(length=50), nullable=True))
    op.add_column("orders", sa.Column("estimated_delivery_date", sa.DateTime(), nullable=True))
    op.add_column("orders", sa.Column("cancelled_by", sa.BigInteger(), nullable=True))
    op.add_column(
        "orders",
        sa.Column("refunded_amount", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"),
    )
    op.add_column("orders", sa.Column("refunded_at", sa.DateTime(), nullable=True))
    op.add_column("orders", sa.Column("refund_transaction_id", sa.String(length=255), nullable=True))

    op.add_column("order_items", sa.Column("product_image", sa.String(length=500), nullable=True))
    op.add_column("order_items", sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.execute("UPDATE order_items SET updated_at = created_at WHERE updated_at IS NULL")
    op.alter_column("order_items", "updated_at", nullable=False)

    op.add_column("reviews", sa.Column("comment_am", sa.Text(), nullable=True))
    op.add_column("reviews", sa.Column("approved_by", sa.BigInteger(), nullable=True))
    op.add_column("reviews", sa.Column("vendor_response", sa.Text(), nullable=True))
    op.add_column("reviews", sa.Column("vendor_response_at", sa.DateTime(), nullable=True))
    op.add_column(
        "reviews",
        sa.Column("helpful_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "reviews",
        sa.Column("not_helpful_count", sa.Integer(), nullable=False, server_default="0"),
    )

    op.add_column("inventory_movements", sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.execute("UPDATE inventory_movements SET updated_at = created_at WHERE updated_at IS NULL")
    op.alter_column("inventory_movements", "updated_at", nullable=False)

    op.create_table(
        "campaigns",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("campaign_type", sa.String(length=50), nullable=False),
        sa.Column("start_date", sa.DateTime(), nullable=False),
        sa.Column("end_date", sa.DateTime(), nullable=False),
        sa.Column("target_segments", sa.JSON(), nullable=True),
        sa.Column("target_cities", sa.JSON(), nullable=True),
        sa.Column("budget", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("spent", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("impressions", sa.Integer(), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False),
        sa.Column("conversions", sa.Integer(), nullable=False),
        sa.Column("revenue", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("rules", sa.JSON(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "categories",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("name_am", sa.String(length=100), nullable=True),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("description_am", sa.Text(), nullable=True),
        sa.Column("parent_id", sa.BigInteger(), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("icon_url", sa.String(length=500), nullable=True),
        sa.Column("meta_title", sa.String(length=255), nullable=True),
        sa.Column("meta_description", sa.Text(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_featured", sa.Boolean(), nullable=False),
        sa.Column("product_count", sa.Integer(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_categories_name"), "categories", ["name"], unique=False)
    op.create_index(op.f("ix_categories_parent_id"), "categories", ["parent_id"], unique=False)
    op.create_index(op.f("ix_categories_slug"), "categories", ["slug"], unique=True)
    op.create_foreign_key(
        "fk_products_category_id_categories",
        "products",
        "categories",
        ["category_id"],
        ["id"],
    )
    op.create_table(
        "coupons",
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("discount_type", sa.String(length=20), nullable=False),
        sa.Column("discount_value", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("max_discount_amount", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("min_purchase_amount", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("valid_from", sa.DateTime(), nullable=False),
        sa.Column("valid_to", sa.DateTime(), nullable=False),
        sa.Column("usage_limit", sa.Integer(), nullable=True),
        sa.Column("per_user_limit", sa.Integer(), nullable=True),
        sa.Column("used_count", sa.Integer(), nullable=False),
        sa.Column("applicable_categories", sa.JSON(), nullable=True),
        sa.Column("applicable_products", sa.JSON(), nullable=True),
        sa.Column("excluded_categories", sa.JSON(), nullable=True),
        sa.Column("excluded_products", sa.JSON(), nullable=True),
        sa.Column("new_customers_only", sa.Boolean(), nullable=False),
        sa.Column("first_order_only", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_stackable", sa.Boolean(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_coupons_code"), "coupons", ["code"], unique=True)
    op.create_table(
        "faq_categories",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("name_am", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("icon", sa.String(length=50), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_faq_categories_slug"), "faq_categories", ["slug"], unique=True)
    op.create_table(
        "loyalty_programs",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("points_per_birr", sa.Float(), nullable=False),
        sa.Column("points_per_review", sa.Integer(), nullable=False),
        sa.Column("points_per_share", sa.Integer(), nullable=False),
        sa.Column("points_per_birthday", sa.Integer(), nullable=False),
        sa.Column("birr_per_point", sa.Float(), nullable=False),
        sa.Column("min_redeem_points", sa.Integer(), nullable=False),
        sa.Column("max_redeem_per_order", sa.Integer(), nullable=True),
        sa.Column("tier_enabled", sa.Boolean(), nullable=False),
        sa.Column("tier_config", sa.JSON(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "support_articles",
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("title_am", sa.String(length=255), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_am", sa.Text(), nullable=True),
        sa.Column("slug", sa.String(length=280), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("author_id", sa.BigInteger(), nullable=True),
        sa.Column("meta_title", sa.String(length=255), nullable=True),
        sa.Column("meta_description", sa.Text(), nullable=True),
        sa.Column("views", sa.Integer(), nullable=False),
        sa.Column("helpful_count", sa.Integer(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_support_articles_slug"), "support_articles", ["slug"], unique=True)
    op.create_table(
        "ticket_categories",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("name_am", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("icon", sa.String(length=50), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sla_hours", sa.Integer(), nullable=False),
        sa.Column("auto_assign_to", sa.BigInteger(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ticket_categories_slug"), "ticket_categories", ["slug"], unique=True)
    op.create_table(
        "campaign_rules",
        sa.Column("campaign_id", sa.BigInteger(), nullable=False),
        sa.Column("rule_type", sa.String(length=50), nullable=False),
        sa.Column("operator", sa.String(length=20), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_campaign_rules_campaign_id"), "campaign_rules", ["campaign_id"], unique=False)
    op.create_table(
        "coupon_usages",
        sa.Column("coupon_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("discount_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("order_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["coupon_id"], ["coupons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_coupon_usages_order_id"), "coupon_usages", ["order_id"], unique=False)
    op.create_index(op.f("ix_coupon_usages_user_id"), "coupon_usages", ["user_id"], unique=False)
    op.create_index(op.f("ix_coupon_usages_coupon_id"), "coupon_usages", ["coupon_id"], unique=False)
    op.create_table(
        "faqs",
        sa.Column("category_id", sa.BigInteger(), nullable=True),
        sa.Column("question", sa.String(length=500), nullable=False),
        sa.Column("question_am", sa.String(length=500), nullable=True),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("answer_am", sa.Text(), nullable=True),
        sa.Column("slug", sa.String(length=550), nullable=False),
        sa.Column("keywords", sa.JSON(), nullable=True),
        sa.Column("helpful_count", sa.Integer(), nullable=False),
        sa.Column("not_helpful_count", sa.Integer(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["faq_categories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_faqs_slug"), "faqs", ["slug"], unique=True)
    op.create_index(op.f("ix_faqs_category_id"), "faqs", ["category_id"], unique=False)
    op.create_table(
        "loyalty_transactions",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("transaction_type", sa.String(length=50), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        sa.Column("points_balance", sa.Integer(), nullable=False),
        sa.Column("reference_id", sa.BigInteger(), nullable=True),
        sa.Column("reference_type", sa.String(length=50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_loyalty_user_date", "loyalty_transactions", ["user_id", "created_at"], unique=False
    )
    op.create_index(
        op.f("ix_loyalty_transactions_user_id"),
        "loyalty_transactions",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "promotions",
        sa.Column("campaign_id", sa.BigInteger(), nullable=True),
        sa.Column("promotion_type", sa.String(length=50), nullable=False),
        sa.Column("product_ids", sa.JSON(), nullable=True),
        sa.Column("category_ids", sa.JSON(), nullable=True),
        sa.Column("discount_type", sa.String(length=20), nullable=False),
        sa.Column("discount_value", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("max_discount", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("buy_quantity", sa.Integer(), nullable=True),
        sa.Column("get_quantity", sa.Integer(), nullable=True),
        sa.Column("get_product_ids", sa.JSON(), nullable=True),
        sa.Column("start_date", sa.DateTime(), nullable=False),
        sa.Column("end_date", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("usage_limit", sa.Integer(), nullable=True),
        sa.Column("used_count", sa.Integer(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_promotions_campaign_id"), "promotions", ["campaign_id"], unique=False)
    op.create_table(
        "tickets",
        sa.Column("ticket_number", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("assigned_to", sa.BigInteger(), nullable=True),
        sa.Column("category_id", sa.BigInteger(), nullable=True),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("attachments", sa.JSON(), nullable=True),
        sa.Column("ticket_metadata", sa.JSON(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("closed_by", sa.BigInteger(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["ticket_categories.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tickets_assigned_to"), "tickets", ["assigned_to"], unique=False)
    op.create_index(op.f("ix_tickets_user_id"), "tickets", ["user_id"], unique=False)
    op.create_index(op.f("ix_tickets_status"), "tickets", ["status"], unique=False)
    op.create_index(op.f("ix_tickets_ticket_number"), "tickets", ["ticket_number"], unique=True)
    op.create_table(
        "user_addresses",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("address_line1", sa.String(length=255), nullable=False),
        sa.Column("address_line2", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("subcity", sa.String(length=100), nullable=True),
        sa.Column("woreda", sa.String(length=50), nullable=True),
        sa.Column("house_number", sa.String(length=50), nullable=True),
        sa.Column("landmark", sa.String(length=255), nullable=True),
        sa.Column("recipient_name", sa.String(length=100), nullable=False),
        sa.Column("recipient_phone", sa.String(length=20), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("address_type", sa.String(length=20), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_addresses_user_id"), "user_addresses", ["user_id"], unique=False)
    op.create_table(
        "ticket_messages",
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_staff_reply", sa.Boolean(), nullable=False),
        sa.Column("attachments", sa.JSON(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ticket_messages_ticket_id"), "ticket_messages", ["ticket_id"], unique=False
    )
    op.create_table(
        "order_history",
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("previous_status", sa.String(length=50), nullable=True),
        sa.Column("new_status", sa.String(length=50), nullable=False),
        sa.Column("changed_by", sa.BigInteger(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_order_history_order_id"), "order_history", ["order_id"], unique=False)
    op.create_table(
        "shipments",
        sa.Column("order_id", sa.BigInteger(), nullable=False),
        sa.Column("tracking_number", sa.String(length=100), nullable=False),
        sa.Column("carrier", sa.String(length=50), nullable=False),
        sa.Column("tracking_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("estimated_delivery", sa.DateTime(), nullable=True),
        sa.Column("actual_delivery", sa.DateTime(), nullable=True),
        sa.Column("tracking_history", sa.JSON(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_shipments_order_id"), "shipments", ["order_id"], unique=True)

    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=False)


def downgrade() -> None:
    op.drop_table("shipments")
    op.drop_index(op.f("ix_order_history_order_id"), table_name="order_history")
    op.drop_table("order_history")
    op.drop_index(op.f("ix_ticket_messages_ticket_id"), table_name="ticket_messages")
    op.drop_table("ticket_messages")
    op.drop_index(op.f("ix_user_addresses_user_id"), table_name="user_addresses")
    op.drop_table("user_addresses")
    op.drop_index(op.f("ix_tickets_ticket_number"), table_name="tickets")
    op.drop_index(op.f("ix_tickets_status"), table_name="tickets")
    op.drop_index(op.f("ix_tickets_user_id"), table_name="tickets")
    op.drop_index(op.f("ix_tickets_assigned_to"), table_name="tickets")
    op.drop_table("tickets")
    op.drop_index(op.f("ix_promotions_campaign_id"), table_name="promotions")
    op.drop_table("promotions")
    op.drop_index(op.f("ix_loyalty_transactions_user_id"), table_name="loyalty_transactions")
    op.drop_index("idx_loyalty_user_date", table_name="loyalty_transactions")
    op.drop_table("loyalty_transactions")
    op.drop_index(op.f("ix_faqs_category_id"), table_name="faqs")
    op.drop_index(op.f("ix_faqs_slug"), table_name="faqs")
    op.drop_table("faqs")
    op.drop_index(op.f("ix_coupon_usages_coupon_id"), table_name="coupon_usages")
    op.drop_index(op.f("ix_coupon_usages_user_id"), table_name="coupon_usages")
    op.drop_index(op.f("ix_coupon_usages_order_id"), table_name="coupon_usages")
    op.drop_table("coupon_usages")
    op.drop_index(op.f("ix_campaign_rules_campaign_id"), table_name="campaign_rules")
    op.drop_table("campaign_rules")
    op.drop_index(op.f("ix_ticket_categories_slug"), table_name="ticket_categories")
    op.drop_table("ticket_categories")
    op.drop_index(op.f("ix_support_articles_slug"), table_name="support_articles")
    op.drop_table("support_articles")
    op.drop_table("loyalty_programs")
    op.drop_index(op.f("ix_faq_categories_slug"), table_name="faq_categories")
    op.drop_table("faq_categories")
    op.drop_index(op.f("ix_coupons_code"), table_name="coupons")
    op.drop_table("coupons")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_column("inventory_movements", "updated_at")
    op.drop_column("reviews", "not_helpful_count")
    op.drop_column("reviews", "helpful_count")
    op.drop_column("reviews", "vendor_response_at")
    op.drop_column("reviews", "vendor_response")
    op.drop_column("reviews", "approved_by")
    op.drop_column("reviews", "comment_am")
    op.drop_column("order_items", "updated_at")
    op.drop_column("order_items", "product_image")
    op.drop_column("orders", "refund_transaction_id")
    op.drop_column("orders", "refunded_at")
    op.drop_column("orders", "refunded_amount")
    op.drop_column("orders", "cancelled_by")
    op.drop_column("orders", "estimated_delivery_date")
    op.drop_column("orders", "tracking_carrier")
    op.drop_column("orders", "payment_details")
    op.drop_column("vendors", "rejection_reason")
    op.drop_column("vendors", "rejected_at")
    op.drop_column("vendors", "approved_by")
    op.drop_column("vendors", "total_products")
    op.drop_index(op.f("ix_vendors_business_name"), table_name="vendors")
    op.drop_column("product_images", "updated_at")
    op.alter_column(
        "product_images",
        "display_order",
        existing_type=sa.Integer(),
        new_column_name="order",
        existing_nullable=False,
    )
    op.alter_column(
        "products",
        "slug",
        existing_type=sa.String(length=280),
        type_=sa.String(length=255),
        existing_nullable=False,
    )
    op.drop_index(op.f("ix_products_category_id"), table_name="products")
    op.drop_index(op.f("ix_products_name"), table_name="products")
    op.drop_column("products", "extra_data")
    op.drop_column("products", "is_deleted")
    op.drop_column("products", "deleted_at")
    op.drop_constraint("fk_products_category_id_categories", "products", type_="foreignkey")
    op.drop_column("products", "category_id")
    op.drop_column("products", "description_am")
    op.drop_column("products", "name_am")
    op.alter_column(
        "products",
        "category_type",
        existing_type=sa.Enum(
            "electronics",
            "clothing",
            "food",
            "books",
            "beauty",
            "health",
            "home",
            "sports",
            "toys",
            "other",
            name="product_category",
        ),
        new_column_name="category",
        existing_nullable=True,
        nullable=False,
    )
    op.alter_column("users", "telegram_id", existing_type=sa.BigInteger(), nullable=False)
    op.drop_index(op.f("ix_categories_slug"), table_name="categories")
    op.drop_index(op.f("ix_categories_parent_id"), table_name="categories")
    op.drop_index(op.f("ix_categories_name"), table_name="categories")
    op.drop_table("categories")
