from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import (
    Branch,
    BranchPriceOverride,
    DiscountCampaign,
    DiscountPrice,
    Product,
)


TWO_DECIMAL_PLACES = Decimal("0.01")


def format_price(value: Decimal) -> Decimal:
    return Decimal(value).quantize(
        TWO_DECIMAL_PLACES,
        rounding=ROUND_HALF_UP,
    )


def calculate_savings(
    normal_price: Decimal,
    special_price: Decimal,
) -> tuple[Decimal, Decimal]:
    savings_amount = format_price(
        normal_price - special_price
    )

    if normal_price <= 0:
        savings_percentage = Decimal("0.00")
    else:
        savings_percentage = format_price(
            savings_amount
            / normal_price
            * Decimal("100")
        )

    return savings_amount, savings_percentage


def get_active_storefront_branch(
    db: Session,
    branch_id: int,
) -> Branch:
    branch = db.get(Branch, branch_id)

    if not branch or not branch.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active branch not found.",
        )

    return branch


def get_active_storefront_product(
    db: Session,
    product_id: int,
) -> Product:
    product = db.get(Product, product_id)

    if not product or not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active product not found.",
        )

    return product


def get_normal_product_price(
    db: Session,
    product: Product,
    branch_id: int,
) -> dict[str, Any]:
    price_override = db.scalar(
        select(BranchPriceOverride).where(
            BranchPriceOverride.product_id
            == product.id,
            BranchPriceOverride.branch_id
            == branch_id,
        )
    )

    master_price = format_price(
        product.master_price
    )

    if price_override:
        branch_override_price = format_price(
            price_override.override_price
        )

        return {
            "master_price": master_price,
            "branch_override_price": (
                branch_override_price
            ),
            "normal_price": branch_override_price,
            "normal_price_source": (
                "branch_override"
            ),
        }

    return {
        "master_price": master_price,
        "branch_override_price": None,
        "normal_price": master_price,
        "normal_price_source": "master",
    }


def get_active_product_discount(
    db: Session,
    product_id: int,
    branch_id: int,
) -> tuple[
    DiscountPrice,
    DiscountCampaign,
] | None:
    current_time = datetime.now(timezone.utc)

    result = db.execute(
        select(
            DiscountPrice,
            DiscountCampaign,
        )
        .join(
            DiscountCampaign,
            DiscountCampaign.id
            == DiscountPrice.campaign_id,
        )
        .where(
            DiscountPrice.product_id == product_id,
            DiscountPrice.branch_id == branch_id,
            DiscountCampaign.is_active.is_(True),
            DiscountCampaign.start_at <= current_time,
            DiscountCampaign.end_at > current_time,
        )
        .order_by(
            DiscountCampaign.display_order,
            DiscountPrice.special_price,
            DiscountCampaign.id,
        )
        .limit(1)
    ).first()

    if not result:
        return None

    return result[0], result[1]


def get_storefront_effective_price(
    db: Session,
    product_id: int,
    branch_id: int,
) -> dict[str, Any]:
    get_active_storefront_branch(
        db=db,
        branch_id=branch_id,
    )

    product = get_active_storefront_product(
        db=db,
        product_id=product_id,
    )

    normal_price_data = get_normal_product_price(
        db=db,
        product=product,
        branch_id=branch_id,
    )

    normal_price = normal_price_data[
        "normal_price"
    ]

    active_discount = get_active_product_discount(
        db=db,
        product_id=product_id,
        branch_id=branch_id,
    )

    response = {
        "product_id": product.id,
        "branch_id": branch_id,
        "master_price": normal_price_data[
            "master_price"
        ],
        "branch_override_price": normal_price_data[
            "branch_override_price"
        ],
        "normal_price": normal_price,
        "special_price": None,
        "effective_price": normal_price,
        "normal_price_source": normal_price_data[
            "normal_price_source"
        ],
        "price_source": normal_price_data[
            "normal_price_source"
        ],
        "discount_campaign_id": None,
        "discount_campaign_title": None,
        "discount_campaign_type": None,
        "discount_ends_at": None,
        "savings_amount": Decimal("0.00"),
        "savings_percentage": Decimal("0.00"),
    }

    if not active_discount:
        return response

    discount_price, campaign = active_discount

    special_price = format_price(
        discount_price.special_price
    )

    # If the normal price was reduced after campaign creation,
    # never show a fake or more expensive discount.
    if special_price >= normal_price:
        return response

    savings_amount, savings_percentage = (
        calculate_savings(
            normal_price=normal_price,
            special_price=special_price,
        )
    )

    response.update(
        {
            "special_price": special_price,
            "effective_price": special_price,
            "price_source": "discount",
            "discount_campaign_id": campaign.id,
            "discount_campaign_title": (
                campaign.title
            ),
            "discount_campaign_type": (
                campaign.campaign_type
            ),
            "discount_ends_at": campaign.end_at,
            "savings_amount": savings_amount,
            "savings_percentage": (
                savings_percentage
            ),
        }
    )

    return response


def get_active_discounted_products(
    db: Session,
    branch_id: int,
    campaign_type: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> dict[str, Any]:
    get_active_storefront_branch(
        db=db,
        branch_id=branch_id,
    )

    current_time = datetime.now(timezone.utc)

    statement = (
        select(
            DiscountPrice,
            DiscountCampaign,
            Product,
        )
        .join(
            DiscountCampaign,
            DiscountCampaign.id
            == DiscountPrice.campaign_id,
        )
        .join(
            Product,
            Product.id
            == DiscountPrice.product_id,
        )
        .where(
            DiscountPrice.branch_id == branch_id,
            DiscountCampaign.is_active.is_(True),
            DiscountCampaign.start_at <= current_time,
            DiscountCampaign.end_at > current_time,
            Product.is_active.is_(True),
        )
        .order_by(
            DiscountCampaign.display_order,
            Product.name,
        )
    )

    if campaign_type:
        statement = statement.where(
            DiscountCampaign.campaign_type
            == campaign_type
        )

    discount_records = list(
        db.execute(statement).all()
    )

    product_ids = {
        product.id
        for _, _, product in discount_records
    }

    overrides_by_product_id = {}

    if product_ids:
        price_overrides = db.scalars(
            select(BranchPriceOverride).where(
                BranchPriceOverride.branch_id
                == branch_id,
                BranchPriceOverride.product_id.in_(
                    product_ids
                ),
            )
        ).all()

        overrides_by_product_id = {
            price_override.product_id: price_override
            for price_override in price_overrides
        }

    items = []
    included_product_ids: set[int] = set()

    for (
        discount_price,
        campaign,
        product,
    ) in discount_records:
        # Defensive protection if overlapping campaigns
        # somehow enter the database concurrently.
        if product.id in included_product_ids:
            continue

        price_override = (
            overrides_by_product_id.get(
                product.id
            )
        )

        if price_override:
            normal_price = format_price(
                price_override.override_price
            )
            normal_price_source = (
                "branch_override"
            )
        else:
            normal_price = format_price(
                product.master_price
            )
            normal_price_source = "master"

        special_price = format_price(
            discount_price.special_price
        )

        if special_price >= normal_price:
            continue

        savings_amount, savings_percentage = (
            calculate_savings(
                normal_price=normal_price,
                special_price=special_price,
            )
        )

        items.append(
            {
                "product_id": product.id,
                "barcode": product.barcode,
                "name": product.name,
                "slug": product.slug,
                "image_url": product.image_url,
                "category_id": product.category_id,
                "branch_id": branch_id,
                "campaign_id": campaign.id,
                "campaign_title": campaign.title,
                "campaign_type": (
                    campaign.campaign_type
                ),
                "normal_price": normal_price,
                "special_price": special_price,
                "savings_amount": savings_amount,
                "savings_percentage": (
                    savings_percentage
                ),
                "normal_price_source": (
                    normal_price_source
                ),
                "discount_ends_at": (
                    campaign.end_at
                ),
            }
        )

        included_product_ids.add(product.id)

    total = len(items)

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items[skip : skip + limit],
    }