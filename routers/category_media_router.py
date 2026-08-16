from fastapi import (
    APIRouter,
    Depends,
    File,
    UploadFile,
)
from sqlalchemy.orm import Session

from database import get_db
from schemas import (
    CategoryDisplayModeUpdate,
    CategoryResponse,
)
from services.category_media_service import (
    remove_category_banner,
    remove_category_icon,
    update_category_display_mode,
    upload_category_banner,
    upload_category_icon,
)


router = APIRouter(
    prefix="/api/categories",
    tags=["Category Images"],
)


@router.post(
    "/{category_id}/icon",
    response_model=CategoryResponse,
)
async def add_category_icon(
    category_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    return await upload_category_icon(
        db=db,
        category_id=category_id,
        uploaded_file=file,
    )


@router.delete(
    "/{category_id}/icon",
    response_model=CategoryResponse,
)
def delete_category_icon(
    category_id: int,
    db: Session = Depends(get_db),
):
    return remove_category_icon(
        db=db,
        category_id=category_id,
    )


@router.post(
    "/{category_id}/banner",
    response_model=CategoryResponse,
)
async def add_category_banner(
    category_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    return await upload_category_banner(
        db=db,
        category_id=category_id,
        uploaded_file=file,
    )


@router.delete(
    "/{category_id}/banner",
    response_model=CategoryResponse,
)
def delete_category_banner(
    category_id: int,
    db: Session = Depends(get_db),
):
    return remove_category_banner(
        db=db,
        category_id=category_id,
    )


@router.patch(
    "/{category_id}/display-mode",
    response_model=CategoryResponse,
)
def change_category_display_mode(
    category_id: int,
    mode_data: CategoryDisplayModeUpdate,
    db: Session = Depends(get_db),
):
    return update_category_display_mode(
        db=db,
        category_id=category_id,
        mode_data=mode_data,
    )