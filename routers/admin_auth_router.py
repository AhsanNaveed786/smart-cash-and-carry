from fastapi import (
    APIRouter,
    Depends,
    Header,
    Request,
    Response,
)
from sqlalchemy.orm import Session

from database import get_db
from models import Admin, AdminSession
from schemas import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminResponse,
    MessageResponse,
)
from services.admin_auth_service import (
    login_admin,
    logout_admin,
    require_admin_session,
    require_current_admin,
)


router = APIRouter(
    prefix="/api/admin/auth",
    tags=["Admin Authentication"],
)


@router.post(
    "/login",
    response_model=AdminLoginResponse,
)
def admin_login(
    login_data: AdminLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    return login_admin(
        db=db,
        login_data=login_data,
        request=request,
        response=response,
    )


@router.get(
    "/me",
    response_model=AdminResponse,
)
def view_current_admin(
    admin: Admin = Depends(
        require_current_admin
    ),
):
    return admin


@router.post(
    "/logout",
    response_model=MessageResponse,
)
def admin_logout(
    request: Request,
    response: Response,
    x_csrf_token: str | None = Header(
        default=None,
        alias="X-CSRF-Token",
    ),
    admin_session: AdminSession = Depends(
        require_admin_session
    ),
    db: Session = Depends(get_db),
):
    return logout_admin(
        db=db,
        request=request,
        response=response,
        admin_session=admin_session,
        csrf_token=x_csrf_token,
    )
