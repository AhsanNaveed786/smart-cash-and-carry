from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

class SchemaBase(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        extra="forbid",
    )


# =========================================================
# Branch Schemas
# =========================================================


class BranchCreate(SchemaBase):
    name: str = Field(min_length=2, max_length=100)
    code: str = Field(
        min_length=2,
        max_length=50,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    is_active: bool = True


class BranchUpdate(SchemaBase):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    code: str | None = Field(
        default=None,
        min_length=2,
        max_length=50,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    is_active: bool | None = None


class BranchResponse(SchemaBase):
    id: int
    name: str
    code: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


# =========================================================
# Category Schemas
# =========================================================

class CategoryCreate(SchemaBase):
    name: str = Field(
        min_length=2,
        max_length=120,
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
    )
    image_url: str | None = Field(
        default=None,
        max_length=500,
    )
    display_order: int = Field(
        default=0,
        ge=0,
    )
    is_active: bool = True


class CategoryUpdate(SchemaBase):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=120,
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
    )
    image_url: str | None = Field(
        default=None,
        max_length=500,
    )
    display_order: int | None = Field(
        default=None,
        ge=0,
    )
    is_active: bool | None = None


class CategoryDisplayModeUpdate(SchemaBase):
    display_mode: Literal[
        "default_heading",
        "custom_image_banner",
    ]


class CategoryResponse(SchemaBase):
    id: int
    name: str
    slug: str
    description: str | None
    image_url: str | None
    banner_image_url: str | None
    display_mode: Literal[
        "default_heading",
        "custom_image_banner",
    ]
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
# =========================================================
# Product Schemas
# =========================================================


class ProductCreate(SchemaBase):
    barcode: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    unit_size: str | None = Field(default=None, max_length=100)
    master_price: Decimal = Field(
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    image_url: str | None = Field(default=None, max_length=500)
    category_id: int = Field(gt=0)
    is_active: bool = True


class ProductUpdate(SchemaBase):
    barcode: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    unit_size: str | None = Field(default=None, max_length=100)
    master_price: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    image_url: str | None = Field(default=None, max_length=500)
    category_id: int | None = Field(default=None, gt=0)
    is_active: bool | None = None


class ProductResponse(SchemaBase):
    id: int
    barcode: str
    name: str
    slug: str
    description: str | None
    unit_size: str | None
    master_price: Decimal
    image_url: str | None
    category_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# =========================================================
# Product Variant and Image Schemas
# =========================================================


class ProductImageUpdate(SchemaBase):
    alt_text: str | None = Field(
        default=None,
        max_length=255,
    )
    display_order: int | None = Field(
        default=None,
        ge=0,
    )
    is_primary: bool | None = None


class ProductImageResponse(SchemaBase):
    id: int
    product_id: int
    variant_id: int | None
    image_url: str
    alt_text: str | None
    display_order: int
    is_primary: bool
    created_at: datetime
    updated_at: datetime


class ProductVariantCreate(SchemaBase):
    name: str = Field(
        min_length=1,
        max_length=180,
    )
    sku: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9._-]+$",
    )
    barcode: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
    )
    attributes: dict[str, str] = Field(
        default_factory=dict,
        max_length=20,
    )
    price_adjustment: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
    )
    display_order: int = Field(
        default=0,
        ge=0,
    )
    is_default: bool = False
    is_active: bool = True

    @field_validator("attributes")
    @classmethod
    def validate_variant_attributes(
        cls,
        attributes: dict[str, str],
    ) -> dict[str, str]:
        normalized_attributes = {}

        for key, value in attributes.items():
            normalized_key = key.strip()
            normalized_value = value.strip()

            if not normalized_key or not normalized_value:
                raise ValueError(
                    "Variant attribute names and values "
                    "cannot be empty."
                )

            if len(normalized_key) > 50:
                raise ValueError(
                    "Variant attribute names cannot exceed "
                    "50 characters."
                )

            if len(normalized_value) > 120:
                raise ValueError(
                    "Variant attribute values cannot exceed "
                    "120 characters."
                )

            normalized_attributes[
                normalized_key
            ] = normalized_value

        return normalized_attributes


class ProductVariantUpdate(SchemaBase):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=180,
    )
    sku: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9._-]+$",
    )
    barcode: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
    )
    attributes: dict[str, str] | None = Field(
        default=None,
        max_length=20,
    )
    price_adjustment: Decimal | None = Field(
        default=None,
        max_digits=12,
        decimal_places=2,
    )
    display_order: int | None = Field(
        default=None,
        ge=0,
    )
    is_default: bool | None = None
    is_active: bool | None = None

    @field_validator("attributes")
    @classmethod
    def validate_optional_variant_attributes(
        cls,
        attributes: dict[str, str] | None,
    ) -> dict[str, str] | None:
        if attributes is None:
            return None

        return ProductVariantCreate.validate_variant_attributes(
            attributes
        )


class ProductVariantResponse(SchemaBase):
    id: int
    product_id: int
    name: str
    sku: str
    barcode: str | None
    attributes: dict[str, str]
    price_adjustment: Decimal
    display_order: int
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    images: list[ProductImageResponse] = Field(
        default_factory=list
    )


class ProductDetailResponse(ProductResponse):
    variants: list[ProductVariantResponse] = Field(
        default_factory=list
    )
    images: list[ProductImageResponse] = Field(
        default_factory=list
    )


class VariantAvailabilityUpdate(SchemaBase):
    is_in_stock: bool
    stock_message: str | None = Field(
        default=None,
        max_length=100,
    )


class VariantAvailabilityResponse(SchemaBase):
    id: int
    variant_id: int
    branch_id: int
    is_in_stock: bool
    stock_message: str | None
    created_at: datetime
    updated_at: datetime


class StorefrontVariantResponse(SchemaBase):
    id: int
    product_id: int
    name: str
    sku: str
    barcode: str | None
    attributes: dict[str, str]
    price_adjustment: Decimal
    effective_price: Decimal
    is_default: bool
    is_in_stock: bool
    stock_message: str | None
    images: list[ProductImageResponse]


# =========================================================
# Branch Price Override Schemas
# =========================================================


class BranchPriceOverrideCreate(SchemaBase):
    branch_id: int = Field(gt=0)
    product_id: int = Field(gt=0)
    override_price: Decimal = Field(
        ge=0,
        max_digits=12,
        decimal_places=2,
    )


class BranchPriceOverrideUpdate(SchemaBase):
    override_price: Decimal = Field(
        ge=0,
        max_digits=12,
        decimal_places=2,
    )


class BranchPriceOverrideResponse(SchemaBase):
    id: int
    branch_id: int
    product_id: int
    override_price: Decimal
    created_at: datetime
    updated_at: datetime


# =========================================================
# Effective Product Price
# =========================================================


class EffectivePriceResponse(SchemaBase):
    product_id: int
    branch_id: int
    master_price: Decimal
    branch_override_price: Decimal | None
    effective_price: Decimal
    price_source: Literal["master", "branch_override"]


class ProductListResponse(SchemaBase):
    total: int
    skip: int
    limit: int
    items: list[ProductResponse]

class MasterPriceUpdate(SchemaBase):
    master_price: Decimal = Field(
        ge=0,
        max_digits=12,
        decimal_places=2,
    )

class PriceImportRowResponse(SchemaBase):
    id: int
    batch_id: int
    excel_row_number: int
    product_id: int | None
    barcode: str | None
    item_name: str | None
    current_price: Decimal | None
    uploaded_price: Decimal | None
    status: str
    apply_selected: bool
    error_message: str | None
    created_at: datetime


class PriceImportBatchResponse(SchemaBase):
    id: int
    import_scope: str
    branch_id: int | None
    product_import_batch_id: int | None = None
    original_filename: str
    status: str
    total_rows: int
    changed_rows: int
    unchanged_rows: int
    invalid_rows: int
    new_product_rows: int = 0
    created_at: datetime
    applied_at: datetime | None


class PriceImportPreviewResponse(
    PriceImportBatchResponse
):
    rows: list[PriceImportRowResponse]


class PriceImportApplyRequest(SchemaBase):
    confirm: Literal[True]


class ImportRowSelectionUpdate(SchemaBase):
    row_ids: list[int] = Field(
        min_length=1,
        max_length=500,
    )
    apply_selected: bool

class ProductImportRowResponse(SchemaBase):
    id: int
    batch_id: int
    excel_row_number: int
    barcode: str | None
    item_name: str | None
    uploaded_price: Decimal | None
    suggested_category_id: int | None
    confirmed_category_id: int | None
    suggested_category_name: str | None = None
    confirmed_category_name: str | None = None
    category_confidence: Decimal | None
    category_source: str | None
    ai_reason: str | None
    status: str
    apply_selected: bool
    error_message: str | None
    created_at: datetime


class ProductImportBatchResponse(SchemaBase):
    id: int
    original_filename: str
    status: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    categorized_rows: int
    created_at: datetime
    applied_at: datetime | None


class ProductImportPreviewResponse(
    ProductImportBatchResponse
):
    rows: list[ProductImportRowResponse]


class ProductImportCategoryConfirmRequest(SchemaBase):
    confirmed_category_id: int | None = Field(
        default=None,
        gt=0,
    )
    confirmed_category_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=120,
    )
    apply_selected: bool = True

    @model_validator(mode="after")
    def validate_category_choice(
        self,
    ) -> "ProductImportCategoryConfirmRequest":
        if not self.apply_selected:
            return self

        has_existing = self.confirmed_category_id is not None
        has_new = bool(
            self.confirmed_category_name
            and self.confirmed_category_name.strip()
        )

        if has_existing == has_new:
            raise ValueError(
                "Choose either one existing category or one new "
                "category name."
            )

        return self

class ProductImportRowsResponse(SchemaBase):
    total: int
    skip: int
    limit: int
    items: list[ProductImportRowResponse]

class ProductCategorizationRunResponse(SchemaBase):
    batch_id: int
    processed_rows: int
    remaining_rows: int
    categorized_rows: int
    batch_status: str

class ProductImportConfirmAllRequest(SchemaBase):
    confirm: Literal[True]


class ProductImportConfirmationResponse(SchemaBase):
    batch_id: int
    confirmed_rows: int
    selected_rows: int
    remaining_unconfirmed_rows: int
    batch_status: str


class ProductImportReviewSummary(SchemaBase):
    batch_id: int
    total_rows: int
    selected_rows: int
    categorized_rows: int
    pending_rows: int
    existing_category_rows: int
    new_category_rows: int
    invalid_rows: int
    progress_percentage: float

class ProductImportApplyRequest(SchemaBase):
    confirm: Literal[True]


class ProductImportApplyResponse(SchemaBase):
    batch_id: int
    status: str
    created_products: int
    skipped_rows: int
    applied_at: datetime
    created_categories: list[str] = Field(default_factory=list)


class MasterImportConfirmResponse(SchemaBase):
    price_batch_id: int
    product_batch_id: int | None
    updated_prices: int
    unchanged_prices: int
    created_products: int
    created_categories: list[str]
    skipped_products: int
    status: str

class AdminLoginRequest(SchemaBase):
    email: EmailStr
    password: str = Field(
        min_length=1,
        max_length=128,
    )


class AdminResponse(SchemaBase):
    id: int
    full_name: str
    email: str
    role: Literal[
        "super_admin",
        "mini_admin",
    ]
    is_active: bool
    login_allowed: bool
    login_allowed_from: datetime | None
    login_allowed_until: datetime | None
    last_login_at: datetime | None
    created_at: datetime


class AdminLoginResponse(SchemaBase):
    message: str
    admin: AdminResponse
    csrf_token: str
    expires_at: datetime


class PermissionResponse(SchemaBase):
    id: int
    code: str
    description: str
    is_assignable_to_mini_admin: bool


class AdminBranchAccessResponse(SchemaBase):
    id: int
    branch_id: int
    created_at: datetime


class AdminAccessResponse(AdminResponse):
    permission_codes: list[str]
    branch_ids: list[int]


class MiniAdminCreateRequest(SchemaBase):
    full_name: str = Field(
        min_length=2,
        max_length=100,
    )
    email: EmailStr
    password: str = Field(
        min_length=8,
        max_length=128,
    )
    branch_ids: list[int] = Field(
        min_length=1,
        max_length=5,
    )
    permission_codes: list[str] = Field(
        default_factory=lambda: [
            "products.read",
            "prices.read",
            "prices.update",
            "orders.read",
            "orders.update_status",
            "imports.manage",
        ],
        min_length=1,
        max_length=20,
    )
    login_allowed: bool = True
    login_allowed_from: datetime | None = None
    login_allowed_until: datetime | None = None

    @field_validator("branch_ids")
    @classmethod
    def validate_unique_branch_ids(
        cls,
        values: list[int],
    ) -> list[int]:
        if any(value <= 0 for value in values):
            raise ValueError("Every branch ID must be positive.")
        if len(values) != len(set(values)):
            raise ValueError("Duplicate branch IDs are not allowed.")
        return values

    @field_validator("permission_codes")
    @classmethod
    def validate_unique_permission_codes(
        cls,
        values: list[str],
    ) -> list[str]:
        normalized = [value.strip().lower() for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError("Duplicate permissions are not allowed.")
        return normalized

    @field_validator(
        "login_allowed_from",
        "login_allowed_until",
    )
    @classmethod
    def require_login_policy_timezone(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError("Login date/time must include a timezone.")
        return value

    @model_validator(mode="after")
    def validate_login_window(self):
        if (
            self.login_allowed_from is not None
            and self.login_allowed_until is not None
            and self.login_allowed_until <= self.login_allowed_from
        ):
            raise ValueError(
                "login_allowed_until must be later than login_allowed_from."
            )
        return self


class AdminAccessUpdateRequest(SchemaBase):
    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )
    is_active: bool | None = None
    login_allowed: bool | None = None
    login_allowed_from: datetime | None = None
    login_allowed_until: datetime | None = None
    branch_ids: list[int] | None = Field(
        default=None,
        min_length=1,
        max_length=5,
    )
    permission_codes: list[str] | None = Field(
        default=None,
        min_length=1,
        max_length=20,
    )

    @field_validator("branch_ids")
    @classmethod
    def validate_optional_branch_ids(
        cls,
        values: list[int] | None,
    ) -> list[int] | None:
        if values is None:
            return None
        return MiniAdminCreateRequest.validate_unique_branch_ids(values)

    @field_validator("permission_codes")
    @classmethod
    def validate_optional_permissions(
        cls,
        values: list[str] | None,
    ) -> list[str] | None:
        if values is None:
            return None
        return MiniAdminCreateRequest.validate_unique_permission_codes(values)

    @field_validator(
        "login_allowed_from",
        "login_allowed_until",
    )
    @classmethod
    def require_optional_policy_timezone(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        return MiniAdminCreateRequest.require_login_policy_timezone(value)


class AdminSessionResponse(SchemaBase):
    id: int
    admin_id: int
    user_agent: str | None
    ip_address: str | None
    expires_at: datetime
    last_used_at: datetime
    revoked_at: datetime | None
    revoked_by_admin_id: int | None
    revoke_reason: str | None
    created_at: datetime


class AdminSessionRevokeRequest(SchemaBase):
    reason: str | None = Field(
        default=None,
        max_length=255,
    )


class AdminAuditLogResponse(SchemaBase):
    id: int
    actor_admin_id: int | None
    target_admin_id: int | None
    action: str
    details: dict
    ip_address: str | None
    created_at: datetime


class MessageResponse(SchemaBase):
    message: str

class DiscountCampaignCreate(SchemaBase):
    title: str = Field(
        min_length=2,
        max_length=150,
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
    )
    campaign_type: Literal[
        "deal",
        "special_discount",
    ]
    start_at: datetime
    end_at: datetime
    display_order: int = Field(default=0, ge=0)
    is_active: bool = True

    @field_validator("start_at", "end_at")
    @classmethod
    def require_timezone(
        cls,
        value: datetime,
    ) -> datetime:
        if (
            value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError(
                "Date and time must include a timezone."
            )

        return value

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.end_at <= self.start_at:
            raise ValueError(
                "end_at must be later than start_at."
            )

        return self


class DiscountCampaignUpdate(SchemaBase):
    title: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
    )
    campaign_type: Literal[
        "deal",
        "special_discount",
    ] | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    display_order: int | None = Field(
        default=None,
        ge=0,
    )
    is_active: bool | None = None

    @field_validator("start_at", "end_at")
    @classmethod
    def require_optional_timezone(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is None:
            return None

        if (
            value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError(
                "Date and time must include a timezone."
            )

        return value


class DiscountCampaignResponse(SchemaBase):
    id: int
    title: str
    description: str | None
    campaign_type: str
    start_at: datetime
    end_at: datetime
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class DiscountPriceCreate(SchemaBase):
    product_id: int = Field(gt=0)
    branch_ids: list[int] = Field(
        min_length=1,
        max_length=100,
    )
    special_price: Decimal = Field(
        ge=0,
        max_digits=12,
        decimal_places=2,
    )

    @field_validator("branch_ids")
    @classmethod
    def validate_branch_ids(
        cls,
        branch_ids: list[int],
    ) -> list[int]:
        if any(
            branch_id <= 0
            for branch_id in branch_ids
        ):
            raise ValueError(
                "Every branch ID must be greater than zero."
            )

        if len(branch_ids) != len(set(branch_ids)):
            raise ValueError(
                "Duplicate branch IDs are not allowed."
            )

        return branch_ids


class DiscountPriceUpdate(SchemaBase):
    special_price: Decimal = Field(
        ge=0,
        max_digits=12,
        decimal_places=2,
    )


class DiscountPriceResponse(SchemaBase):
    id: int
    campaign_id: int
    product_id: int
    branch_id: int
    special_price: Decimal
    created_at: datetime
    updated_at: datetime


class DiscountCampaignDetailResponse(
    DiscountCampaignResponse
):
    prices: list[DiscountPriceResponse]

class StorefrontPriceResponse(SchemaBase):
    product_id: int
    branch_id: int
    master_price: Decimal
    branch_override_price: Decimal | None
    normal_price: Decimal
    special_price: Decimal | None
    effective_price: Decimal
    normal_price_source: Literal[
        "master",
        "branch_override",
    ]
    price_source: Literal[
        "master",
        "branch_override",
        "discount",
    ]
    discount_campaign_id: int | None
    discount_campaign_title: str | None
    discount_campaign_type: str | None
    discount_ends_at: datetime | None
    savings_amount: Decimal
    savings_percentage: Decimal


class DiscountedProductResponse(SchemaBase):
    product_id: int
    barcode: str
    name: str
    slug: str
    image_url: str | None
    category_id: int
    branch_id: int
    campaign_id: int
    campaign_title: str
    campaign_type: str
    normal_price: Decimal
    special_price: Decimal
    savings_amount: Decimal
    savings_percentage: Decimal
    normal_price_source: Literal[
        "master",
        "branch_override",
    ]
    discount_ends_at: datetime


class DiscountedProductListResponse(SchemaBase):
    total: int
    skip: int
    limit: int
    items: list[DiscountedProductResponse]

class WebsiteSettingUpdate(SchemaBase):
    store_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )
    announcement_primary: str | None = Field(
        default=None,
        max_length=300,
    )
    announcement_secondary: str | None = Field(
        default=None,
        max_length=300,
    )
    announcement_is_active: bool | None = None


class WebsiteSettingResponse(SchemaBase):
    id: int
    store_name: str
    logo_url: str | None
    announcement_primary: str | None
    announcement_secondary: str | None
    announcement_is_active: bool
    created_at: datetime
    updated_at: datetime


class HomepageBannerCreate(SchemaBase):
    title: str = Field(
        min_length=2,
        max_length=150,
    )
    subtitle: str | None = Field(
        default=None,
        max_length=500,
    )
    button_text: str | None = Field(
        default=None,
        max_length=80,
    )
    button_url: str | None = Field(
        default=None,
        max_length=500,
    )
    display_order: int = Field(
        default=0,
        ge=0,
    )
    start_at: datetime | None = None
    end_at: datetime | None = None
    is_active: bool = True

    @field_validator("start_at", "end_at")
    @classmethod
    def require_banner_timezone(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is None:
            return None

        if (
            value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError(
                "Date and time must include a timezone."
            )

        return value

    @model_validator(mode="after")
    def validate_banner_dates(self):
        if (
            self.start_at is not None
            and self.end_at is not None
            and self.end_at <= self.start_at
        ):
            raise ValueError(
                "end_at must be later than start_at."
            )

        return self


class HomepageBannerUpdate(SchemaBase):
    title: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )
    subtitle: str | None = Field(
        default=None,
        max_length=500,
    )
    button_text: str | None = Field(
        default=None,
        max_length=80,
    )
    button_url: str | None = Field(
        default=None,
        max_length=500,
    )
    display_order: int | None = Field(
        default=None,
        ge=0,
    )
    start_at: datetime | None = None
    end_at: datetime | None = None
    is_active: bool | None = None

    @field_validator("start_at", "end_at")
    @classmethod
    def require_optional_banner_timezone(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is None:
            return None

        if (
            value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise ValueError(
                "Date and time must include a timezone."
            )

        return value


class HomepageBannerResponse(SchemaBase):
    id: int
    title: str
    subtitle: str | None
    image_url: str | None
    button_text: str | None
    button_url: str | None
    display_order: int
    start_at: datetime | None
    end_at: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProductAvailabilityUpdate(SchemaBase):
    is_in_stock: bool
    stock_message: str | None = Field(
        default=None,
        max_length=100,
    )


class ProductAvailabilityResponse(SchemaBase):
    id: int
    product_id: int
    branch_id: int
    is_in_stock: bool
    stock_message: str | None
    created_at: datetime
    updated_at: datetime

class ProductAvailabilityBulkUpdate(SchemaBase):
    product_ids: list[int] = Field(
        min_length=1,
        max_length=500,
    )
    branch_ids: list[int] = Field(
        min_length=1,
        max_length=10,
    )
    is_in_stock: bool
    stock_message: str | None = Field(
        default=None,
        max_length=100,
    )

    @field_validator(
        "product_ids",
        "branch_ids",
    )
    @classmethod
    def validate_unique_positive_ids(
        cls,
        values: list[int],
    ) -> list[int]:
        if any(value <= 0 for value in values):
            raise ValueError(
                "Every ID must be greater than zero."
            )

        if len(values) != len(set(values)):
            raise ValueError(
                "Duplicate IDs are not allowed."
            )

        return values


class StorefrontAvailabilityResponse(SchemaBase):
    availability_record_id: int | None
    product_id: int
    branch_id: int
    is_in_stock: bool
    stock_message: str | None
    availability_source: Literal[
        "default",
        "branch_record",
    ]


class BranchAvailabilityItemResponse(
    StorefrontAvailabilityResponse
):
    barcode: str
    product_name: str
    category_id: int
    image_url: str | None


class BranchAvailabilityListResponse(SchemaBase):
    total: int
    skip: int
    limit: int
    items: list[BranchAvailabilityItemResponse]


class StorefrontContentResponse(SchemaBase):
    branch_id: int
    settings: WebsiteSettingResponse
    banners: list[HomepageBannerResponse]
    categories: list[CategoryResponse]


# =========================================================
# Variant Storefront and Branch Stock Schemas
# =========================================================


class VariantStockUpdate(SchemaBase):
    is_in_stock: bool
    stock_message: str | None = Field(
        default=None,
        max_length=100,
    )


class VariantStockResponse(SchemaBase):
    availability_record_id: int | None
    variant_id: int
    branch_id: int
    is_in_stock: bool
    stock_message: str | None
    availability_source: Literal[
        "default",
        "branch_record",
    ]


class StorefrontVariantItemResponse(SchemaBase):
    variant_id: int
    product_id: int
    name: str
    sku: str
    barcode: str | None
    attributes: dict[str, str]
    price_adjustment: Decimal
    base_effective_price: Decimal
    effective_price: Decimal
    is_default: bool
    is_in_stock: bool
    stock_message: str | None
    image_urls: list[str]


class StorefrontVariantListResponse(SchemaBase):
    product_id: int
    branch_id: int
    total: int
    items: list[StorefrontVariantItemResponse]


# =========================================================
# Cart, Checkout and Order Schemas
# =========================================================


class CheckoutItemRequest(SchemaBase):
    product_id: int = Field(gt=0)
    variant_id: int | None = Field(
        default=None,
        gt=0,
    )
    quantity: int = Field(
        ge=1,
        le=99,
    )


class CartQuoteRequest(SchemaBase):
    branch_id: int = Field(gt=0)
    fulfillment_method: Literal[
        "home_delivery",
        "self_pickup",
    ]
    items: list[CheckoutItemRequest] = Field(
        min_length=1,
        max_length=100,
    )

    @field_validator("items")
    @classmethod
    def prevent_duplicate_checkout_items(
        cls,
        items: list[CheckoutItemRequest],
    ) -> list[CheckoutItemRequest]:
        item_keys = [
            (
                item.product_id,
                item.variant_id,
            )
            for item in items
        ]

        if len(item_keys) != len(set(item_keys)):
            raise ValueError(
                "Duplicate product/variant items "
                "are not allowed."
            )

        return items


class CartQuoteItemResponse(SchemaBase):
    product_id: int
    variant_id: int | None
    product_name: str
    variant_name: str | None
    sku: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class CartQuoteResponse(SchemaBase):
    branch_id: int
    fulfillment_method: Literal[
        "home_delivery",
        "self_pickup",
    ]
    subtotal: Decimal
    delivery_fee: Decimal
    total_amount: Decimal
    minimum_order_amount: Decimal
    minimum_order_met: bool
    items: list[CartQuoteItemResponse]


class OrderCreateRequest(CartQuoteRequest):
    customer_name: str = Field(
        min_length=2,
        max_length=150,
    )
    phone_number: str = Field(
        min_length=7,
        max_length=30,
        pattern=r"^[0-9+() -]+$",
    )
    customer_email: EmailStr | None = None
    order_channel: Literal[
        "website",
        "whatsapp",
    ] = "website"
    delivery_address: str | None = Field(
        default=None,
        max_length=1000,
    )
    city: str | None = Field(
        default=None,
        max_length=100,
    )
    notes: str | None = Field(
        default=None,
        max_length=500,
    )

    @model_validator(mode="after")
    def validate_fulfillment_details(self):
        if self.fulfillment_method == "home_delivery":
            if not self.delivery_address:
                raise ValueError(
                    "Delivery address is required "
                    "for home delivery."
                )

            if not self.city:
                raise ValueError(
                    "City is required for home delivery."
                )

        return self


class WhatsAppOrderRequest(OrderCreateRequest):
    order_channel: Literal["whatsapp"] = "whatsapp"


class OrderItemResponse(SchemaBase):
    id: int
    product_id: int
    variant_id: int | None
    product_name: str
    variant_name: str | None
    sku: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    created_at: datetime


class OrderResponse(SchemaBase):
    id: int
    order_number: str
    branch_id: int
    customer_name: str
    phone_number: str
    customer_email: str | None
    fulfillment_method: Literal[
        "home_delivery",
        "self_pickup",
    ]
    order_channel: Literal[
        "website",
        "whatsapp",
    ]
    payment_method: Literal[
        "cash_on_delivery",
        "pay_at_store",
    ]
    delivery_address: str | None
    city: str | None
    notes: str | None
    status: Literal[
        "pending",
        "confirmed",
        "processing",
        "ready_for_pickup",
        "out_for_delivery",
        "completed",
        "cancelled",
    ]
    subtotal: Decimal
    delivery_fee: Decimal
    total_amount: Decimal
    process_after: datetime
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse]


class OrderStatusUpdate(SchemaBase):
    status: Literal[
        "pending",
        "confirmed",
        "processing",
        "ready_for_pickup",
        "out_for_delivery",
        "completed",
        "cancelled",
    ]
    note: str | None = Field(
        default=None,
        max_length=500,
    )


class OrderStatusHistoryResponse(SchemaBase):
    id: int
    order_id: int | None
    order_number: str
    branch_id: int | None
    previous_status: str | None
    new_status: str
    change_note: str | None
    changed_by_admin_id: int | None
    changed_by_name: str | None
    changed_by_email: str | None
    created_at: datetime


class OrderListResponse(SchemaBase):
    total: int
    skip: int
    limit: int
    items: list[OrderResponse]


class WhatsAppOrderResponse(SchemaBase):
    whatsapp_url: str
    message: str
    quote: CartQuoteResponse
    process_after: datetime


# =========================================================
# Parts 14-16: Exports, Revenue and Admin Pricing
# =========================================================


class DataExportResponse(SchemaBase):
    id: int
    export_type: Literal["orders", "products"]
    status: Literal["completed", "failed"]
    branch_id: int | None
    created_by_admin_id: int | None
    file_name: str
    file_sha256: str
    filters_snapshot: dict
    record_count: int
    total_amount: Decimal
    allows_order_deletion: bool
    deleted_order_count: int
    orders_deleted_at: datetime | None
    created_at: datetime


class DeleteExportedOrdersRequest(SchemaBase):
    export_id: int = Field(gt=0)
    confirm: Literal[True]


class DeleteExportedOrdersResponse(SchemaBase):
    message: str
    export_id: int
    deleted_orders: int
    revenue_records_preserved: int
    status_history_preserved: int


class RevenueDailyResponse(SchemaBase):
    sale_date: date
    order_count: int
    revenue: Decimal


class RevenueBranchResponse(SchemaBase):
    branch_id: int | None
    branch_name: str
    order_count: int
    revenue: Decimal


class RevenueDashboardResponse(SchemaBase):
    date_from: date
    date_to: date
    branch_id: int | None
    total_orders: int
    total_revenue: Decimal
    daily: list[RevenueDailyResponse]
    branches: list[RevenueBranchResponse]


class AdminBranchPriceResponse(SchemaBase):
    branch_id: int
    branch_name: str
    master_price: Decimal
    override_price: Decimal | None
    effective_price: Decimal
    price_source: Literal["master", "branch_override"]
    differs_from_master: bool


class AdminProductPriceResponse(SchemaBase):
    product_id: int
    barcode: str
    product_name: str
    category_id: int
    category_name: str
    master_price: Decimal
    is_active: bool
    same_price_on_all_branches: bool
    different_branch_names: list[str]
    branch_prices: list[AdminBranchPriceResponse]


class AdminProductPriceListResponse(SchemaBase):
    total: int
    skip: int
    limit: int
    items: list[AdminProductPriceResponse]


class BranchPriceSetRequest(SchemaBase):
    override_price: Decimal = Field(
        ge=0,
        max_digits=12,
        decimal_places=2,
    )


class AdminPriceUpdateResponse(SchemaBase):
    message: str
    product_id: int
    branch_id: int | None
    master_price: Decimal
    override_price: Decimal | None
    effective_price: Decimal
    price_source: Literal["master", "branch_override"]
