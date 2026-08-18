import asyncio
import os
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_STATIC_DIRECTORY = PROJECT_ROOT / "frontend" / "static"
STATIC_DIRECTORY = (
    FRONTEND_STATIC_DIRECTORY
    if FRONTEND_STATIC_DIRECTORY.is_dir()
    else PROJECT_ROOT / "static"
)
UPLOAD_DIRECTORY = STATIC_DIRECTORY / "uploads"

MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


def cloud_storage_enabled() -> bool:
    return bool(os.getenv("CLOUDINARY_URL", "").strip())


def create_upload_directories() -> None:
    UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)


def optimize_image(file_content: bytes) -> bytes:
    try:
        Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
        with Image.open(BytesIO(file_content)) as test_image:
            if test_image.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValueError("Unsupported image format.")
            test_image.verify()

        with Image.open(BytesIO(file_content)) as source_image:
            image = ImageOps.exif_transpose(source_image)
            if image.width <= 0 or image.height <= 0:
                raise ValueError("Invalid image dimensions.")
            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise ValueError("Image dimensions are too large.")

            image.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
            if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
                image = image.convert("RGBA")
            else:
                image = image.convert("RGB")

            output = BytesIO()
            image.save(output, format="WEBP", quality=86, method=6)
            return output.getvalue()
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is not a valid supported image.",
        ) from error


def upload_to_cloudinary(
    image_content: bytes,
    folder_name: str,
) -> str:
    try:
        import cloudinary
        import cloudinary.uploader
    except ImportError as error:
        raise RuntimeError(
            "Cloudinary is configured but its Python package is missing."
        ) from error

    cloudinary.config(secure=True)
    result = cloudinary.uploader.upload(
        BytesIO(image_content),
        folder=f"smart-cash-and-carry/{folder_name}",
        public_id=uuid4().hex,
        resource_type="image",
        format="webp",
        overwrite=False,
    )
    secure_url = result.get("secure_url")
    if not secure_url:
        raise RuntimeError("Cloud image upload did not return a URL.")
    return str(secure_url)


async def save_uploaded_image(
    uploaded_file: UploadFile,
    folder_name: str,
) -> str:
    try:
        if uploaded_file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Only JPEG, PNG and WEBP images are allowed.",
            )

        file_content = await uploaded_file.read(MAX_IMAGE_SIZE + 1)
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

        optimized_content = optimize_image(file_content)
        safe_folder = "-".join(
            part for part in folder_name.lower().split("/") if part
        )
        safe_folder = safe_folder or "general"

        if cloud_storage_enabled():
            return await asyncio.to_thread(
                upload_to_cloudinary,
                optimized_content,
                safe_folder,
            )

        target_directory = UPLOAD_DIRECTORY / safe_folder
        target_directory.mkdir(parents=True, exist_ok=True)
        file_name = f"{uuid4().hex}.webp"
        (target_directory / file_name).write_bytes(optimized_content)
        return f"/static/uploads/{safe_folder}/{file_name}"
    finally:
        await uploaded_file.close()


def cloudinary_public_id(media_url: str) -> str | None:
    parsed = urlparse(media_url)
    if parsed.hostname != "res.cloudinary.com":
        return None
    marker = "/image/upload/"
    if marker not in parsed.path:
        return None
    public_path = parsed.path.split(marker, 1)[1]
    parts = public_path.split("/")
    if parts and parts[0].startswith("v") and parts[0][1:].isdigit():
        parts = parts[1:]
    if not parts:
        return None
    public_id = "/".join(parts)
    if "." in public_id.rsplit("/", 1)[-1]:
        public_id = public_id.rsplit(".", 1)[0]
    return public_id or None


def delete_media_file(media_url: str | None) -> None:
    if not media_url:
        return

    public_id = cloudinary_public_id(media_url)
    if public_id:
        try:
            import cloudinary
            import cloudinary.uploader

            cloudinary.config(secure=True)
            cloudinary.uploader.destroy(
                public_id,
                resource_type="image",
                invalidate=True,
            )
        except Exception:
            # Database changes should never be undone only because remote
            # media cleanup was temporarily unavailable.
            pass
        return

    expected_prefix = "/static/uploads/"
    if not media_url.startswith(expected_prefix):
        return
    relative_path = media_url.removeprefix("/static/")
    file_path = (STATIC_DIRECTORY / relative_path).resolve()
    uploads_root = UPLOAD_DIRECTORY.resolve()
    try:
        file_path.relative_to(uploads_root)
    except ValueError:
        return
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        pass
