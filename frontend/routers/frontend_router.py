from pathlib import Path

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIRECTORY = BASE_DIR / "templates"

templates = Jinja2Templates(
    directory=str(TEMPLATES_DIRECTORY)
)

router = APIRouter(include_in_schema=False)


from sqlalchemy.orm import Session
from database import get_db
from services.content_service import get_website_settings

def page_context(
    request: Request,
    page_title: str,
    page_name: str,
    db: Session,
    **extra,
) -> dict:
    settings = get_website_settings(db)
    return {
        "request": request,
        "page_title": page_title,
        "page_name": page_name,
        "theme_color": settings.theme_color,
        **extra,
    }


@router.get("/", response_class=HTMLResponse)
def storefront_home(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request=request,
        name="storefront/home.html",
        context=page_context(request, "Fresh groceries, branch-perfect prices", "home", db=db,
        ),
    )


@router.get("/shop", response_class=HTMLResponse)
def storefront_shop(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request=request,
        name="storefront/shop.html",
        context=page_context(request, "Shop all products", "shop", db=db,
        ),
    )


@router.get(
    "/product/{product_id}",
    response_class=HTMLResponse,
)
def storefront_product(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db)
):
    return templates.TemplateResponse(
        request=request,
        name="storefront/product.html",
        context=page_context(request, "Product details", "product", db=db,
            product_id=product_id,
        ),
    )


@router.get("/cart", response_class=HTMLResponse)
def storefront_cart(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request=request,
        name="storefront/cart.html",
        context=page_context(request, "Your shopping cart", "cart", db=db,
        ),
    )


@router.get("/checkout", response_class=HTMLResponse)
def storefront_checkout(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request=request,
        name="storefront/checkout.html",
        context=page_context(request, "Checkout", "checkout", db=db,
        ),
    )


@router.get("/track-order", response_class=HTMLResponse)
def storefront_track_order(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request=request,
        name="storefront/track_order.html",
        context=page_context(request, "Track your order", "track-order", db=db,
        ),
    )


@router.get("/superadmin/login", response_class=HTMLResponse)
def admin_login_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request=request,
        name="admin/login.html",
        context=page_context(request, "Admin sign in", "admin-login", db=db,
        ),
    )


@router.get("/superadmin", response_class=HTMLResponse)
@router.get("/superadmin/", response_class=HTMLResponse)
def admin_dashboard_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context=page_context(request, "Admin dashboard", "admin-dashboard", db=db,
        ),
    )
