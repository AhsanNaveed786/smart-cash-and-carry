from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from database import get_db
from dependencies.admin_access import (
    permission_required,
    require_admin_write_csrf,
)
from models import Admin, AdminSession
from schemas import (
    CartQuoteRequest,
    CartQuoteResponse,
    OrderCreateRequest,
    OrderListResponse,
    OrderResponse,
    OrderStatusHistoryResponse,
    OrderStatusUpdate,
)
from services.admin_auth_service import get_request_ip
from services.order_service import (
    create_order,
    get_admin_order_by_id,
    get_customer_order,
    get_order_status_history,
    list_orders,
    quote_cart,
    update_order_status,
)


router = APIRouter(
    prefix="/api/orders",
    tags=["Cart, Checkout and Orders"],
)


@router.post(
    "/quote",
    response_model=CartQuoteResponse,
)
def create_cart_quote(
    quote_data: CartQuoteRequest,
    db: Session = Depends(get_db),
):
    return quote_cart(db=db, quote_data=quote_data)


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def checkout_order(
    order_data: OrderCreateRequest,
    db: Session = Depends(get_db),
):
    return create_order(db=db, order_data=order_data)


@router.get(
    "",
    response_model=OrderListResponse,
)
def view_orders(
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
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: Admin = Depends(
        permission_required("orders.read")
    ),
):
    return list_orders(
        db=db,
        admin=admin,
        branch_id=branch_id,
        order_status=order_status,
        created_from=created_from,
        created_to=created_to,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/lookup/{order_number}",
    response_model=OrderResponse,
)
def track_customer_order(
    order_number: str,
    phone_number: str = Query(min_length=7, max_length=30),
    db: Session = Depends(get_db),
):
    return get_customer_order(
        db=db,
        order_number=order_number,
        phone_number=phone_number,
    )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
)
def view_order(
    order_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(
        permission_required("orders.read")
    ),
):
    return get_admin_order_by_id(
        db=db,
        order_id=order_id,
        admin=admin,
    )


@router.get(
    "/{order_id}/history",
    response_model=list[OrderStatusHistoryResponse],
)
def view_order_status_history(
    order_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(
        permission_required("orders.read")
    ),
):
    return get_order_status_history(
        db=db,
        order_id=order_id,
        admin=admin,
    )


@router.patch(
    "/{order_id}/status",
    response_model=OrderResponse,
)
def change_order_status(
    order_id: int,
    status_data: OrderStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(
        permission_required("orders.update_status")
    ),
    _admin_session: AdminSession = Depends(
        require_admin_write_csrf
    ),
):
    return update_order_status(
        db=db,
        order_id=order_id,
        status_data=status_data,
        admin=admin,
        ip_address=get_request_ip(request),
    )
