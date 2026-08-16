from database import SessionLocal
from models import WebsiteSetting


def seed_website_settings() -> None:
    db = SessionLocal()

    try:
        existing_settings = db.get(
            WebsiteSetting,
            1,
        )

        if existing_settings:
            print(
                "Website settings already exist."
            )
            return

        settings = WebsiteSetting(
            id=1,
            store_name="SMART CASH & CARRY",
            logo_url=None,
            announcement_primary=(
                "Free delivery on orders above Rs. 3,000"
            ),
            announcement_secondary=(
                "Fresh prices - Reliable delivery"
            ),
            announcement_is_active=True,
        )

        db.add(settings)
        db.commit()

        print(
            "Default website settings created successfully."
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_website_settings()