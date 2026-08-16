from datetime import datetime, timezone

from fastapi import (
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import (
    HomepageBanner,
    WebsiteSetting,
)
from schemas import (
    HomepageBannerCreate,
    HomepageBannerUpdate,
    WebsiteSettingUpdate,
)
from services.media_service import (
    delete_media_file,
    save_uploaded_image,
)


def get_website_settings(
    db: Session,
) -> WebsiteSetting:
    settings = db.get(
        WebsiteSetting,
        1,
    )

    if settings:
        return settings

    try:
        settings = WebsiteSetting(
            id=1,
            store_name="SMART CASH & CARRY",
            announcement_primary=(
                "Free delivery on orders above Rs. 3,000"
            ),
            announcement_secondary=(
                "Fresh prices - Reliable delivery"
            ),
            announcement_is_active=True,
        )

        db.add(settings)
        db.commit()
        db.refresh(settings)

        return settings

    except Exception:
        db.rollback()
        raise


def update_website_settings(
    db: Session,
    settings_data: WebsiteSettingUpdate,
) -> WebsiteSetting:
    try:
        settings = get_website_settings(db)

        update_data = settings_data.model_dump(
            exclude_unset=True
        )

        if (
            "store_name" in update_data
            and update_data["store_name"] is not None
        ):
            settings.store_name = (
                update_data["store_name"].strip()
            )

        if "announcement_primary" in update_data:
            value = update_data[
                "announcement_primary"
            ]

            settings.announcement_primary = (
                value.strip()
                if value
                else None
            )

        if "announcement_secondary" in update_data:
            value = update_data[
                "announcement_secondary"
            ]

            settings.announcement_secondary = (
                value.strip()
                if value
                else None
            )

        if (
            "announcement_is_active"
            in update_data
            and update_data[
                "announcement_is_active"
            ]
            is not None
        ):
            settings.announcement_is_active = (
                update_data[
                    "announcement_is_active"
                ]
            )

        db.commit()
        db.refresh(settings)

        return settings

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


async def upload_website_logo(
    db: Session,
    uploaded_file: UploadFile,
) -> WebsiteSetting:
    settings = get_website_settings(db)
    old_logo_url = settings.logo_url

    new_logo_url = await save_uploaded_image(
        uploaded_file=uploaded_file,
        folder_name="logos",
    )

    try:
        settings.logo_url = new_logo_url

        db.commit()
        db.refresh(settings)

    except Exception:
        db.rollback()
        delete_media_file(new_logo_url)
        raise

    delete_media_file(old_logo_url)

    return settings


def remove_website_logo(
    db: Session,
) -> WebsiteSetting:
    settings = get_website_settings(db)
    old_logo_url = settings.logo_url

    try:
        settings.logo_url = None

        db.commit()
        db.refresh(settings)

    except Exception:
        db.rollback()
        raise

    delete_media_file(old_logo_url)

    return settings


def get_homepage_banner_by_id(
    db: Session,
    banner_id: int,
) -> HomepageBanner:
    banner = db.get(
        HomepageBanner,
        banner_id,
    )

    if not banner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Homepage banner not found.",
        )

    return banner


def get_homepage_banners(
    db: Session,
    active_now: bool = False,
) -> list[HomepageBanner]:
    statement = select(
        HomepageBanner
    ).order_by(
        HomepageBanner.display_order,
        HomepageBanner.created_at.desc(),
    )

    if active_now:
        current_time = datetime.now(
            timezone.utc
        )

        statement = statement.where(
            HomepageBanner.is_active.is_(True),
            (
                HomepageBanner.start_at.is_(None)
                | (
                    HomepageBanner.start_at
                    <= current_time
                )
            ),
            (
                HomepageBanner.end_at.is_(None)
                | (
                    HomepageBanner.end_at
                    > current_time
                )
            ),
        )

    return list(
        db.scalars(statement).all()
    )


def create_homepage_banner(
    db: Session,
    banner_data: HomepageBannerCreate,
) -> HomepageBanner:
    try:
        banner = HomepageBanner(
            title=banner_data.title.strip(),
            subtitle=(
                banner_data.subtitle.strip()
                if banner_data.subtitle
                else None
            ),
            button_text=(
                banner_data.button_text.strip()
                if banner_data.button_text
                else None
            ),
            button_url=(
                banner_data.button_url.strip()
                if banner_data.button_url
                else None
            ),
            display_order=(
                banner_data.display_order
            ),
            start_at=banner_data.start_at,
            end_at=banner_data.end_at,
            is_active=banner_data.is_active,
        )

        db.add(banner)
        db.commit()
        db.refresh(banner)

        return banner

    except Exception:
        db.rollback()
        raise


def update_homepage_banner(
    db: Session,
    banner_id: int,
    banner_data: HomepageBannerUpdate,
) -> HomepageBanner:
    try:
        banner = get_homepage_banner_by_id(
            db=db,
            banner_id=banner_id,
        )

        update_data = banner_data.model_dump(
            exclude_unset=True
        )

        if (
            "title" in update_data
            and update_data["title"] is not None
        ):
            banner.title = (
                update_data["title"].strip()
            )

        for field_name in (
            "subtitle",
            "button_text",
            "button_url",
        ):
            if field_name in update_data:
                value = update_data[field_name]

                setattr(
                    banner,
                    field_name,
                    value.strip() if value else None,
                )

        if "start_at" in update_data:
            banner.start_at = update_data[
                "start_at"
            ]

        if "end_at" in update_data:
            banner.end_at = update_data[
                "end_at"
            ]

        if (
            banner.start_at is not None
            and banner.end_at is not None
            and banner.end_at <= banner.start_at
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "end_at must be later than start_at."
                ),
            )

        if (
            "display_order" in update_data
            and update_data[
                "display_order"
            ]
            is not None
        ):
            banner.display_order = update_data[
                "display_order"
            ]

        if (
            "is_active" in update_data
            and update_data["is_active"] is not None
        ):
            banner.is_active = update_data[
                "is_active"
            ]

        db.commit()
        db.refresh(banner)

        return banner

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


async def upload_homepage_banner_image(
    db: Session,
    banner_id: int,
    uploaded_file: UploadFile,
) -> HomepageBanner:
    banner = get_homepage_banner_by_id(
        db=db,
        banner_id=banner_id,
    )

    old_image_url = banner.image_url

    new_image_url = await save_uploaded_image(
        uploaded_file=uploaded_file,
        folder_name="banners",
    )

    try:
        banner.image_url = new_image_url

        db.commit()
        db.refresh(banner)

    except Exception:
        db.rollback()
        delete_media_file(new_image_url)
        raise

    delete_media_file(old_image_url)

    return banner


def remove_homepage_banner_image(
    db: Session,
    banner_id: int,
) -> HomepageBanner:
    banner = get_homepage_banner_by_id(
        db=db,
        banner_id=banner_id,
    )

    old_image_url = banner.image_url

    try:
        banner.image_url = None

        db.commit()
        db.refresh(banner)

    except Exception:
        db.rollback()
        raise

    delete_media_file(old_image_url)

    return banner


def delete_homepage_banner(
    db: Session,
    banner_id: int,
) -> dict:
    banner = get_homepage_banner_by_id(
        db=db,
        banner_id=banner_id,
    )

    image_url = banner.image_url

    try:
        db.delete(banner)
        db.commit()

    except Exception:
        db.rollback()
        raise

    delete_media_file(image_url)

    return {
        "message": "Homepage banner deleted successfully."
    }