from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import (
    Category,
    Product,
    ProductImportBatch,
    ProductImportRow,
)
from services.product_service import (
    generate_unique_product_slug,
)


def apply_product_import(
    db: Session,
    batch_id: int,
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

        if batch.status in {
            "cancelled",
            "failed",
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This product import cannot be applied. "
                    f"Current status: {batch.status}."
                ),
            )

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

        if (
            pending_category_rows > 0
            or unconfirmed_ready_rows > 0
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": (
                        "Every valid product must have a confirmed "
                        "category before applying this import."
                    ),
                    "pending_category_rows": (
                        pending_category_rows
                    ),
                    "unconfirmed_ready_rows": (
                        unconfirmed_ready_rows
                    ),
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
                .order_by(
                    ProductImportRow.excel_row_number
                )
                .with_for_update()
            ).all()
        )

        if not selected_rows:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "No confirmed products are selected "
                    "for creation."
                ),
            )

        incomplete_rows = [
            import_row.excel_row_number
            for import_row in selected_rows
            if (
                not import_row.barcode
                or not import_row.item_name
                or import_row.uploaded_price is None
                or import_row.confirmed_category_id is None
            )
        ]

        if incomplete_rows:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": (
                        "Some selected rows contain incomplete data."
                    ),
                    "excel_rows": incomplete_rows[:50],
                },
            )

        selected_barcodes = [
            import_row.barcode
            for import_row in selected_rows
        ]

        if len(selected_barcodes) != len(
            set(selected_barcodes)
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Selected rows contain duplicate barcodes."
                ),
            )

        existing_products = list(
            db.scalars(
                select(Product)
                .where(
                    Product.barcode.in_(
                        selected_barcodes
                    )
                )
                .with_for_update()
            ).all()
        )

        if existing_products:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": (
                        "Some products were added after the "
                        "preview. No products were created. "
                        "Create a fresh Excel preview."
                    ),
                    "existing_barcodes": [
                        product.barcode
                        for product in existing_products[:50]
                    ],
                },
            )

        category_ids = {
            import_row.confirmed_category_id
            for import_row in selected_rows
            if import_row.confirmed_category_id is not None
        }

        valid_categories = list(
            db.scalars(
                select(Category)
                .where(
                    Category.id.in_(category_ids),
                    Category.is_active.is_(True),
                    Category.slug != "deals",
                )
                .with_for_update()
            ).all()
        )

        valid_category_ids = {
            category.id
            for category in valid_categories
        }

        invalid_category_ids = (
            category_ids - valid_category_ids
        )

        if invalid_category_ids:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": (
                        "Some confirmed categories are inactive, "
                        "missing or unsuitable for products."
                    ),
                    "category_ids": sorted(
                        invalid_category_ids
                    ),
                },
            )

        created_products = 0

        for import_row in selected_rows:
            product_name = import_row.item_name.strip()
            product_barcode = import_row.barcode.strip()

            product = Product(
                barcode=product_barcode,
                name=product_name,
                slug=generate_unique_product_slug(
                    db=db,
                    name=product_name,
                ),
                description=None,
                unit_size=None,
                master_price=import_row.uploaded_price,
                image_url=None,
                category_id=(
                    import_row.confirmed_category_id
                ),
                is_active=True,
            )

            db.add(product)

            import_row.status = "applied"
            created_products += 1

        unselected_rows = list(
            db.scalars(
                select(ProductImportRow)
                .where(
                    ProductImportRow.batch_id == batch_id,
                    ProductImportRow.status == "ready",
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

        db.commit()

        return {
            "batch_id": batch.id,
            "status": batch.status,
            "created_products": created_products,
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
                "A product barcode or slug conflict occurred. "
                "No products were created. Create a fresh preview."
            ),
        ) from error

    except Exception:
        db.rollback()
        raise