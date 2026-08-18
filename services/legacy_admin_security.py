from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from database import SessionLocal
from services.admin_auth_service import (
    SESSION_COOKIE_NAME,
    get_active_admin_session,
    verify_csrf_token,
)
from services.rbac_service import validate_admin_login_policy
from services.rbac_service import admin_has_permission


PROTECTED_WRITE_PREFIXES = (
    "/api/branches",
    "/api/categories",
    "/api/products",
    "/api/product-gallery",
    "/api/variants",
    "/api/variant-stock",
    "/api/prices",
    "/api/price-imports",
    "/api/product-imports",
    "/api/availability",
    "/api/discounts",
    "/api/content",
)

IMPORT_WRITE_PREFIXES = (
    "/api/price-imports",
    "/api/product-imports",
)

UNSAFE_METHODS = {
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
}


def error_response(error: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"detail": error.detail},
    )


def install_legacy_admin_security(app: FastAPI) -> None:
    @app.middleware("http")
    async def enforce_super_admin_writes(
        request: Request,
        call_next,
    ):
        must_protect = (
            request.method in UNSAFE_METHODS
            and request.url.path.startswith(
                PROTECTED_WRITE_PREFIXES
            )
        )

        if not must_protect:
            return await call_next(request)

        raw_session_token = request.cookies.get(
            SESSION_COOKIE_NAME
        )
        if not raw_session_token:
            return error_response(
                HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Admin login required.",
                )
            )

        database = SessionLocal()
        try:
            admin_session = get_active_admin_session(
                db=database,
                raw_session_token=raw_session_token,
            )
            if admin_session is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Admin session is invalid or expired.",
                )

            validate_admin_login_policy(
                admin_session.admin
            )
            is_import_write = request.url.path.startswith(
                IMPORT_WRITE_PREFIXES
            )

            has_access = (
                admin_session.admin.role == "super_admin"
                or (
                    is_import_write
                    and admin_has_permission(
                        database,
                        admin_session.admin,
                        "imports.manage",
                    )
                )
            )

            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        "Super Admin access or imports.manage "
                        "permission required."
                    ),
                )

            verify_csrf_token(
                request=request,
                admin_session=admin_session,
                header_token=request.headers.get(
                    "X-CSRF-Token"
                ),
            )
        except HTTPException as error:
            return error_response(error)
        finally:
            database.close()

        return await call_next(request)
