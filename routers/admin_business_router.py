from datetime import date
from io import BytesIO
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from dependencies.admin_access import (
    permission_required,
    require_admin_write_csrf,
    require_super_admin,
)
from models import Admin, AdminSession
from schemas import (
    AdminPriceUpdateResponse,
    AdminProductPriceListResponse,
    AdminProductPriceResponse,
    BranchPriceSetRequest,
    DataExportResponse,
    DeleteExportedOrdersRequest,
    DeleteExportedOrdersResponse,
    MasterPriceUpdate,
    RevenueDashboardResponse,
)
from services.admin_auth_service import get_request_ip
from services.admin_pricing_service import (
    get_admin_product_price,
    list_admin_product_prices,
    remove_branch_product_price,
    set_branch_product_price,
    update_master_product_price,
)
from services.export_service import (
    delete_orders_from_export,
    export_orders_workbook,
    export_products_workbook,
    list_export_records,
)
from services.revenue_service import get_revenue_dashboard


router = APIRouter(
    prefix="/api/admin/business",
    tags=["Admin Business Management"],
)

EXCEL_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument."
    "spreadsheetml.sheet"
)


def excel_response(
    content: bytes,
    file_name: str,
    export_id: int,
    file_sha256: str,
) -> StreamingResponse:
    return StreamingResponse(
        BytesIO(content),
        media_type=EXCEL_MEDIA_TYPE,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{file_name}"'
            ),
            "X-Export-ID": str(export_id),
            "X-File-SHA256": file_sha256,
            "Access-Control-Expose-Headers": (
                "Content-Disposition, X-Export-ID, X-File-SHA256"
            ),
        },
    )


@router.get(
    "/products/prices",
    response_model=AdminProductPriceListResponse,
)
def view_product_prices(
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=255,
    ),
    active_only: bool = Query(default=False),
    different_only: bool = Query(default=False),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    admin: Admin = Depends(
        permission_required("products.read")
    ),
    _price_admin: Admin = Depends(
        permission_required("prices.read")
    ),
):
    return list_admin_product_prices(
        db=db,
        admin=admin,
        search=search,
        active_only=active_only,
        different_only=different_only,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/products/{product_id}/prices",
    response_model=AdminProductPriceResponse,
)
def view_one_product_prices(
    product_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(
        permission_required("products.read")
    ),
    _price_admin: Admin = Depends(
        permission_required("prices.read")
    ),
):
    return get_admin_product_price(
        db=db,
        admin=admin,
        product_id=product_id,
    )


@router.put(
    "/branches/{branch_id}/products/{product_id}/price",
    response_model=AdminPriceUpdateResponse,
)
def set_branch_price(
    branch_id: int,
    product_id: int,
    price_data: BranchPriceSetRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(
        permission_required("prices.update")
    ),
    _admin_session: AdminSession = Depends(
        require_admin_write_csrf
    ),
):
    return set_branch_product_price(
        db=db,
        admin=admin,
        branch_id=branch_id,
        product_id=product_id,
        override_price=price_data.override_price,
        ip_address=get_request_ip(request),
    )


@router.delete(
    "/branches/{branch_id}/products/{product_id}/price",
    response_model=AdminPriceUpdateResponse,
)
def reset_branch_price_to_master(
    branch_id: int,
    product_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(
        permission_required("prices.update")
    ),
    _admin_session: AdminSession = Depends(
        require_admin_write_csrf
    ),
):
    return remove_branch_product_price(
        db=db,
        admin=admin,
        branch_id=branch_id,
        product_id=product_id,
        ip_address=get_request_ip(request),
    )


@router.patch(
    "/products/{product_id}/master-price",
    response_model=AdminPriceUpdateResponse,
)
def set_master_price(
    product_id: int,
    price_data: MasterPriceUpdate,
    request: Request,
    db: Session = Depends(get_db),
    super_admin: Admin = Depends(require_super_admin),
    _admin_session: AdminSession = Depends(
        require_admin_write_csrf
    ),
):
    return update_master_product_price(
        db=db,
        super_admin=super_admin,
        product_id=product_id,
        master_price=price_data.master_price,
        ip_address=get_request_ip(request),
    )


@router.get(
    "/revenue",
    response_model=RevenueDashboardResponse,
)
def view_revenue_dashboard(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    branch_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
    _super_admin: Admin = Depends(require_super_admin),
):
    return get_revenue_dashboard(
        db=db,
        date_from=date_from,
        date_to=date_to,
        branch_id=branch_id,
    )


@router.get("/exports/orders")
def download_orders_excel(
    request: Request,
    branch_id: int | None = Query(default=None, gt=0),
    order_status: Literal[
        "pending",
        "confirmed",
        "processing",
        "ready_for_pickup",
        "out_for_delivery",
        "completed",
        "cancelled",
    ] | None = Query(default=None),
    created_from: date | None = Query(default=None),
    created_to: date | None = Query(default=None),
    db: Session = Depends(get_db),
    super_admin: Admin = Depends(require_super_admin),
):
    content, export_record = export_orders_workbook(
        db=db,
        super_admin=super_admin,
        branch_id=branch_id,
        order_status=order_status,
        created_from=created_from,
        created_to=created_to,
        ip_address=get_request_ip(request),
    )
    return excel_response(
        content=content,
        file_name=export_record.file_name,
        export_id=export_record.id,
        file_sha256=export_record.file_sha256,
    )


@router.get("/exports/products")
def download_products_excel(
    request: Request,
    branch_id: int | None = Query(default=None, gt=0),
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=255,
    ),
    active_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    super_admin: Admin = Depends(require_super_admin),
):
    content, export_record = export_products_workbook(
        db=db,
        super_admin=super_admin,
        branch_id=branch_id,
        search=search,
        active_only=active_only,
        ip_address=get_request_ip(request),
    )
    return excel_response(
        content=content,
        file_name=export_record.file_name,
        export_id=export_record.id,
        file_sha256=export_record.file_sha256,
    )


@router.get(
    "/exports",
    response_model=list[DataExportResponse],
)
def view_export_history(
    export_type: Literal[
        "orders",
        "products",
    ] | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _super_admin: Admin = Depends(require_super_admin),
):
    return list_export_records(
        db=db,
        export_type=export_type,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/orders/delete-exported",
    response_model=DeleteExportedOrdersResponse,
)
def permanently_delete_exported_orders(
    delete_data: DeleteExportedOrdersRequest,
    request: Request,
    db: Session = Depends(get_db),
    super_admin: Admin = Depends(require_super_admin),
    _admin_session: AdminSession = Depends(
        require_admin_write_csrf
    ),
):
    return delete_orders_from_export(
        db=db,
        export_id=delete_data.export_id,
        super_admin=super_admin,
        ip_address=get_request_ip(request),
    )
