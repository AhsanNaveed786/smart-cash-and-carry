from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from database import get_db
from schemas import (
    PriceImportApplyRequest,
    PriceImportPreviewResponse,
)
from services.excel_price_service import (
    apply_branch_price_import,
    apply_master_price_import,
    create_branch_price_preview,
    create_master_price_preview,
    get_price_import_preview,
)


router = APIRouter(
    prefix="/api/price-imports",
    tags=["Excel Price Imports"],
)


@router.post(
    "/master/preview",
    response_model=PriceImportPreviewResponse,
)
async def upload_master_price_preview(
    excel_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    return await create_master_price_preview(
        db=db,
        excel_file=excel_file,
    )


@router.post(
    "/master/{batch_id}/apply",
    response_model=PriceImportPreviewResponse,
)
def confirm_master_price_import(
    batch_id: int,
    confirmation: PriceImportApplyRequest,
    db: Session = Depends(get_db),
):
    return apply_master_price_import(
        db=db,
        batch_id=batch_id,
    )


@router.post(
    "/branch/{branch_id}/preview",
    response_model=PriceImportPreviewResponse,
)
async def upload_branch_price_preview(
    branch_id: int,
    excel_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    return await create_branch_price_preview(
        db=db,
        branch_id=branch_id,
        excel_file=excel_file,
    )


@router.post(
    "/branch/{batch_id}/apply",
    response_model=PriceImportPreviewResponse,
)
def confirm_branch_price_import(
    batch_id: int,
    confirmation: PriceImportApplyRequest,
    db: Session = Depends(get_db),
):
    return apply_branch_price_import(
        db=db,
        batch_id=batch_id,
    )


@router.get(
    "/{batch_id}",
    response_model=PriceImportPreviewResponse,
)
def view_price_import_preview(
    batch_id: int,
    db: Session = Depends(get_db),
):
    return get_price_import_preview(
        db=db,
        batch_id=batch_id,
    )