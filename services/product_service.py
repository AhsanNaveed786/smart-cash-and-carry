import re
import unicodedata
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from models import Category, Product
from schemas import ProductCreate, ProductUpdate


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
    normalized_name = product_data.name.strip()

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
        normalized_name = update_data["name"].strip()

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