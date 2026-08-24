from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from models import (
    BranchPriceOverride,
    Product,
    ProductVariant,
)
from schemas import (
    ProductVariantCreate,
    ProductVariantUpdate,
)


def get_variant_product(
    db: Session,
    product_id: int,
    allow_inactive: bool = False,
) -> Product:
    product = db.get(
        Product,
        product_id,
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    if not product.is_active and not allow_inactive:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Variants cannot be managed for "
                "an inactive product."
            ),
        )

    return product


def get_product_variant_by_id(
    db: Session,
    variant_id: int,
) -> ProductVariant:
    variant = db.scalar(
        select(ProductVariant)
        .options(
            selectinload(ProductVariant.images)
        )
        .where(
            ProductVariant.id == variant_id
        )
    )

    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product variant not found.",
        )

    return variant


import re


def determine_base_variant_name(product: Product) -> str:
    """
    Determine a clean name for the base product variant option (e.g. '1 Litre', '1kg', '100ml', 'Standard').
    """
    if product.unit_size and product.unit_size.strip():
        return product.unit_size.strip()

    name = (product.name or "").strip()
    size_match = re.search(
        r'(\d+(?:\.\d+)?\s*(?:kg|g|l|litre|litres|ml|oz|lb|pack|pcs|pieces))\b',
        name,
        re.IGNORECASE,
    )
    if size_match:
        val = size_match.group(1).strip()
        if val.upper() in ["1L", "1 L"]:
            return "1 Litre"
        return val

    for word in ["Small Pack", "Large Pack", "Gift Box", "Set", "Regular", "Standard"]:
        if word.lower() in name.lower():
            return word

    return "Standard"


def determine_base_variant_sku(db: Session, product: Product) -> str:
    """
    Generate a guaranteed unique SKU for the product's base variant option.
    """
    raw_base = product.barcode or f"PROD{product.id}"
    cleaned = re.sub(r'[^A-Za-z0-9_-]', '', raw_base).upper()
    if not cleaned:
        cleaned = f"PROD{product.id}"

    candidate = f"{cleaned}-BASE"
    counter = 1
    while db.scalar(select(ProductVariant).where(ProductVariant.sku == candidate)) is not None:
        candidate = f"{cleaned}-BASE-{counter}"
        counter += 1
    return candidate


def ensure_product_base_variant(db: Session, product_id: int) -> ProductVariant | None:
    """
    If a product has active variants but no base variant (price_adjustment == 0),
    automatically create the base variant representing the original product so the original option
    is never lost on the storefront.
    """
    product = db.get(Product, product_id)
    if not product:
        return None

    active_variants = list(
        db.scalars(
            select(ProductVariant).where(
                ProductVariant.product_id == product_id,
                ProductVariant.is_active.is_(True),
            ).order_by(ProductVariant.display_order, ProductVariant.id)
        ).all()
    )

    if not active_variants:
        return None

    # Check if a base variant (price_adjustment == 0) already exists
    has_base = any(Decimal(str(v.price_adjustment)) == Decimal("0.00") for v in active_variants)
    if has_base:
        return None

    # No base variant exists! Create it now.
    base_name = determine_base_variant_name(product)
    base_sku = determine_base_variant_sku(db=db, product=product)

    # Shift display_order of other variants
    for v in active_variants:
        if v.display_order == 0:
            v.display_order = 1

    has_default = any(v.is_default for v in active_variants)

    base_variant = ProductVariant(
        product_id=product_id,
        name=base_name,
        sku=base_sku,
        barcode=None,
        attributes={},
        price_adjustment=Decimal("0.00"),
        display_order=0,
        is_default=not has_default,
        is_active=True,
    )
    db.add(base_variant)
    db.flush()
    ensure_product_has_default_variant(db=db, product_id=product_id)
    db.commit()
    return base_variant


def get_product_variants(
    db: Session,
    product_id: int,
    include_inactive: bool = False,
) -> list[ProductVariant]:
    get_variant_product(
        db=db,
        product_id=product_id,
        allow_inactive=include_inactive,
    )

    # Auto-ensure base variant exists if variants exist
    ensure_product_base_variant(db=db, product_id=product_id)

    statement = (
        select(ProductVariant)
        .options(
            selectinload(ProductVariant.images)
        )
        .where(
            ProductVariant.product_id
            == product_id
        )
        .order_by(
            ProductVariant.display_order,
            ProductVariant.id,
        )
    )

    if not include_inactive:
        statement = statement.where(
            ProductVariant.is_active.is_(True)
        )

    return list(
        db.scalars(statement).all()
    )


def validate_variant_sku(
    db: Session,
    sku: str,
    current_variant_id: int | None = None,
) -> str:
    normalized_sku = sku.strip().upper()

    statement = select(
        ProductVariant
    ).where(
        ProductVariant.sku == normalized_sku
    )

    if current_variant_id is not None:
        statement = statement.where(
            ProductVariant.id
            != current_variant_id
        )

    existing_variant = db.scalar(statement)

    if existing_variant:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Variant SKU already exists.",
        )

    return normalized_sku


def validate_variant_barcode(
    db: Session,
    barcode: str | None,
    current_variant_id: int | None = None,
) -> str | None:
    if not barcode:
        return None

    normalized_barcode = barcode.strip()

    product_with_barcode = db.scalar(
        select(Product).where(
            Product.barcode
            == normalized_barcode
        )
    )

    if product_with_barcode:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Barcode is already used by a product."
            ),
        )

    statement = select(
        ProductVariant
    ).where(
        ProductVariant.barcode
        == normalized_barcode
    )

    if current_variant_id is not None:
        statement = statement.where(
            ProductVariant.id
            != current_variant_id
        )

    existing_variant = db.scalar(statement)

    if existing_variant:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Barcode is already used by "
                "another variant."
            ),
        )

    return normalized_barcode


def validate_variant_price_adjustment(
    db: Session,
    product: Product,
    price_adjustment: Decimal,
) -> None:
    possible_base_prices = [
        Decimal(product.master_price)
    ]

    branch_prices = db.scalars(
        select(
            BranchPriceOverride.override_price
        ).where(
            BranchPriceOverride.product_id
            == product.id
        )
    ).all()

    possible_base_prices.extend(
        Decimal(price)
        for price in branch_prices
    )

    minimum_base_price = min(
        possible_base_prices
    )

    final_minimum_price = (
        minimum_base_price
        + Decimal(price_adjustment)
    )

    if final_minimum_price < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": (
                    "Variant price adjustment makes "
                    "the final price negative."
                ),
                "minimum_base_price": str(
                    minimum_base_price
                ),
                "price_adjustment": str(
                    price_adjustment
                ),
            },
        )


def clear_existing_default_variant(
    db: Session,
    product_id: int,
    excluded_variant_id: int | None = None,
) -> None:
    statement = select(
        ProductVariant
    ).where(
        ProductVariant.product_id
        == product_id,
        ProductVariant.is_default.is_(True),
    )

    if excluded_variant_id is not None:
        statement = statement.where(
            ProductVariant.id
            != excluded_variant_id
        )

    default_variants = db.scalars(
        statement
    ).all()

    for default_variant in default_variants:
        default_variant.is_default = False


def ensure_product_has_default_variant(
    db: Session,
    product_id: int,
) -> None:
    existing_default = db.scalar(
        select(ProductVariant).where(
            ProductVariant.product_id
            == product_id,
            ProductVariant.is_active.is_(True),
            ProductVariant.is_default.is_(True),
        )
    )

    if existing_default:
        return

    next_variant = db.scalar(
        select(ProductVariant)
        .where(
            ProductVariant.product_id
            == product_id,
            ProductVariant.is_active.is_(True),
        )
        .order_by(
            ProductVariant.display_order,
            ProductVariant.id,
        )
        .limit(1)
    )

    if next_variant:
        next_variant.is_default = True


def create_product_variant(
    db: Session,
    product_id: int,
    variant_data: ProductVariantCreate,
) -> ProductVariant:
    product = get_variant_product(
        db=db,
        product_id=product_id,
    )

    normalized_sku = validate_variant_sku(
        db=db,
        sku=variant_data.sku,
    )

    normalized_barcode = (
        validate_variant_barcode(
            db=db,
            barcode=variant_data.barcode,
        )
    )

    validate_variant_price_adjustment(
        db=db,
        product=product,
        price_adjustment=(
            variant_data.price_adjustment
        ),
    )

    try:
        active_variants = list(
            db.scalars(
                select(ProductVariant).where(
                    ProductVariant.product_id == product_id,
                    ProductVariant.is_active.is_(True),
                )
            ).all()
        )

        # If this is the FIRST variant being added to a product that currently has 0 active variants:
        # Automatically create the base variant representing the original product!
        if len(active_variants) == 0:
            base_name = determine_base_variant_name(product)
            base_sku = determine_base_variant_sku(db=db, product=product)

            base_variant = ProductVariant(
                product_id=product_id,
                name=base_name,
                sku=base_sku,
                barcode=None,
                attributes={},
                price_adjustment=Decimal("0.00"),
                display_order=0,
                is_default=not variant_data.is_default,  # Base is default if new variant is not default
                is_active=True,
            )
            db.add(base_variant)
            db.flush()

        # If the new variant is marked default, clear existing default
        if variant_data.is_default:
            clear_existing_default_variant(
                db=db,
                product_id=product_id,
            )

        existing_count = len(active_variants)
        order = variant_data.display_order if variant_data.display_order > 0 else (existing_count + (1 if len(active_variants) == 0 else 0))

        variant = ProductVariant(
            product_id=product_id,
            name=variant_data.name.strip(),
            sku=normalized_sku,
            barcode=normalized_barcode,
            attributes=variant_data.attributes,
            price_adjustment=variant_data.price_adjustment,
            display_order=order,
            is_default=variant_data.is_default if len(active_variants) > 0 else (variant_data.is_default or False),
            is_active=variant_data.is_active,
        )

        db.add(variant)
        db.flush()

        # Always guarantee a default exists after creation. This handles the
        # edge case where a new variant is added with is_default=False but
        # is_active=False — in that case no variant will be default and we
        # must promote the next eligible one.
        ensure_product_has_default_variant(
            db=db,
            product_id=product_id,
        )

        db.commit()

        return get_product_variant_by_id(
            db=db,
            variant_id=variant.id,
        )

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Variant SKU, barcode or default "
                "selection conflicts with existing data."
            ),
        )

    except Exception:
        db.rollback()
        raise


def update_product_variant(
    db: Session,
    variant_id: int,
    variant_data: ProductVariantUpdate,
) -> ProductVariant:
    variant = get_product_variant_by_id(
        db=db,
        variant_id=variant_id,
    )

    product = get_variant_product(
        db=db,
        product_id=variant.product_id,
    )

    update_data = variant_data.model_dump(
        exclude_unset=True
    )

    try:
        if (
            "name" in update_data
            and update_data["name"] is not None
        ):
            variant.name = (
                update_data["name"].strip()
            )

        if (
            "sku" in update_data
            and update_data["sku"] is not None
        ):
            variant.sku = validate_variant_sku(
                db=db,
                sku=update_data["sku"],
                current_variant_id=variant.id,
            )

        if "barcode" in update_data:
            variant.barcode = (
                validate_variant_barcode(
                    db=db,
                    barcode=update_data["barcode"],
                    current_variant_id=variant.id,
                )
            )

        if (
            "attributes" in update_data
            and update_data["attributes"]
            is not None
        ):
            variant.attributes = update_data[
                "attributes"
            ]

        if (
            "price_adjustment" in update_data
            and update_data["price_adjustment"]
            is not None
        ):
            validate_variant_price_adjustment(
                db=db,
                product=product,
                price_adjustment=update_data[
                    "price_adjustment"
                ],
            )

            variant.price_adjustment = (
                update_data["price_adjustment"]
            )

        if (
            "display_order" in update_data
            and update_data["display_order"]
            is not None
        ):
            variant.display_order = update_data[
                "display_order"
            ]

        if (
            update_data.get("is_default")
            is True
        ):
            clear_existing_default_variant(
                db=db,
                product_id=variant.product_id,
                excluded_variant_id=variant.id,
            )

            variant.is_default = True

        if (
            "is_default" in update_data
            and update_data["is_default"]
            is False
        ):
            variant.is_default = False

        if (
            "is_active" in update_data
            and update_data["is_active"]
            is not None
        ):
            variant.is_active = update_data[
                "is_active"
            ]

            if not variant.is_active:
                variant.is_default = False

        db.flush()

        ensure_product_has_default_variant(
            db=db,
            product_id=variant.product_id,
        )

        db.commit()

        return get_product_variant_by_id(
            db=db,
            variant_id=variant.id,
        )

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Variant update conflicts with "
                "existing SKU, barcode or default variant."
            ),
        )

    except Exception:
        db.rollback()
        raise


def deactivate_product_variant(
    db: Session,
    variant_id: int,
) -> ProductVariant:
    variant = get_product_variant_by_id(
        db=db,
        variant_id=variant_id,
    )

    try:
        variant.is_active = False
        variant.is_default = False

        db.flush()

        ensure_product_has_default_variant(
            db=db,
            product_id=variant.product_id,
        )

        db.commit()

        return get_product_variant_by_id(
            db=db,
            variant_id=variant.id,
        )

    except Exception:
        db.rollback()
        raise


def activate_product_variant(
    db: Session,
    variant_id: int,
) -> ProductVariant:
    variant = get_product_variant_by_id(
        db=db,
        variant_id=variant_id,
    )

    try:
        variant.is_active = True

        db.flush()

        ensure_product_has_default_variant(
            db=db,
            product_id=variant.product_id,
        )

        db.commit()

        return get_product_variant_by_id(
            db=db,
            variant_id=variant.id,
        )

    except Exception:
        db.rollback()
        raise


def delete_product_variant(
    db: Session,
    variant_id: int,
) -> dict[str, Any]:
    variant = get_product_variant_by_id(
        db=db,
        variant_id=variant_id,
    )

    product_id = variant.product_id
    was_default = variant.is_default

    try:
        db.delete(variant)
        db.flush()

        if was_default:
            ensure_product_has_default_variant(
                db=db,
                product_id=product_id,
            )

        db.commit()

        return {
            "message": "Product variant permanently deleted.",
            "variant_id": variant_id,
            "product_id": product_id,
        }

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete this variant because it is referenced by existing orders. You can disable it instead.",
        )

    except Exception:
        db.rollback()
        raise