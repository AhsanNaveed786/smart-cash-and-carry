from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from database import get_db
from models import Admin, AdminSession
from services.admin_auth_service import (
    require_admin_session,
    require_current_admin,
    verify_csrf_token,
)
from services.rbac_service import (
    ensure_admin_branch_access,
    ensure_admin_permission,
)


def require_super_admin(
    admin: Admin = Depends(require_current_admin),
) -> Admin:
    if admin.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin access required.",
        )
    return admin


def require_admin_write_csrf(
    request: Request,
    x_csrf_token: str | None = Header(
        default=None,
        alias="X-CSRF-Token",
    ),
    admin_session: AdminSession = Depends(
        require_admin_session
    ),
) -> AdminSession:
    verify_csrf_token(
        request=request,
        admin_session=admin_session,
        header_token=x_csrf_token,
    )
    return admin_session


def permission_required(
    permission_code: str,
) -> Callable:
    def dependency(
        db: Session = Depends(get_db),
        admin: Admin = Depends(require_current_admin),
    ) -> Admin:
        ensure_admin_permission(
            db=db,
            admin=admin,
            permission_code=permission_code,
        )
        return admin

    return dependency


def require_selected_branch_access(
    branch_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_current_admin),
) -> Admin:
    ensure_admin_branch_access(
        db=db,
        admin=admin,
        branch_id=branch_id,
    )
    return admin
