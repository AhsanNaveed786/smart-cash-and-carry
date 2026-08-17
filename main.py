from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from frontend.routers.frontend_router import (
    router as frontend_router,
)
from routers.admin_auth_router import (
    router as admin_auth_router,
)
from routers.admin_business_router import (
    router as admin_business_router,
)
from routers.availability_router import (
    router as availability_router,
)
from routers.branch_router import (
    router as branch_router,
)
from routers.category_media_router import (
    router as category_media_router,
)
from routers.category_router import (
    router as category_router,
)
from routers.content_router import (
    router as content_router,
)
from routers.discount_router import (
    router as discount_router,
)
from routers.order_router import (
    router as order_router,
)
from routers.price_import_router import (
    router as price_import_router,
)
from routers.price_router import (
    router as price_router,
)
from routers.product_gallery_router import (
    router as product_gallery_router,
)
from routers.product_image_router import (
    router as product_image_router,
)
from routers.product_import_router import (
    router as product_import_router,
)
from routers.product_router import (
    router as product_router,
)
from routers.rbac_router import (
    router as rbac_router,
)
from routers.storefront_content_router import (
    router as storefront_content_router,
)
from routers.storefront_price_router import (
    router as storefront_price_router,
)
from routers.variant_router import (
    router as variant_router,
)
from routers.variant_stock_router import (
    router as variant_stock_router,
)
from routers.whatsapp_order_router import (
    router as whatsapp_order_router,
)
from services.media_service import (
    STATIC_DIRECTORY as MEDIA_STATIC_DIRECTORY,
    create_upload_directories,
)


BASE_DIR = Path(__file__).resolve().parent

FRONTEND_STATIC_DIRECTORY = (
    BASE_DIR / "frontend" / "static"
)

PRODUCT_UPLOADS_DIRECTORY = (
    BASE_DIR / "uploads"
)

MEDIA_UPLOADS_DIRECTORY = (
    MEDIA_STATIC_DIRECTORY / "uploads"
)


FRONTEND_STATIC_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)

PRODUCT_UPLOADS_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)

create_upload_directories()

Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="SMART CASH & CARRY",
    description=(
        "Storefront and administration API "
        "for SMART CASH & CARRY"
    ),
    version="2.0.0",
)


# Uploaded category icons, banners and content images
app.mount(
    "/static/uploads",
    StaticFiles(
        directory=str(MEDIA_UPLOADS_DIRECTORY)
    ),
    name="media_uploads",
)


# Frontend CSS, JavaScript and other assets
app.mount(
    "/static",
    StaticFiles(
        directory=str(FRONTEND_STATIC_DIRECTORY)
    ),
    name="static",
)


# Product and gallery uploads
app.mount(
    "/uploads",
    StaticFiles(
        directory=str(PRODUCT_UPLOADS_DIRECTORY)
    ),
    name="uploads",
)


app.include_router(admin_auth_router)
app.include_router(rbac_router)
app.include_router(branch_router)
app.include_router(category_router)
app.include_router(category_media_router)
app.include_router(product_router)
app.include_router(product_image_router)
app.include_router(product_gallery_router)
app.include_router(variant_router)
app.include_router(variant_stock_router)
app.include_router(price_router)
app.include_router(storefront_price_router)
app.include_router(price_import_router)
app.include_router(product_import_router)
app.include_router(availability_router)
app.include_router(discount_router)
app.include_router(content_router)
app.include_router(storefront_content_router)
app.include_router(order_router)
app.include_router(whatsapp_order_router)
app.include_router(admin_business_router)

# Frontend router should be included only once
app.include_router(frontend_router)


@app.get("/api", tags=["System"])
def api_root():
    return {
        "message": (
            "SMART CASH & CARRY API is running"
        ),
        "storefront": "/",
        "admin": "/admin",
        "docs": "/docs",
    }


@app.get(
    "/health/database",
    tags=["System"],
)
def database_health(
    db: Session = Depends(get_db),
):
    db.execute(text("SELECT 1"))

    return {
        "status": "healthy",
        "database": "connected",
    }