from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models import (
    Branch,
    DiscountCampaign,
    DiscountPrice,
    Product,
)
from schemas import (
    DiscountCampaignCreate,
    DiscountCampaignUpdate,
    DiscountPriceCreate,
    DiscountPriceUpdate,
)
from services.price_service import get_effective_price


def get_discount_campaign_by_id(
    db: Session,
    campaign_id: int,
) -> DiscountCampaign:
    campaign = db.scalar(
        select(DiscountCampaign)
        .options(
            selectinload(DiscountCampaign.prices)
        )
        .where(
            DiscountCampaign.id == campaign_id
        )
    )

    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discount campaign not found.",
        )

    return campaign


def get_all_discount_campaigns(
    db: Session,
    campaign_type: str | None = None,
    active_now: bool = False,
) -> list[DiscountCampaign]:
    statement = (
        select(DiscountCampaign)
        .options(
            selectinload(DiscountCampaign.prices)
        )
        .order_by(
            DiscountCampaign.display_order,
            DiscountCampaign.created_at.desc(),
        )
    )

    if campaign_type:
        statement = statement.where(
            DiscountCampaign.campaign_type
            == campaign_type
        )

    if active_now:
        current_time = datetime.now(timezone.utc)

        statement = statement.where(
            DiscountCampaign.is_active.is_(True),
            DiscountCampaign.start_at <= current_time,
            DiscountCampaign.end_at > current_time,
        )

    return list(db.scalars(statement).all())


def find_overlapping_campaign(
    db: Session,
    campaign: DiscountCampaign,
    product_id: int,
    branch_id: int,
) -> DiscountCampaign | None:
    if not campaign.is_active:
        return None

    return db.scalar(
        select(DiscountCampaign)
        .join(
            DiscountPrice,
            DiscountPrice.campaign_id
            == DiscountCampaign.id,
        )
        .where(
            DiscountCampaign.id != campaign.id,
            DiscountCampaign.is_active.is_(True),
            DiscountPrice.product_id == product_id,
            DiscountPrice.branch_id == branch_id,
            DiscountCampaign.start_at
            < campaign.end_at,
            DiscountCampaign.end_at
            > campaign.start_at,
        )
        .limit(1)
    )


def validate_campaign_overlaps(
    db: Session,
    campaign: DiscountCampaign,
) -> None:
    if not campaign.is_active:
        return

    for discount_price in campaign.prices:
        overlapping_campaign = find_overlapping_campaign(
            db=db,
            campaign=campaign,
            product_id=discount_price.product_id,
            branch_id=discount_price.branch_id,
        )

        if overlapping_campaign:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": (
                        "This campaign overlaps another active "
                        "campaign for the same product and branch."
                    ),
                    "product_id": discount_price.product_id,
                    "branch_id": discount_price.branch_id,
                    "overlapping_campaign_id": (
                        overlapping_campaign.id
                    ),
                    "overlapping_campaign_title": (
                        overlapping_campaign.title
                    ),
                },
            )


def create_discount_campaign(
    db: Session,
    campaign_data: DiscountCampaignCreate,
) -> DiscountCampaign:
    try:
        campaign = DiscountCampaign(
            title=campaign_data.title.strip(),
            description=campaign_data.description,
            campaign_type=campaign_data.campaign_type,
            start_at=campaign_data.start_at,
            end_at=campaign_data.end_at,
            display_order=campaign_data.display_order,
            is_active=campaign_data.is_active,
        )

        db.add(campaign)
        db.commit()

        return get_discount_campaign_by_id(
            db=db,
            campaign_id=campaign.id,
        )

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


def update_discount_campaign(
    db: Session,
    campaign_id: int,
    campaign_data: DiscountCampaignUpdate,
) -> DiscountCampaign:
    try:
        campaign = get_discount_campaign_by_id(
            db=db,
            campaign_id=campaign_id,
        )

        update_data = campaign_data.model_dump(
            exclude_unset=True
        )

        if (
            "title" in update_data
            and update_data["title"] is not None
        ):
            campaign.title = update_data["title"].strip()

        if "description" in update_data:
            campaign.description = update_data[
                "description"
            ]

        if (
            "campaign_type" in update_data
            and update_data["campaign_type"] is not None
        ):
            campaign.campaign_type = update_data[
                "campaign_type"
            ]

        if (
            "start_at" in update_data
            and update_data["start_at"] is not None
        ):
            campaign.start_at = update_data["start_at"]

        if (
            "end_at" in update_data
            and update_data["end_at"] is not None
        ):
            campaign.end_at = update_data["end_at"]

        if campaign.end_at <= campaign.start_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "end_at must be later than start_at."
                ),
            )

        if (
            "display_order" in update_data
            and update_data["display_order"] is not None
        ):
            campaign.display_order = update_data[
                "display_order"
            ]

        if (
            "is_active" in update_data
            and update_data["is_active"] is not None
        ):
            campaign.is_active = update_data[
                "is_active"
            ]

        validate_campaign_overlaps(
            db=db,
            campaign=campaign,
        )

        db.commit()

        return get_discount_campaign_by_id(
            db=db,
            campaign_id=campaign.id,
        )

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


def deactivate_discount_campaign(
    db: Session,
    campaign_id: int,
) -> DiscountCampaign:
    try:
        campaign = get_discount_campaign_by_id(
            db=db,
            campaign_id=campaign_id,
        )

        campaign.is_active = False
        db.commit()

        return get_discount_campaign_by_id(
            db=db,
            campaign_id=campaign.id,
        )

    except Exception:
        db.rollback()
        raise


def get_active_product(
    db: Session,
    product_id: int,
) -> Product:
    product = db.get(Product, product_id)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    if not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive product cannot be discounted.",
        )

    return product


def get_active_branches(
    db: Session,
    branch_ids: list[int],
) -> list[Branch]:
    branches = list(
        db.scalars(
            select(Branch).where(
                Branch.id.in_(branch_ids),
                Branch.is_active.is_(True),
            )
        ).all()
    )

    found_branch_ids = {
        branch.id
        for branch in branches
    }

    missing_branch_ids = (
        set(branch_ids) - found_branch_ids
    )

    if missing_branch_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": (
                    "Some branches are missing or inactive."
                ),
                "branch_ids": sorted(
                    missing_branch_ids
                ),
            },
        )

    return branches


def validate_special_price(
    db: Session,
    product_id: int,
    branch_id: int,
    special_price: Decimal,
) -> None:
    normal_price_data = get_effective_price(
        db=db,
        product_id=product_id,
        branch_id=branch_id,
    )

    normal_price = Decimal(
        normal_price_data["effective_price"]
    )

    if special_price >= normal_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": (
                    "Special price must be lower than "
                    "the normal branch price."
                ),
                "product_id": product_id,
                "branch_id": branch_id,
                "normal_price": str(normal_price),
                "special_price": str(special_price),
            },
        )


def add_or_update_discount_prices(
    db: Session,
    campaign_id: int,
    price_data: DiscountPriceCreate,
) -> list[DiscountPrice]:
    try:
        campaign = get_discount_campaign_by_id(
            db=db,
            campaign_id=campaign_id,
        )

        current_time = datetime.now(timezone.utc)

        if campaign.end_at <= current_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Products cannot be added to an "
                    "expired campaign."
                ),
            )

        get_active_product(
            db=db,
            product_id=price_data.product_id,
        )

        get_active_branches(
            db=db,
            branch_ids=price_data.branch_ids,
        )

        for branch_id in price_data.branch_ids:
            validate_special_price(
                db=db,
                product_id=price_data.product_id,
                branch_id=branch_id,
                special_price=price_data.special_price,
            )

            overlapping_campaign = (
                find_overlapping_campaign(
                    db=db,
                    campaign=campaign,
                    product_id=price_data.product_id,
                    branch_id=branch_id,
                )
            )

            if overlapping_campaign:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": (
                            "Another active campaign overlaps "
                            "for this product and branch."
                        ),
                        "product_id": price_data.product_id,
                        "branch_id": branch_id,
                        "overlapping_campaign_id": (
                            overlapping_campaign.id
                        ),
                    },
                )

        saved_prices = []

        for branch_id in price_data.branch_ids:
            discount_price = db.scalar(
                select(DiscountPrice).where(
                    DiscountPrice.campaign_id
                    == campaign.id,
                    DiscountPrice.product_id
                    == price_data.product_id,
                    DiscountPrice.branch_id
                    == branch_id,
                )
            )

            if discount_price:
                discount_price.special_price = (
                    price_data.special_price
                )

            else:
                discount_price = DiscountPrice(
                    campaign_id=campaign.id,
                    product_id=price_data.product_id,
                    branch_id=branch_id,
                    special_price=price_data.special_price,
                )

                db.add(discount_price)

            saved_prices.append(discount_price)

        db.commit()

        for discount_price in saved_prices:
            db.refresh(discount_price)

        return saved_prices

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


def update_discount_price(
    db: Session,
    discount_price_id: int,
    price_data: DiscountPriceUpdate,
) -> DiscountPrice:
    try:
        discount_price = db.get(
            DiscountPrice,
            discount_price_id,
        )

        if not discount_price:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Discount price not found.",
            )

        campaign = get_discount_campaign_by_id(
            db=db,
            campaign_id=discount_price.campaign_id,
        )

        if campaign.end_at <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Expired discount cannot be edited.",
            )

        validate_special_price(
            db=db,
            product_id=discount_price.product_id,
            branch_id=discount_price.branch_id,
            special_price=price_data.special_price,
        )

        discount_price.special_price = (
            price_data.special_price
        )

        db.commit()
        db.refresh(discount_price)

        return discount_price

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


def delete_discount_price(
    db: Session,
    discount_price_id: int,
) -> dict:
    try:
        discount_price = db.get(
            DiscountPrice,
            discount_price_id,
        )

        if not discount_price:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Discount price not found.",
            )

        db.delete(discount_price)
        db.commit()

        return {
            "message": (
                "Product removed from discount campaign."
            )
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise