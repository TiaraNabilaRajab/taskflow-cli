"""Task domain model for TaskFlow CLI.

Contains the :class:`Task` dataclass plus the :class:`Priority` and
:class:`Status` enums, and small validation helpers used across layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any

from exceptions import (
    EmptyInputError,
    InvalidDateError,
    InvalidPriorityError,
    InvalidStatusError,
)

DATE_FORMAT = "%Y-%m-%d"
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M"


class Priority(str, Enum):
    """Task priority level."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

    @classmethod
    def from_str(cls, value: str) -> "Priority":
        """Parse a case-insensitive string into a :class:`Priority`.

        Raises:
            InvalidPriorityError: If the value is not a valid priority.
        """
        normalized = value.strip().capitalize()
        for member in cls:
            if member.value == normalized:
                return member
        raise InvalidPriorityError(value)

    @property
    def weight(self) -> int:
        """Numeric weight used for sorting (High first)."""
        return {"High": 3, "Medium": 2, "Low": 1}[self.value]


class Status(str, Enum):
    """Task completion status."""

    PENDING = "Pending"
    COMPLETED = "Completed"

    @classmethod
    def from_str(cls, value: str) -> "Status":
        """Parse a case-insensitive string into a :class:`Status`.

        Raises:
            InvalidStatusError: If the value is not a valid status.
        """
        normalized = value.strip().capitalize()
        for member in cls:
            if member.value == normalized:
                return member
        raise InvalidStatusError(value)


def now_timestamp() -> str:
    """Return the current timestamp as a formatted string."""
    return datetime.now().strftime(TIMESTAMP_FORMAT)


def parse_deadline(value: str) -> str:
    """Validate a deadline string and return it normalized.

    Args:
        value: Date string expected in ``YYYY-MM-DD`` format.

    Returns:
        The normalized date string.

    Raises:
        EmptyInputError: If the value is empty.
        InvalidDateError: If the value is not a valid date.
    """
    cleaned = value.strip()
    if not cleaned:
        raise EmptyInputError("deadline")
    try:
        parsed = datetime.strptime(cleaned, DATE_FORMAT)
    except ValueError as exc:
        raise InvalidDateError(cleaned) from exc
    return parsed.strftime(DATE_FORMAT)


def validate_text(value: str, field_name: str) -> str:
    """Ensure a text field is not empty and return it stripped.

    Raises:
        EmptyInputError: If the value is empty or whitespace only.
    """
    cleaned = value.strip()
    if not cleaned:
        raise EmptyInputError(field_name)
    return cleaned


@dataclass
class Task:
    """A single to-do task persisted in the JSON database."""

    id: int
    title: str
    description: str
    category: str
    priority: Priority
    deadline: str
    status: Status = Status.PENDING
    created_at: str = field(default_factory=now_timestamp)
    updated_at: str | None = None
    completed_at: str | None = None

    def mark_completed(self) -> None:
        """Mark this task as completed and record the timestamp."""
        self.status = Status.COMPLETED
        self.completed_at = now_timestamp()

    def is_completed(self) -> bool:
        """Return ``True`` when the task status is Completed."""
        return self.status is Status.COMPLETED

    def is_due_today(self) -> bool:
        """Return ``True`` when the deadline is today's date."""
        return self.deadline == date.today().strftime(DATE_FORMAT)

    def is_overdue(self) -> bool:
        """Return ``True`` when the deadline has passed and task is pending."""
        if self.is_completed():
            return False
        deadline_date = datetime.strptime(self.deadline, DATE_FORMAT).date()
        return deadline_date < date.today()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the task into a JSON-compatible dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "priority": self.priority.value,
            "deadline": self.deadline,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        """Deserialize a dictionary (from JSON) into a :class:`Task`."""
        return cls(
            id=int(data["id"]),
            title=str(data["title"]),
            description=str(data.get("description", "")),
            category=str(data.get("category", "General")),
            priority=Priority.from_str(str(data.get("priority", "Low"))),
            deadline=parse_deadline(str(data["deadline"])),
            status=Status.from_str(str(data.get("status", "Pending"))),
            created_at=str(data.get("created_at", now_timestamp())),
            updated_at=data.get("updated_at"),
            completed_at=data.get("completed_at"),
        )
