import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import (
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database import get_db
from models import Admin, AdminSession
from schemas import AdminLoginRequest
from services.password_service import verify_password
from services.rbac_service import validate_admin_login_policy


SESSION_COOKIE_NAME = "smart_admin_session"
CSRF_COOKIE_NAME = "smart_admin_csrf"


def get_session_duration_hours() -> int:
    raw_value = os.getenv(
        "ADMIN_SESSION_HOURS",
        "12",
    )

    try:
        duration = int(raw_value)
    except ValueError:
        duration = 12

    return max(1, min(duration, 168))


SESSION_DURATION_HOURS = get_session_duration_hours()

COOKIE_SECURE = os.getenv(
    "COOKIE_SECURE",
    "false",
).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def hash_security_token(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def create_random_token() -> str:
    return secrets.token_urlsafe(32)


def get_request_ip(request: Request) -> str | None:
    if request.client is None:
        return None

    return request.client.host[:45]


def get_request_user_agent(
    request: Request,
) -> str | None:
    user_agent = request.headers.get(
        "user-agent"
    )

    if not user_agent:
        return None

    return user_agent[:500]


def set_admin_cookies(
    response: Response,
    session_token: str,
    csrf_token: str,
    expires_at: datetime,
) -> None:
    max_age = int(
        timedelta(
            hours=SESSION_DURATION_HOURS
        ).total_seconds()
    )

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        max_age=max_age,
        expires=expires_at,
        path="/",
        secure=COOKIE_SECURE,
        httponly=True,
        samesite="strict",
    )

    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=max_age,
        expires=expires_at,
        path="/",
        secure=COOKIE_SECURE,
        httponly=False,
        samesite="strict",
    )


def clear_admin_cookies(
    response: Response,
) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=COOKIE_SECURE,
        httponly=True,
        samesite="strict",
    )

    response.delete_cookie(
        key=CSRF_COOKIE_NAME,
        path="/",
        secure=COOKIE_SECURE,
        httponly=False,
        samesite="strict",
    )


def login_admin(
    db: Session,
    login_data: AdminLoginRequest,
    request: Request,
    response: Response,
) -> dict:
    normalized_email = str(
        login_data.email
    ).strip().lower()

    admin = db.scalar(
        select(Admin).where(
            Admin.email == normalized_email
        )
    )

    if (
        admin is None
        or not verify_password(
            login_data.password,
            admin.password_hash,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    validate_admin_login_policy(admin)

    session_token = create_random_token()
    csrf_token = create_random_token()

    current_time = datetime.now(timezone.utc)

    expires_at = current_time + timedelta(
        hours=SESSION_DURATION_HOURS
    )

    admin_session = AdminSession(
        admin_id=admin.id,
        session_token_hash=hash_security_token(
            session_token
        ),
        csrf_token_hash=hash_security_token(
            csrf_token
        ),
        user_agent=get_request_user_agent(
            request
        ),
        ip_address=get_request_ip(request),
        expires_at=expires_at,
        last_used_at=current_time,
        revoked_at=None,
        revoked_by_admin_id=None,
        revoke_reason=None,
    )

    admin.last_login_at = current_time

    db.add(admin_session)
    db.commit()
    db.refresh(admin)
    db.refresh(admin_session)

    set_admin_cookies(
        response=response,
        session_token=session_token,
        csrf_token=csrf_token,
        expires_at=expires_at,
    )

    return {
        "message": "Admin login successful.",
        "admin": admin,
        "csrf_token": csrf_token,
        "expires_at": expires_at,
    }


def get_active_admin_session(
    db: Session,
    raw_session_token: str,
) -> AdminSession | None:
    current_time = datetime.now(timezone.utc)

    session_token_hash = hash_security_token(
        raw_session_token
    )

    return db.scalar(
        select(AdminSession)
        .options(
            selectinload(AdminSession.admin)
        )
        .where(
            AdminSession.session_token_hash
            == session_token_hash,
            AdminSession.revoked_at.is_(None),
            AdminSession.expires_at > current_time,
        )
    )


def require_admin_session(
    request: Request,
    db: Session = Depends(get_db),
) -> AdminSession:
    raw_session_token = request.cookies.get(
        SESSION_COOKIE_NAME
    )

    if not raw_session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin login required.",
        )

    admin_session = get_active_admin_session(
        db=db,
        raw_session_token=raw_session_token,
    )

    if admin_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Admin session is invalid or expired."
            ),
        )

    try:
        validate_admin_login_policy(admin_session.admin)
    except HTTPException as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin access is disabled or outside its login window.",
        ) from error

    current_time = datetime.now(timezone.utc)
    if (
        admin_session.last_used_at is None
        or current_time - admin_session.last_used_at
        >= timedelta(minutes=5)
    ):
        admin_session.last_used_at = current_time
        db.commit()

    return admin_session


def require_current_admin(
    admin_session: AdminSession = Depends(
        require_admin_session
    ),
) -> Admin:
    return admin_session.admin


def verify_csrf_token(
    request: Request,
    admin_session: AdminSession,
    header_token: str | None,
) -> None:
    cookie_token = request.cookies.get(
        CSRF_COOKIE_NAME
    )

    if not header_token or not cookie_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token is missing.",
        )

    if not hmac.compare_digest(
        header_token,
        cookie_token,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token is invalid.",
        )

    received_token_hash = hash_security_token(
        header_token
    )

    if not hmac.compare_digest(
        received_token_hash,
        admin_session.csrf_token_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token is invalid.",
        )


def logout_admin(
    db: Session,
    request: Request,
    response: Response,
    admin_session: AdminSession,
    csrf_token: str | None,
) -> dict:
    verify_csrf_token(
        request=request,
        admin_session=admin_session,
        header_token=csrf_token,
    )

    current_time = datetime.now(timezone.utc)

    admin_session.revoked_at = current_time
    admin_session.revoked_by_admin_id = admin_session.admin_id
    admin_session.revoke_reason = "Admin logged out."
    admin_session.last_used_at = current_time

    db.commit()

    clear_admin_cookies(response)

    return {
        "message": "Admin logged out successfully."
    }
