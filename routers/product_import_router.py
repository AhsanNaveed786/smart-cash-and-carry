from fastapi import (
    status,
    APIRouter,
    Depends,
    File,
    Query,
    UploadFile,
)
from sqlalchemy.orm import Session

from database import get_db
from dependencies.admin_access import permission_required
from schemas import (
    BulkImportSelectionUpdate,
    ImportRowSelectionUpdate,
    ProductCategorizationRunResponse,
    ProductImportApplyRequest,
    ProductImportApplyResponse,
    ProductImportBatchResponse,
    ProductImportBulkAssignRequest,
    ProductImportCategoryConfirmRequest,
    ProductImportConfirmationResponse,
    ProductImportConfirmAllRequest,
    ProductImportQuickCategorizeResponse,
    ProductImportRowResponse,
    ProductImportRowsResponse,
    ProductImportReviewSummary,
    VariantBulkActionResponse,
    VariantGroupActionRequest,
    VariantGroupsResponse,
    VariantMergeResponse,
)
from services.variant_detection_service import (
    get_variant_groups,
    merge_variant_group,
    unmerge_variant_group,
    merge_all_variant_groups,
    unmerge_all_variant_groups,
)
from services.product_category_ai_service import (
    categorize_product_import_rows,
    quick_auto_categorize_product_import_rows,
)
from services.product_import_apply_service import (
    apply_product_import,
)
from services.product_import_confirmation_service import (
    confirm_all_ai_suggestions,
    confirm_product_import_row_category,
)
from services.product_import_service import (
    bulk_assign_category_to_pending,
    create_product_import_preview,
    get_product_import_batch,
    get_product_import_rows,
    get_product_import_review_summary,
    update_product_import_row_selection,
    update_all_product_import_row_selection,
)
from services.variant_detection_service import (
    get_variant_groups,
    merge_variant_group,
    unmerge_variant_group,
)


router = APIRouter(
    prefix="/api/product-imports",
    tags=["Bulk Product Imports"],
    dependencies=[
        Depends(permission_required("imports.manage"))
    ],
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
    "/{batch_id}/quick-categorize",
    response_model=ProductImportQuickCategorizeResponse,
)
def quick_categorize_import_rows(
    batch_id: int,
    db: Session = Depends(get_db),
):
    return quick_auto_categorize_product_import_rows(
        db=db,
        batch_id=batch_id,
    )


@router.post(
    "/{batch_id}/assign-category-all",
    response_model=ProductImportReviewSummary,
)
def bulk_assign_category_to_all_pending(
    batch_id: int,
    payload: ProductImportBulkAssignRequest,
    db: Session = Depends(get_db),
):
    return bulk_assign_category_to_pending(
        db=db,
        batch_id=batch_id,
        category_id=payload.category_id,
        category_name=payload.category_name,
        include_ai_categorized=payload.include_ai_categorized,
        target_scope=payload.target_scope,
    )


@router.post(
    "/{batch_id}/categorize-ai",
    response_model=ProductCategorizationRunResponse,
)
async def categorize_import_using_ai(
    batch_id: int,
    limit: int = Query(
        default=100,
        ge=1,
        le=200,
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
        fallback_category_id=confirmation.fallback_category_id,
        auto_assign_default=confirmation.auto_assign_default,
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


@router.get(
    "/{batch_id}/summary",
    response_model=ProductImportReviewSummary,
)
def view_product_import_summary(
    batch_id: int,
    db: Session = Depends(get_db),
):
    return get_product_import_review_summary(db, batch_id)


@router.patch(
    "/{batch_id}/rows/selection",
    response_model=ProductImportReviewSummary,
)
def change_product_row_selection(
    batch_id: int,
    selection: ImportRowSelectionUpdate,
    db: Session = Depends(get_db),
):
    return update_product_import_row_selection(
        db=db,
        batch_id=batch_id,
        row_ids=selection.row_ids,
        apply_selected=selection.apply_selected,
    )


@router.patch(
    "/{batch_id}/rows/selection-all",
    response_model=ProductImportReviewSummary,
)
def change_all_product_rows_selection(
    batch_id: int,
    selection: BulkImportSelectionUpdate,
    db: Session = Depends(get_db),
):
    return update_all_product_import_row_selection(
        db=db,
        batch_id=batch_id,
        apply_selected=selection.apply_selected,
    )


@router.get(
    "/{batch_id}/variant-groups",
    response_model=VariantGroupsResponse,
    status_code=status.HTTP_200_OK,
)
def get_batch_variant_groups(
    batch_id: int,
    db: Session = Depends(get_db),
):
    groups = get_variant_groups(db=db, batch_id=batch_id)
    total_variant_rows = sum(g['member_count'] for g in groups)
    return {
        'batch_id': batch_id,
        'total_groups': len(groups),
        'total_variant_rows': total_variant_rows,
        'groups': groups,
    }


@router.post(
    "/{batch_id}/variant-groups/merge-all",
    response_model=VariantBulkActionResponse,
    status_code=status.HTTP_200_OK,
)
def merge_all_batch_variant_groups(
    batch_id: int,
    db: Session = Depends(get_db),
):
    return merge_all_variant_groups(
        db=db,
        batch_id=batch_id,
    )


@router.post(
    "/{batch_id}/variant-groups/unmerge-all",
    response_model=VariantBulkActionResponse,
    status_code=status.HTTP_200_OK,
)
def unmerge_all_batch_variant_groups(
    batch_id: int,
    db: Session = Depends(get_db),
):
    return unmerge_all_variant_groups(
        db=db,
        batch_id=batch_id,
    )


@router.post(
    "/{batch_id}/variant-groups/merge",
    response_model=VariantMergeResponse,
    status_code=status.HTTP_200_OK,
)
def merge_batch_variant_group_body(
    batch_id: int,
    payload: VariantGroupActionRequest,
    db: Session = Depends(get_db),
):
    return merge_variant_group(
        db=db,
        batch_id=batch_id,
        group_key=payload.group_key,
    )


@router.post(
    "/{batch_id}/variant-groups/unmerge",
    response_model=VariantMergeResponse,
    status_code=status.HTTP_200_OK,
)
def unmerge_batch_variant_group_body(
    batch_id: int,
    payload: VariantGroupActionRequest,
    db: Session = Depends(get_db),
):
    return unmerge_variant_group(
        db=db,
        batch_id=batch_id,
        group_key=payload.group_key,
    )


@router.post(
    "/{batch_id}/variant-groups/{group_key:path}/merge",
    response_model=VariantMergeResponse,
    status_code=status.HTTP_200_OK,
)
def merge_batch_variant_group(
    batch_id: int,
    group_key: str,
    db: Session = Depends(get_db),
):
    return merge_variant_group(
        db=db,
        batch_id=batch_id,
        group_key=group_key,
    )


@router.post(
    "/{batch_id}/variant-groups/{group_key:path}/unmerge",
    response_model=VariantMergeResponse,
    status_code=status.HTTP_200_OK,
)
def unmerge_batch_variant_group(
    batch_id: int,
    group_key: str,
    db: Session = Depends(get_db),
):
    return unmerge_variant_group(
        db=db,
        batch_id=batch_id,
        group_key=group_key,
    )

