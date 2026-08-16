import re
import unicodedata

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import Category
from schemas import CategoryCreate, CategoryUpdate


def generate_slug(value: str) -> str:
    normalized_value = unicodedata.normalize("NFKD", value)

    ascii_value = normalized_value.encode(
        "ascii",
        "ignore",
    ).decode("ascii")

    slug = ascii_value.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")

    return slug or "category"


def generate_unique_slug(
    db: Session,
    name: str,
    exclude_category_id: int | None = None,
) -> str:
    base_slug = generate_slug(name)
    slug = base_slug
    counter = 2

    while True:
        statement = select(Category.id).where(
            Category.slug == slug
        )

        if exclude_category_id is not None:
            statement = statement.where(
                Category.id != exclude_category_id
            )

        existing_category_id = db.scalar(statement)

        if existing_category_id is None:
            return slug

        slug = f"{base_slug}-{counter}"
        counter += 1


def get_all_categories(
    db: Session,
    active_only: bool = False,
) -> list[Category]:
    statement = select(Category).order_by(
        Category.display_order,
        Category.name,
    )

    if active_only:
        statement = statement.where(
            Category.is_active.is_(True)
        )

    return list(db.scalars(statement).all())


def get_category_by_id(
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


def create_category(
    db: Session,
    category_data: CategoryCreate,
) -> Category:
    normalized_name = category_data.name.strip()

    existing_category = db.scalar(
        select(Category).where(
            func.lower(Category.name) == normalized_name.lower()
        )
    )

    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with this name already exists.",
        )

    category = Category(
        name=normalized_name,
        slug=generate_unique_slug(
            db=db,
            name=normalized_name,
        ),
        description=category_data.description,
        image_url=category_data.image_url,
        display_order=category_data.display_order,
        is_active=category_data.is_active,
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    return category


def update_category(
    db: Session,
    category_id: int,
    category_data: CategoryUpdate,
) -> Category:
    category = get_category_by_id(
        db=db,
        category_id=category_id,
    )

    update_data = category_data.model_dump(
        exclude_unset=True
    )

    if "name" in update_data and update_data["name"] is not None:
        normalized_name = update_data["name"].strip()

        duplicate_category = db.scalar(
            select(Category).where(
                func.lower(Category.name)
                == normalized_name.lower(),
                Category.id != category_id,
            )
        )

        if duplicate_category:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A category with this name already exists.",
            )

        category.name = normalized_name
        category.slug = generate_unique_slug(
            db=db,
            name=normalized_name,
            exclude_category_id=category_id,
        )

    if "description" in update_data:
        category.description = update_data["description"]

    if "image_url" in update_data:
        category.image_url = update_data["image_url"]

    if (
        "display_order" in update_data
        and update_data["display_order"] is not None
    ):
        category.display_order = update_data["display_order"]

    if (
        "is_active" in update_data
        and update_data["is_active"] is not None
    ):
        category.is_active = update_data["is_active"]

    db.commit()
    db.refresh(category)

    return category


def deactivate_category(
    db: Session,
    category_id: int,
) -> Category:
    category = get_category_by_id(
        db=db,
        category_id=category_id,
    )

    category.is_active = False

    db.commit()
    db.refresh(category)

    return category