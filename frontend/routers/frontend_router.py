from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIRECTORY = BASE_DIR / "templates"

templates = Jinja2Templates(
    directory=str(TEMPLATES_DIRECTORY)
)

router = APIRouter(include_in_schema=False)


def page_context(
    request: Request,
    page_title: str,
    page_name: str,
    **extra,
) -> dict:
    return {
        "request": request,
        "page_title": page_title,
        "page_name": page_name,
        **extra,
    }


@router.get("/", response_class=HTMLResponse)
def storefront_home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="storefront/home.html",
        context=page_context(
            request,
            "Fresh groceries, branch-perfect prices",
            "home",
        ),
    )


@router.get("/shop", response_class=HTMLResponse)
def storefront_shop(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="storefront/shop.html",
        context=page_context(
            request,
            "Shop all products",
            "shop",
        ),
    )


@router.get(
    "/product/{product_id}",
    response_class=HTMLResponse,
)
def storefront_product(
    request: Request,
    product_id: int,
):
    return templates.TemplateResponse(
        request=request,
        name="storefront/product.html",
        context=page_context(
            request,
            "Product details",
            "product",
            product_id=product_id,
        ),
    )


@router.get("/cart", response_class=HTMLResponse)
def storefront_cart(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="storefront/cart.html",
        context=page_context(
            request,
            "Your shopping cart",
            "cart",
        ),
    )


@router.get("/checkout", response_class=HTMLResponse)
def storefront_checkout(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="storefront/checkout.html",
        context=page_context(
            request,
            "Checkout",
            "checkout",
        ),
    )


@router.get("/track-order", response_class=HTMLResponse)
def storefront_track_order(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="storefront/track_order.html",
        context=page_context(
            request,
            "Track your order",
            "track-order",
        ),
    )


@router.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="admin/login.html",
        context=page_context(
            request,
            "Admin sign in",
            "admin-login",
        ),
    )


@router.get("/admin", response_class=HTMLResponse)
@router.get("/admin/", response_class=HTMLResponse)
def admin_dashboard_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context=page_context(
            request,
            "Admin dashboard",
            "admin-dashboard",
        ),
    )
