from fastapi import (
    APIRouter,
    Depends,
    File,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from database import get_db
from schemas import (
    HomepageBannerCreate,
    HomepageBannerResponse,
    HomepageBannerUpdate,
    MessageResponse,
    WebsiteSettingResponse,
    WebsiteSettingUpdate,
)
from services.content_service import (
    create_homepage_banner,
    delete_homepage_banner,
    get_homepage_banner_by_id,
    get_homepage_banners,
    get_website_settings,
    remove_homepage_banner_image,
    remove_website_logo,
    update_homepage_banner,
    update_website_settings,
    upload_homepage_banner_image,
    upload_website_logo,
)


router = APIRouter(
    prefix="/api/content",
    tags=["Website Content"],
)


@router.get(
    "/settings",
    response_model=WebsiteSettingResponse,
)
def view_website_settings(
    db: Session = Depends(get_db),
):
    return get_website_settings(db)


@router.patch(
    "/settings",
    response_model=WebsiteSettingResponse,
)
def edit_website_settings(
    settings_data: WebsiteSettingUpdate,
    db: Session = Depends(get_db),
):
    return update_website_settings(
        db=db,
        settings_data=settings_data,
    )


@router.post(
    "/settings/logo",
    response_model=WebsiteSettingResponse,
)
async def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    return await upload_website_logo(
        db=db,
        uploaded_file=file,
    )


@router.delete(
    "/settings/logo",
    response_model=WebsiteSettingResponse,
)
def delete_logo(
    db: Session = Depends(get_db),
):
    return remove_website_logo(db)


@router.get(
    "/banners",
    response_model=list[HomepageBannerResponse],
)
def list_homepage_banners(
    active_now: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    return get_homepage_banners(
        db=db,
        active_now=active_now,
    )


@router.post(
    "/banners",
    response_model=HomepageBannerResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_homepage_banner(
    banner_data: HomepageBannerCreate,
    db: Session = Depends(get_db),
):
    return create_homepage_banner(
        db=db,
        banner_data=banner_data,
    )


@router.get(
    "/banners/{banner_id}",
    response_model=HomepageBannerResponse,
)
def view_homepage_banner(
    banner_id: int,
    db: Session = Depends(get_db),
):
    return get_homepage_banner_by_id(
        db=db,
        banner_id=banner_id,
    )


@router.patch(
    "/banners/{banner_id}",
    response_model=HomepageBannerResponse,
)
def edit_homepage_banner(
    banner_id: int,
    banner_data: HomepageBannerUpdate,
    db: Session = Depends(get_db),
):
    return update_homepage_banner(
        db=db,
        banner_id=banner_id,
        banner_data=banner_data,
    )


@router.post(
    "/banners/{banner_id}/image",
    response_model=HomepageBannerResponse,
)
async def upload_banner_image(
    banner_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    return await upload_homepage_banner_image(
        db=db,
        banner_id=banner_id,
        uploaded_file=file,
    )


@router.delete(
    "/banners/{banner_id}/image",
    response_model=HomepageBannerResponse,
)
def delete_banner_image(
    banner_id: int,
    db: Session = Depends(get_db),
):
    return remove_homepage_banner_image(
        db=db,
        banner_id=banner_id,
    )


@router.delete(
    "/banners/{banner_id}",
    response_model=MessageResponse,
)
def remove_homepage_banner(
    banner_id: int,
    db: Session = Depends(get_db),
):
    return delete_homepage_banner(
        db=db,
        banner_id=banner_id,
    )