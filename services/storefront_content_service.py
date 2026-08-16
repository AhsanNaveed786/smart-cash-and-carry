from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Category
from services.availability_service import (
    get_active_availability_branch,
)
from services.content_service import (
    get_homepage_banners,
    get_website_settings,
)


def get_storefront_content(
    db: Session,
    branch_id: int,
) -> dict:
    get_active_availability_branch(
        db=db,
        branch_id=branch_id,
    )

    settings = get_website_settings(db)

    banners = [
        banner
        for banner in get_homepage_banners(
            db=db,
            active_now=True,
        )
        if banner.image_url
    ]

    categories = list(
        db.scalars(
            select(Category)
            .where(
                Category.is_active.is_(True)
            )
            .order_by(
                Category.display_order,
                Category.name,
            )
        ).all()
    )

    return {
        "branch_id": branch_id,
        "settings": settings,
        "banners": banners,
        "categories": categories,
    }