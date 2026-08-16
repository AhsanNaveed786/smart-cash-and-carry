from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from database import get_db
from schemas import ProductResponse
from services.product_image_service import (
    upload_product_image,
)


router = APIRouter(
    prefix="/api/products",
    tags=["Product Images"],
)


@router.post(
    "/{product_id}/image",
    response_model=ProductResponse,
)
async def add_or_replace_product_image(
    product_id: int,
    image_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    return await upload_product_image(
        db=db,
        product_id=product_id,
        image_file=image_file,
    )