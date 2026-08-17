from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from secrets import token_hex
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from models import (
    Admin,
    Order,
    OrderItem,
    OrderStatusHistory,
    ProductVariant,
)
from schemas import CartQuoteRequest, OrderCreateRequest, OrderStatusUpdate
from services.availability_service import (
    get_active_availability_branch,
    get_product_availability,
)
from services.rbac_service import (
    create_admin_audit_log,
    ensure_admin_branch_access,
    get_admin_branch_ids,
)
from services.revenue_service import record_completed_order_revenue
from services.storefront_price_service import get_storefront_effective_price
from services.variant_service import (
    get_product_variant_by_id,
    get_variant_product,
)
from services.variant_stock_service import find_variant_stock_record


STORE_TIMEZONE = ZoneInfo("Asia/Karachi")
STORE_OPEN_HOUR = 9
STORE_CLOSE_HOUR = 21
MINIMUM_HOME_DELIVERY_ORDER = Decimal("3000.00")
FREE_DELIVERY_FEE = Decimal("0.00")
TWO_DECIMAL_PLACES = Decimal("0.01")


def get_order_date_boundaries(
    created_from: date | None,
    created_to: date | None,
) -> tuple[datetime | None, datetime | None]:
    if (
        created_from is not None
        and created_to is not None
        and created_to < created_from
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="created_to cannot be earlier than created_from.",
        )

    start_at = None
    end_before = None

    if created_from is not None:
        start_at = datetime.combine(
            created_from,
            time.min,
            tzinfo=STORE_TIMEZONE,
        ).astimezone(timezone.utc)

    if created_to is not None:
        end_before = datetime.combine(
            created_to + timedelta(days=1),
            time.min,
            tzinfo=STORE_TIMEZONE,
        ).astimezone(timezone.utc)

    return start_at, end_before


def money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(
        TWO_DECIMAL_PLACES,
        rounding=ROUND_HALF_UP,
    )


def get_order_processing_time(
    current_time: datetime | None = None,
) -> datetime:
    now_utc = current_time or datetime.now(timezone.utc)
    local_now = now_utc.astimezone(STORE_TIMEZONE)
    opening_time = local_now.replace(
        hour=STORE_OPEN_HOUR,
        minute=0,
        second=0,
        microsecond=0,
    )
    closing_time = local_now.replace(
        hour=STORE_CLOSE_HOUR,
        minute=0,
        second=0,
        microsecond=0,
    )

    if local_now < opening_time:
        process_at = opening_time
    elif local_now >= closing_time:
        process_at = opening_time + timedelta(days=1)
    else:
        process_at = local_now

    return process_at.astimezone(timezone.utc)


def generate_order_number() -> str:
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"SCC-{date_part}-{token_hex(4).upper()}"


def quote_cart(
    db: Session,
    quote_data: CartQuoteRequest,
) -> dict:
    get_active_availability_branch(
        db=db,
        branch_id=quote_data.branch_id,
    )

    quote_items = []
    subtotal = Decimal("0.00")

    for requested_item in quote_data.items:
        product = get_variant_product(
            db=db,
            product_id=requested_item.product_id,
        )
        product_stock = get_product_availability(
            db=db,
            product_id=product.id,
            branch_id=quote_data.branch_id,
        )

        if not product_stock["is_in_stock"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Product is out of stock.",
                    "product_id": product.id,
                    "stock_message": product_stock["stock_message"],
                },
            )

        price_data = get_storefront_effective_price(
            db=db,
            product_id=product.id,
            branch_id=quote_data.branch_id,
        )
        unit_price = money(price_data["effective_price"])
        variant_name = None
        variant_id = requested_item.variant_id
        sku = product.barcode

        if variant_id is not None:
            variant = get_product_variant_by_id(
                db=db,
                variant_id=variant_id,
            )

            if variant.product_id != product.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Variant does not belong to product.",
                        "product_id": product.id,
                        "variant_id": variant.id,
                    },
                )

            if not variant.is_active:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Selected variant is inactive.",
                )

            variant_stock = find_variant_stock_record(
                db=db,
                variant_id=variant.id,
                branch_id=quote_data.branch_id,
            )

            if variant_stock and not variant_stock.is_in_stock:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": "Selected variant is out of stock.",
                        "variant_id": variant.id,
                        "stock_message": variant_stock.stock_message,
                    },
                )

            unit_price = money(
                unit_price + Decimal(variant.price_adjustment)
            )
            if unit_price < 0:
                unit_price = Decimal("0.00")

            variant_name = variant.name
            sku = variant.sku
        else:
            active_variant = db.scalar(
                select(ProductVariant).where(
                    ProductVariant.product_id == product.id,
                    ProductVariant.is_active.is_(True),
                ).limit(1)
            )
            if active_variant:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "A product variant must be selected.",
                        "product_id": product.id,
                    },
                )

        line_total = money(unit_price * requested_item.quantity)
        subtotal += line_total
        quote_items.append(
            {
                "product_id": product.id,
                "variant_id": variant_id,
                "product_name": product.name,
                "variant_name": variant_name,
                "sku": sku,
                "quantity": requested_item.quantity,
                "unit_price": unit_price,
                "line_total": line_total,
            }
        )

    subtotal = money(subtotal)
    minimum_order_amount = (
        MINIMUM_HOME_DELIVERY_ORDER
        if quote_data.fulfillment_method == "home_delivery"
        else Decimal("0.00")
    )
    minimum_order_met = subtotal >= minimum_order_amount
    delivery_fee = FREE_DELIVERY_FEE

    return {
        "branch_id": quote_data.branch_id,
        "fulfillment_method": quote_data.fulfillment_method,
        "subtotal": subtotal,
        "delivery_fee": delivery_fee,
        "total_amount": money(subtotal + delivery_fee),
        "minimum_order_amount": minimum_order_amount,
        "minimum_order_met": minimum_order_met,
        "items": quote_items,
    }


def get_order_by_id(
    db: Session,
    order_id: int,
) -> Order:
    order = db.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.id == order_id)
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )
    return order


def get_order_by_number(
    db: Session,
    order_number: str,
) -> Order:
    order = db.scalar(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.order_number == order_number.strip().upper())
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )
    return order


def create_order(
    db: Session,
    order_data: OrderCreateRequest,
) -> Order:
    quote = quote_cart(db=db, quote_data=order_data)

    if not quote["minimum_order_met"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Minimum home-delivery order is Rs. 3,000.",
                "subtotal": str(quote["subtotal"]),
                "minimum_order_amount": str(
                    quote["minimum_order_amount"]
                ),
            },
        )

    payment_method = (
        "cash_on_delivery"
        if order_data.fulfillment_method == "home_delivery"
        else "pay_at_store"
    )

    try:
        order = Order(
            order_number=generate_order_number(),
            branch_id=order_data.branch_id,
            customer_name=order_data.customer_name.strip(),
            phone_number=order_data.phone_number.strip(),
            customer_email=(
                str(order_data.customer_email)
                if order_data.customer_email
                else None
            ),
            fulfillment_method=order_data.fulfillment_method,
            order_channel=order_data.order_channel,
            payment_method=payment_method,
            delivery_address=(
                order_data.delivery_address.strip()
                if order_data.delivery_address
                else None
            ),
            city=order_data.city.strip() if order_data.city else None,
            notes=order_data.notes.strip() if order_data.notes else None,
            status="pending",
            subtotal=quote["subtotal"],
            delivery_fee=quote["delivery_fee"],
            total_amount=quote["total_amount"],
            process_after=get_order_processing_time(),
        )
        db.add(order)
        db.flush()

        db.add(
            OrderStatusHistory(
                order_id=order.id,
                order_number=order.order_number,
                branch_id=order.branch_id,
                previous_status=None,
                new_status="pending",
                change_note=(
                    f"Order created through {order.order_channel}."
                ),
                changed_by_admin_id=None,
                changed_by_name=None,
                changed_by_email=None,
            )
        )

        for item in quote["items"]:
            db.add(
                OrderItem(
                    order_id=order.id,
                    product_id=item["product_id"],
                    variant_id=item["variant_id"],
                    product_name=item["product_name"],
                    variant_name=item["variant_name"],
                    sku=item["sku"],
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    line_total=item["line_total"],
                )
            )

        db.commit()
        return get_order_by_id(db=db, order_id=order.id)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Order number conflict. Please submit the order again.",
        )
    except Exception:
        db.rollback()
        raise


def get_customer_order(
    db: Session,
    order_number: str,
    phone_number: str,
) -> Order:
    order = get_order_by_number(db=db, order_number=order_number)
    if order.phone_number != phone_number.strip():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found.",
        )
    return order


def list_orders(
    db: Session,
    admin: Admin,
    branch_id: int | None = None,
    order_status: str | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    skip: int = 0,
    limit: int = 50,
) -> dict:
    conditions = []

    if branch_id is not None:
        ensure_admin_branch_access(
            db=db,
            admin=admin,
            branch_id=branch_id,
        )
        conditions.append(Order.branch_id == branch_id)
    elif admin.role != "super_admin":
        assigned_branch_ids = get_admin_branch_ids(
            db=db,
            admin=admin,
        )
        if not assigned_branch_ids:
            return {
                "total": 0,
                "skip": skip,
                "limit": limit,
                "items": [],
            }
        conditions.append(
            Order.branch_id.in_(assigned_branch_ids)
        )

    if order_status is not None:
        conditions.append(Order.status == order_status)

    start_at, end_before = get_order_date_boundaries(
        created_from=created_from,
        created_to=created_to,
    )
    if start_at is not None:
        conditions.append(Order.created_at >= start_at)
    if end_before is not None:
        conditions.append(Order.created_at < end_before)

    total_statement = select(func.count(Order.id))
    statement = (
        select(Order)
        .options(selectinload(Order.items))
        .order_by(Order.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if conditions:
        total_statement = total_statement.where(*conditions)
        statement = statement.where(*conditions)

    return {
        "total": db.scalar(total_statement) or 0,
        "skip": skip,
        "limit": limit,
        "items": list(db.scalars(statement).all()),
    }


def get_admin_order_by_id(
    db: Session,
    order_id: int,
    admin: Admin,
) -> Order:
    order = get_order_by_id(
        db=db,
        order_id=order_id,
    )
    ensure_admin_branch_access(
        db=db,
        admin=admin,
        branch_id=order.branch_id,
    )
    return order


def get_order_status_history(
    db: Session,
    order_id: int,
    admin: Admin,
) -> list[OrderStatusHistory]:
    order = get_admin_order_by_id(
        db=db,
        order_id=order_id,
        admin=admin,
    )
    return list(
        db.scalars(
            select(OrderStatusHistory)
            .where(
                OrderStatusHistory.order_number
                == order.order_number
            )
            .order_by(
                OrderStatusHistory.created_at,
                OrderStatusHistory.id,
            )
        ).all()
    )


ALLOWED_STATUS_TRANSITIONS = {
    "pending": {"confirmed", "cancelled"},
    "confirmed": {"processing", "cancelled"},
    "processing": {
        "ready_for_pickup",
        "out_for_delivery",
        "cancelled",
    },
    "ready_for_pickup": {"completed", "cancelled"},
    "out_for_delivery": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


def update_order_status(
    db: Session,
    order_id: int,
    status_data: OrderStatusUpdate,
    admin: Admin,
    ip_address: str | None = None,
) -> Order:
    order = get_admin_order_by_id(
        db=db,
        order_id=order_id,
        admin=admin,
    )
    new_status = status_data.status

    if new_status == order.status:
        return order

    if new_status not in ALLOWED_STATUS_TRANSITIONS[order.status]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Order cannot move from {order.status} "
                f"to {new_status}."
            ),
        )

    if (
        new_status == "ready_for_pickup"
        and order.fulfillment_method != "self_pickup"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only self-pickup orders can be ready for pickup.",
        )

    if (
        new_status == "out_for_delivery"
        and order.fulfillment_method != "home_delivery"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only home-delivery orders can be out for delivery.",
        )

    try:
        previous_status = order.status
        changed_at = datetime.now(timezone.utc)
        order.status = new_status

        db.add(
            OrderStatusHistory(
                order_id=order.id,
                order_number=order.order_number,
                branch_id=order.branch_id,
                previous_status=previous_status,
                new_status=new_status,
                change_note=(
                    status_data.note.strip()
                    if status_data.note
                    else None
                ),
                changed_by_admin_id=admin.id,
                changed_by_name=admin.full_name,
                changed_by_email=admin.email,
                created_at=changed_at,
            )
        )

        if new_status == "completed":
            record_completed_order_revenue(
                db=db,
                order=order,
                completed_at=changed_at,
            )

        create_admin_audit_log(
            db=db,
            action="order.status_updated",
            actor_admin_id=admin.id,
            details={
                "order_id": order.id,
                "order_number": order.order_number,
                "branch_id": order.branch_id,
                "previous_status": previous_status,
                "new_status": new_status,
            },
            ip_address=ip_address,
        )

        db.commit()
        return get_order_by_id(db=db, order_id=order.id)
    except Exception:
        db.rollback()
        raise
