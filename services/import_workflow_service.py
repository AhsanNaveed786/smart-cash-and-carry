from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import PriceImportBatch, PriceImportRow
from services.excel_price_service import apply_master_price_import
from services.product_import_apply_service import apply_product_import


def confirm_master_import_workflow(
    db: Session,
    batch_id: int,
) -> dict:
    batch = db.scalar(
        select(PriceImportBatch)
        .where(PriceImportBatch.id == batch_id)
        .with_for_update()
    )
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Master import preview not found.",
        )
    if batch.import_scope != "master":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This is not a master import.",
        )

    updated_prices = db.scalar(
        select(func.count(PriceImportRow.id)).where(
            PriceImportRow.batch_id == batch_id,
            PriceImportRow.status == "changed",
            PriceImportRow.apply_selected.is_(True),
        )
    ) or 0
    product_batch_id = batch.product_import_batch_id

    try:
        apply_master_price_import(
            db=db,
            batch_id=batch_id,
            commit_changes=False,
        )

        product_result = {
            "created_products": 0,
            "created_categories": [],
            "skipped_rows": 0,
        }
        if product_batch_id is not None:
            product_result = apply_product_import(
                db=db,
                batch_id=product_batch_id,
                commit_changes=False,
            )

        db.commit()
        return {
            "price_batch_id": batch_id,
            "product_batch_id": product_batch_id,
            "updated_prices": updated_prices,
            "unchanged_prices": batch.unchanged_rows,
            "created_products": product_result["created_products"],
            "created_categories": product_result["created_categories"],
            "skipped_products": product_result["skipped_rows"],
            "status": "applied",
        }
    except Exception:
        db.rollback()
        raise
