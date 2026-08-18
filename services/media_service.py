from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError


PROJECT_ROOT = Path(__file__).resolve().parent.parent

# The public frontend is mounted from frontend/static in main.py. Save
# managed content there as well so returned /static/uploads/... URLs are
# served by the same StaticFiles mount.
FRONTEND_STATIC_DIRECTORY = PROJECT_ROOT / "frontend" / "static"
STATIC_DIRECTORY = (
    FRONTEND_STATIC_DIRECTORY
    if FRONTEND_STATIC_DIRECTORY.is_dir()
    else PROJECT_ROOT / "static"
)
UPLOAD_DIRECTORY = STATIC_DIRECTORY / "uploads"

MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}


def create_upload_directories() -> None:
    UPLOAD_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )


async def save_uploaded_image(
    uploaded_file: UploadFile,
    folder_name: str,
) -> str:
    if uploaded_file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only JPEG, PNG and WEBP images are allowed."
            ),
        )

    file_content = await uploaded_file.read(
        MAX_IMAGE_SIZE + 1
    )

    if not file_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image is empty.",
        )

    if len(file_content) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image size cannot exceed 5 MB.",
        )

    try:
        Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

        with Image.open(
            BytesIO(file_content)
        ) as test_image:
            test_image.verify()

        with Image.open(
            BytesIO(file_content)
        ) as source_image:
            image = ImageOps.exif_transpose(
                source_image
            )

            if (
                image.width <= 0
                or image.height <= 0
            ):
                raise ValueError(
                    "Invalid image dimensions."
                )

            if (
                image.width * image.height
                > MAX_IMAGE_PIXELS
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Image dimensions are too large.",
                )

            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA")

            target_directory = (
                UPLOAD_DIRECTORY / folder_name
            )

            target_directory.mkdir(
                parents=True,
                exist_ok=True,
            )

            file_name = f"{uuid4().hex}.webp"
            file_path = (
                target_directory / file_name
            )

            image.save(
                file_path,
                format="WEBP",
                quality=88,
                method=6,
            )

    except HTTPException:
        raise

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "The uploaded file is not a valid image."
            ),
        )

    finally:
        await uploaded_file.close()

    return (
        f"/static/uploads/"
        f"{folder_name}/{file_name}"
    )


def delete_media_file(
    media_url: str | None,
) -> None:
    if not media_url:
        return

    expected_prefix = "/static/uploads/"

    if not media_url.startswith(expected_prefix):
        return

    relative_path = media_url.removeprefix(
        "/static/"
    )

    file_path = (
        STATIC_DIRECTORY / relative_path
    ).resolve()

    uploads_root = UPLOAD_DIRECTORY.resolve()

    try:
        file_path.relative_to(uploads_root)
    except ValueError:
        return

    if file_path.is_file():
        file_path.unlink()
