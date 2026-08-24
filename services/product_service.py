import re
import unicodedata
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Category, Product
from schemas import ProductCreate, ProductUpdate
from services.excel_price_service import clean_product_name


def generate_product_slug(value: str) -> str:
    normalized_value = unicodedata.normalize("NFKD", value)

    ascii_value = normalized_value.encode(
        "ascii",
        "ignore",
    ).decode("ascii")

    slug = ascii_value.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")

    return slug or "product"


def generate_unique_product_slug(
    db: Session,
    name: str,
    exclude_product_id: int | None = None,
) -> str:
    base_slug = generate_product_slug(name)
    slug = base_slug
    counter = 2

    while True:
        statement = select(Product.id).where(
            Product.slug == slug
        )

        if exclude_product_id is not None:
            statement = statement.where(
                Product.id != exclude_product_id
            )

        existing_product_id = db.scalar(statement)

        if existing_product_id is None:
            return slug

        slug = f"{base_slug}-{counter}"
        counter += 1


def bulk_generate_product_slugs(
    names: list[str],
    existing_slugs: set[str],
) -> list[str]:
    """
    Generates unique product slugs in memory for large batches (55k+ items)
    in milliseconds without issuing individual database queries.
    """
    generated_slugs: list[str] = []

    for name in names:
        base_slug = generate_product_slug(name)
        candidate = base_slug
        counter = 2

        while candidate in existing_slugs:
            candidate = f"{base_slug}-{counter}"
            counter += 1

        existing_slugs.add(candidate)
        generated_slugs.append(candidate)

    return generated_slugs


def get_category_or_404(
    db: Session,
    category_id: int,
) -> Category:
    category = db.get(Category, category_id)

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found.",
        )

    return category


def get_all_products(
    db: Session,
    search: str | None = None,
    category_id: int | None = None,
    active_only: bool = False,
    skip: int = 0,
    limit: int = 20,
) -> dict[str, Any]:
    filters = []

    if search:
        normalized_search = search.strip()
        search_pattern = f"%{normalized_search}%"

        filters.append(
            or_(
                Product.barcode.ilike(search_pattern),
                Product.name.ilike(search_pattern),
            )
        )

    if category_id is not None:
        filters.append(Product.category_id == category_id)

    if active_only:
        filters.append(Product.is_active.is_(True))

    products_statement = select(Product)

    count_statement = select(
        func.count(Product.id)
    )

    if filters:
        products_statement = products_statement.where(*filters)
        count_statement = count_statement.where(*filters)

    products_statement = (
        products_statement
        .order_by(Product.name)
        .offset(skip)
        .limit(limit)
    )

    products = list(
        db.scalars(products_statement).all()
    )

    total = db.scalar(count_statement) or 0

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": products,
    }


def get_product_by_id(
    db: Session,
    product_id: int,
) -> Product:
    product = db.get(Product, product_id)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )

    return product


def get_product_by_barcode(
    db: Session,
    barcode: str,
) -> Product:
    normalized_barcode = barcode.strip()

    product = db.scalar(
        select(Product).where(
            Product.barcode == normalized_barcode
        )
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found for this barcode.",
        )

    return product


def create_product(
    db: Session,
    product_data: ProductCreate,
) -> Product:
    normalized_barcode = product_data.barcode.strip()
    normalized_name = clean_product_name(product_data.name)

    existing_product = db.scalar(
        select(Product).where(
            Product.barcode == normalized_barcode
        )
    )

    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with this barcode already exists.",
        )

    get_category_or_404(
        db=db,
        category_id=product_data.category_id,
    )

    product = Product(
        barcode=normalized_barcode,
        name=normalized_name,
        slug=generate_unique_product_slug(
            db=db,
            name=normalized_name,
        ),
        description=product_data.description,
        unit_size=product_data.unit_size,
        master_price=product_data.master_price,
        image_url=product_data.image_url,
        category_id=product_data.category_id,
        is_active=product_data.is_active,
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


def update_product(
    db: Session,
    product_id: int,
    product_data: ProductUpdate,
) -> Product:
    product = get_product_by_id(
        db=db,
        product_id=product_id,
    )

    update_data = product_data.model_dump(
        exclude_unset=True
    )

    if (
        "barcode" in update_data
        and update_data["barcode"] is not None
    ):
        normalized_barcode = update_data["barcode"].strip()

        duplicate_product = db.scalar(
            select(Product).where(
                Product.barcode == normalized_barcode,
                Product.id != product_id,
            )
        )

        if duplicate_product:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A product with this barcode already exists.",
            )

        product.barcode = normalized_barcode

    if (
        "name" in update_data
        and update_data["name"] is not None
    ):
        normalized_name = " ".join(update_data["name"].strip().split())

        product.name = normalized_name
        product.slug = generate_unique_product_slug(
            db=db,
            name=normalized_name,
            exclude_product_id=product_id,
        )

    if (
        "category_id" in update_data
        and update_data["category_id"] is not None
    ):
        get_category_or_404(
            db=db,
            category_id=update_data["category_id"],
        )

        product.category_id = update_data["category_id"]

    nullable_fields = [
        "description",
        "unit_size",
        "image_url",
    ]

    for field_name in nullable_fields:
        if field_name in update_data:
            setattr(
                product,
                field_name,
                update_data[field_name],
            )

    if (
        "master_price" in update_data
        and update_data["master_price"] is not None
    ):
        product.master_price = update_data["master_price"]

    if (
        "is_active" in update_data
        and update_data["is_active"] is not None
    ):
        product.is_active = update_data["is_active"]

    db.commit()
    db.refresh(product)

    return product


def activate_product(
    db: Session,
    product_id: int,
) -> Product:
    product = get_product_by_id(
        db=db,
        product_id=product_id,
    )

    product.is_active = True

    db.commit()
    db.refresh(product)

    return product


def deactivate_product(
    db: Session,
    product_id: int,
) -> Product:
    product = get_product_by_id(
        db=db,
        product_id=product_id,
    )

    product.is_active = False

    db.commit()
    db.refresh(product)

    return product


def delete_product(
    db: Session,
    product_id: int,
) -> dict[str, Any]:
    from models import (
        BranchPriceOverride,
        DiscountPrice,
        OrderItem,
        PriceImportRow,
        ProductAvailability,
        ProductImage,
        ProductVariant,
        VariantAvailability,
    )
    from sqlalchemy import delete, update

    product = get_product_by_id(
        db=db,
        product_id=product_id,
    )

    try:
        # Nullify foreign keys in historical order items and price import rows
        db.execute(
            update(OrderItem)
            .where(OrderItem.product_id == product_id)
            .values(product_id=None, variant_id=None)
        )
        db.execute(
            update(PriceImportRow)
            .where(PriceImportRow.product_id == product_id)
            .values(product_id=None)
        )

        # Delete dependent tables
        var_ids = list(db.scalars(select(ProductVariant.id).where(ProductVariant.product_id == product_id)).all())
        if var_ids:
            db.execute(delete(VariantAvailability).where(VariantAvailability.variant_id.in_(var_ids)))
        db.execute(delete(BranchPriceOverride).where(BranchPriceOverride.product_id == product_id))
        db.execute(delete(ProductAvailability).where(ProductAvailability.product_id == product_id))
        db.execute(delete(DiscountPrice).where(DiscountPrice.product_id == product_id))
        db.execute(delete(ProductImage).where(ProductImage.product_id == product_id))
        db.execute(delete(ProductVariant).where(ProductVariant.product_id == product_id))

        db.delete(product)
        db.commit()

        return {
            "message": "Product permanently deleted.",
            "product_id": product_id,
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


def delete_all_products(db: Session) -> dict[str, Any]:
    """
    Permanently deletes all products from the store catalog,
    cleaning up price overrides, availability records, variants,
    images, and discount prices while preserving orders by setting
    order items' product reference to NULL.
    """
    from models import (
        BranchPriceOverride,
        DiscountPrice,
        OrderItem,
        PriceImportRow,
        ProductAvailability,
        ProductImage,
        ProductVariant,
        VariantAvailability,
    )
    from sqlalchemy import delete, update

    try:
        total_products = db.scalar(select(func.count(Product.id))) or 0
        if total_products == 0:
            return {
                "message": "Catalog is already empty.",
                "deleted_count": 0,
            }

        # Nullify foreign keys in historical order items and price import rows
        db.execute(
            update(OrderItem)
            .where(OrderItem.product_id.is_not(None))
            .values(product_id=None, variant_id=None)
        )
        db.execute(
            update(PriceImportRow)
            .where(PriceImportRow.product_id.is_not(None))
            .values(product_id=None)
        )

        # Delete dependent tables
        db.execute(delete(VariantAvailability))
        db.execute(delete(BranchPriceOverride))
        db.execute(delete(ProductAvailability))
        db.execute(delete(DiscountPrice))
        db.execute(delete(ProductImage))
        db.execute(delete(ProductVariant))

        # Delete all products
        db.execute(delete(Product))
        db.commit()

        return {
            "message": f"Successfully deleted all {total_products} products from the catalog.",
            "deleted_count": total_products,
        }
    except Exception:
        db.rollback()
        raise


def bulk_delete_products(
    db: Session,
    product_ids: list[int] | None = None,
    select_all: bool = False,
    search: str | None = None,
    category_id: int | None = None,
) -> dict[str, Any]:
    from models import (
        BranchPriceOverride,
        DiscountPrice,
        OrderItem,
        PriceImportRow,
        ProductAvailability,
        ProductImage,
        ProductVariant,
        VariantAvailability,
    )
    from sqlalchemy import delete, update

    try:
        target_ids: list[int] = []
        if select_all:
            query = select(Product.id)
            filters = []
            if search:
                s_pat = f"%{search.strip()}%"
                filters.append(or_(Product.barcode.ilike(s_pat), Product.name.ilike(s_pat)))
            if category_id is not None:
                filters.append(Product.category_id == category_id)
            if filters:
                query = query.where(*filters)
            target_ids = list(db.scalars(query).all())
        elif product_ids:
            target_ids = list(dict.fromkeys(product_ids))

        if not target_ids:
            return {"deleted_count": 0, "message": "No products selected for deletion."}

        CHUNK = 1000
        for i in range(0, len(target_ids), CHUNK):
            chunk = target_ids[i : i + CHUNK]
            db.execute(
                update(OrderItem)
                .where(OrderItem.product_id.in_(chunk))
                .values(product_id=None, variant_id=None)
            )
            db.execute(
                update(PriceImportRow)
                .where(PriceImportRow.product_id.in_(chunk))
                .values(product_id=None)
            )
            var_ids = list(db.scalars(select(ProductVariant.id).where(ProductVariant.product_id.in_(chunk))).all())
            if var_ids:
                db.execute(delete(VariantAvailability).where(VariantAvailability.variant_id.in_(var_ids)))
            db.execute(delete(BranchPriceOverride).where(BranchPriceOverride.product_id.in_(chunk)))
            db.execute(delete(ProductAvailability).where(ProductAvailability.product_id.in_(chunk)))
            db.execute(delete(DiscountPrice).where(DiscountPrice.product_id.in_(chunk)))
            db.execute(delete(ProductImage).where(ProductImage.product_id.in_(chunk)))
            db.execute(delete(ProductVariant).where(ProductVariant.product_id.in_(chunk)))
            db.execute(delete(Product).where(Product.id.in_(chunk)))
            db.flush()

        db.commit()
        return {
            "deleted_count": len(target_ids),
            "message": f"Successfully deleted {len(target_ids)} product(s).",
        }
    except Exception:
        db.rollback()
        raise


def bulk_activate_products(
    db: Session,
    product_ids: list[int] | None = None,
    select_all: bool = False,
    search: str | None = None,
    category_id: int | None = None,
) -> dict[str, Any]:
    from sqlalchemy import update

    try:
        filters = []
        if select_all:
            if search:
                s_pat = f"%{search.strip()}%"
                filters.append(or_(Product.barcode.ilike(s_pat), Product.name.ilike(s_pat)))
            if category_id is not None:
                filters.append(Product.category_id == category_id)
        elif product_ids:
            filters.append(Product.id.in_(list(dict.fromkeys(product_ids))))
        else:
            return {"activated_count": 0, "message": "No products selected."}

        stmt = update(Product).where(*filters, Product.is_active.is_(False)).values(is_active=True)
        res = db.execute(stmt)
        db.commit()
        count = res.rowcount if hasattr(res, "rowcount") and res.rowcount >= 0 else len(product_ids or [])
        return {
            "activated_count": count,
            "message": f"Successfully enabled {count} product(s).",
        }
    except Exception:
        db.rollback()
        raise


def bulk_deactivate_products(
    db: Session,
    product_ids: list[int] | None = None,
    select_all: bool = False,
    search: str | None = None,
    category_id: int | None = None,
) -> dict[str, Any]:
    from sqlalchemy import update

    try:
        filters = []
        if select_all:
            if search:
                s_pat = f"%{search.strip()}%"
                filters.append(or_(Product.barcode.ilike(s_pat), Product.name.ilike(s_pat)))
            if category_id is not None:
                filters.append(Product.category_id == category_id)
        elif product_ids:
            filters.append(Product.id.in_(list(dict.fromkeys(product_ids))))
        else:
            return {"requested_count": 0, "deactivated_count": 0, "product_ids": []}

        stmt = update(Product).where(*filters, Product.is_active.is_(True)).values(is_active=False)
        res = db.execute(stmt)
        db.commit()
        count = res.rowcount if hasattr(res, "rowcount") and res.rowcount >= 0 else len(product_ids or [])
        return {
            "requested_count": len(product_ids) if product_ids else count,
            "deactivated_count": count,
            "product_ids": product_ids or [],
        }
    except Exception:
        db.rollback()
        raise


def sanitize_existing_product_names(db: Session) -> dict[str, Any]:
    """
    Sanitizes existing product names in the database by stripping leading numerical digits
    and regenerating slugs where appropriate.
    """
    products = list(db.scalars(select(Product)).all())
    cleaned_count = 0

    for p in products:
        cleaned = clean_product_name(p.name)
        if cleaned != p.name:
            p.name = cleaned
            cleaned_count += 1

    if cleaned_count > 0:
        db.commit()

    return {
        "total_products": len(products),
        "cleaned_count": cleaned_count,
        "message": f"Sanitized {cleaned_count} product names.",
    }


def bulk_move_products_category(
    db: Session,
    target_category_id: int,
    product_ids: list[int] | None = None,
    select_all: bool = False,
    search: str | None = None,
    category_id: int | None = None,
) -> dict[str, Any]:
    from sqlalchemy import update

    target_category = get_category_or_404(db=db, category_id=target_category_id)
    if not target_category.is_active or target_category.slug == "deals":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select an active normal product category.",
        )

    try:
        filters = []
        if select_all:
            if search:
                s_pat = f"%{search.strip()}%"
                filters.append(or_(Product.barcode.ilike(s_pat), Product.name.ilike(s_pat)))
            if category_id is not None:
                filters.append(Product.category_id == category_id)
        elif product_ids:
            filters.append(Product.id.in_(list(dict.fromkeys(product_ids))))
        else:
            return {"moved_count": 0, "message": "No products selected."}

        stmt = update(Product).where(*filters).values(category_id=target_category_id)
        res = db.execute(stmt)
        db.commit()
        count = res.rowcount if hasattr(res, "rowcount") and res.rowcount >= 0 else len(product_ids or [])
        return {
            "moved_count": count,
            "target_category_id": target_category.id,
            "target_category_name": target_category.name,
            "message": f"Successfully moved {count} product(s) to category '{target_category.name}'.",
        }
    except Exception:
        db.rollback()
        raise

