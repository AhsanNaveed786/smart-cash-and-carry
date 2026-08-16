from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    Query,
)
from sqlalchemy.orm import Session

from database import get_db
from schemas import (
    DiscountedProductListResponse,
    StorefrontPriceResponse,
)
from services.storefront_price_service import (
    get_active_discounted_products,
    get_storefront_effective_price,
)


router = APIRouter(
    prefix="/api/storefront",
    tags=["Storefront Pricing"],
)


@router.get(
    "/prices/{product_id}/{branch_id}",
    response_model=StorefrontPriceResponse,
)
def view_storefront_product_price(
    product_id: int,
    branch_id: int,
    db: Session = Depends(get_db),
):
    return get_storefront_effective_price(
        db=db,
        product_id=product_id,
        branch_id=branch_id,
    )


@router.get(
    "/discount-products/{branch_id}",
    response_model=DiscountedProductListResponse,
)
def list_storefront_discount_products(
    branch_id: int,
    campaign_type: Literal[
        "deal",
        "special_discount",
    ] | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    db: Session = Depends(get_db),
):
    return get_active_discounted_products(
        db=db,
        branch_id=branch_id,
        campaign_type=campaign_type,
        skip=skip,
        limit=limit,
    )