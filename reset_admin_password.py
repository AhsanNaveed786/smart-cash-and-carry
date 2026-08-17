from datetime import datetime, timezone
from getpass import getpass

from sqlalchemy import select

from database import SessionLocal
from models import Admin, AdminSession
from services.password_service import hash_password


def validate_password(password: str) -> list[str]:
    errors = []

    if len(password) < 12:
        errors.append(
            "Password must contain at least 12 characters."
        )

    if len(password) > 128:
        errors.append(
            "Password cannot exceed 128 characters."
        )

    if not any(character.islower() for character in password):
        errors.append(
            "Password must contain a lowercase letter."
        )

    if not any(character.isupper() for character in password):
        errors.append(
            "Password must contain an uppercase letter."
        )

    if not any(character.isdigit() for character in password):
        errors.append(
            "Password must contain a number."
        )

    if not any(
        not character.isalnum()
        for character in password
    ):
        errors.append(
            "Password must contain a special character."
        )

    return errors


def reset_super_admin_password() -> None:
    email = input(
        "Super Admin email: "
    ).strip().lower()

    new_password = getpass(
        "Enter new password: "
    )

    password_errors = validate_password(
        new_password
    )

    if password_errors:
        print("\nPassword was not accepted:")

        for error in password_errors:
            print(f"- {error}")

        return

    password_confirmation = getpass(
        "Confirm new password: "
    )

    if new_password != password_confirmation:
        print("Passwords do not match.")
        return

    db = SessionLocal()

    try:
        admin = db.scalar(
            select(Admin).where(
                Admin.email == email,
                Admin.role == "super_admin",
            )
        )

        if admin is None:
            print(
                "Super Admin with this email was not found."
            )
            return

        admin.password_hash = hash_password(
            new_password
        )

        admin.is_active = True
        admin.login_allowed = True
        admin.login_allowed_from = None
        admin.login_allowed_until = None

        current_time = datetime.now(timezone.utc)

        active_sessions = db.scalars(
            select(AdminSession).where(
                AdminSession.admin_id == admin.id,
                AdminSession.revoked_at.is_(None),
            )
        ).all()

        for admin_session in active_sessions:
            admin_session.revoked_at = current_time
            admin_session.last_used_at = current_time
            admin_session.revoke_reason = (
                "Password reset"
            )

        db.commit()

        print(
            "\nSuper Admin password reset successfully."
        )
        print(
            "All previous login sessions were logged out."
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    reset_super_admin_password()