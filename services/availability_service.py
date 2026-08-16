from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from models import (
    Branch,
    Product,
    ProductAvailability,
)
from schemas import (
    ProductAvailabilityBulkUpdate,
    ProductAvailabilityUpdate,
)


def get_active_availability_branch(
    db: Session,
    branch_id: int,
) -> Branch:
    branch = db.get(
        Branch,
        branch_id,
    )

    if not branch or not branch.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active branch not found.",
        )

    return branch


def get_active_availability_product(
    db: Session,
    product_id: int,
) -> Product:
    product = db.get(
        Product,
        product_id,
    )

    if not product or not product.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active product not found.",
        )

    return product


def find_availability_record(
    db: Session,
    product_id: int,
    branch_id: int,
) -> ProductAvailability | None:
    return db.scalar(
        select(ProductAvailability).where(
            ProductAvailability.product_id
            == product_id,
            ProductAvailability.branch_id
            == branch_id,
        )
    )


def build_availability_response(
    product_id: int,
    branch_id: int,
    availability: ProductAvailability | None,
) -> dict[str, Any]:
    if availability:
        return {
            "availability_record_id": (
                availability.id
            ),
            "product_id": product_id,
            "branch_id": branch_id,
            "is_in_stock": (
                availability.is_in_stock
            ),
            "stock_message": (
                availability.stock_message
            ),
            "availability_source": (
                "branch_record"
            ),
        }

    return {
        "availability_record_id": None,
        "product_id": product_id,
        "branch_id": branch_id,
        "is_in_stock": True,
        "stock_message": None,
        "availability_source": "default",
    }


def get_product_availability(
    db: Session,
    product_id: int,
    branch_id: int,
) -> dict[str, Any]:
    get_active_availability_branch(
        db=db,
        branch_id=branch_id,
    )

    get_active_availability_product(
        db=db,
        product_id=product_id,
    )

    availability = find_availability_record(
        db=db,
        product_id=product_id,
        branch_id=branch_id,
    )

    return build_availability_response(
        product_id=product_id,
        branch_id=branch_id,
        availability=availability,
    )


def set_product_availability(
    db: Session,
    product_id: int,
    branch_id: int,
    availability_data: ProductAvailabilityUpdate,
) -> ProductAvailability:
    get_active_availability_branch(
        db=db,
        branch_id=branch_id,
    )

    get_active_availability_product(
        db=db,
        product_id=product_id,
    )

    try:
        availability = find_availability_record(
            db=db,
            product_id=product_id,
            branch_id=branch_id,
        )

        stock_message = (
            availability_data.stock_message.strip()
            if availability_data.stock_message
            else None
        )

        if availability:
            availability.is_in_stock = (
                availability_data.is_in_stock
            )
            availability.stock_message = (
                stock_message
            )

        else:
            availability = ProductAvailability(
                product_id=product_id,
                branch_id=branch_id,
                is_in_stock=(
                    availability_data.is_in_stock
                ),
                stock_message=stock_message,
            )

            db.add(availability)

        db.commit()
        db.refresh(availability)

        return availability

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


def set_bulk_product_availability(
    db: Session,
    availability_data: ProductAvailabilityBulkUpdate,
) -> list[ProductAvailability]:
    product_ids = availability_data.product_ids
    branch_ids = availability_data.branch_ids

    active_product_ids = set(
        db.scalars(
            select(Product.id).where(
                Product.id.in_(product_ids),
                Product.is_active.is_(True),
            )
        ).all()
    )

    missing_product_ids = (
        set(product_ids) - active_product_ids
    )

    if missing_product_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": (
                    "Some products are missing or inactive."
                ),
                "product_ids": sorted(
                    missing_product_ids
                ),
            },
        )

    active_branch_ids = set(
        db.scalars(
            select(Branch.id).where(
                Branch.id.in_(branch_ids),
                Branch.is_active.is_(True),
            )
        ).all()
    )

    missing_branch_ids = (
        set(branch_ids) - active_branch_ids
    )

    if missing_branch_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": (
                    "Some branches are missing or inactive."
                ),
                "branch_ids": sorted(
                    missing_branch_ids
                ),
            },
        )

    try:
        existing_records = db.scalars(
            select(ProductAvailability).where(
                ProductAvailability.product_id.in_(
                    product_ids
                ),
                ProductAvailability.branch_id.in_(
                    branch_ids
                ),
            )
        ).all()

        records_by_pair = {
            (
                record.product_id,
                record.branch_id,
            ): record
            for record in existing_records
        }

        saved_records = []

        stock_message = (
            availability_data.stock_message.strip()
            if availability_data.stock_message
            else None
        )

        for product_id in product_ids:
            for branch_id in branch_ids:
                record_key = (
                    product_id,
                    branch_id,
                )

                availability = (
                    records_by_pair.get(record_key)
                )

                if availability:
                    availability.is_in_stock = (
                        availability_data.is_in_stock
                    )
                    availability.stock_message = (
                        stock_message
                    )

                else:
                    availability = (
                        ProductAvailability(
                            product_id=product_id,
                            branch_id=branch_id,
                            is_in_stock=(
                                availability_data
                                .is_in_stock
                            ),
                            stock_message=stock_message,
                        )
                    )

                    db.add(availability)

                saved_records.append(availability)

        db.commit()

        for availability in saved_records:
            db.refresh(availability)

        return saved_records

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


def reset_product_availability(
    db: Session,
    product_id: int,
    branch_id: int,
) -> dict[str, Any]:
    get_active_availability_branch(
        db=db,
        branch_id=branch_id,
    )

    get_active_availability_product(
        db=db,
        product_id=product_id,
    )

    try:
        availability = find_availability_record(
            db=db,
            product_id=product_id,
            branch_id=branch_id,
        )

        if availability:
            db.delete(availability)
            db.commit()

        return build_availability_response(
            product_id=product_id,
            branch_id=branch_id,
            availability=None,
        )

    except Exception:
        db.rollback()
        raise


def get_branch_product_availability(
    db: Session,
    branch_id: int,
    category_id: int | None = None,
    in_stock: bool | None = None,
    skip: int = 0,
    limit: int = 50,
) -> dict[str, Any]:
    get_active_availability_branch(
        db=db,
        branch_id=branch_id,
    )

    statement = (
        select(
            Product,
            ProductAvailability,
        )
        .outerjoin(
            ProductAvailability,
            and_(
                ProductAvailability.product_id
                == Product.id,
                ProductAvailability.branch_id
                == branch_id,
            ),
        )
        .where(
            Product.is_active.is_(True)
        )
        .order_by(
            Product.name,
            Product.id,
        )
    )

    if category_id is not None:
        statement = statement.where(
            Product.category_id == category_id
        )

    records = list(
        db.execute(statement).all()
    )

    items = []

    for product, availability in records:
        availability_data = (
            build_availability_response(
                product_id=product.id,
                branch_id=branch_id,
                availability=availability,
            )
        )

        if (
            in_stock is not None
            and availability_data["is_in_stock"]
            is not in_stock
        ):
            continue

        items.append(
            {
                **availability_data,
                "barcode": product.barcode,
                "product_name": product.name,
                "category_id": product.category_id,
                "image_url": product.image_url,
            }
        )

    total = len(items)

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items[skip : skip + limit],
    }