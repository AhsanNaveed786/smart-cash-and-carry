from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from models import (
    Admin,
    Branch,
    BranchPriceOverride,
    Product,
)
from services.rbac_service import (
    create_admin_audit_log,
    ensure_admin_branch_access,
    get_admin_branch_ids,
)


def get_product_or_404(
    db: Session,
    product_id: int,
) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    return product


def get_active_admin_branches(
    db: Session,
    admin: Admin,
) -> list[Branch]:
    statement = select(Branch).where(
        Branch.is_active.is_(True)
    )
    if admin.role != "super_admin":
        allowed_ids = get_admin_branch_ids(
            db=db,
            admin=admin,
        )
        if not allowed_ids:
            return []
        statement = statement.where(
            Branch.id.in_(allowed_ids)
        )
    return list(
        db.scalars(statement.order_by(Branch.id)).all()
    )


def build_product_price_row(
    product: Product,
    branches: list[Branch],
) -> dict:
    overrides = {
        override.branch_id: Decimal(override.override_price)
        for override in product.price_overrides
    }
    master_price = Decimal(product.master_price)
    branch_prices = []
    different_branch_names = []

    for branch in branches:
        override_price = overrides.get(branch.id)
        effective_price = (
            override_price
            if override_price is not None
            else master_price
        )
        differs = effective_price != master_price
        if differs:
            different_branch_names.append(branch.name)
        branch_prices.append(
            {
                "branch_id": branch.id,
                "branch_name": branch.name,
                "master_price": master_price,
                "override_price": override_price,
                "effective_price": effective_price,
                "price_source": (
                    "branch_override"
                    if override_price is not None
                    else "master"
                ),
                "differs_from_master": differs,
            }
        )

    unique_prices = {
        item["effective_price"] for item in branch_prices
    }

    return {
        "product_id": product.id,
        "barcode": product.barcode,
        "product_name": product.name,
        "category_id": product.category_id,
        "category_name": product.category.name,
        "master_price": master_price,
        "is_active": product.is_active,
        "same_price_on_all_branches": len(unique_prices) <= 1,
        "different_branch_names": different_branch_names,
        "branch_prices": branch_prices,
    }


def list_admin_product_prices(
    db: Session,
    admin: Admin,
    search: str | None = None,
    active_only: bool = False,
    different_only: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> dict:
    branches = get_active_admin_branches(
        db=db,
        admin=admin,
    )
    conditions = []

    if search:
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(
                Product.name.ilike(pattern),
                Product.barcode.ilike(pattern),
            )
        )
    if active_only:
        conditions.append(Product.is_active.is_(True))

    total_statement = select(func.count(Product.id))
    statement = (
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.price_overrides),
        )
        .order_by(Product.name, Product.id)
    )

    if conditions:
        total_statement = total_statement.where(*conditions)
        statement = statement.where(*conditions)

    if different_only:
        products = list(db.scalars(statement).all())
        rows = [
            build_product_price_row(product, branches)
            for product in products
        ]
        rows = [
            row
            for row in rows
            if not row["same_price_on_all_branches"]
        ]
        return {
            "total": len(rows),
            "skip": skip,
            "limit": limit,
            "items": rows[skip:skip + limit],
        }

    products = list(
        db.scalars(
            statement.offset(skip).limit(limit)
        ).all()
    )
    return {
        "total": db.scalar(total_statement) or 0,
        "skip": skip,
        "limit": limit,
        "items": [
            build_product_price_row(product, branches)
            for product in products
        ],
    }


def get_admin_product_price(
    db: Session,
    admin: Admin,
    product_id: int,
) -> dict:
    product = db.scalar(
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.price_overrides),
        )
        .where(Product.id == product_id)
    )
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    return build_product_price_row(
        product=product,
        branches=get_active_admin_branches(db, admin),
    )


def set_branch_product_price(
    db: Session,
    admin: Admin,
    branch_id: int,
    product_id: int,
    override_price: Decimal,
    ip_address: str | None = None,
) -> dict:
    ensure_admin_branch_access(
        db=db,
        admin=admin,
        branch_id=branch_id,
    )
    branch = db.scalar(
        select(Branch).where(
            Branch.id == branch_id,
            Branch.is_active.is_(True),
        )
    )
    if branch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active branch not found.",
        )
    product = get_product_or_404(db, product_id)

    try:
        price_override = db.scalar(
            select(BranchPriceOverride).where(
                BranchPriceOverride.branch_id == branch_id,
                BranchPriceOverride.product_id == product_id,
            )
        )
        previous_price = (
            Decimal(price_override.override_price)
            if price_override
            else None
        )
        if price_override is None:
            price_override = BranchPriceOverride(
                branch_id=branch_id,
                product_id=product_id,
                override_price=override_price,
            )
            db.add(price_override)
        else:
            price_override.override_price = override_price

        create_admin_audit_log(
            db=db,
            action="product.branch_price_updated",
            actor_admin_id=admin.id,
            details={
                "product_id": product.id,
                "branch_id": branch.id,
                "previous_override_price": (
                    str(previous_price)
                    if previous_price is not None
                    else None
                ),
                "new_override_price": str(override_price),
            },
            ip_address=ip_address,
        )
        db.commit()
        return {
            "message": "Branch product price updated.",
            "product_id": product.id,
            "branch_id": branch.id,
            "master_price": product.master_price,
            "override_price": override_price,
            "effective_price": override_price,
            "price_source": "branch_override",
        }
    except Exception:
        db.rollback()
        raise


def remove_branch_product_price(
    db: Session,
    admin: Admin,
    branch_id: int,
    product_id: int,
    ip_address: str | None = None,
) -> dict:
    ensure_admin_branch_access(
        db=db,
        admin=admin,
        branch_id=branch_id,
    )
    product = get_product_or_404(db, product_id)
    price_override = db.scalar(
        select(BranchPriceOverride).where(
            BranchPriceOverride.branch_id == branch_id,
            BranchPriceOverride.product_id == product_id,
        )
    )
    if price_override is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch price override not found.",
        )

    try:
        previous_price = str(price_override.override_price)
        db.delete(price_override)
        create_admin_audit_log(
            db=db,
            action="product.branch_price_removed",
            actor_admin_id=admin.id,
            details={
                "product_id": product.id,
                "branch_id": branch_id,
                "removed_override_price": previous_price,
            },
            ip_address=ip_address,
        )
        db.commit()
        return {
            "message": "Branch override removed; master price is active.",
            "product_id": product.id,
            "branch_id": branch_id,
            "master_price": product.master_price,
            "override_price": None,
            "effective_price": product.master_price,
            "price_source": "master",
        }
    except Exception:
        db.rollback()
        raise


def update_master_product_price(
    db: Session,
    super_admin: Admin,
    product_id: int,
    master_price: Decimal,
    ip_address: str | None = None,
) -> dict:
    if super_admin.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admin can update master prices.",
        )
    product = get_product_or_404(db, product_id)

    try:
        previous_price = Decimal(product.master_price)
        product.master_price = master_price
        create_admin_audit_log(
            db=db,
            action="product.master_price_updated",
            actor_admin_id=super_admin.id,
            details={
                "product_id": product.id,
                "previous_master_price": str(previous_price),
                "new_master_price": str(master_price),
            },
            ip_address=ip_address,
        )
        db.commit()
        return {
            "message": "Master product price updated.",
            "product_id": product.id,
            "branch_id": None,
            "master_price": master_price,
            "override_price": None,
            "effective_price": master_price,
            "price_source": "master",
        }
    except Exception:
        db.rollback()
        raise
