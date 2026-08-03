import json
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from exceptions import (  # noqa: E402
    CorruptedDataError,
    EmptyInputError,
    InvalidDateError,
    InvalidPriorityError,
    TaskNotFoundError,
)
from storage import StorageManager  # noqa: E402
from task import Priority, Status  # noqa: E402
from task_manager import TaskManager  # noqa: E402


class TaskManagerTestCase(unittest.TestCase):
    """Test suite covering CRUD, search, complete, sort, and statistics."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.storage = StorageManager(
            data_file=base / "data" / "tasks.json",
            backup_dir=base / "backup",
            export_dir=base / "exports",
        )
        self.manager = TaskManager(self.storage)
        self.today = date.today().isoformat()
        self.tomorrow = (date.today() + timedelta(days=1)).isoformat()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _add_sample(self, **overrides) -> object:
        """Create a task with sensible defaults, overridable per test."""
        payload = {
            "title": "Belajar Python",
            "description": "Function dan OOP",
            "category": "Study",
            "priority": "High",
            "deadline": self.tomorrow,
        }
        payload.update(overrides)
        return self.manager.add_task(**payload)

    def test_add_task_creates_task_with_sequential_id(self) -> None:
        first = self._add_sample()
        second = self._add_sample(title="Task kedua")
        self.assertEqual(first.id, 1)
        self.assertEqual(second.id, 2)
        self.assertEqual(first.status, Status.PENDING)
        self.assertEqual(first.priority, Priority.HIGH)

    def test_add_task_persists_to_json(self) -> None:
        self._add_sample()
        records = json.loads(self.storage.data_file.read_text(encoding="utf-8"))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["title"], "Belajar Python")

    def test_add_task_rejects_empty_title(self) -> None:
        with self.assertRaises(EmptyInputError):
            self._add_sample(title="   ")

    def test_add_task_rejects_invalid_priority(self) -> None:
        with self.assertRaises(InvalidPriorityError):
            self._add_sample(priority="Urgent")

    def test_add_task_rejects_invalid_deadline(self) -> None:
        with self.assertRaises(InvalidDateError):
            self._add_sample(deadline="10-08-2026")

    def test_update_task_changes_fields(self) -> None:
        task = self._add_sample()
        updated = self.manager.update_task(
            task.id, title="Belajar OOP", priority="Low"
        )
        self.assertEqual(updated.title, "Belajar OOP")
        self.assertEqual(updated.priority, Priority.LOW)
        self.assertIsNotNone(updated.updated_at)

    def test_update_task_ignores_empty_fields(self) -> None:
        task = self._add_sample()
        updated = self.manager.update_task(task.id, title="", category="  ")
        self.assertEqual(updated.title, "Belajar Python")
        self.assertEqual(updated.category, "Study")

    def test_update_missing_task_raises(self) -> None:
        with self.assertRaises(TaskNotFoundError):
            self.manager.update_task(999, title="X")

    def test_delete_task_removes_task(self) -> None:
        task = self._add_sample()
        self.manager.delete_task(task.id)
        self.assertEqual(self.manager.tasks, [])
        with self.assertRaises(TaskNotFoundError):
            self.manager.get_task(task.id)

    def test_delete_missing_task_raises(self) -> None:
        with self.assertRaises(TaskNotFoundError):
            self.manager.delete_task(42)

    def test_search_by_title_is_case_insensitive_substring(self) -> None:
        self._add_sample(title="Belajar Python")
        self._add_sample(title="Olahraga pagi")
        results = self.manager.search_tasks("title", "python")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Belajar Python")

    def test_search_by_category_and_priority(self) -> None:
        self._add_sample(category="Study", priority="High")
        self._add_sample(title="Belanja", category="Home", priority="Low")
        self.assertEqual(len(self.manager.search_tasks("category", "home")), 1)
        self.assertEqual(len(self.manager.search_tasks("priority", "HIGH")), 1)

    def test_filter_by_status(self) -> None:
        task = self._add_sample()
        self._add_sample(title="Task lain")
        self.manager.mark_completed(task.id)
        pending = self.manager.filter_tasks("status", "Pending")
        completed = self.manager.filter_tasks("status", "Completed")
        self.assertEqual(len(pending), 1)
        self.assertEqual(len(completed), 1)

    def test_search_unknown_field_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.manager.search_tasks("owner", "x")

    def test_mark_completed_sets_status_and_timestamp(self) -> None:
        task = self._add_sample()
        completed = self.manager.mark_completed(task.id)
        self.assertEqual(completed.status, Status.COMPLETED)
        self.assertIsNotNone(completed.completed_at)

    def test_sort_by_deadline(self) -> None:
        self._add_sample(title="Nanti", deadline="2030-12-31")
        self._add_sample(title="Segera", deadline=self.today)
        titles = [task.title for task in self.manager.sort_tasks("deadline")]
        self.assertEqual(titles, ["Segera", "Nanti"])

    def test_sort_by_priority_puts_high_first(self) -> None:
        self._add_sample(title="Santai", priority="Low")
        self._add_sample(title="Penting", priority="High")
        self._add_sample(title="Biasa", priority="Medium")
        titles = [task.title for task in self.manager.sort_tasks("priority")]
        self.assertEqual(titles, ["Penting", "Biasa", "Santai"])

    def test_sort_unknown_key_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.manager.sort_tasks("alphabet")

    def test_statistics_counts(self) -> None:
        first = self._add_sample(priority="High", deadline=self.today)
        self._add_sample(title="Kedua", priority="Low")
        self.manager.mark_completed(first.id)
        stats = self.manager.get_statistics()
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["completed"], 1)
        self.assertEqual(stats["pending"], 1)
        self.assertEqual(stats["completion_rate"], 50.0)

    def test_corrupted_json_raises(self) -> None:
        self.storage.data_file.write_text("{bukan json", encoding="utf-8")
        with self.assertRaises(CorruptedDataError):
            self.storage.load()

    def test_backup_and_restore_roundtrip(self) -> None:
        self._add_sample()
        backup_path = self.storage.create_backup()
        self.manager.delete_task(1)
        self.assertEqual(self.manager.tasks, [])
        self.storage.restore_backup(backup_path)
        self.manager.reload()
        self.assertEqual(len(self.manager.tasks), 1)

    def test_export_csv_and_txt(self) -> None:
        self._add_sample()
        records = [task.to_dict() for task in self.manager.tasks]
        csv_path = self.storage.export_csv(records)
        txt_path = self.storage.export_txt(records)
        self.assertTrue(csv_path.exists())
        self.assertIn("Belajar Python", txt_path.read_text(encoding="utf-8"))

if __name__ == "__main__":
    unittest.main()
