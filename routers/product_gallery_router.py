from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from database import get_db
from schemas import MessageResponse, ProductImageResponse, ProductImageUpdate
from services.product_gallery_service import (
    add_product_gallery_image,
    delete_product_gallery_image,
    get_gallery_image_by_id,
    get_product_gallery,
    update_product_gallery_image,
)


router = APIRouter(
    prefix="/api/product-gallery",
    tags=["Product Gallery"],
)


@router.get(
    "/product/{product_id}",
    response_model=list[ProductImageResponse],
)
def list_product_gallery(
    product_id: int,
    db: Session = Depends(get_db),
):
    return get_product_gallery(db=db, product_id=product_id)


@router.post(
    "/product/{product_id}",
    response_model=ProductImageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_gallery_image(
    product_id: int,
    file: UploadFile = File(...),
    variant_id: int | None = Form(default=None),
    alt_text: str | None = Form(default=None),
    display_order: int = Form(default=0),
    is_primary: bool = Form(default=False),
    db: Session = Depends(get_db),
):
    return await add_product_gallery_image(
        db=db,
        product_id=product_id,
        image_file=file,
        variant_id=variant_id,
        alt_text=alt_text,
        display_order=display_order,
        is_primary=is_primary,
    )


@router.get(
    "/{image_id}",
    response_model=ProductImageResponse,
)
def view_gallery_image(
    image_id: int,
    db: Session = Depends(get_db),
):
    return get_gallery_image_by_id(db=db, image_id=image_id)


@router.patch(
    "/{image_id}",
    response_model=ProductImageResponse,
)
def edit_gallery_image(
    image_id: int,
    image_data: ProductImageUpdate,
    db: Session = Depends(get_db),
):
    return update_product_gallery_image(
        db=db,
        image_id=image_id,
        image_data=image_data,
    )


@router.delete(
    "/{image_id}",
    response_model=MessageResponse,
)
def remove_gallery_image(
    image_id: int,
    db: Session = Depends(get_db),
):
    return delete_product_gallery_image(db=db, image_id=image_id)
