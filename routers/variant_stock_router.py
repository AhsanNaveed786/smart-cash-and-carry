from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from schemas import (
    StorefrontVariantListResponse,
    VariantAvailabilityResponse,
    VariantStockResponse,
    VariantStockUpdate,
)
from services.variant_stock_service import (
    get_storefront_product_variants,
    get_variant_stock,
    reset_variant_stock,
    set_variant_stock,
)


router = APIRouter(
    prefix="/api",
    tags=["Variant Stock and Storefront Pricing"],
)


@router.get(
    "/variant-stock/{variant_id}/{branch_id}",
    response_model=VariantStockResponse,
)
def view_variant_stock(
    variant_id: int,
    branch_id: int,
    db: Session = Depends(get_db),
):
    return get_variant_stock(
        db=db,
        variant_id=variant_id,
        branch_id=branch_id,
    )


@router.put(
    "/variant-stock/{variant_id}/{branch_id}",
    response_model=VariantAvailabilityResponse,
)
def update_variant_stock(
    variant_id: int,
    branch_id: int,
    stock_data: VariantStockUpdate,
    db: Session = Depends(get_db),
):
    return set_variant_stock(
        db=db,
        variant_id=variant_id,
        branch_id=branch_id,
        stock_data=stock_data,
    )


@router.delete(
    "/variant-stock/{variant_id}/{branch_id}",
    response_model=VariantStockResponse,
)
def restore_default_variant_stock(
    variant_id: int,
    branch_id: int,
    db: Session = Depends(get_db),
):
    return reset_variant_stock(
        db=db,
        variant_id=variant_id,
        branch_id=branch_id,
    )


@router.get(
    "/storefront/products/{product_id}/variants/{branch_id}",
    response_model=StorefrontVariantListResponse,
)
def list_storefront_product_variants(
    product_id: int,
    branch_id: int,
    db: Session = Depends(get_db),
):
    return get_storefront_product_variants(
        db=db,
        product_id=product_id,
        branch_id=branch_id,
    )
