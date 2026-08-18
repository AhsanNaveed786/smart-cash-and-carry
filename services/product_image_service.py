from fastapi import UploadFile
from sqlalchemy.orm import Session

from models import Product
from services.media_service import delete_media_file, save_uploaded_image
from services.product_service import get_product_by_id


async def upload_product_image(
    db: Session,
    product_id: int,
    image_file: UploadFile,
) -> Product:
    product = get_product_by_id(db=db, product_id=product_id)
    old_image_url = product.image_url
    new_image_url = await save_uploaded_image(
        uploaded_file=image_file,
        folder_name="products",
    )

    try:
        product.image_url = new_image_url
        db.commit()
        db.refresh(product)
    except Exception:
        db.rollback()
        delete_media_file(new_image_url)
        raise

    if old_image_url != new_image_url:
        delete_media_file(old_image_url)
    return product


def delete_old_product_image(image_url: str | None) -> None:
    delete_media_file(image_url)
