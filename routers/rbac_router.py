from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from dependencies.admin_access import (
    require_admin_write_csrf,
    require_super_admin,
)
from models import Admin, AdminSession, Permission
from schemas import (
    AdminAccessResponse,
    AdminAccessUpdateRequest,
    AdminAuditLogResponse,
    AdminSessionResponse,
    AdminSessionRevokeRequest,
    MessageResponse,
    MiniAdminCreateRequest,
    PermissionResponse,
)
from services.admin_auth_service import (
    get_request_ip,
    require_current_admin,
)
from services.rbac_service import (
    build_admin_access_response,
    create_mini_admin,
    get_admin_with_access,
    list_admin_audit_logs,
    list_admin_sessions,
    list_admins_with_access,
    revoke_admin_sessions_by_super,
    revoke_one_admin_session,
    seed_permission_catalog,
    update_mini_admin_access,
)


router = APIRouter(
    prefix="/api/admin/access",
    tags=["Admin Access Control"],
)


@router.get(
    "/me",
    response_model=AdminAccessResponse,
)
def view_current_access(
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_current_admin),
):
    loaded_admin = get_admin_with_access(db, admin.id)
    return build_admin_access_response(db, loaded_admin)


@router.get(
    "/permissions",
    response_model=list[PermissionResponse],
)
def view_permission_catalog(
    db: Session = Depends(get_db),
    _super_admin: Admin = Depends(require_super_admin),
):
    if not db.scalar(select(Permission.id).limit(1)):
        seed_permission_catalog(db)
    return list(
        db.scalars(
            select(Permission).order_by(Permission.code)
        ).all()
    )


@router.get(
    "/admins",
    response_model=list[AdminAccessResponse],
)
def view_admins(
    db: Session = Depends(get_db),
    _super_admin: Admin = Depends(require_super_admin),
):
    return list_admins_with_access(db)


@router.post(
    "/admins",
    response_model=AdminAccessResponse,
    status_code=201,
)
def add_mini_admin(
    admin_data: MiniAdminCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    super_admin: Admin = Depends(require_super_admin),
    _admin_session: AdminSession = Depends(
        require_admin_write_csrf
    ),
):
    seed_permission_catalog(db)
    return create_mini_admin(
        db=db,
        admin_data=admin_data,
        super_admin=super_admin,
        ip_address=get_request_ip(request),
    )


@router.get(
    "/admins/{admin_id}",
    response_model=AdminAccessResponse,
)
def view_admin_access(
    admin_id: int,
    db: Session = Depends(get_db),
    _super_admin: Admin = Depends(require_super_admin),
):
    admin = get_admin_with_access(db, admin_id)
    return build_admin_access_response(db, admin)


@router.patch(
    "/admins/{admin_id}",
    response_model=AdminAccessResponse,
)
def edit_mini_admin_access(
    admin_id: int,
    update_data: AdminAccessUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    super_admin: Admin = Depends(require_super_admin),
    _admin_session: AdminSession = Depends(
        require_admin_write_csrf
    ),
):
    seed_permission_catalog(db)
    return update_mini_admin_access(
        db=db,
        admin_id=admin_id,
        update_data=update_data,
        super_admin=super_admin,
        ip_address=get_request_ip(request),
    )


@router.get(
    "/admins/{admin_id}/sessions",
    response_model=list[AdminSessionResponse],
)
def view_admin_sessions(
    admin_id: int,
    active_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    _super_admin: Admin = Depends(require_super_admin),
):
    return list_admin_sessions(
        db=db,
        admin_id=admin_id,
        active_only=active_only,
    )


@router.post(
    "/sessions/{session_id}/revoke",
    response_model=AdminSessionResponse,
)
def revoke_admin_session(
    session_id: int,
    revoke_data: AdminSessionRevokeRequest,
    request: Request,
    db: Session = Depends(get_db),
    super_admin: Admin = Depends(require_super_admin),
    _admin_session: AdminSession = Depends(
        require_admin_write_csrf
    ),
):
    return revoke_one_admin_session(
        db=db,
        session_id=session_id,
        super_admin=super_admin,
        reason=revoke_data.reason,
        ip_address=get_request_ip(request),
    )


@router.post(
    "/admins/{admin_id}/sessions/revoke-all",
    response_model=MessageResponse,
)
def revoke_all_sessions(
    admin_id: int,
    revoke_data: AdminSessionRevokeRequest,
    request: Request,
    db: Session = Depends(get_db),
    super_admin: Admin = Depends(require_super_admin),
    _admin_session: AdminSession = Depends(
        require_admin_write_csrf
    ),
):
    return revoke_admin_sessions_by_super(
        db=db,
        admin_id=admin_id,
        super_admin=super_admin,
        reason=revoke_data.reason,
        ip_address=get_request_ip(request),
    )


@router.get(
    "/audit-logs",
    response_model=list[AdminAuditLogResponse],
)
def view_admin_audit_logs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _super_admin: Admin = Depends(require_super_admin),
):
    return list_admin_audit_logs(
        db=db,
        skip=skip,
        limit=limit,
    )
