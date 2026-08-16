from datetime import datetime
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
    barcode: str = Field(min_length=1, max_length=100)
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
    barcode: str | None = Field(default=None, min_length=1, max_length=100)
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
    original_filename: str
    status: str
    total_rows: int
    changed_rows: int
    unchanged_rows: int
    invalid_rows: int
    created_at: datetime
    applied_at: datetime | None


class PriceImportPreviewResponse(
    PriceImportBatchResponse
):
    rows: list[PriceImportRowResponse]


class PriceImportApplyRequest(SchemaBase):
    confirm: Literal[True]

class ProductImportRowResponse(SchemaBase):
    id: int
    batch_id: int
    excel_row_number: int
    barcode: str | None
    item_name: str | None
    uploaded_price: Decimal | None
    suggested_category_id: int | None
    confirmed_category_id: int | None
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
    confirmed_category_id: int = Field(gt=0)
    apply_selected: bool = True

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

class ProductImportApplyRequest(SchemaBase):
    confirm: Literal[True]


class ProductImportApplyResponse(SchemaBase):
    batch_id: int
    status: str
    created_products: int
    skipped_rows: int
    applied_at: datetime

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
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime


class AdminLoginResponse(SchemaBase):
    message: str
    admin: AdminResponse
    csrf_token: str
    expires_at: datetime


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