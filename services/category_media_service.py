from fastapi import (
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from models import Category
from schemas import CategoryDisplayModeUpdate
from services.media_service import (
    delete_media_file,
    save_uploaded_image,
)


def get_category_media_record(
    db: Session,
    category_id: int,
) -> Category:
    category = db.get(
        Category,
        category_id,
    )

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found.",
        )

    return category


async def upload_category_icon(
    db: Session,
    category_id: int,
    uploaded_file: UploadFile,
) -> Category:
    category = get_category_media_record(
        db=db,
        category_id=category_id,
    )

    old_image_url = category.image_url

    new_image_url = await save_uploaded_image(
        uploaded_file=uploaded_file,
        folder_name="category-icons",
    )

    try:
        category.image_url = new_image_url

        db.commit()
        db.refresh(category)

    except Exception:
        db.rollback()
        delete_media_file(new_image_url)
        raise

    delete_media_file(old_image_url)

    return category


def remove_category_icon(
    db: Session,
    category_id: int,
) -> Category:
    category = get_category_media_record(
        db=db,
        category_id=category_id,
    )

    old_image_url = category.image_url

    try:
        category.image_url = None

        db.commit()
        db.refresh(category)

    except Exception:
        db.rollback()
        raise

    delete_media_file(old_image_url)

    return category


async def upload_category_banner(
    db: Session,
    category_id: int,
    uploaded_file: UploadFile,
) -> Category:
    category = get_category_media_record(
        db=db,
        category_id=category_id,
    )

    old_banner_url = category.banner_image_url

    new_banner_url = await save_uploaded_image(
        uploaded_file=uploaded_file,
        folder_name="category-banners",
    )

    try:
        category.banner_image_url = new_banner_url

        db.commit()
        db.refresh(category)

    except Exception:
        db.rollback()
        delete_media_file(new_banner_url)
        raise

    delete_media_file(old_banner_url)

    return category


def remove_category_banner(
    db: Session,
    category_id: int,
) -> Category:
    category = get_category_media_record(
        db=db,
        category_id=category_id,
    )

    old_banner_url = category.banner_image_url

    try:
        category.banner_image_url = None

        if (
            category.display_mode
            == "custom_image_banner"
        ):
            category.display_mode = (
                "default_heading"
            )

        db.commit()
        db.refresh(category)

    except Exception:
        db.rollback()
        raise

    delete_media_file(old_banner_url)

    return category


def update_category_display_mode(
    db: Session,
    category_id: int,
    mode_data: CategoryDisplayModeUpdate,
) -> Category:
    category = get_category_media_record(
        db=db,
        category_id=category_id,
    )

    if (
        mode_data.display_mode
        == "custom_image_banner"
        and not category.banner_image_url
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Upload a category banner before selecting "
                "custom_image_banner mode."
            ),
        )

    try:
        category.display_mode = (
            mode_data.display_mode
        )

        db.commit()
        db.refresh(category)

        return category

    except Exception:
        db.rollback()
        raise