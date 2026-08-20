from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from database import get_db
from dependencies.admin_access import require_current_admin
from models import Admin
from schemas import (
    BranchCreate,
    BranchResponse,
    BranchUpdate,
)
from services.branch_service import (
    create_branch,
    deactivate_branch,
    get_all_branches,
    get_branch_by_id,
    update_branch,
)


router = APIRouter(
    prefix="/api/branches",
    tags=["Branches"],
)


@router.get(
    "",
    response_model=list[BranchResponse],
)
def list_branches(
    active_only: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    return get_all_branches(
        db=db,
        active_only=active_only,
    )


@router.get(
    "/{branch_id}",
    response_model=BranchResponse,
)
def get_branch(
    branch_id: int,
    db: Session = Depends(get_db),
):
    return get_branch_by_id(
        db=db,
        branch_id=branch_id,
    )


@router.post(
    "",
    response_model=BranchResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_branch(
    branch_data: BranchCreate,
    db: Session = Depends(get_db),
    _admin: Admin = Depends(require_current_admin),
):
    return create_branch(
        db=db,
        branch_data=branch_data,
    )


@router.patch(
    "/{branch_id}",
    response_model=BranchResponse,
)
def edit_branch(
    branch_id: int,
    branch_data: BranchUpdate,
    db: Session = Depends(get_db),
    _admin: Admin = Depends(require_current_admin),
):
    return update_branch(
        db=db,
        branch_id=branch_id,
        branch_data=branch_data,
    )


@router.delete(
    "/{branch_id}",
    response_model=BranchResponse,
)
def remove_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    _admin: Admin = Depends(require_current_admin),
):
    return deactivate_branch(
        db=db,
        branch_id=branch_id,
    )