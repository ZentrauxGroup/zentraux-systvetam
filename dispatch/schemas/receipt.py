"""
SYSTVETAM — Receipt Schemas
Zentraux Group LLC

Pydantic models for receipt API response serialization.
Receipts are read-only from the API — no create/update request schemas exist.
The receipt engine is the only writer. This is doctrine.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ReceiptResponse(BaseModel):
    """Single receipt response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    receipt_ref: str
    receipt_type: str
    task_id: uuid.UUID | None = None
    crew_member_id: uuid.UUID | None = None
    issued_by: str
    summary: str
    payload: dict[str, Any] | None = None
    sop_reference: str | None = None
    created_at: datetime


class ReceiptListResponse(BaseModel):
    """Paginated receipt vault response."""
    receipts: list[ReceiptResponse]
    total: int
    offset: int
    limit: int
