from getpass import getpass

from pydantic import EmailStr, TypeAdapter
from sqlalchemy import select

from database import SessionLocal
from models import Admin
from services.password_service import hash_password


email_validator = TypeAdapter(EmailStr)


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


def create_super_admin() -> None:
    db = SessionLocal()

    try:
        existing_admin = db.scalar(
            select(Admin).limit(1)
        )

        if existing_admin:
            print(
                "A Super Admin already exists. "
                "A second admin was not created."
            )
            return

        full_name = input(
            "Super Admin full name: "
        ).strip()

        if len(full_name) < 2 or len(full_name) > 100:
            print(
                "Full name must contain between "
                "2 and 100 characters."
            )
            return

        raw_email = input(
            "Super Admin email: "
        ).strip().lower()

        try:
            email = str(
                email_validator.validate_python(
                    raw_email
                )
            ).lower()

        except ValueError:
            print("Please enter a valid email address.")
            return

        password = getpass(
            "Create Super Admin password: "
        )

        password_errors = validate_password(password)

        if password_errors:
            print("\nPassword was not accepted:")

            for error in password_errors:
                print(f"- {error}")

            return

        password_confirmation = getpass(
            "Confirm Super Admin password: "
        )

        if password != password_confirmation:
            print("Passwords do not match.")
            return

        admin = Admin(
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            is_active=True,
        )

        db.add(admin)
        db.commit()

        print(
            "\nSuper Admin created successfully."
        )
        print(f"Login email: {email}")
        print(
            "Password is securely hashed and was "
            "not saved as plain text."
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    create_super_admin()