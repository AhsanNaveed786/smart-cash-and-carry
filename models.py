from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
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

    variant_availability_records: Mapped[
        list[VariantAvailability]
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

    variants: Mapped[list[ProductVariant]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductVariant.display_order",
    )

    images: Mapped[list[ProductImage]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.display_order",
    )


class ProductVariant(Base):
    __tablename__ = "product_variants"

    __table_args__ = (
        CheckConstraint(
            "display_order >= 0",
            name="product_variant_display_order_non_negative",
        ),
        Index(
            "uq_product_variants_one_default",
            "product_id",
            unique=True,
            postgresql_where=text("is_default = true"),
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

    name: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
    )

    sku: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    barcode: Mapped[str | None] = mapped_column(
        String(64),
        unique=True,
        nullable=True,
        index=True,
    )

    attributes: Mapped[dict[str, str]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    price_adjustment: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
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

    product: Mapped[Product] = relationship(
        back_populates="variants",
    )

    images: Mapped[list[ProductImage]] = relationship(
        back_populates="variant",
    )

    availability_records: Mapped[
        list[VariantAvailability]
    ] = relationship(
        back_populates="variant",
        cascade="all, delete-orphan",
    )


class ProductImage(Base):
    __tablename__ = "product_images"

    __table_args__ = (
        CheckConstraint(
            "display_order >= 0",
            name="product_image_display_order_non_negative",
        ),
        UniqueConstraint(
            "product_id",
            "image_url",
            name="uq_product_image_url",
        ),
        Index(
            "uq_product_images_one_primary",
            "product_id",
            unique=True,
            postgresql_where=text("is_primary = true"),
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

    variant_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "product_variants.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    image_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    alt_text: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
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

    product: Mapped[Product] = relationship(
        back_populates="images",
    )

    variant: Mapped[ProductVariant | None] = relationship(
        back_populates="images",
    )


class VariantAvailability(Base):
    __tablename__ = "variant_availability"

    __table_args__ = (
        UniqueConstraint(
            "variant_id",
            "branch_id",
            name="uq_variant_availability_branch_variant",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    variant_id: Mapped[int] = mapped_column(
        ForeignKey(
            "product_variants.id",
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

    variant: Mapped[ProductVariant] = relationship(
        back_populates="availability_records",
    )

    branch: Mapped[Branch] = relationship(
        back_populates="variant_availability_records",
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

    __table_args__ = (
        CheckConstraint(
            "role IN ('super_admin', 'mini_admin')",
            name="admin_valid_role",
        ),
    )

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

    role: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="mini_admin",
        server_default="mini_admin",
        index=True,
    )

    login_allowed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        index=True,
    )

    login_allowed_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    login_allowed_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
        foreign_keys="AdminSession.admin_id",
    )

    permission_links: Mapped[list[AdminPermission]] = relationship(
        back_populates="admin",
        cascade="all, delete-orphan",
        foreign_keys="AdminPermission.admin_id",
    )

    branch_accesses: Mapped[list[AdminBranchAccess]] = relationship(
        back_populates="admin",
        cascade="all, delete-orphan",
        foreign_keys="AdminBranchAccess.admin_id",
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

    revoked_by_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "admins.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    revoke_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    admin: Mapped[Admin] = relationship(
        back_populates="sessions",
        foreign_keys=[admin_id],
    )


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    description: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_assignable_to_mini_admin: Mapped[bool] = mapped_column(
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

    admin_links: Mapped[list[AdminPermission]] = relationship(
        back_populates="permission",
        cascade="all, delete-orphan",
    )


class AdminPermission(Base):
    __tablename__ = "admin_permissions"

    __table_args__ = (
        UniqueConstraint(
            "admin_id",
            "permission_id",
            name="uq_admin_permission",
        ),
    )

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

    permission_id: Mapped[int] = mapped_column(
        ForeignKey(
            "permissions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    granted_by_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "admins.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    admin: Mapped[Admin] = relationship(
        back_populates="permission_links",
        foreign_keys=[admin_id],
    )

    permission: Mapped[Permission] = relationship(
        back_populates="admin_links",
    )


class AdminBranchAccess(Base):
    __tablename__ = "admin_branch_access"

    __table_args__ = (
        UniqueConstraint(
            "admin_id",
            "branch_id",
            name="uq_admin_branch_access",
        ),
    )

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

    branch_id: Mapped[int] = mapped_column(
        ForeignKey(
            "branches.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    granted_by_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "admins.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    admin: Mapped[Admin] = relationship(
        back_populates="branch_accesses",
        foreign_keys=[admin_id],
    )

    branch: Mapped[Branch] = relationship()


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    actor_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "admins.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    target_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "admins.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    details: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
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


class Order(Base):
    __tablename__ = "orders"

    __table_args__ = (
        CheckConstraint(
            "fulfillment_method IN "
            "('home_delivery', 'self_pickup')",
            name="order_valid_fulfillment_method",
        ),
        CheckConstraint(
            "order_channel IN ('website', 'whatsapp')",
            name="order_valid_channel",
        ),
        CheckConstraint(
            "status IN "
            "('pending', 'confirmed', 'processing', "
            "'ready_for_pickup', 'out_for_delivery', "
            "'completed', 'cancelled')",
            name="order_valid_status",
        ),
        CheckConstraint(
            "payment_method IN "
            "('cash_on_delivery', 'pay_at_store')",
            name="order_valid_payment_method",
        ),
        CheckConstraint(
            "subtotal >= 0 AND delivery_fee >= 0 "
            "AND total_amount >= 0",
            name="order_amounts_non_negative",
        ),
        Index(
            "ix_orders_branch_status_created_at",
            "branch_id",
            "status",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    order_number: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        nullable=False,
        index=True,
    )

    branch_id: Mapped[int] = mapped_column(
        ForeignKey(
            "branches.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    customer_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    phone_number: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    customer_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    fulfillment_method: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    order_channel: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="website",
        server_default="website",
    )

    payment_method: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    delivery_address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    delivery_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    process_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
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

    branch: Mapped[Branch] = relationship()

    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderItem.id",
    )

    status_history: Mapped[
        list[OrderStatusHistory]
    ] = relationship(
        back_populates="order",
        passive_deletes=True,
        order_by="OrderStatusHistory.created_at",
    )


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    __table_args__ = (
        CheckConstraint(
            "previous_status IS NULL OR previous_status IN "
            "('pending', 'confirmed', 'processing', "
            "'ready_for_pickup', 'out_for_delivery', "
            "'completed', 'cancelled')",
            name="order_history_valid_previous_status",
        ),
        CheckConstraint(
            "new_status IN "
            "('pending', 'confirmed', 'processing', "
            "'ready_for_pickup', 'out_for_delivery', "
            "'completed', 'cancelled')",
            name="order_history_valid_new_status",
        ),
        Index(
            "ix_order_history_number_created_at",
            "order_number",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    order_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "orders.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    order_number: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        index=True,
    )

    branch_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "branches.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    previous_status: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    new_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    change_note: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    changed_by_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "admins.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    changed_by_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    changed_by_email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    order: Mapped[Order | None] = relationship(
        back_populates="status_history",
    )

    branch: Mapped[Branch | None] = relationship()

    changed_by_admin: Mapped[Admin | None] = relationship()


class OrderItem(Base):
    __tablename__ = "order_items"

    __table_args__ = (
        CheckConstraint(
            "quantity > 0",
            name="order_item_quantity_positive",
        ),
        CheckConstraint(
            "unit_price >= 0 AND line_total >= 0",
            name="order_item_amounts_non_negative",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey(
            "orders.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey(
            "products.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    variant_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "product_variants.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    product_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    variant_name: Mapped[str | None] = mapped_column(
        String(180),
        nullable=True,
    )

    sku: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    line_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    order: Mapped[Order] = relationship(
        back_populates="items",
    )

    product: Mapped[Product] = relationship()

    variant: Mapped[ProductVariant | None] = relationship()


class DataExport(Base):
    __tablename__ = "data_exports"

    __table_args__ = (
        CheckConstraint(
            "export_type IN ('orders', 'products')",
            name="data_export_valid_type",
        ),
        CheckConstraint(
            "status IN ('completed', 'failed')",
            name="data_export_valid_status",
        ),
        CheckConstraint(
            "record_count >= 0 AND deleted_order_count >= 0",
            name="data_export_counts_non_negative",
        ),
        CheckConstraint(
            "total_amount >= 0",
            name="data_export_total_non_negative",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    export_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="completed",
        server_default="completed",
        index=True,
    )

    branch_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "branches.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    created_by_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "admins.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    file_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    filters_snapshot: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    record_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
    )

    allows_order_deletion: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    deleted_order_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    orders_deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    branch: Mapped[Branch | None] = relationship()

    created_by_admin: Mapped[Admin | None] = relationship()

    order_items: Mapped[list[OrderExportItem]] = relationship(
        back_populates="export",
        cascade="all, delete-orphan",
    )


class OrderExportItem(Base):
    __tablename__ = "order_export_items"

    __table_args__ = (
        UniqueConstraint(
            "export_id",
            "order_number",
            name="uq_order_export_item",
        ),
        CheckConstraint(
            "total_amount >= 0",
            name="order_export_item_total_non_negative",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    export_id: Mapped[int] = mapped_column(
        ForeignKey(
            "data_exports.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    order_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "orders.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    order_number: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        index=True,
    )

    branch_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "branches.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    status_at_export: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    order_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    deleted_by_admin_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "admins.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    export: Mapped[DataExport] = relationship(
        back_populates="order_items",
    )

    order: Mapped[Order | None] = relationship()

    branch: Mapped[Branch | None] = relationship()

    deleted_by_admin: Mapped[Admin | None] = relationship()


class RevenueOrderLedger(Base):
    __tablename__ = "revenue_order_ledger"

    __table_args__ = (
        CheckConstraint(
            "total_amount >= 0",
            name="revenue_ledger_total_non_negative",
        ),
        Index(
            "ix_revenue_ledger_date_branch",
            "completion_date",
            "branch_id",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    order_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "orders.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    order_number: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        unique=True,
        index=True,
    )

    branch_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "branches.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    branch_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    completion_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    order: Mapped[Order | None] = relationship()

    branch: Mapped[Branch | None] = relationship()
