from sqlalchemy import select
from sqlalchemy.orm import Session

from database import Base, engine
import models
from models import Admin
from services.rbac_service import seed_permission_catalog


def main() -> None:
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        seed_permission_catalog(db)

        super_admin = db.scalar(
            select(Admin).where(
                Admin.role == "super_admin"
            )
        )

        if super_admin:
            print(
                "RBAC permissions seeded. "
                f"Super Admin: {super_admin.email}"
            )
            return

        first_admin = db.scalar(
            select(Admin).order_by(
                Admin.created_at,
                Admin.id,
            )
        )

        if first_admin is None:
            print(
                "RBAC permissions seeded, but no existing admin was found. "
                "Create the first admin with your existing admin seed flow, "
                "then run this file again."
            )
            return

        first_admin.role = "super_admin"
        first_admin.is_active = True
        first_admin.login_allowed = True
        first_admin.login_allowed_from = None
        first_admin.login_allowed_until = None
        db.commit()

        print(
            "RBAC permissions seeded. Existing admin promoted to "
            f"Super Admin: {first_admin.email}"
        )


if __name__ == "__main__":
    main()
