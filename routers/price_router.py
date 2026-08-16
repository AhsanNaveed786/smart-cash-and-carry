from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from schemas import (
    BranchPriceOverrideCreate,
    BranchPriceOverrideResponse,
    EffectivePriceResponse,
    MasterPriceUpdate,
    ProductResponse,
)
from services.price_service import (
    get_effective_price,
    get_product_price_overrides,
    reset_branch_price_to_master,
    set_branch_price_override,
    update_master_price,
)


router = APIRouter(
    prefix="/api/prices",
    tags=["Prices"],
)


@router.get(
    "/effective/{product_id}/{branch_id}",
    response_model=EffectivePriceResponse,
)
def view_effective_price(
    product_id: int,
    branch_id: int,
    db: Session = Depends(get_db),
):
    return get_effective_price(
        db=db,
        product_id=product_id,
        branch_id=branch_id,
    )


@router.get(
    "/overrides/{product_id}",
    response_model=list[BranchPriceOverrideResponse],
)
def list_product_overrides(
    product_id: int,
    db: Session = Depends(get_db),
):
    return get_product_price_overrides(
        db=db,
        product_id=product_id,
    )


@router.put(
    "/branch-override",
    response_model=BranchPriceOverrideResponse,
)
def add_or_update_branch_override(
    override_data: BranchPriceOverrideCreate,
    db: Session = Depends(get_db),
):
    return set_branch_price_override(
        db=db,
        override_data=override_data,
    )


@router.patch(
    "/master/{product_id}",
    response_model=ProductResponse,
)
def change_master_price(
    product_id: int,
    price_data: MasterPriceUpdate,
    db: Session = Depends(get_db),
):
    return update_master_price(
        db=db,
        product_id=product_id,
        price_data=price_data,
    )


@router.delete(
    "/branch-override/{branch_id}/{product_id}",
    response_model=EffectivePriceResponse,
)
def reset_to_master_price(
    branch_id: int,
    product_id: int,
    db: Session = Depends(get_db),
):
    return reset_branch_price_to_master(
        db=db,
        product_id=product_id,
        branch_id=branch_id,
    )