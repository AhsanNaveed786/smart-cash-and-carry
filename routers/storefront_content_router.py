from fastapi import (
    APIRouter,
    Depends,
)
from sqlalchemy.orm import Session

from database import get_db
from schemas import StorefrontContentResponse
from services.storefront_content_service import (
    get_storefront_content,
)


router = APIRouter(
    prefix="/api/storefront",
    tags=["Storefront Content"],
)


@router.get(
    "/content/{branch_id}",
    response_model=StorefrontContentResponse,
)
def view_storefront_content(
    branch_id: int,
    db: Session = Depends(get_db),
):
    return get_storefront_content(
        db=db,
        branch_id=branch_id,
    )