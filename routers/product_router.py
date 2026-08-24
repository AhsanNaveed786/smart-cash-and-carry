from typing import Any
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from dependencies.admin_access import require_current_admin, require_super_admin
from models import Admin
from schemas import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)
from services.product_service import (
    activate_product,
    bulk_activate_products,
    bulk_deactivate_products,
    bulk_delete_products,
    bulk_move_products_category,
    create_product,
    deactivate_product,
    delete_all_products,
    delete_product,
    get_all_products,
    get_product_by_barcode,
    get_product_by_id,
    sanitize_existing_product_names,
    update_product,
)


class ProductBulkActionRequest(BaseModel):
    product_ids: list[int] = Field(default_factory=list)
    select_all: bool = False
    search: str | None = None
    category_id: int | None = None


class ProductBulkDeactivateRequest(BaseModel):
    product_ids: list[int] = Field(default_factory=list)
    select_all: bool = False
    search: str | None = None
    category_id: int | None = None


class ProductBulkMoveCategoryRequest(BaseModel):
    product_ids: list[int] = Field(default_factory=list)
    select_all: bool = False
    search: str | None = None
    category_id: int | None = None
    target_category_id: int = Field(gt=0)


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


@router.delete(
    "/delete-all",
)
def remove_all_products(
    db: Session = Depends(get_db),
    _admin: Admin = Depends(require_super_admin),
):
    return delete_all_products(db=db)


@router.post(
    "/bulk-delete",
)
def bulk_remove_products_permanently(
    request_data: ProductBulkActionRequest,
    db: Session = Depends(get_db),
    _admin: Admin = Depends(require_super_admin),
):
    return bulk_delete_products(
        db=db,
        product_ids=request_data.product_ids,
        select_all=request_data.select_all,
        search=request_data.search,
        category_id=request_data.category_id,
    )


@router.post(
    "/bulk-activate",
)
def bulk_enable_products(
    request_data: ProductBulkActionRequest,
    db: Session = Depends(get_db),
    _admin: Admin = Depends(require_current_admin),
):
    return bulk_activate_products(
        db=db,
        product_ids=request_data.product_ids,
        select_all=request_data.select_all,
        search=request_data.search,
        category_id=request_data.category_id,
    )


@router.post(
    "/bulk-deactivate",
)
def bulk_remove_products(
    request_data: ProductBulkDeactivateRequest,
    db: Session = Depends(get_db),
    _admin: Admin = Depends(require_current_admin),
):
    return bulk_deactivate_products(
        db=db,
        product_ids=request_data.product_ids,
        select_all=request_data.select_all,
        search=request_data.search,
        category_id=request_data.category_id,
    )


@router.post(
    "/bulk-move-category",
)
def bulk_move_category_endpoint(
    request_data: ProductBulkMoveCategoryRequest,
    db: Session = Depends(get_db),
    _admin: Admin = Depends(require_current_admin),
):
    return bulk_move_products_category(
        db=db,
        target_category_id=request_data.target_category_id,
        product_ids=request_data.product_ids,
        select_all=request_data.select_all,
        search=request_data.search,
        category_id=request_data.category_id,
    )


@router.post(
    "/sanitize-names",
)
def sanitize_names_endpoint(
    db: Session = Depends(get_db),
    _admin: Admin = Depends(require_super_admin),
):
    return sanitize_existing_product_names(db=db)


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
    _admin: Admin = Depends(require_current_admin),
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
    _admin: Admin = Depends(require_current_admin),
):
    return update_product(
        db=db,
        product_id=product_id,
        product_data=product_data,
    )


@router.post(
    "/{product_id}/activate",
    response_model=ProductResponse,
)
def enable_product(
    product_id: int,
    db: Session = Depends(get_db),
    _admin: Admin = Depends(require_current_admin),
):
    return activate_product(
        db=db,
        product_id=product_id,
    )


@router.delete(
    "/{product_id}",
    response_model=ProductResponse,
)
def remove_product(
    product_id: int,
    db: Session = Depends(get_db),
    _admin: Admin = Depends(require_current_admin),
):
    return deactivate_product(
        db=db,
        product_id=product_id,
    )


@router.delete(
    "/{product_id}/permanent",
)
def permanently_remove_product(
    product_id: int,
    db: Session = Depends(get_db),
    _admin: Admin = Depends(require_current_admin),
):
    return delete_product(
        db=db,
        product_id=product_id,
    )
