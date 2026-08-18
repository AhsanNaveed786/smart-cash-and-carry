from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Category, Product, ProductImportBatch, ProductImportRow
from services.category_service import generate_unique_slug
from services.product_service import generate_unique_product_slug


def _resolve_new_categories(
    db: Session,
    selected_rows: list[ProductImportRow],
) -> list[str]:
    requested_names: dict[str, str] = {}
    for row in selected_rows:
        if row.confirmed_category_name:
            clean_name = " ".join(
                row.confirmed_category_name.strip().split()
            )
            requested_names.setdefault(clean_name.casefold(), clean_name)

    if not requested_names:
        return []

    categories_by_name = {
        category.name.casefold(): category
        for category in db.scalars(
            select(Category).where(
                func.lower(Category.name).in_(
                    [name.lower() for name in requested_names.values()]
                )
            )
        ).all()
    }
    next_order = (
        db.scalar(select(func.max(Category.display_order))) or 0
    ) + 1
    created_names: list[str] = []

    for key, requested_name in requested_names.items():
        category = categories_by_name.get(key)
        if category is None:
            category = Category(
                name=requested_name,
                slug=generate_unique_slug(db=db, name=requested_name),
                description="Created from a reviewed product import.",
                image_url=None,
                display_order=next_order,
                is_active=True,
            )
            next_order += 1
            db.add(category)
            db.flush()
            categories_by_name[key] = category
            created_names.append(category.name)
        elif category.slug == "deals":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Deals cannot be used as a product category.",
            )
        elif not category.is_active:
            category.is_active = True

    for row in selected_rows:
        if row.confirmed_category_name:
            key = " ".join(
                row.confirmed_category_name.strip().split()
            ).casefold()
            row.confirmed_category_id = categories_by_name[key].id

    return created_names


def apply_product_import(
    db: Session,
    batch_id: int,
    commit_changes: bool = True,
) -> dict:
    try:
        batch = db.scalar(
            select(ProductImportBatch)
            .where(ProductImportBatch.id == batch_id)
            .with_for_update()
        )
        if not batch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product import batch not found.",
            )
        if batch.status == "applied":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This product import has already been applied.",
            )
        if batch.status in {"cancelled", "failed"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This product import cannot be applied.",
            )

        selected_pending = db.scalar(
            select(func.count(ProductImportRow.id)).where(
                ProductImportRow.batch_id == batch_id,
                ProductImportRow.apply_selected.is_(True),
                or_(
                    ProductImportRow.status == "pending_category",
                    (
                        (ProductImportRow.status == "ready")
                        & ProductImportRow.confirmed_category_id.is_(None)
                        & ProductImportRow.confirmed_category_name.is_(None)
                    ),
                ),
            )
        ) or 0
        if selected_pending:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": (
                        "Every selected product must have a reviewed "
                        "category before final confirmation."
                    ),
                    "remaining_selected_rows": selected_pending,
                },
            )

        selected_rows = list(
            db.scalars(
                select(ProductImportRow)
                .where(
                    ProductImportRow.batch_id == batch_id,
                    ProductImportRow.status == "ready",
                    ProductImportRow.apply_selected.is_(True),
                )
                .order_by(ProductImportRow.excel_row_number)
                .with_for_update()
            ).all()
        )
        incomplete_rows = [
            row.excel_row_number
            for row in selected_rows
            if (
                not row.barcode
                or not row.item_name
                or row.uploaded_price is None
                or (
                    row.confirmed_category_id is None
                    and not row.confirmed_category_name
                )
            )
        ]
        if incomplete_rows:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Some selected rows contain incomplete data.",
                    "excel_rows": incomplete_rows[:50],
                },
            )

        selected_barcodes = [row.barcode for row in selected_rows]
        if len(selected_barcodes) != len(set(selected_barcodes)):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Selected rows contain duplicate barcodes.",
            )
        if selected_barcodes:
            existing_products = list(
                db.scalars(
                    select(Product)
                    .where(Product.barcode.in_(selected_barcodes))
                    .with_for_update()
                ).all()
            )
            if existing_products:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": (
                            "Some products were added after preview. "
                            "Create a fresh preview."
                        ),
                        "existing_barcodes": [
                            product.barcode
                            for product in existing_products[:50]
                        ],
                    },
                )

        created_categories = _resolve_new_categories(db, selected_rows)
        category_ids = {
            row.confirmed_category_id
            for row in selected_rows
            if row.confirmed_category_id is not None
        }
        valid_category_ids = set()
        if category_ids:
            valid_category_ids = set(
                db.scalars(
                    select(Category.id).where(
                        Category.id.in_(category_ids),
                        Category.is_active.is_(True),
                        Category.slug != "deals",
                    )
                ).all()
            )
        if category_ids - valid_category_ids:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A confirmed category is missing or inactive.",
            )

        for import_row in selected_rows:
            product_name = import_row.item_name.strip()
            db.add(
                Product(
                    barcode=import_row.barcode.strip(),
                    name=product_name,
                    slug=generate_unique_product_slug(db, product_name),
                    description=None,
                    unit_size=None,
                    master_price=import_row.uploaded_price,
                    image_url=None,
                    category_id=import_row.confirmed_category_id,
                    is_active=True,
                )
            )
            import_row.status = "applied"

        unselected_rows = list(
            db.scalars(
                select(ProductImportRow)
                .where(
                    ProductImportRow.batch_id == batch_id,
                    ProductImportRow.status.in_(
                        {"pending_category", "ready"}
                    ),
                    ProductImportRow.apply_selected.is_(False),
                )
                .with_for_update()
            ).all()
        )
        for import_row in unselected_rows:
            import_row.status = "skipped"

        applied_at = datetime.now(timezone.utc)
        batch.status = "applied"
        batch.applied_at = applied_at

        if commit_changes:
            db.commit()
        else:
            db.flush()

        return {
            "batch_id": batch.id,
            "status": batch.status,
            "created_products": len(selected_rows),
            "created_categories": created_categories,
            "skipped_rows": len(unselected_rows),
            "applied_at": applied_at,
        }
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A product barcode, category or slug conflict occurred. "
                "No changes were saved."
            ),
        ) from error
    except Exception:
        db.rollback()
        raise
