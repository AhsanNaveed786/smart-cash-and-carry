from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from database import get_db
from dependencies.admin_access import require_current_admin
from models import Admin
from schemas import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
)
from services.category_service import (
    create_category,
    deactivate_category,
    get_all_categories,
    get_category_by_id,
    update_category,
)


router = APIRouter(
    prefix="/api/categories",
    tags=["Categories"],
)


@router.get(
    "",
    response_model=list[CategoryResponse],
)
def list_categories(
    active_only: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    return get_all_categories(
        db=db,
        active_only=active_only,
    )


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
):
    return get_category_by_id(
        db=db,
        category_id=category_id,
    )


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    _admin: Admin = Depends(require_current_admin),
):
    return create_category(
        db=db,
        category_data=category_data,
    )


@router.patch(
    "/{category_id}",
    response_model=CategoryResponse,
)
def edit_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: Session = Depends(get_db),
    _admin: Admin = Depends(require_current_admin),
):
    return update_category(
        db=db,
        category_id=category_id,
        category_data=category_data,
    )


@router.delete(
    "/{category_id}",
    response_model=CategoryResponse,
)
def remove_category(
    category_id: int,
    db: Session = Depends(get_db),
    _admin: Admin = Depends(require_current_admin),
):
    return deactivate_category(
        db=db,
        category_id=category_id,
    )