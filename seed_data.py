from sqlalchemy import select
from sqlalchemy.orm import Session

from database import SessionLocal
from models import Branch, Category


BRANCHES = [
    {
        "name": "Zafarwal",
        "code": "ZAFARWAL",
    },
    {
        "name": "Narowal",
        "code": "NAROWAL",
    },
    {
        "name": "Pasrur",
        "code": "PASRUR",
    },
    {
        "name": "Shakargarh",
        "code": "SHAKARGARH",
    },
    {
        "name": "Nurkot",
        "code": "NURKOT",
    },
]


CATEGORIES = [
    {
        "name": "Deals",
        "slug": "deals",
        "display_order": 1,
    },
    {
        "name": "Grocery",
        "slug": "grocery",
        "display_order": 2,
    },
    {
        "name": "Fruits",
        "slug": "fruits",
        "display_order": 3,
    },
    {
        "name": "Skin Care",
        "slug": "skin-care",
        "display_order": 4,
    },
    {
        "name": "Giftings",
        "slug": "giftings",
        "display_order": 5,
    },
]


def seed_branches(db: Session) -> None:
    for branch_data in BRANCHES:
        existing_branch = db.scalar(
            select(Branch).where(
                Branch.code == branch_data["code"]
            )
        )

        if existing_branch:
            print(
                f"Branch already exists: {branch_data['name']}"
            )
            continue

        branch = Branch(
            name=branch_data["name"],
            code=branch_data["code"],
            is_active=True,
        )

        db.add(branch)
        print(f"Branch created: {branch_data['name']}")


def seed_categories(db: Session) -> None:
    for category_data in CATEGORIES:
        existing_category = db.scalar(
            select(Category).where(
                Category.slug == category_data["slug"]
            )
        )

        if existing_category:
            print(
                f"Category already exists: "
                f"{category_data['name']}"
            )
            continue

        category = Category(
            name=category_data["name"],
            slug=category_data["slug"],
            display_order=category_data["display_order"],
            is_active=True,
        )

        db.add(category)
        print(f"Category created: {category_data['name']}")


def run_seed() -> None:
    db = SessionLocal()

    try:
        seed_branches(db)
        seed_categories(db)

        db.commit()

        print("\nDatabase seed completed successfully.")

    except Exception as error:
        db.rollback()
        print(f"\nSeed failed: {error}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    run_seed()