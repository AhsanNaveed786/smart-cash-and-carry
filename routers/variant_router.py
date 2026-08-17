from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
)
from sqlalchemy.orm import Session

from database import get_db
from schemas import (
    ProductVariantCreate,
    ProductVariantResponse,
    ProductVariantUpdate,
)
from services.variant_service import (
    create_product_variant,
    deactivate_product_variant,
    get_product_variant_by_id,
    get_product_variants,
    update_product_variant,
)


router = APIRouter(
    prefix="/api/variants",
    tags=["Product Variants"],
)


@router.get(
    "/product/{product_id}",
    response_model=list[ProductVariantResponse],
)
def list_product_variants(
    product_id: int,
    include_inactive: bool = Query(
        default=False,
    ),
    db: Session = Depends(get_db),
):
    return get_product_variants(
        db=db,
        product_id=product_id,
        include_inactive=include_inactive,
    )


@router.post(
    "/product/{product_id}",
    response_model=ProductVariantResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_product_variant(
    product_id: int,
    variant_data: ProductVariantCreate,
    db: Session = Depends(get_db),
):
    return create_product_variant(
        db=db,
        product_id=product_id,
        variant_data=variant_data,
    )


@router.get(
    "/{variant_id}",
    response_model=ProductVariantResponse,
)
def view_product_variant(
    variant_id: int,
    db: Session = Depends(get_db),
):
    return get_product_variant_by_id(
        db=db,
        variant_id=variant_id,
    )


@router.patch(
    "/{variant_id}",
    response_model=ProductVariantResponse,
)
def edit_product_variant(
    variant_id: int,
    variant_data: ProductVariantUpdate,
    db: Session = Depends(get_db),
):
    return update_product_variant(
        db=db,
        variant_id=variant_id,
        variant_data=variant_data,
    )


@router.delete(
    "/{variant_id}",
    response_model=ProductVariantResponse,
)
def remove_product_variant(
    variant_id: int,
    db: Session = Depends(get_db),
):
    return deactivate_product_variant(
        db=db,
        variant_id=variant_id,
    )