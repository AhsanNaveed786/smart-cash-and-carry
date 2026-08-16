from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import BranchPriceOverride
from schemas import (
    BranchPriceOverrideCreate,
    MasterPriceUpdate,
)
from services.branch_service import get_branch_by_id
from services.product_service import get_product_by_id


def get_effective_price(
    db: Session,
    product_id: int,
    branch_id: int,
) -> dict[str, Any]:
    product = get_product_by_id(
        db=db,
        product_id=product_id,
    )

    get_branch_by_id(
        db=db,
        branch_id=branch_id,
    )

    price_override = db.scalar(
        select(BranchPriceOverride).where(
            BranchPriceOverride.product_id == product_id,
            BranchPriceOverride.branch_id == branch_id,
        )
    )

    if price_override:
        effective_price = price_override.override_price
        price_source = "branch_override"
        branch_override_price = price_override.override_price

    else:
        effective_price = product.master_price
        price_source = "master"
        branch_override_price = None

    return {
        "product_id": product.id,
        "branch_id": branch_id,
        "master_price": product.master_price,
        "branch_override_price": branch_override_price,
        "effective_price": effective_price,
        "price_source": price_source,
    }


def get_product_price_overrides(
    db: Session,
    product_id: int,
) -> list[BranchPriceOverride]:
    get_product_by_id(
        db=db,
        product_id=product_id,
    )

    statement = (
        select(BranchPriceOverride)
        .where(
            BranchPriceOverride.product_id == product_id
        )
        .order_by(BranchPriceOverride.branch_id)
    )

    return list(db.scalars(statement).all())


def set_branch_price_override(
    db: Session,
    override_data: BranchPriceOverrideCreate,
) -> BranchPriceOverride:
    get_product_by_id(
        db=db,
        product_id=override_data.product_id,
    )

    get_branch_by_id(
        db=db,
        branch_id=override_data.branch_id,
    )

    existing_override = db.scalar(
        select(BranchPriceOverride).where(
            BranchPriceOverride.product_id
            == override_data.product_id,
            BranchPriceOverride.branch_id
            == override_data.branch_id,
        )
    )

    if existing_override:
        existing_override.override_price = (
            override_data.override_price
        )

        price_override = existing_override

    else:
        price_override = BranchPriceOverride(
            product_id=override_data.product_id,
            branch_id=override_data.branch_id,
            override_price=override_data.override_price,
        )

        db.add(price_override)

    db.commit()
    db.refresh(price_override)

    return price_override


def update_master_price(
    db: Session,
    product_id: int,
    price_data: MasterPriceUpdate,
):
    product = get_product_by_id(
        db=db,
        product_id=product_id,
    )

    product.master_price = price_data.master_price

    # Branch overrides are intentionally not changed.
    db.commit()
    db.refresh(product)

    return product


def reset_branch_price_to_master(
    db: Session,
    product_id: int,
    branch_id: int,
) -> dict[str, Any]:
    get_product_by_id(
        db=db,
        product_id=product_id,
    )

    get_branch_by_id(
        db=db,
        branch_id=branch_id,
    )

    existing_override = db.scalar(
        select(BranchPriceOverride).where(
            BranchPriceOverride.product_id == product_id,
            BranchPriceOverride.branch_id == branch_id,
        )
    )

    if existing_override:
        db.delete(existing_override)
        db.commit()

    return get_effective_price(
        db=db,
        product_id=product_id,
        branch_id=branch_id,
    )