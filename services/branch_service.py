from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import Branch
from schemas import BranchCreate, BranchUpdate


def get_all_branches(
    db: Session,
    active_only: bool = False,
) -> list[Branch]:
    statement = select(Branch).order_by(Branch.name)

    if active_only:
        statement = statement.where(Branch.is_active.is_(True))

    return list(db.scalars(statement).all())


def get_branch_by_id(
    db: Session,
    branch_id: int,
) -> Branch:
    branch = db.get(Branch, branch_id)

    if not branch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found.",
        )

    return branch


def create_branch(
    db: Session,
    branch_data: BranchCreate,
) -> Branch:
    normalized_name = branch_data.name.strip()
    normalized_code = branch_data.code.strip().upper()

    branch_with_name = db.scalar(
        select(Branch).where(
            func.lower(Branch.name) == normalized_name.lower()
        )
    )

    if branch_with_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A branch with this name already exists.",
        )

    branch_with_code = db.scalar(
        select(Branch).where(
            Branch.code == normalized_code
        )
    )

    if branch_with_code:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A branch with this code already exists.",
        )

    branch = Branch(
        name=normalized_name,
        code=normalized_code,
        is_active=branch_data.is_active,
    )

    db.add(branch)
    db.commit()
    db.refresh(branch)

    return branch


def update_branch(
    db: Session,
    branch_id: int,
    branch_data: BranchUpdate,
) -> Branch:
    branch = get_branch_by_id(db, branch_id)

    update_data = branch_data.model_dump(exclude_unset=True)

    if "name" in update_data and update_data["name"] is not None:
        normalized_name = update_data["name"].strip()

        duplicate_name = db.scalar(
            select(Branch).where(
                func.lower(Branch.name) == normalized_name.lower(),
                Branch.id != branch_id,
            )
        )

        if duplicate_name:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A branch with this name already exists.",
            )

        branch.name = normalized_name

    if "code" in update_data and update_data["code"] is not None:
        normalized_code = update_data["code"].strip().upper()

        duplicate_code = db.scalar(
            select(Branch).where(
                Branch.code == normalized_code,
                Branch.id != branch_id,
            )
        )

        if duplicate_code:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A branch with this code already exists.",
            )

        branch.code = normalized_code

    if (
        "is_active" in update_data
        and update_data["is_active"] is not None
    ):
        branch.is_active = update_data["is_active"]

    db.commit()
    db.refresh(branch)

    return branch


def deactivate_branch(
    db: Session,
    branch_id: int,
) -> Branch:
    branch = get_branch_by_id(db, branch_id)

    branch.is_active = False

    db.commit()
    db.refresh(branch)

    return branch