import warnings
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.orm import Session

from models import Product
from services.product_service import get_product_by_id


BASE_DIR = Path(__file__).resolve().parent.parent

PRODUCT_IMAGE_DIRECTORY = (
    BASE_DIR / "uploads" / "products"
)

PRODUCT_IMAGE_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)


ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

ALLOWED_IMAGE_FORMATS = {
    "JPEG",
    "PNG",
    "WEBP",
}

MAXIMUM_FILE_SIZE = 5 * 1024 * 1024
MAXIMUM_IMAGE_WIDTH = 8000
MAXIMUM_IMAGE_HEIGHT = 8000

Image.MAX_IMAGE_PIXELS = 25_000_000


def optimize_image(image_content: bytes) -> bytes:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter(
                "error",
                Image.DecompressionBombWarning,
            )

            with Image.open(
                BytesIO(image_content)
            ) as validation_image:
                detected_format = validation_image.format

                if detected_format not in ALLOWED_IMAGE_FORMATS:
                    raise ValueError("Unsupported image format.")

                validation_image.verify()

            with Image.open(BytesIO(image_content)) as source_image:
                source_image = ImageOps.exif_transpose(source_image)

                width, height = source_image.size

                if (
                    width > MAXIMUM_IMAGE_WIDTH
                    or height > MAXIMUM_IMAGE_HEIGHT
                ):
                    raise ValueError("Image dimensions are too large.")

                source_image.thumbnail(
                    (1600, 1600),
                    Image.Resampling.LANCZOS,
                )

                if (
                    source_image.mode in {"RGBA", "LA"}
                    or "transparency" in source_image.info
                ):
                    processed_image = source_image.convert("RGBA")
                else:
                    processed_image = source_image.convert("RGB")

                output = BytesIO()

                processed_image.save(
                    output,
                    format="WEBP",
                    quality=85,
                    method=6,
                )

                return output.getvalue()

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is not a valid supported image.",
        ) from error


def delete_old_product_image(
    image_url: str | None,
) -> None:
    if not image_url:
        return

    expected_prefix = "/uploads/products/"

    if not image_url.startswith(expected_prefix):
        return

    filename = Path(image_url).name

    if not filename:
        return

    image_path = (
        PRODUCT_IMAGE_DIRECTORY / filename
    ).resolve()

    expected_directory = PRODUCT_IMAGE_DIRECTORY.resolve()

    if image_path.parent != expected_directory:
        return

    try:
        image_path.unlink(missing_ok=True)
    except OSError:
        pass


async def upload_product_image(
    db: Session,
    product_id: int,
    image_file: UploadFile,
) -> Product:
    new_image_path: Path | None = None

    try:
        product = get_product_by_id(
            db=db,
            product_id=product_id,
        )

        if image_file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Only JPEG, PNG and WebP images are allowed.",
            )

        image_content = await image_file.read(
            MAXIMUM_FILE_SIZE + 1
        )

        if not image_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded image is empty.",
            )

        if len(image_content) > MAXIMUM_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Image size cannot be greater than 5 MB.",
            )

        optimized_content = optimize_image(image_content)

        filename = f"{uuid4().hex}.webp"

        new_image_path = (
            PRODUCT_IMAGE_DIRECTORY / filename
        )

        new_image_path.write_bytes(optimized_content)

        old_image_url = product.image_url
        new_image_url = f"/uploads/products/{filename}"

        product.image_url = new_image_url

        try:
            db.commit()
            db.refresh(product)

        except Exception:
            db.rollback()
            new_image_path.unlink(missing_ok=True)
            raise

        if old_image_url != new_image_url:
            delete_old_product_image(old_image_url)

        return product

    finally:
        await image_file.close()