from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    price_overrides: Mapped[
        list[BranchPriceOverride]
    ] = relationship(
        back_populates="branch",
        cascade="all, delete-orphan",
    )


class Category(Base):
    __tablename__ = "categories"

    __table_args__ = (
        CheckConstraint(
            "display_order >= 0",
            name="category_display_order_non_negative",
        ),
        CheckConstraint(
            "display_mode IN "
            "('default_heading', 'custom_image_banner')",
            name="category_valid_display_mode",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(140),
        unique=True,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    banner_image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    display_mode: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="default_heading",
        server_default="default_heading",
    )


    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    products: Mapped[list[Product]] = relationship(
        back_populates="category",
    )


class Product(Base):
    __tablename__ = "products"

    __table_args__ = (
        CheckConstraint(
            "master_price >= 0",
            name="product_master_price_non_negative",
        ),
        Index(
            "ix_products_name",
            "name",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    barcode: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(280),
        unique=True,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    unit_size: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    master_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    category_id: Mapped[int] = mapped_column(
        ForeignKey(
            "categories.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    category: Mapped[Category] = relationship(
        back_populates="products",
    )

    price_overrides: Mapped[
        list[BranchPriceOverride]
    ] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )


class BranchPriceOverride(Base):
    __tablename__ = "branch_price_overrides"

    __table_args__ = (
        UniqueConstraint(
            "branch_id",
            "product_id",
            name="uq_branch_product_price",
        ),
        CheckConstraint(
            "override_price >= 0",
            name="branch_override_price_non_negative",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    branch_id: Mapped[int] = mapped_column(
        ForeignKey(
            "branches.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    override_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    branch: Mapped[Branch] = relationship(
        back_populates="price_overrides",
    )

    product: Mapped[Product] = relationship(
        back_populates="price_overrides",
    )


class PriceImportBatch(Base):
    __tablename__ = "price_import_batches"

    __table_args__ = (
        CheckConstraint(
            "import_scope IN ('master', 'branch')",
            name="ck_price_import_batch_scope",
        ),
        CheckConstraint(
            "status IN "
            "('preview', 'applied', 'cancelled', 'failed')",
            name="ck_price_import_batch_status",
        ),
        CheckConstraint(
            "total_rows >= 0",
            name="ck_price_import_total_rows",
        ),
        CheckConstraint(
            "changed_rows >= 0",
            name="ck_price_import_changed_rows",
        ),
        CheckConstraint(
            "unchanged_rows >= 0",
            name="ck_price_import_unchanged_rows",
        ),
        CheckConstraint(
            "invalid_rows >= 0",
            name="ck_price_import_invalid_rows",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    import_scope: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    branch_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "branches.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="preview",
        server_default="preview",
        index=True,
    )

    total_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    changed_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    unchanged_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    invalid_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    rows: Mapped[list[PriceImportRow]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan",
        order_by="PriceImportRow.excel_row_number",
    )


class PriceImportRow(Base):
    __tablename__ = "price_import_rows"

    __table_args__ = (
        UniqueConstraint(
            "batch_id",
            "excel_row_number",
            name="uq_price_import_batch_excel_row",
        ),
        CheckConstraint(
            "uploaded_price IS NULL OR uploaded_price >= 0",
            name="ck_price_import_uploaded_price",
        ),
        CheckConstraint(
            "current_price IS NULL OR current_price >= 0",
            name="ck_price_import_current_price",
        ),
        CheckConstraint(
            "status IN "
            "('changed', 'unchanged', 'product_not_found', "
            "'invalid', 'applied', 'conflict', 'skipped')",
            name="ck_price_import_row_status",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    batch_id: Mapped[int] = mapped_column(
        ForeignKey(
            "price_import_batches.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    excel_row_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    product_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    barcode: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    item_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    current_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    uploaded_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    apply_selected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    batch: Mapped[PriceImportBatch] = relationship(
        back_populates="rows",
    )

    product: Mapped[Product | None] = relationship()

class ProductImportBatch(Base):
    __tablename__ = "product_import_batches"

    __table_args__ = (
        CheckConstraint(
            "status IN "
            "('preview', 'categorized', 'applied', "
            "'cancelled', 'failed')",
            name="ck_product_import_batch_status",
        ),
        CheckConstraint(
            "total_rows >= 0",
            name="ck_product_import_total_rows",
        ),
        CheckConstraint(
            "valid_rows >= 0",
            name="ck_product_import_valid_rows",
        ),
        CheckConstraint(
            "invalid_rows >= 0",
            name="ck_product_import_invalid_rows",
        ),
        CheckConstraint(
            "categorized_rows >= 0",
            name="ck_product_import_categorized_rows",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="preview",
        server_default="preview",
        index=True,
    )

    total_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    valid_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    invalid_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    categorized_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    rows: Mapped[list[ProductImportRow]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan",
        order_by="ProductImportRow.excel_row_number",
    )


class ProductImportRow(Base):
    __tablename__ = "product_import_rows"

    __table_args__ = (
        UniqueConstraint(
            "batch_id",
            "excel_row_number",
            name="uq_product_import_batch_excel_row",
        ),
        CheckConstraint(
            "uploaded_price IS NULL OR uploaded_price >= 0",
            name="ck_product_import_uploaded_price",
        ),
        CheckConstraint(
            "category_confidence IS NULL OR "
            "(category_confidence >= 0 "
            "AND category_confidence <= 1)",
            name="ck_product_import_category_confidence",
        ),
        CheckConstraint(
            "status IN "
            "('invalid', 'duplicate_file', 'already_exists', "
            "'pending_category', 'ready', 'applied', 'skipped')",
            name="ck_product_import_row_status",
        ),
        CheckConstraint(
            "category_source IS NULL OR "
            "category_source IN ('ai', 'manual')",
            name="ck_product_import_category_source",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    batch_id: Mapped[int] = mapped_column(
        ForeignKey(
            "product_import_batches.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    excel_row_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    barcode: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    item_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    uploaded_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    suggested_category_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "categories.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    confirmed_category_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "categories.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    category_confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
    )

    category_source: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    ai_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    apply_selected: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    batch: Mapped[ProductImportBatch] = relationship(
        back_populates="rows",
    )

    suggested_category: Mapped[Category | None] = relationship(
        foreign_keys=[suggested_category_id],
    )

    confirmed_category: Mapped[Category | None] = relationship(
        foreign_keys=[confirmed_category_id],
    )

class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    full_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        unique=True,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    sessions: Mapped[list[AdminSession]] = relationship(
        back_populates="admin",
        cascade="all, delete-orphan",
    )


class AdminSession(Base):
    __tablename__ = "admin_sessions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    admin_id: Mapped[int] = mapped_column(
        ForeignKey(
            "admins.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    session_token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    csrf_token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    admin: Mapped[Admin] = relationship(
        back_populates="sessions",
    )

class DiscountCampaign(Base):
    __tablename__ = "discount_campaigns"

    __table_args__ = (
        CheckConstraint(
            "campaign_type IN ('deal', 'special_discount')",
            name="ck_discount_campaign_type",
        ),
        CheckConstraint(
            "end_at > start_at",
            name="ck_discount_campaign_dates",
        ),
        CheckConstraint(
            "display_order >= 0",
            name="ck_discount_campaign_display_order",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    title: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    campaign_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    end_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    prices: Mapped[list[DiscountPrice]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
        order_by="DiscountPrice.id",
    )


class DiscountPrice(Base):
    __tablename__ = "discount_prices"

    __table_args__ = (
        UniqueConstraint(
            "campaign_id",
            "product_id",
            "branch_id",
            name="uq_discount_campaign_product_branch",
        ),
        CheckConstraint(
            "special_price >= 0",
            name="ck_discount_special_price",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    campaign_id: Mapped[int] = mapped_column(
        ForeignKey(
            "discount_campaigns.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    branch_id: Mapped[int] = mapped_column(
        ForeignKey(
            "branches.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    special_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    campaign: Mapped[DiscountCampaign] = relationship(
        back_populates="prices",
    )

    product: Mapped[Product] = relationship()

    branch: Mapped[Branch] = relationship()

class WebsiteSetting(Base):
    __tablename__ = "website_settings"

    __table_args__ = (
        CheckConstraint(
            "id = 1",
            name="ck_website_settings_single_row",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        default=1,
        server_default="1",
    )

    store_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        default="SMART CASH & CARRY",
        server_default="SMART CASH & CARRY",
    )

    logo_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    announcement_primary: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )

    announcement_secondary: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )

    announcement_is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class HomepageBanner(Base):
    __tablename__ = "homepage_banners"

    __table_args__ = (
        CheckConstraint(
            "display_order >= 0",
            name="ck_homepage_banner_display_order",
        ),
        CheckConstraint(
            "end_at IS NULL OR start_at IS NULL "
            "OR end_at > start_at",
            name="ck_homepage_banner_dates",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    title: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    subtitle: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    button_text: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    button_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ProductAvailability(Base):
    __tablename__ = "product_availability"

    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "branch_id",
            name="uq_product_availability_branch_product",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    branch_id: Mapped[int] = mapped_column(
        ForeignKey(
            "branches.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    is_in_stock: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        index=True,
    )

    stock_message: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    product: Mapped[Product] = relationship()

    branch: Mapped[Branch] = relationship()