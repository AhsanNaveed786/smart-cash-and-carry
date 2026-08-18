from collections import Counter
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from models import (
    ProductImportBatch,
    ProductImportRow,
)
from services.excel_price_service import (
    MAXIMUM_FILE_SIZE,
    extract_excel_rows,
    get_products_by_barcodes,
)


ALLOWED_ROW_STATUSES = {
    "invalid",
    "duplicate_file",
    "already_exists",
    "pending_category",
    "ready",
    "applied",
    "skipped",
}


def get_product_import_batch(
    db: Session,
    batch_id: int,
) -> ProductImportBatch:
    batch = db.get(ProductImportBatch, batch_id)

    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product import preview not found.",
        )

    return batch


def get_product_import_rows(
    db: Session,
    batch_id: int,
    row_status: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> dict[str, Any]:
    get_product_import_batch(
        db=db,
        batch_id=batch_id,
    )

    filters = [
        ProductImportRow.batch_id == batch_id
    ]

    if row_status:
        if row_status not in ALLOWED_ROW_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid product import row status.",
            )

        filters.append(
            ProductImportRow.status == row_status
        )

    rows_statement = (
        select(ProductImportRow)
        .where(*filters)
        .order_by(
            ProductImportRow.excel_row_number
        )
        .offset(skip)
        .limit(limit)
    )

    count_statement = (
        select(func.count(ProductImportRow.id))
        .where(*filters)
    )

    rows = list(
        db.scalars(rows_statement).all()
    )

    total = db.scalar(count_statement) or 0

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": rows,
    }


def update_product_import_row_selection(
    db: Session,
    batch_id: int,
    row_ids: list[int],
    apply_selected: bool,
) -> dict[str, Any]:
    batch = get_product_import_batch(db, batch_id)

    if batch.status in {"applied", "cancelled", "failed"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This product import can no longer be edited.",
        )

    unique_ids = set(row_ids)
    rows = list(
        db.scalars(
            select(ProductImportRow)
            .where(
                ProductImportRow.batch_id == batch_id,
                ProductImportRow.id.in_(unique_ids),
                ProductImportRow.status.in_(
                    {"pending_category", "ready"}
                ),
            )
            .with_for_update()
        ).all()
    )

    if len(rows) != len(unique_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "One or more selected rows are missing or cannot "
                "be reviewed."
            ),
        )

    for import_row in rows:
        import_row.apply_selected = apply_selected

    db.commit()

    return get_product_import_review_summary(db, batch_id)


def get_product_import_review_summary(
    db: Session,
    batch_id: int,
) -> dict[str, Any]:
    batch = get_product_import_batch(db, batch_id)

    def count_rows(*filters: Any) -> int:
        return db.scalar(
            select(func.count(ProductImportRow.id)).where(
                ProductImportRow.batch_id == batch_id,
                *filters,
            )
        ) or 0

    selected_rows = count_rows(
        ProductImportRow.apply_selected.is_(True),
        ProductImportRow.status.in_(
            {"pending_category", "ready"}
        ),
    )
    categorized_rows = count_rows(
        ProductImportRow.apply_selected.is_(True),
        ProductImportRow.status == "ready",
    )
    pending_rows = count_rows(
        ProductImportRow.apply_selected.is_(True),
        ProductImportRow.status == "pending_category",
    )
    existing_category_rows = count_rows(
        ProductImportRow.apply_selected.is_(True),
        ProductImportRow.status == "ready",
        or_(
            ProductImportRow.confirmed_category_id.is_not(None),
            ProductImportRow.suggested_category_id.is_not(None),
        ),
    )
    new_category_rows = count_rows(
        ProductImportRow.apply_selected.is_(True),
        ProductImportRow.status == "ready",
        or_(
            ProductImportRow.confirmed_category_name.is_not(None),
            ProductImportRow.suggested_category_name.is_not(None),
        ),
    )
    invalid_rows = count_rows(
        ProductImportRow.status.in_(
            {"invalid", "duplicate_file", "already_exists"}
        )
    )

    progress = (
        round((categorized_rows / selected_rows) * 100, 2)
        if selected_rows
        else 100.0
    )

    return {
        "batch_id": batch.id,
        "total_rows": batch.total_rows,
        "selected_rows": selected_rows,
        "categorized_rows": categorized_rows,
        "pending_rows": pending_rows,
        "existing_category_rows": existing_category_rows,
        "new_category_rows": new_category_rows,
        "invalid_rows": invalid_rows,
        "progress_percentage": progress,
    }


async def create_product_import_preview(
    db: Session,
    excel_file: UploadFile,
) -> ProductImportBatch:
    try:
        original_filename = Path(
            excel_file.filename or "product-import.xlsx"
        ).name

        file_extension = Path(
            original_filename
        ).suffix.lower()

        if file_extension not in {".xlsx", ".xls"}:
            raise HTTPException(
                status_code=(
                    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
                ),
                detail=(
                    "Only .xlsx and .xls Excel files are supported."
                ),
            )

        file_content = await excel_file.read(
            MAXIMUM_FILE_SIZE + 1
        )

        if not file_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded Excel file is empty.",
            )

        if len(file_content) > MAXIMUM_FILE_SIZE:
            raise HTTPException(
                status_code=(
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                ),
                detail="Excel file size cannot exceed 25 MB.",
            )

        extracted_rows = extract_excel_rows(
            file_content=file_content,
            file_extension=file_extension,
        )

        if not extracted_rows:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No product rows were found in the Excel file.",
            )

        barcode_counts = Counter(
            row["barcode"]
            for row in extracted_rows
            if row["barcode"]
        )

        database_lookup_barcodes = {
            row["barcode"]
            for row in extracted_rows
            if (
                row["barcode"]
                and row["item_name"]
                and row["uploaded_price"] is not None
            )
        }

        existing_products = get_products_by_barcodes(
            db=db,
            barcodes=database_lookup_barcodes,
        )

        batch = ProductImportBatch(
            original_filename=original_filename[:255],
            status="preview",
            total_rows=len(extracted_rows),
            valid_rows=0,
            invalid_rows=0,
            categorized_rows=0,
        )

        db.add(batch)
        db.flush()

        valid_rows = 0
        invalid_rows = 0

        for extracted_row in extracted_rows:
            barcode = extracted_row["barcode"]
            item_name = extracted_row["item_name"]
            uploaded_price = extracted_row["uploaded_price"]

            row_status = "invalid"
            error_message = None

            validation_errors = []

            if barcode is None:
                validation_errors.append(
                    "Invalid or missing barcode."
                )

            if item_name is None:
                validation_errors.append(
                    "Invalid or missing item name."
                )

            if uploaded_price is None:
                validation_errors.append(
                    "Invalid or missing price."
                )

            if validation_errors:
                row_status = "invalid"
                error_message = " ".join(
                    validation_errors
                )
                invalid_rows += 1

            elif barcode_counts[barcode] > 1:
                row_status = "duplicate_file"
                error_message = (
                    "This barcode appears more than once "
                    "in the uploaded file."
                )
                invalid_rows += 1

            elif barcode in existing_products:
                row_status = "already_exists"
                error_message = (
                    "A product with this barcode already "
                    "exists in the database."
                )
                invalid_rows += 1

            else:
                row_status = "pending_category"
                valid_rows += 1

            import_row = ProductImportRow(
                batch_id=batch.id,
                excel_row_number=(
                    extracted_row["excel_row_number"]
                ),
                barcode=barcode,
                item_name=item_name,
                uploaded_price=uploaded_price,
                suggested_category_id=None,
                confirmed_category_id=None,
                category_confidence=None,
                category_source=None,
                ai_reason=None,
                status=row_status,
                apply_selected=(
                    row_status == "pending_category"
                ),
                error_message=error_message,
            )

            db.add(import_row)

        batch.valid_rows = valid_rows
        batch.invalid_rows = invalid_rows

        db.commit()
        db.refresh(batch)

        return batch

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise

    finally:
        await excel_file.close()
