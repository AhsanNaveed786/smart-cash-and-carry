from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from database import get_db
from dependencies.admin_access import (
    permission_required,
    require_selected_branch_access,
)
from models import Admin, PriceImportBatch
from schemas import (
    ImportRowSelectionUpdate,
    MasterImportConfirmResponse,
    PriceImportApplyRequest,
    PriceImportPreviewResponse,
)
from services.excel_price_service import (
    apply_branch_price_import,
    apply_master_price_import,
    create_branch_price_preview,
    create_master_price_preview,
    get_price_import_preview,
    update_price_import_row_selection,
)
from services.import_workflow_service import (
    confirm_master_import_workflow,
)


router = APIRouter(
    prefix="/api/price-imports",
    tags=["Excel Price Imports"],
    dependencies=[
        Depends(permission_required("imports.manage"))
    ],
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
    _admin: Admin = Depends(require_selected_branch_access),
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
    admin: Admin = Depends(
        permission_required("imports.manage")
    ),
    db: Session = Depends(get_db),
):
    batch = db.get(PriceImportBatch, batch_id)
    if batch and batch.branch_id is not None:
        from services.rbac_service import ensure_admin_branch_access

        ensure_admin_branch_access(db, admin, batch.branch_id)
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


@router.post(
    "/master/{batch_id}/confirm-all",
    response_model=MasterImportConfirmResponse,
)
def confirm_all_master_import_changes(
    batch_id: int,
    confirmation: PriceImportApplyRequest,
    db: Session = Depends(get_db),
):
    return confirm_master_import_workflow(
        db=db,
        batch_id=batch_id,
    )


@router.patch(
    "/{batch_id}/rows/selection",
    response_model=PriceImportPreviewResponse,
)
def change_price_row_selection(
    batch_id: int,
    selection: ImportRowSelectionUpdate,
    db: Session = Depends(get_db),
):
    return update_price_import_row_selection(
        db=db,
        batch_id=batch_id,
        row_ids=selection.row_ids,
        apply_selected=selection.apply_selected,
    )
