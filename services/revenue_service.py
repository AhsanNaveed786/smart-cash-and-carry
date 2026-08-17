from datetime import date, datetime, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from models import Branch, Order, RevenueOrderLedger


STORE_TIMEZONE = ZoneInfo("Asia/Karachi")


def pakistan_today() -> date:
    return datetime.now(timezone.utc).astimezone(
        STORE_TIMEZONE
    ).date()


def record_completed_order_revenue(
    db: Session,
    order: Order,
    completed_at: datetime | None = None,
) -> bool:
    completion_time = completed_at or datetime.now(timezone.utc)
    if completion_time.tzinfo is None:
        completion_time = completion_time.replace(
            tzinfo=timezone.utc
        )

    branch_name = db.scalar(
        select(Branch.name).where(
            Branch.id == order.branch_id
        )
    )
    if branch_name is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Order branch no longer exists.",
        )

    statement = (
        insert(RevenueOrderLedger)
        .values(
            order_id=order.id,
            order_number=order.order_number,
            branch_id=order.branch_id,
            branch_name=branch_name,
            completion_date=completion_time.astimezone(
                STORE_TIMEZONE
            ).date(),
            completed_at=completion_time,
            total_amount=order.total_amount,
        )
        .on_conflict_do_nothing(
            index_elements=["order_number"]
        )
        .returning(RevenueOrderLedger.id)
    )

    return db.scalar(statement) is not None


def get_revenue_dashboard(
    db: Session,
    date_from: date | None = None,
    date_to: date | None = None,
    branch_id: int | None = None,
) -> dict:
    today = pakistan_today()
    resolved_to = date_to or today
    resolved_from = date_from or (
        resolved_to if date_to is not None else today
    )

    if resolved_to < resolved_from:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_to cannot be earlier than date_from.",
        )

    conditions = [
        RevenueOrderLedger.completion_date >= resolved_from,
        RevenueOrderLedger.completion_date <= resolved_to,
    ]

    if branch_id is not None:
        branch_exists = db.scalar(
            select(Branch.id).where(Branch.id == branch_id)
        )
        if branch_exists is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found.",
            )
        conditions.append(
            RevenueOrderLedger.branch_id == branch_id
        )

    total_row = db.execute(
        select(
            func.count(RevenueOrderLedger.id),
            func.coalesce(
                func.sum(RevenueOrderLedger.total_amount),
                Decimal("0.00"),
            ),
        ).where(*conditions)
    ).one()

    daily_rows = db.execute(
        select(
            RevenueOrderLedger.completion_date,
            func.count(RevenueOrderLedger.id),
            func.coalesce(
                func.sum(RevenueOrderLedger.total_amount),
                Decimal("0.00"),
            ),
        )
        .where(*conditions)
        .group_by(RevenueOrderLedger.completion_date)
        .order_by(RevenueOrderLedger.completion_date)
    ).all()

    branch_rows = db.execute(
        select(
            RevenueOrderLedger.branch_id,
            RevenueOrderLedger.branch_name,
            func.count(RevenueOrderLedger.id),
            func.coalesce(
                func.sum(RevenueOrderLedger.total_amount),
                Decimal("0.00"),
            ),
        )
        .where(*conditions)
        .group_by(
            RevenueOrderLedger.branch_id,
            RevenueOrderLedger.branch_name,
        )
        .order_by(RevenueOrderLedger.branch_name)
    ).all()

    return {
        "date_from": resolved_from,
        "date_to": resolved_to,
        "branch_id": branch_id,
        "total_orders": total_row[0],
        "total_revenue": total_row[1],
        "daily": [
            {
                "sale_date": row[0],
                "order_count": row[1],
                "revenue": row[2],
            }
            for row in daily_rows
        ],
        "branches": [
            {
                "branch_id": row[0],
                "branch_name": row[1],
                "order_count": row[2],
                "revenue": row[3],
            }
            for row in branch_rows
        ],
    }
