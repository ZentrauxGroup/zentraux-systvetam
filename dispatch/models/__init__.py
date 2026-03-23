"""SYSTVETAM — ORM Models
Import all models here so Alembic autogenerate detects every table.
"""
from dispatch.models.task import Task, TaskStatus, TaskType, TaskPriority
from dispatch.models.receipt import Receipt, ReceiptType
from dispatch.models.crew_member import CrewMember, CrewStatus, ExecutionPlane

__all__ = [
    "Task", "TaskStatus", "TaskType", "TaskPriority",
    "Receipt", "ReceiptType",
    "CrewMember", "CrewStatus", "ExecutionPlane",
]
