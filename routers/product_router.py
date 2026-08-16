from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from database import get_db
from schemas import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)
from services.product_service import (
    create_product,
    deactivate_product,
    get_all_products,
    get_product_by_barcode,
    get_product_by_id,
    update_product,
)


router = APIRouter(
    prefix="/api/products",
    tags=["Products"],
)


@router.get(
    "",
    response_model=ProductListResponse,
)
def list_products(
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=255,
    ),
    category_id: int | None = Query(
        default=None,
        gt=0,
    ),
    active_only: bool = Query(default=False),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return get_all_products(
        db=db,
        search=search,
        category_id=category_id,
        active_only=active_only,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/barcode/{barcode}",
    response_model=ProductResponse,
)
def get_product_using_barcode(
    barcode: str,
    db: Session = Depends(get_db),
):
    return get_product_by_barcode(
        db=db,
        barcode=barcode,
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    return get_product_by_id(
        db=db,
        product_id=product_id,
    )


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
):
    return create_product(
        db=db,
        product_data=product_data,
    )


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
)
def edit_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
):
    return update_product(
        db=db,
        product_id=product_id,
        product_data=product_data,
    )


@router.delete(
    "/{product_id}",
    response_model=ProductResponse,
)
def remove_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    return deactivate_product(
        db=db,
        product_id=product_id,
    )