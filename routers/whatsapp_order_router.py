from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from schemas import WhatsAppOrderRequest, WhatsAppOrderResponse
from services.whatsapp_order_service import create_whatsapp_order_link


router = APIRouter(
    prefix="/api/whatsapp",
    tags=["WhatsApp Orders"],
)


@router.post(
    "/order-link",
    response_model=WhatsAppOrderResponse,
)
def build_whatsapp_order_link(
    order_data: WhatsAppOrderRequest,
    db: Session = Depends(get_db),
):
    return create_whatsapp_order_link(
        db=db,
        order_data=order_data,
    )
