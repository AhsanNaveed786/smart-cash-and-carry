from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
)
from sqlalchemy.orm import Session

from database import get_db
from schemas import (
    DiscountCampaignCreate,
    DiscountCampaignDetailResponse,
    DiscountCampaignUpdate,
    DiscountPriceCreate,
    DiscountPriceResponse,
    DiscountPriceUpdate,
    MessageResponse,
)
from services.discount_service import (
    add_or_update_discount_prices,
    create_discount_campaign,
    deactivate_discount_campaign,
    delete_discount_price,
    get_all_discount_campaigns,
    get_discount_campaign_by_id,
    update_discount_campaign,
    update_discount_price,
)


router = APIRouter(
    prefix="/api/discounts",
    tags=["Deals and Discounts"],
)


@router.get(
    "",
    response_model=list[
        DiscountCampaignDetailResponse
    ],
)
def list_discount_campaigns(
    campaign_type: Literal[
        "deal",
        "special_discount",
    ] | None = Query(default=None),
    active_now: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    return get_all_discount_campaigns(
        db=db,
        campaign_type=campaign_type,
        active_now=active_now,
    )


@router.post(
    "",
    response_model=DiscountCampaignDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_discount_campaign(
    campaign_data: DiscountCampaignCreate,
    db: Session = Depends(get_db),
):
    return create_discount_campaign(
        db=db,
        campaign_data=campaign_data,
    )


@router.patch(
    "/prices/{discount_price_id}",
    response_model=DiscountPriceResponse,
)
def edit_discount_price(
    discount_price_id: int,
    price_data: DiscountPriceUpdate,
    db: Session = Depends(get_db),
):
    return update_discount_price(
        db=db,
        discount_price_id=discount_price_id,
        price_data=price_data,
    )


@router.delete(
    "/prices/{discount_price_id}",
    response_model=MessageResponse,
)
def remove_discount_price(
    discount_price_id: int,
    db: Session = Depends(get_db),
):
    return delete_discount_price(
        db=db,
        discount_price_id=discount_price_id,
    )


@router.get(
    "/{campaign_id}",
    response_model=DiscountCampaignDetailResponse,
)
def get_discount_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
):
    return get_discount_campaign_by_id(
        db=db,
        campaign_id=campaign_id,
    )


@router.patch(
    "/{campaign_id}",
    response_model=DiscountCampaignDetailResponse,
)
def edit_discount_campaign(
    campaign_id: int,
    campaign_data: DiscountCampaignUpdate,
    db: Session = Depends(get_db),
):
    return update_discount_campaign(
        db=db,
        campaign_id=campaign_id,
        campaign_data=campaign_data,
    )


@router.delete(
    "/{campaign_id}",
    response_model=DiscountCampaignDetailResponse,
)
def remove_discount_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
):
    return deactivate_discount_campaign(
        db=db,
        campaign_id=campaign_id,
    )


@router.put(
    "/{campaign_id}/prices",
    response_model=list[DiscountPriceResponse],
)
def assign_discount_prices(
    campaign_id: int,
    price_data: DiscountPriceCreate,
    db: Session = Depends(get_db),
):
    return add_or_update_discount_prices(
        db=db,
        campaign_id=campaign_id,
        price_data=price_data,
    )