from fastapi import (
    APIRouter,
    Depends,
    Query,
)
from sqlalchemy.orm import Session

from database import get_db
from schemas import (
    BranchAvailabilityListResponse,
    ProductAvailabilityBulkUpdate,
    ProductAvailabilityResponse,
    ProductAvailabilityUpdate,
    StorefrontAvailabilityResponse,
)
from services.availability_service import (
    get_branch_product_availability,
    get_product_availability,
    reset_product_availability,
    set_bulk_product_availability,
    set_product_availability,
)


router = APIRouter(
    prefix="/api/availability",
    tags=["Branch Product Availability"],
)


@router.get(
    "/branch/{branch_id}",
    response_model=BranchAvailabilityListResponse,
)
def list_branch_availability(
    branch_id: int,
    category_id: int | None = Query(
        default=None,
        gt=0,
    ),
    in_stock: bool | None = Query(
        default=None,
    ),
    skip: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
    ),
    db: Session = Depends(get_db),
):
    return get_branch_product_availability(
        db=db,
        branch_id=branch_id,
        category_id=category_id,
        in_stock=in_stock,
        skip=skip,
        limit=limit,
    )


@router.put(
    "/bulk",
    response_model=list[
        ProductAvailabilityResponse
    ],
)
def update_bulk_availability(
    availability_data: (
        ProductAvailabilityBulkUpdate
    ),
    db: Session = Depends(get_db),
):
    return set_bulk_product_availability(
        db=db,
        availability_data=availability_data,
    )


@router.get(
    "/{product_id}/{branch_id}",
    response_model=StorefrontAvailabilityResponse,
)
def view_product_availability(
    product_id: int,
    branch_id: int,
    db: Session = Depends(get_db),
):
    return get_product_availability(
        db=db,
        product_id=product_id,
        branch_id=branch_id,
    )


@router.put(
    "/{product_id}/{branch_id}",
    response_model=ProductAvailabilityResponse,
)
def update_product_availability(
    product_id: int,
    branch_id: int,
    availability_data: ProductAvailabilityUpdate,
    db: Session = Depends(get_db),
):
    return set_product_availability(
        db=db,
        product_id=product_id,
        branch_id=branch_id,
        availability_data=availability_data,
    )


@router.delete(
    "/{product_id}/{branch_id}",
    response_model=StorefrontAvailabilityResponse,
)
def restore_default_availability(
    product_id: int,
    branch_id: int,
    db: Session = Depends(get_db),
):
    return reset_product_availability(
        db=db,
        product_id=product_id,
        branch_id=branch_id,
    )