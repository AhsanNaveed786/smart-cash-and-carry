import os
from urllib.parse import quote

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from schemas import WhatsAppOrderRequest
from services.availability_service import get_active_availability_branch
from services.order_service import (
    STORE_TIMEZONE,
    get_order_processing_time,
    quote_cart,
)


def normalize_whatsapp_number(number: str) -> str:
    normalized_number = "".join(
        character for character in number if character.isdigit()
    )

    if len(normalized_number) < 10:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WHATSAPP_ORDER_NUMBER is not configured correctly.",
        )

    return normalized_number


def create_whatsapp_order_link(
    db: Session,
    order_data: WhatsAppOrderRequest,
) -> dict:
    whatsapp_number = os.getenv("WHATSAPP_ORDER_NUMBER")

    if not whatsapp_number:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WHATSAPP_ORDER_NUMBER is not configured.",
        )

    normalized_number = normalize_whatsapp_number(whatsapp_number)
    branch = get_active_availability_branch(
        db=db,
        branch_id=order_data.branch_id,
    )
    cart_quote = quote_cart(db=db, quote_data=order_data)

    if not cart_quote["minimum_order_met"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Minimum home-delivery order is Rs. 3,000.",
                "subtotal": str(cart_quote["subtotal"]),
            },
        )

    process_after = get_order_processing_time()
    local_process_time = process_after.astimezone(STORE_TIMEZONE)
    fulfillment_label = (
        "Home Delivery"
        if order_data.fulfillment_method == "home_delivery"
        else "Self Pickup"
    )

    message_lines = [
        "SMART CASH & CARRY ORDER",
        "",
        f"Customer: {order_data.customer_name}",
        f"Phone: {order_data.phone_number}",
        f"Branch: {branch.name}",
        f"Order Type: {fulfillment_label}",
    ]

    if order_data.delivery_address:
        message_lines.append(
            f"Address: {order_data.delivery_address}, {order_data.city}"
        )

    message_lines.extend(["", "Items:"])

    for index, item in enumerate(cart_quote["items"], start=1):
        item_name = item["product_name"]
        if item["variant_name"]:
            item_name += f" ({item['variant_name']})"

        message_lines.append(
            f"{index}. {item_name} x {item['quantity']} "
            f"= Rs. {item['line_total']}"
        )

    message_lines.extend(
        [
            "",
            f"Subtotal: Rs. {cart_quote['subtotal']}",
            f"Total: Rs. {cart_quote['total_amount']}",
            "Payment: Cash on Delivery"
            if order_data.fulfillment_method == "home_delivery"
            else "Payment: Pay at Store",
            (
                "Process after: "
                f"{local_process_time.strftime('%d %b %Y, %I:%M %p')}"
            ),
        ]
    )

    if order_data.notes:
        message_lines.extend(["", f"Notes: {order_data.notes}"])

    message = "\n".join(message_lines)
    whatsapp_url = (
        f"https://wa.me/{normalized_number}?text={quote(message)}"
    )

    return {
        "whatsapp_url": whatsapp_url,
        "message": message,
        "quote": cart_quote,
        "process_after": process_after,
    }
