"""Business-logic layer for TaskFlow CLI.

:class:`TaskManager` performs all CRUD operations, searching, filtering,
sorting, and statistics. Every mutation is auto-saved through the
injected :class:`~storage.StorageManager`.
"""

from __future__ import annotations

from typing import Any, Callable

from exceptions import TaskNotFoundError
from storage import StorageManager
from task import (
    Priority,
    Status,
    Task,
    now_timestamp,
    parse_deadline,
    validate_text,
)

SortKey = Callable[[Task], Any]


class TaskManager:
    """Manage the in-memory task collection with auto-save persistence."""

    #: Supported sort keys mapped to (key function, reverse flag).
    _SORT_KEYS: dict[str, tuple[SortKey, bool]] = {
        "deadline": (lambda task: task.deadline, False),
        "priority": (lambda task: task.priority.weight, True),
        "created_at": (lambda task: task.created_at, False),
    }

    def __init__(self, storage: StorageManager) -> None:
        self._storage = storage
        self._tasks: list[Task] = []
        self.reload()

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def reload(self) -> None:
        """Reload tasks from storage (used at startup and after restore)."""
        self._tasks = [Task.from_dict(record) for record in self._storage.load()]

    def _save(self) -> None:
        """Auto-save the current task list to storage."""
        self._storage.save([task.to_dict() for task in self._tasks])

    def _next_id(self) -> int:
        """Generate the next sequential task ID."""
        return max((task.id for task in self._tasks), default=0) + 1

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @property
    def tasks(self) -> list[Task]:
        """Return a copy of all tasks."""
        return list(self._tasks)

    def add_task(
        self,
        title: str,
        description: str,
        category: str,
        priority: str,
        deadline: str,
    ) -> Task:
        """Create, validate, and persist a new task.

        Returns:
            The newly created :class:`Task`.
        """
        task = Task(
            id=self._next_id(),
            title=validate_text(title, "judul"),
            description=description.strip(),
            category=validate_text(category, "kategori"),
            priority=Priority.from_str(priority),
            deadline=parse_deadline(deadline),
        )
        self._tasks.append(task)
        self._save()
        return task

    def get_task(self, task_id: int) -> Task:
        """Return the task with the given ID.

        Raises:
            TaskNotFoundError: If no task matches the ID.
        """
        for task in self._tasks:
            if task.id == task_id:
                return task
        raise TaskNotFoundError(task_id)

    def update_task(self, task_id: int, **changes: str) -> Task:
        """Update one or more fields of an existing task.

        Accepted keys: ``title``, ``description``, ``category``,
        ``priority``, ``deadline``, ``status``. Empty values are ignored.

        Returns:
            The updated :class:`Task`.
        """
        task = self.get_task(task_id)
        if value := changes.get("title", "").strip():
            task.title = validate_text(value, "judul")
        if value := changes.get("description", "").strip():
            task.description = value
        if value := changes.get("category", "").strip():
            task.category = validate_text(value, "kategori")
        if value := changes.get("priority", "").strip():
            task.priority = Priority.from_str(value)
        if value := changes.get("deadline", "").strip():
            task.deadline = parse_deadline(value)
        if value := changes.get("status", "").strip():
            task.status = Status.from_str(value)
        task.updated_at = now_timestamp()
        self._save()
        return task

    def delete_task(self, task_id: int) -> Task:
        """Delete a task and return it.

        Raises:
            TaskNotFoundError: If no task matches the ID.
        """
        task = self.get_task(task_id)
        self._tasks.remove(task)
        self._save()
        return task

    def mark_completed(self, task_id: int) -> Task:
        """Mark a task as completed and persist the change."""
        task = self.get_task(task_id)
        task.mark_completed()
        self._save()
        return task

    # ------------------------------------------------------------------
    # Query operations
    # ------------------------------------------------------------------
    def search_tasks(self, field: str, keyword: str) -> list[Task]:
        """Search tasks by field using case-insensitive matching.

        ``title`` uses substring matching; ``category``, ``priority``,
        and ``status`` use exact matching.
        """
        needle = keyword.strip().lower()
        matchers: dict[str, Callable[[Task], bool]] = {
            "title": lambda task: needle in task.title.lower(),
            "category": lambda task: task.category.lower() == needle,
            "priority": lambda task: task.priority.value.lower() == needle,
            "status": lambda task: task.status.value.lower() == needle,
        }
        matcher = matchers.get(field.lower())
        if matcher is None:
            raise ValueError(f"Field pencarian '{field}' tidak dikenal.")
        return [task for task in self._tasks if matcher(task)]

    def filter_tasks(self, field: str, value: str) -> list[Task]:
        """Filter tasks by ``category``, ``status``, or ``priority``."""
        if field.lower() not in {"category", "status", "priority"}:
            raise ValueError(f"Field filter '{field}' tidak dikenal.")
        return self.search_tasks(field, value)

    def sort_tasks(self, key: str) -> list[Task]:
        """Return tasks sorted by ``deadline``, ``priority``, or ``created_at``."""
        try:
            key_func, reverse = self._SORT_KEYS[key.lower()]
        except KeyError as exc:
            raise ValueError(f"Kunci sorting '{key}' tidak dikenal.") from exc
        return sorted(self._tasks, key=key_func, reverse=reverse)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------
    def get_statistics(self) -> dict[str, int | float]:
        """Compute summary statistics for the dashboard and statistics view."""
        total = len(self._tasks)
        completed = sum(1 for task in self._tasks if task.is_completed())
        pending = total - completed
        high_priority = sum(
            1
            for task in self._tasks
            if task.priority is Priority.HIGH and not task.is_completed()
        )
        due_today = sum(
            1
            for task in self._tasks
            if task.is_due_today() and not task.is_completed()
        )
        overdue = sum(1 for task in self._tasks if task.is_overdue())
        completion_rate = (completed / total * 100) if total else 0.0
        return {
            "total": total,
            "completed": completed,
            "pending": pending,
            "high_priority": high_priority,
            "due_today": due_today,
            "overdue": overdue,
            "completion_rate": round(completion_rate, 1),
        }
