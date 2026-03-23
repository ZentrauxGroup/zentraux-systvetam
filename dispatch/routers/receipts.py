"""
SYSTVETAM — Receipts Router
Zentraux Group LLC

The Receipt Vault is append-only. Read-only from the API.
No create, update, or delete endpoints exist.
The receipt_engine is the only writer. This is L0 doctrine.

Endpoints from Engineering Directive v1.0:
  GET  /receipts             Vault — paginated, filter by receipt_type
  GET  /receipts/{ref}       Single receipt by receipt_ref
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from dispatch.database import get_db
from dispatch.models.receipt import Receipt, ReceiptType
from dispatch.schemas.receipt import ReceiptListResponse, ReceiptResponse
from dispatch.state_machine import DoctrineViolation

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /receipts — Vault (paginated, filterable)
# ---------------------------------------------------------------------------

@router.get("", response_model=ReceiptListResponse)
async def list_receipts(
    db: AsyncSession = Depends(get_db),
    receipt_type: str | None = Query(None, description="Filter by receipt_type enum value"),
    task_id: str | None = Query(None, description="Filter by task UUID"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """
    Query the Receipt Vault. Paginated, newest first.
    Every action in the Systvetam produces a receipt.
    This endpoint is the compliance audit surface.
    """
    query = select(Receipt)

    if receipt_type:
        try:
            resolved = ReceiptType(receipt_type)
            query = query.where(Receipt.receipt_type == resolved)
        except ValueError:
            valid = [t.value for t in ReceiptType]
            raise DoctrineViolation(
                f"Invalid receipt_type filter: {receipt_type}. Valid: {valid}",
                sop_reference="L0-RECEIPT",
            )

    if task_id:
        import uuid as _uuid
        try:
            parsed = _uuid.UUID(task_id)
            query = query.where(Receipt.task_id == parsed)
        except ValueError:
            raise DoctrineViolation(
                f"Invalid task_id format: {task_id}",
                sop_reference="L0-RECEIPT",
            )

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Newest first — the most recent receipt is always the most relevant
    query = query.order_by(Receipt.created_at.desc())
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    receipts = result.scalars().all()

    return ReceiptListResponse(
        receipts=[ReceiptResponse.model_validate(r) for r in receipts],
        total=total,
        offset=offset,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# GET /receipts/{ref} — Single receipt by receipt_ref
# ---------------------------------------------------------------------------

@router.get("/{receipt_ref}", response_model=ReceiptResponse)
async def get_receipt(
    receipt_ref: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve a single receipt by its human-readable reference.
    Format: RCPT-{task_ref}-{TYPE}-{YYYYMMDD}-{NNN}
    """
    result = await db.execute(
        select(Receipt).where(Receipt.receipt_ref == receipt_ref)
    )
    receipt = result.scalar_one_or_none()

    if receipt is None:
        raise DoctrineViolation(
            f"Receipt not found: {receipt_ref}",
            sop_reference="L0-RECEIPT",
        )

    return receipt
