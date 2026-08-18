from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from models import Category, ProductImportRow
from schemas import ProductImportCategoryConfirmRequest
from services.product_import_service import get_product_import_batch


BLOCKED_BATCH_STATUSES = {"applied", "cancelled", "failed"}


def validate_product_import_batch(db: Session, batch_id: int):
    batch = get_product_import_batch(db=db, batch_id=batch_id)
    if batch.status in BLOCKED_BATCH_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This product import can no longer be edited. "
                f"Current status: {batch.status}."
            ),
        )
    return batch


def get_import_category(db: Session, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found.",
        )
    if not category.is_active or category.slug == "deals":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select an active normal product category.",
        )
    return category


def normalize_new_category_name(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    if not 2 <= len(normalized) <= 120:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New category name must contain 2 to 120 characters.",
        )
    return normalized


def update_batch_progress(db: Session, batch) -> None:
    categorized_rows = db.scalar(
        select(func.count(ProductImportRow.id)).where(
            ProductImportRow.batch_id == batch.id,
            ProductImportRow.status == "ready",
            ProductImportRow.apply_selected.is_(True),
        )
    ) or 0
    pending_rows = db.scalar(
        select(func.count(ProductImportRow.id)).where(
            ProductImportRow.batch_id == batch.id,
            ProductImportRow.status == "pending_category",
            ProductImportRow.apply_selected.is_(True),
        )
    ) or 0
    batch.categorized_rows = categorized_rows
    batch.status = "categorized" if pending_rows == 0 else "preview"


def confirm_product_import_row_category(
    db: Session,
    batch_id: int,
    row_id: int,
    confirmation: ProductImportCategoryConfirmRequest,
) -> ProductImportRow:
    try:
        batch = validate_product_import_batch(db, batch_id)
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
        if import_row.status not in {"pending_category", "ready"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Category cannot be assigned to this row.",
            )

        import_row.apply_selected = confirmation.apply_selected
        if confirmation.apply_selected:
            if confirmation.confirmed_category_id is not None:
                category = get_import_category(
                    db, confirmation.confirmed_category_id
                )
                import_row.confirmed_category_id = category.id
                import_row.confirmed_category_name = None
            else:
                import_row.confirmed_category_id = None
                import_row.confirmed_category_name = (
                    normalize_new_category_name(
                        confirmation.confirmed_category_name
                    )
                )
            import_row.category_source = "manual"
            import_row.status = "ready"
            import_row.error_message = None

        update_batch_progress(db, batch)
        db.commit()
        db.refresh(import_row)
        return import_row
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


def confirm_all_ai_suggestions(db: Session, batch_id: int) -> dict:
    try:
        batch = validate_product_import_batch(db, batch_id)
        rows_to_confirm = list(
            db.scalars(
                select(ProductImportRow)
                .where(
                    ProductImportRow.batch_id == batch_id,
                    ProductImportRow.status == "ready",
                    ProductImportRow.apply_selected.is_(True),
                    ProductImportRow.confirmed_category_id.is_(None),
                    ProductImportRow.confirmed_category_name.is_(None),
                    or_(
                        ProductImportRow.suggested_category_id.is_not(None),
                        ProductImportRow.suggested_category_name.is_not(None),
                    ),
                )
                .order_by(ProductImportRow.excel_row_number)
                .with_for_update()
            ).all()
        )

        suggested_ids = {
            row.suggested_category_id
            for row in rows_to_confirm
            if row.suggested_category_id is not None
        }
        valid_ids = set()
        if suggested_ids:
            valid_ids = set(
                db.scalars(
                    select(Category.id).where(
                        Category.id.in_(suggested_ids),
                        Category.is_active.is_(True),
                        Category.slug != "deals",
                    )
                ).all()
            )
        if suggested_ids - valid_ids:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Some suggested categories are no longer active.",
            )

        for import_row in rows_to_confirm:
            import_row.confirmed_category_id = (
                import_row.suggested_category_id
            )
            import_row.confirmed_category_name = (
                normalize_new_category_name(
                    import_row.suggested_category_name
                )
                if import_row.suggested_category_name
                else None
            )
            import_row.category_source = "ai"

        db.flush()
        update_batch_progress(db, batch)

        pending_rows = db.scalar(
            select(func.count(ProductImportRow.id)).where(
                ProductImportRow.batch_id == batch_id,
                ProductImportRow.apply_selected.is_(True),
                or_(
                    ProductImportRow.status == "pending_category",
                    and_(
                        ProductImportRow.status == "ready",
                        ProductImportRow.confirmed_category_id.is_(None),
                        ProductImportRow.confirmed_category_name.is_(None),
                    ),
                ),
            )
        ) or 0
        selected_rows = db.scalar(
            select(func.count(ProductImportRow.id)).where(
                ProductImportRow.batch_id == batch_id,
                ProductImportRow.status == "ready",
                ProductImportRow.apply_selected.is_(True),
                or_(
                    ProductImportRow.confirmed_category_id.is_not(None),
                    ProductImportRow.confirmed_category_name.is_not(None),
                ),
            )
        ) or 0

        db.commit()
        return {
            "batch_id": batch.id,
            "confirmed_rows": len(rows_to_confirm),
            "selected_rows": selected_rows,
            "remaining_unconfirmed_rows": pending_rows,
            "batch_status": batch.status,
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
