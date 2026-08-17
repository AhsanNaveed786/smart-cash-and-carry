from datetime import datetime, timezone

from fastapi import HTTPException, status
from pwdlib import PasswordHash
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from models import (
    Admin,
    AdminAuditLog,
    AdminBranchAccess,
    AdminPermission,
    AdminSession,
    Branch,
    Permission,
)
from schemas import AdminAccessUpdateRequest, MiniAdminCreateRequest


MAX_ACTIVE_MINI_ADMINS = 5
PASSWORD_HASHER = PasswordHash.recommended()

PERMISSION_CATALOG = {
    "products.read": ("View product listings", True),
    "prices.read": ("View branch product prices", True),
    "prices.update": ("Update assigned-branch prices", True),
    "orders.read": ("View assigned-branch orders", True),
    "orders.update_status": ("Change assigned-order status", True),
    "admins.manage": ("Create and control admins", False),
    "sessions.manage": ("View and revoke admin sessions", False),
    "exports.orders": ("Export order records", False),
    "exports.products": ("Export product and price records", False),
    "revenue.read": ("View revenue dashboards", False),
    "orders.delete_exported": ("Delete successfully exported orders", False),
}


def to_json_safe(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: to_json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_json_safe(item) for item in value]
    return value


def create_admin_audit_log(
    db: Session,
    action: str,
    actor_admin_id: int | None = None,
    target_admin_id: int | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> AdminAuditLog:
    audit_log = AdminAuditLog(
        actor_admin_id=actor_admin_id,
        target_admin_id=target_admin_id,
        action=action,
        details=details or {},
        ip_address=ip_address,
    )
    db.add(audit_log)
    return audit_log


def seed_permission_catalog(db: Session) -> list[Permission]:
    existing_permissions = {
        permission.code: permission
        for permission in db.scalars(select(Permission)).all()
    }

    for code, (description, assignable) in PERMISSION_CATALOG.items():
        permission = existing_permissions.get(code)
        if permission:
            permission.description = description
            permission.is_assignable_to_mini_admin = assignable
        else:
            permission = Permission(
                code=code,
                description=description,
                is_assignable_to_mini_admin=assignable,
            )
            db.add(permission)

    db.commit()
    return list(db.scalars(select(Permission).order_by(Permission.code)).all())


def validate_admin_login_policy(
    admin: Admin,
    current_time: datetime | None = None,
) -> None:
    now = current_time or datetime.now(timezone.utc)

    if not admin.is_active or not admin.login_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin login is currently disabled.",
        )

    if admin.login_allowed_from and now < admin.login_allowed_from:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin login is not allowed yet.",
        )

    if admin.login_allowed_until and now >= admin.login_allowed_until:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin login permission has expired.",
        )


def get_admin_with_access(
    db: Session,
    admin_id: int,
) -> Admin:
    admin = db.scalar(
        select(Admin)
        .options(
            selectinload(Admin.permission_links).selectinload(
                AdminPermission.permission
            ),
            selectinload(Admin.branch_accesses),
        )
        .where(Admin.id == admin_id)
    )

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin not found.",
        )

    return admin


def build_admin_access_response(
    db: Session,
    admin: Admin,
) -> dict:
    if admin.role == "super_admin":
        permission_codes = ["*"]
        branch_ids = list(
            db.scalars(
                select(Branch.id)
                .where(Branch.is_active.is_(True))
                .order_by(Branch.id)
            ).all()
        )
    else:
        permission_codes = sorted(
            link.permission.code for link in admin.permission_links
        )
        branch_ids = sorted(
            access.branch_id for access in admin.branch_accesses
        )

    return {
        "id": admin.id,
        "full_name": admin.full_name,
        "email": admin.email,
        "role": admin.role,
        "is_active": admin.is_active,
        "login_allowed": admin.login_allowed,
        "login_allowed_from": admin.login_allowed_from,
        "login_allowed_until": admin.login_allowed_until,
        "last_login_at": admin.last_login_at,
        "created_at": admin.created_at,
        "permission_codes": permission_codes,
        "branch_ids": branch_ids,
    }


def admin_has_permission(
    db: Session,
    admin: Admin,
    permission_code: str,
) -> bool:
    if admin.role == "super_admin":
        return True

    return db.scalar(
        select(AdminPermission.id)
        .join(Permission, Permission.id == AdminPermission.permission_id)
        .where(
            AdminPermission.admin_id == admin.id,
            Permission.code == permission_code,
        )
        .limit(1)
    ) is not None


def ensure_admin_permission(
    db: Session,
    admin: Admin,
    permission_code: str,
) -> None:
    if not admin_has_permission(db, admin, permission_code):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing permission: {permission_code}",
        )


def get_admin_branch_ids(
    db: Session,
    admin: Admin,
) -> set[int]:
    if admin.role == "super_admin":
        return set(
            db.scalars(
                select(Branch.id).where(Branch.is_active.is_(True))
            ).all()
        )

    return set(
        db.scalars(
            select(AdminBranchAccess.branch_id).where(
                AdminBranchAccess.admin_id == admin.id
            )
        ).all()
    )


def ensure_admin_branch_access(
    db: Session,
    admin: Admin,
    branch_id: int,
) -> None:
    if admin.role == "super_admin":
        return

    if branch_id not in get_admin_branch_ids(db, admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This admin cannot access the selected branch.",
        )


def validate_active_branch_ids(
    db: Session,
    branch_ids: list[int],
) -> None:
    found_ids = set(
        db.scalars(
            select(Branch.id).where(
                Branch.id.in_(branch_ids),
                Branch.is_active.is_(True),
            )
        ).all()
    )
    missing_ids = set(branch_ids) - found_ids
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Some branches are missing or inactive.",
                "branch_ids": sorted(missing_ids),
            },
        )


def get_assignable_permissions(
    db: Session,
    permission_codes: list[str],
) -> list[Permission]:
    permissions = list(
        db.scalars(
            select(Permission).where(
                Permission.code.in_(permission_codes),
                Permission.is_assignable_to_mini_admin.is_(True),
            )
        ).all()
    )
    found_codes = {permission.code for permission in permissions}
    invalid_codes = set(permission_codes) - found_codes
    if invalid_codes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Invalid or Super-Admin-only permissions.",
                "permission_codes": sorted(invalid_codes),
            },
        )
    return permissions


def replace_admin_branches(
    db: Session,
    admin_id: int,
    branch_ids: list[int],
    granted_by_admin_id: int,
) -> None:
    validate_active_branch_ids(db, branch_ids)
    for existing_access in db.scalars(
        select(AdminBranchAccess).where(
            AdminBranchAccess.admin_id == admin_id
        )
    ).all():
        db.delete(existing_access)
    db.flush()
    for branch_id in branch_ids:
        db.add(
            AdminBranchAccess(
                admin_id=admin_id,
                branch_id=branch_id,
                granted_by_admin_id=granted_by_admin_id,
            )
        )


def replace_admin_permissions(
    db: Session,
    admin_id: int,
    permission_codes: list[str],
    granted_by_admin_id: int,
) -> None:
    permissions = get_assignable_permissions(db, permission_codes)
    for existing_link in db.scalars(
        select(AdminPermission).where(AdminPermission.admin_id == admin_id)
    ).all():
        db.delete(existing_link)
    db.flush()
    for permission in permissions:
        db.add(
            AdminPermission(
                admin_id=admin_id,
                permission_id=permission.id,
                granted_by_admin_id=granted_by_admin_id,
            )
        )


def revoke_all_admin_sessions(
    db: Session,
    target_admin_id: int,
    revoked_by_admin_id: int,
    reason: str,
    excluded_session_id: int | None = None,
) -> int:
    current_time = datetime.now(timezone.utc)
    statement = select(AdminSession).where(
        AdminSession.admin_id == target_admin_id,
        AdminSession.revoked_at.is_(None),
        AdminSession.expires_at > current_time,
    )
    if excluded_session_id is not None:
        statement = statement.where(AdminSession.id != excluded_session_id)
    sessions = db.scalars(statement).all()
    for admin_session in sessions:
        admin_session.revoked_at = current_time
        admin_session.revoked_by_admin_id = revoked_by_admin_id
        admin_session.revoke_reason = reason[:255]
    return len(sessions)


def create_mini_admin(
    db: Session,
    admin_data: MiniAdminCreateRequest,
    super_admin: Admin,
    ip_address: str | None = None,
) -> dict:
    active_mini_admin_count = db.scalar(
        select(func.count(Admin.id)).where(
            Admin.role == "mini_admin",
            Admin.is_active.is_(True),
        )
    ) or 0
    if active_mini_admin_count >= MAX_ACTIVE_MINI_ADMINS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Maximum five active mini admins are allowed.",
        )

    normalized_email = str(admin_data.email).strip().lower()
    if db.scalar(select(Admin.id).where(Admin.email == normalized_email)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admin email already exists.",
        )

    validate_active_branch_ids(db, admin_data.branch_ids)
    get_assignable_permissions(db, admin_data.permission_codes)

    try:
        admin = Admin(
            full_name=admin_data.full_name.strip(),
            email=normalized_email,
            password_hash=PASSWORD_HASHER.hash(admin_data.password),
            role="mini_admin",
            is_active=True,
            login_allowed=admin_data.login_allowed,
            login_allowed_from=admin_data.login_allowed_from,
            login_allowed_until=admin_data.login_allowed_until,
        )
        db.add(admin)
        db.flush()
        replace_admin_branches(
            db=db,
            admin_id=admin.id,
            branch_ids=admin_data.branch_ids,
            granted_by_admin_id=super_admin.id,
        )
        replace_admin_permissions(
            db=db,
            admin_id=admin.id,
            permission_codes=admin_data.permission_codes,
            granted_by_admin_id=super_admin.id,
        )
        create_admin_audit_log(
            db=db,
            action="mini_admin.created",
            actor_admin_id=super_admin.id,
            target_admin_id=admin.id,
            details={
                "branch_ids": admin_data.branch_ids,
                "permission_codes": admin_data.permission_codes,
            },
            ip_address=ip_address,
        )
        db.commit()
        admin = get_admin_with_access(db, admin.id)
        return build_admin_access_response(db, admin)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


def update_mini_admin_access(
    db: Session,
    admin_id: int,
    update_data: AdminAccessUpdateRequest,
    super_admin: Admin,
    ip_address: str | None = None,
) -> dict:
    admin = get_admin_with_access(db, admin_id)
    if admin.role == "super_admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Super Admin access cannot be edited here.",
        )

    changes = update_data.model_dump(exclude_unset=True)
    try:
        if changes.get("full_name") is not None:
            admin.full_name = changes["full_name"].strip()
        if changes.get("is_active") is not None:
            admin.is_active = changes["is_active"]
        if changes.get("login_allowed") is not None:
            admin.login_allowed = changes["login_allowed"]
        if "login_allowed_from" in changes:
            admin.login_allowed_from = changes["login_allowed_from"]
        if "login_allowed_until" in changes:
            admin.login_allowed_until = changes["login_allowed_until"]
        if (
            admin.login_allowed_from
            and admin.login_allowed_until
            and admin.login_allowed_until <= admin.login_allowed_from
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid login permission date range.",
            )
        if changes.get("branch_ids") is not None:
            replace_admin_branches(
                db=db,
                admin_id=admin.id,
                branch_ids=changes["branch_ids"],
                granted_by_admin_id=super_admin.id,
            )
        if changes.get("permission_codes") is not None:
            replace_admin_permissions(
                db=db,
                admin_id=admin.id,
                permission_codes=changes["permission_codes"],
                granted_by_admin_id=super_admin.id,
            )

        revoked_sessions = 0
        if not admin.is_active or not admin.login_allowed:
            revoked_sessions = revoke_all_admin_sessions(
                db=db,
                target_admin_id=admin.id,
                revoked_by_admin_id=super_admin.id,
                reason="Admin access disabled by Super Admin.",
            )

        create_admin_audit_log(
            db=db,
            action="mini_admin.access_updated",
            actor_admin_id=super_admin.id,
            target_admin_id=admin.id,
            details=to_json_safe(
                {**changes, "revoked_sessions": revoked_sessions}
            ),
            ip_address=ip_address,
        )
        db.commit()
        admin = get_admin_with_access(db, admin.id)
        return build_admin_access_response(db, admin)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


def list_admins_with_access(db: Session) -> list[dict]:
    admins = db.scalars(select(Admin).order_by(Admin.created_at)).all()
    return [
        build_admin_access_response(db, get_admin_with_access(db, admin.id))
        for admin in admins
    ]


def list_admin_sessions(
    db: Session,
    admin_id: int,
    active_only: bool = False,
) -> list[AdminSession]:
    get_admin_with_access(db, admin_id)
    statement = select(AdminSession).where(
        AdminSession.admin_id == admin_id
    ).order_by(AdminSession.created_at.desc())
    if active_only:
        now = datetime.now(timezone.utc)
        statement = statement.where(
            AdminSession.revoked_at.is_(None),
            AdminSession.expires_at > now,
        )
    return list(db.scalars(statement).all())


def revoke_one_admin_session(
    db: Session,
    session_id: int,
    super_admin: Admin,
    reason: str | None = None,
    ip_address: str | None = None,
) -> AdminSession:
    admin_session = db.get(AdminSession, session_id)
    if not admin_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Admin session not found.",
        )
    target_admin = get_admin_with_access(db, admin_session.admin_id)
    if target_admin.role == "super_admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Super Admin sessions cannot be revoked here.",
        )
    try:
        if admin_session.revoked_at is None:
            admin_session.revoked_at = datetime.now(timezone.utc)
            admin_session.revoked_by_admin_id = super_admin.id
            admin_session.revoke_reason = (
                reason.strip()[:255]
                if reason
                else "Revoked by Super Admin."
            )
        create_admin_audit_log(
            db=db,
            action="admin_session.revoked",
            actor_admin_id=super_admin.id,
            target_admin_id=target_admin.id,
            details={"session_id": admin_session.id},
            ip_address=ip_address,
        )
        db.commit()
        db.refresh(admin_session)
        return admin_session
    except Exception:
        db.rollback()
        raise


def revoke_admin_sessions_by_super(
    db: Session,
    admin_id: int,
    super_admin: Admin,
    reason: str | None = None,
    ip_address: str | None = None,
) -> dict:
    target_admin = get_admin_with_access(db, admin_id)
    if target_admin.role == "super_admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Super Admin sessions cannot be revoked here.",
        )

    revoke_reason = (
        reason.strip()[:255]
        if reason
        else "All sessions revoked by Super Admin."
    )

    try:
        revoked_count = revoke_all_admin_sessions(
            db=db,
            target_admin_id=target_admin.id,
            revoked_by_admin_id=super_admin.id,
            reason=revoke_reason,
        )
        create_admin_audit_log(
            db=db,
            action="admin_sessions.revoked_all",
            actor_admin_id=super_admin.id,
            target_admin_id=target_admin.id,
            details={"revoked_sessions": revoked_count},
            ip_address=ip_address,
        )
        db.commit()
        return {
            "message": (
                f"{revoked_count} active admin session(s) revoked."
            )
        }
    except Exception:
        db.rollback()
        raise


def list_admin_audit_logs(
    db: Session,
    skip: int = 0,
    limit: int = 100,
) -> list[AdminAuditLog]:
    return list(
        db.scalars(
            select(AdminAuditLog)
            .order_by(AdminAuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        ).all()
    )
