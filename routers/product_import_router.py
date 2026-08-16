from fastapi import (
    APIRouter,
    Depends,
    File,
    Query,
    UploadFile,
)
from sqlalchemy.orm import Session

from database import get_db
from schemas import (
    ProductCategorizationRunResponse,
    ProductImportApplyRequest,
    ProductImportApplyResponse,
    ProductImportBatchResponse,
    ProductImportCategoryConfirmRequest,
    ProductImportConfirmationResponse,
    ProductImportConfirmAllRequest,
    ProductImportRowResponse,
    ProductImportRowsResponse,
)
from services.product_category_ai_service import (
    categorize_product_import_rows,
)
from services.product_import_apply_service import (
    apply_product_import,
)
from services.product_import_confirmation_service import (
    confirm_all_ai_suggestions,
    confirm_product_import_row_category,
)
from services.product_import_service import (
    create_product_import_preview,
    get_product_import_batch,
    get_product_import_rows,
)


router = APIRouter(
    prefix="/api/product-imports",
    tags=["Bulk Product Imports"],
)


@router.post(
    "/preview",
    response_model=ProductImportBatchResponse,
)
async def upload_product_import_preview(
    excel_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    return await create_product_import_preview(
        db=db,
        excel_file=excel_file,
    )


@router.get(
    "/{batch_id}/rows",
    response_model=ProductImportRowsResponse,
)
def view_product_import_rows(
    batch_id: int,
    row_status: str | None = Query(
        default=None,
        alias="status",
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return get_product_import_rows(
        db=db,
        batch_id=batch_id,
        row_status=row_status,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/{batch_id}/categorize-ai",
    response_model=ProductCategorizationRunResponse,
)
async def categorize_import_using_ai(
    batch_id: int,
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    db: Session = Depends(get_db),
):
    return await categorize_product_import_rows(
        db=db,
        batch_id=batch_id,
        limit=limit,
    )


@router.patch(
    "/{batch_id}/rows/{row_id}/category",
    response_model=ProductImportRowResponse,
)
def confirm_or_correct_row_category(
    batch_id: int,
    row_id: int,
    confirmation: ProductImportCategoryConfirmRequest,
    db: Session = Depends(get_db),
):
    return confirm_product_import_row_category(
        db=db,
        batch_id=batch_id,
        row_id=row_id,
        confirmation=confirmation,
    )


@router.post(
    "/{batch_id}/confirm-ai",
    response_model=ProductImportConfirmationResponse,
)
def accept_all_ai_suggestions(
    batch_id: int,
    confirmation: ProductImportConfirmAllRequest,
    db: Session = Depends(get_db),
):
    return confirm_all_ai_suggestions(
        db=db,
        batch_id=batch_id,
    )


@router.post(
    "/{batch_id}/apply",
    response_model=ProductImportApplyResponse,
)
def confirm_and_create_products(
    batch_id: int,
    confirmation: ProductImportApplyRequest,
    db: Session = Depends(get_db),
):
    return apply_product_import(
        db=db,
        batch_id=batch_id,
    )


@router.get(
    "/{batch_id}",
    response_model=ProductImportBatchResponse,
)
def view_product_import_batch(
    batch_id: int,
    db: Session = Depends(get_db),
):
    return get_product_import_batch(
        db=db,
        batch_id=batch_id,
    )