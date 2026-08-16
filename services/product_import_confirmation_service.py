from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import (
    Category,
    ProductImportRow,
)
from schemas import ProductImportCategoryConfirmRequest
from services.product_import_service import (
    get_product_import_batch,
)


BLOCKED_BATCH_STATUSES = {
    "applied",
    "cancelled",
    "failed",
}


def validate_product_import_batch(
    db: Session,
    batch_id: int,
):
    batch = get_product_import_batch(
        db=db,
        batch_id=batch_id,
    )

    if batch.status in BLOCKED_BATCH_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This product import can no longer be edited. "
                f"Current status: {batch.status}."
            ),
        )

    return batch


def get_import_category(
    db: Session,
    category_id: int,
) -> Category:
    category = db.get(Category, category_id)

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found.",
        )

    if not category.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive category cannot be selected.",
        )

    if category.slug == "deals":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Deals is not a product category. "
                "Select a normal product category."
            ),
        )

    return category


def confirm_product_import_row_category(
    db: Session,
    batch_id: int,
    row_id: int,
    confirmation: ProductImportCategoryConfirmRequest,
) -> ProductImportRow:
    try:
        batch = validate_product_import_batch(
            db=db,
            batch_id=batch_id,
        )

        import_row = db.scalar(
            select(ProductImportRow)
            .where(
                ProductImportRow.id == row_id,
                ProductImportRow.batch_id == batch_id,
            )
            .with_for_update()
        )

        if not import_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product import row not found.",
            )

        if import_row.status not in {
            "pending_category",
            "ready",
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Category cannot be assigned to this row. "
                    f"Current status: {import_row.status}."
                ),
            )

        category = get_import_category(
            db=db,
            category_id=(
                confirmation.confirmed_category_id
            ),
        )

        import_row.confirmed_category_id = category.id
        import_row.category_source = "manual"
        import_row.apply_selected = (
            confirmation.apply_selected
        )
        import_row.status = "ready"
        import_row.error_message = None

        categorized_rows = db.scalar(
            select(func.count(ProductImportRow.id))
            .where(
                ProductImportRow.batch_id == batch_id,
                ProductImportRow.status == "ready",
            )
        ) or 0

        pending_rows = db.scalar(
            select(func.count(ProductImportRow.id))
            .where(
                ProductImportRow.batch_id == batch_id,
                ProductImportRow.status
                == "pending_category",
            )
        ) or 0

        batch.categorized_rows = categorized_rows

        if pending_rows == 0:
            batch.status = "categorized"
        else:
            batch.status = "preview"

        db.commit()
        db.refresh(import_row)

        return import_row

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


def confirm_all_ai_suggestions(
    db: Session,
    batch_id: int,
) -> dict:
    try:
        batch = validate_product_import_batch(
            db=db,
            batch_id=batch_id,
        )

        rows_to_confirm = list(
            db.scalars(
                select(ProductImportRow)
                .where(
                    ProductImportRow.batch_id == batch_id,
                    ProductImportRow.status == "ready",
                    ProductImportRow.suggested_category_id
                    .is_not(None),
                    ProductImportRow.confirmed_category_id
                    .is_(None),
                )
                .order_by(
                    ProductImportRow.excel_row_number
                )
                .with_for_update()
            ).all()
        )

        suggested_category_ids = {
            import_row.suggested_category_id
            for import_row in rows_to_confirm
            if import_row.suggested_category_id is not None
        }

        valid_category_ids: set[int] = set()

        if suggested_category_ids:
            valid_category_ids = set(
                db.scalars(
                    select(Category.id).where(
                        Category.id.in_(
                            suggested_category_ids
                        ),
                        Category.is_active.is_(True),
                        Category.slug != "deals",
                    )
                ).all()
            )

        invalid_category_ids = (
            suggested_category_ids - valid_category_ids
        )

        if invalid_category_ids:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": (
                        "Some AI-suggested categories are no "
                        "longer available. Correct those rows "
                        "manually before confirmation."
                    ),
                    "category_ids": sorted(
                        invalid_category_ids
                    ),
                },
            )

        for import_row in rows_to_confirm:
            import_row.confirmed_category_id = (
                import_row.suggested_category_id
            )
            import_row.category_source = "ai"
            import_row.apply_selected = True

        db.flush()

        pending_category_rows = db.scalar(
            select(func.count(ProductImportRow.id))
            .where(
                ProductImportRow.batch_id == batch_id,
                ProductImportRow.status
                == "pending_category",
            )
        ) or 0

        unconfirmed_ready_rows = db.scalar(
            select(func.count(ProductImportRow.id))
            .where(
                ProductImportRow.batch_id == batch_id,
                ProductImportRow.status == "ready",
                ProductImportRow.confirmed_category_id
                .is_(None),
            )
        ) or 0

        selected_rows = db.scalar(
            select(func.count(ProductImportRow.id))
            .where(
                ProductImportRow.batch_id == batch_id,
                ProductImportRow.status == "ready",
                ProductImportRow.apply_selected.is_(True),
                ProductImportRow.confirmed_category_id
                .is_not(None),
            )
        ) or 0

        categorized_rows = db.scalar(
            select(func.count(ProductImportRow.id))
            .where(
                ProductImportRow.batch_id == batch_id,
                ProductImportRow.status == "ready",
            )
        ) or 0

        remaining_unconfirmed_rows = (
            pending_category_rows
            + unconfirmed_ready_rows
        )

        batch.categorized_rows = categorized_rows

        if pending_category_rows == 0:
            batch.status = "categorized"
        else:
            batch.status = "preview"

        db.commit()

        return {
            "batch_id": batch.id,
            "confirmed_rows": len(rows_to_confirm),
            "selected_rows": selected_rows,
            "remaining_unconfirmed_rows": (
                remaining_unconfirmed_rows
            ),
            "batch_status": batch.status,
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise