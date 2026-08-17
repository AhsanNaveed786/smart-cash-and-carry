from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models import ProductImage, ProductVariant, VariantAvailability
from schemas import VariantStockUpdate
from services.availability_service import (
    get_active_availability_branch,
    get_product_availability,
)
from services.storefront_price_service import get_storefront_effective_price
from services.variant_service import (
    get_product_variant_by_id,
    get_variant_product,
)


TWO_DECIMAL_PLACES = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(
        TWO_DECIMAL_PLACES,
        rounding=ROUND_HALF_UP,
    )


def find_variant_stock_record(
    db: Session,
    variant_id: int,
    branch_id: int,
) -> VariantAvailability | None:
    return db.scalar(
        select(VariantAvailability).where(
            VariantAvailability.variant_id == variant_id,
            VariantAvailability.branch_id == branch_id,
        )
    )


def build_variant_stock_response(
    variant_id: int,
    branch_id: int,
    stock_record: VariantAvailability | None,
) -> dict:
    if stock_record:
        return {
            "availability_record_id": stock_record.id,
            "variant_id": variant_id,
            "branch_id": branch_id,
            "is_in_stock": stock_record.is_in_stock,
            "stock_message": stock_record.stock_message,
            "availability_source": "branch_record",
        }

    return {
        "availability_record_id": None,
        "variant_id": variant_id,
        "branch_id": branch_id,
        "is_in_stock": True,
        "stock_message": None,
        "availability_source": "default",
    }


def get_variant_stock(
    db: Session,
    variant_id: int,
    branch_id: int,
) -> dict:
    get_active_availability_branch(db=db, branch_id=branch_id)
    variant = get_product_variant_by_id(db=db, variant_id=variant_id)
    get_variant_product(db=db, product_id=variant.product_id)
    stock_record = find_variant_stock_record(
        db=db,
        variant_id=variant_id,
        branch_id=branch_id,
    )
    return build_variant_stock_response(
        variant_id=variant_id,
        branch_id=branch_id,
        stock_record=stock_record,
    )


def set_variant_stock(
    db: Session,
    variant_id: int,
    branch_id: int,
    stock_data: VariantStockUpdate,
) -> VariantAvailability:
    get_active_availability_branch(db=db, branch_id=branch_id)
    variant = get_product_variant_by_id(db=db, variant_id=variant_id)
    get_variant_product(db=db, product_id=variant.product_id)

    if not variant.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stock cannot be set for an inactive variant.",
        )

    try:
        stock_record = find_variant_stock_record(
            db=db,
            variant_id=variant_id,
            branch_id=branch_id,
        )
        stock_message = (
            stock_data.stock_message.strip()
            if stock_data.stock_message
            else None
        )

        if stock_record:
            stock_record.is_in_stock = stock_data.is_in_stock
            stock_record.stock_message = stock_message
        else:
            stock_record = VariantAvailability(
                variant_id=variant_id,
                branch_id=branch_id,
                is_in_stock=stock_data.is_in_stock,
                stock_message=stock_message,
            )
            db.add(stock_record)

        db.commit()
        db.refresh(stock_record)
        return stock_record
    except Exception:
        db.rollback()
        raise


def reset_variant_stock(
    db: Session,
    variant_id: int,
    branch_id: int,
) -> dict:
    get_active_availability_branch(db=db, branch_id=branch_id)
    variant = get_product_variant_by_id(db=db, variant_id=variant_id)
    get_variant_product(db=db, product_id=variant.product_id)

    try:
        stock_record = find_variant_stock_record(
            db=db,
            variant_id=variant_id,
            branch_id=branch_id,
        )
        if stock_record:
            db.delete(stock_record)
            db.commit()

        return build_variant_stock_response(
            variant_id=variant_id,
            branch_id=branch_id,
            stock_record=None,
        )
    except Exception:
        db.rollback()
        raise


def get_storefront_product_variants(
    db: Session,
    product_id: int,
    branch_id: int,
) -> dict:
    get_active_availability_branch(db=db, branch_id=branch_id)
    product = get_variant_product(db=db, product_id=product_id)
    price_data = get_storefront_effective_price(
        db=db,
        product_id=product_id,
        branch_id=branch_id,
    )
    product_stock = get_product_availability(
        db=db,
        product_id=product_id,
        branch_id=branch_id,
    )

    variants = list(
        db.scalars(
            select(ProductVariant)
            .options(selectinload(ProductVariant.images))
            .where(
                ProductVariant.product_id == product_id,
                ProductVariant.is_active.is_(True),
            )
            .order_by(ProductVariant.display_order, ProductVariant.id)
        ).all()
    )

    variant_ids = [variant.id for variant in variants]
    stock_by_variant_id = {}

    if variant_ids:
        stock_records = db.scalars(
            select(VariantAvailability).where(
                VariantAvailability.branch_id == branch_id,
                VariantAvailability.variant_id.in_(variant_ids),
            )
        ).all()
        stock_by_variant_id = {
            record.variant_id: record for record in stock_records
        }

    general_images = list(
        db.scalars(
            select(ProductImage)
            .where(
                ProductImage.product_id == product_id,
                ProductImage.variant_id.is_(None),
            )
            .order_by(ProductImage.display_order, ProductImage.id)
        ).all()
    )
    general_image_urls = [image.image_url for image in general_images]
    if not general_image_urls and product.image_url:
        general_image_urls = [product.image_url]

    base_effective_price = money(price_data["effective_price"])
    items = []

    for variant in variants:
        stock_record = stock_by_variant_id.get(variant.id)
        variant_in_stock = (
            stock_record.is_in_stock if stock_record else True
        )
        is_in_stock = product_stock["is_in_stock"] and variant_in_stock
        stock_message = None

        if not product_stock["is_in_stock"]:
            stock_message = product_stock["stock_message"]
        elif stock_record and not stock_record.is_in_stock:
            stock_message = stock_record.stock_message

        final_price = money(
            base_effective_price + Decimal(variant.price_adjustment)
        )
        if final_price < 0:
            final_price = Decimal("0.00")

        variant_image_urls = [
            image.image_url
            for image in sorted(
                variant.images,
                key=lambda image: (image.display_order, image.id),
            )
        ]

        items.append(
            {
                "variant_id": variant.id,
                "product_id": product_id,
                "name": variant.name,
                "sku": variant.sku,
                "barcode": variant.barcode,
                "attributes": variant.attributes,
                "price_adjustment": money(variant.price_adjustment),
                "base_effective_price": base_effective_price,
                "effective_price": final_price,
                "is_default": variant.is_default,
                "is_in_stock": is_in_stock,
                "stock_message": stock_message,
                "image_urls": variant_image_urls or general_image_urls,
            }
        )

    return {
        "product_id": product_id,
        "branch_id": branch_id,
        "total": len(items),
        "items": items,
    }
