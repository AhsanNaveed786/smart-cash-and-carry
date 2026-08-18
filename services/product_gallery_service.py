from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Product, ProductImage, ProductVariant
from schemas import ProductImageUpdate
from services.media_service import delete_media_file, save_uploaded_image
from services.variant_service import (
    get_product_variant_by_id,
    get_variant_product,
)


async def save_gallery_image_file(
    image_file: UploadFile,
) -> str:
    return await save_uploaded_image(
        uploaded_file=image_file,
        folder_name="products",
    )


def get_gallery_image_by_id(
    db: Session,
    image_id: int,
) -> ProductImage:
    product_image = db.get(ProductImage, image_id)

    if not product_image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product image not found.",
        )

    return product_image


def get_product_gallery(
    db: Session,
    product_id: int,
) -> list[ProductImage]:
    get_variant_product(db=db, product_id=product_id)

    return list(
        db.scalars(
            select(ProductImage)
            .where(ProductImage.product_id == product_id)
            .order_by(ProductImage.display_order, ProductImage.id)
        ).all()
    )


def validate_gallery_variant(
    db: Session,
    product_id: int,
    variant_id: int | None,
) -> ProductVariant | None:
    if variant_id is None:
        return None

    variant = get_product_variant_by_id(db=db, variant_id=variant_id)

    if variant.product_id != product_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected variant does not belong to this product.",
        )

    if not variant.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image cannot be assigned to an inactive variant.",
        )

    return variant


def normalize_alt_text(alt_text: str | None) -> str | None:
    normalized_text = alt_text.strip() if alt_text else None

    if normalized_text and len(normalized_text) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="alt_text cannot exceed 255 characters.",
        )

    return normalized_text


def clear_primary_gallery_images(
    db: Session,
    product_id: int,
    excluded_image_id: int | None = None,
) -> None:
    statement = select(ProductImage).where(
        ProductImage.product_id == product_id,
        ProductImage.is_primary.is_(True),
    )

    if excluded_image_id is not None:
        statement = statement.where(ProductImage.id != excluded_image_id)

    for primary_image in db.scalars(statement).all():
        primary_image.is_primary = False


def update_product_primary_url(
    db: Session,
    product_id: int,
    image_url: str | None,
) -> None:
    product = db.get(Product, product_id)
    if product:
        product.image_url = image_url


def select_next_primary_gallery_image(
    db: Session,
    product_id: int,
    excluded_image_id: int | None = None,
) -> ProductImage | None:
    statement = (
        select(ProductImage)
        .where(ProductImage.product_id == product_id)
        .order_by(ProductImage.display_order, ProductImage.id)
        .limit(1)
    )

    if excluded_image_id is not None:
        statement = statement.where(ProductImage.id != excluded_image_id)

    next_image = db.scalar(statement)

    if next_image:
        next_image.is_primary = True
        update_product_primary_url(
            db=db,
            product_id=product_id,
            image_url=next_image.image_url,
        )
    else:
        update_product_primary_url(
            db=db,
            product_id=product_id,
            image_url=None,
        )

    return next_image


async def add_product_gallery_image(
    db: Session,
    product_id: int,
    image_file: UploadFile,
    variant_id: int | None = None,
    alt_text: str | None = None,
    display_order: int = 0,
    is_primary: bool = False,
) -> ProductImage:
    product = get_variant_product(db=db, product_id=product_id)
    validate_gallery_variant(
        db=db,
        product_id=product_id,
        variant_id=variant_id,
    )

    if display_order < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="display_order cannot be negative.",
        )

    normalized_alt_text = normalize_alt_text(alt_text)
    image_count = db.scalar(
        select(func.count(ProductImage.id)).where(
            ProductImage.product_id == product_id
        )
    )
    should_be_primary = is_primary or image_count == 0
    legacy_image_url = product.image_url if image_count == 0 else None
    new_image_url = await save_gallery_image_file(image_file)

    try:
        if should_be_primary:
            clear_primary_gallery_images(db=db, product_id=product_id)
            db.flush()

        product_image = ProductImage(
            product_id=product_id,
            variant_id=variant_id,
            image_url=new_image_url,
            alt_text=normalized_alt_text,
            display_order=display_order,
            is_primary=should_be_primary,
        )
        db.add(product_image)
        db.flush()

        if should_be_primary:
            update_product_primary_url(
                db=db,
                product_id=product_id,
                image_url=new_image_url,
            )

        db.commit()
        db.refresh(product_image)
    except IntegrityError:
        db.rollback()
        delete_media_file(new_image_url)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product image conflicts with existing gallery data.",
        )
    except Exception:
        db.rollback()
        delete_media_file(new_image_url)
        raise

    if legacy_image_url and legacy_image_url != new_image_url:
        delete_media_file(legacy_image_url)

    return product_image


def update_product_gallery_image(
    db: Session,
    image_id: int,
    image_data: ProductImageUpdate,
) -> ProductImage:
    product_image = get_gallery_image_by_id(db=db, image_id=image_id)
    update_data = image_data.model_dump(exclude_unset=True)

    try:
        if "alt_text" in update_data:
            product_image.alt_text = normalize_alt_text(update_data["alt_text"])

        if update_data.get("display_order") is not None:
            if update_data["display_order"] < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="display_order cannot be negative.",
                )
            product_image.display_order = update_data["display_order"]

        requested_primary = update_data.get("is_primary")

        if requested_primary is True:
            clear_primary_gallery_images(
                db=db,
                product_id=product_image.product_id,
                excluded_image_id=product_image.id,
            )
            db.flush()
            product_image.is_primary = True
            update_product_primary_url(
                db=db,
                product_id=product_image.product_id,
                image_url=product_image.image_url,
            )
        elif requested_primary is False and product_image.is_primary:
            product_image.is_primary = False
            db.flush()
            next_image = select_next_primary_gallery_image(
                db=db,
                product_id=product_image.product_id,
                excluded_image_id=product_image.id,
            )
            if not next_image:
                product_image.is_primary = True
                update_product_primary_url(
                    db=db,
                    product_id=product_image.product_id,
                    image_url=product_image.image_url,
                )

        db.commit()
        db.refresh(product_image)
        return product_image
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Primary image selection conflict.",
        )
    except Exception:
        db.rollback()
        raise


def delete_product_gallery_image(
    db: Session,
    image_id: int,
) -> dict:
    product_image = get_gallery_image_by_id(db=db, image_id=image_id)
    product_id = product_image.product_id
    image_url = product_image.image_url
    was_primary = product_image.is_primary

    try:
        db.delete(product_image)
        db.flush()
        if was_primary:
            select_next_primary_gallery_image(
                db=db,
                product_id=product_id,
                excluded_image_id=image_id,
            )
        db.commit()
    except Exception:
        db.rollback()
        raise

    delete_media_file(image_url)
    return {"message": "Gallery image deleted successfully."}
