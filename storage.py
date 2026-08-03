"""Persistence layer for TaskFlow CLI.

:class:`StorageManager` is the only module that touches the filesystem:
JSON database read/write, backups, restore, and CSV/TXT export.
"""

from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from exceptions import BackupNotFoundError, CorruptedDataError, StorageError

BACKUP_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"


class StorageManager:
    """Handle all file I/O: JSON database, backup, restore, and export."""

    def __init__(
        self,
        data_file: str | Path = "data/tasks.json",
        backup_dir: str | Path = "backup",
        export_dir: str | Path = "exports",
    ) -> None:
        self.data_file = Path(data_file)
        self.backup_dir = Path(backup_dir)
        self.export_dir = Path(export_dir)
        self._ensure_data_file()

    # ------------------------------------------------------------------
    # JSON database
    # ------------------------------------------------------------------
    def _ensure_data_file(self) -> None:
        """Create the data file with an empty list if it does not exist."""
        try:
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            if not self.data_file.exists():
                self.data_file.write_text("[]", encoding="utf-8")
        except OSError as exc:
            raise StorageError(f"Gagal menyiapkan file data: {exc}") from exc

    def load(self) -> list[dict[str, Any]]:
        """Load raw task dictionaries from the JSON database.

        Raises:
            CorruptedDataError: If the JSON file cannot be parsed.
            StorageError: If the file cannot be read.
        """
        try:
            raw = self.data_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            self._ensure_data_file()
            return []
        except OSError as exc:
            raise StorageError(f"Gagal membaca file data: {exc}") from exc

        try:
            data = json.loads(raw or "[]")
        except json.JSONDecodeError as exc:
            raise CorruptedDataError(
                f"File '{self.data_file}' rusak atau bukan JSON valid: {exc}"
            ) from exc

        if not isinstance(data, list):
            raise CorruptedDataError(
                f"File '{self.data_file}' harus berisi list JSON."
            )
        return data

    def save(self, records: list[dict[str, Any]]) -> None:
        """Persist task dictionaries to the JSON database (atomic write).

        Raises:
            StorageError: If the file cannot be written.
        """
        tmp_file = self.data_file.with_suffix(".tmp")
        try:
            tmp_file.write_text(
                json.dumps(records, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            tmp_file.replace(self.data_file)
        except OSError as exc:
            raise StorageError(f"Gagal menyimpan file data: {exc}") from exc

    # ------------------------------------------------------------------
    # Backup & restore
    # ------------------------------------------------------------------
    def create_backup(self) -> Path:
        """Copy the current database into the backup folder.

        Returns:
            Path of the created backup file.
        """
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime(BACKUP_TIMESTAMP_FORMAT)
            backup_path = self.backup_dir / f"tasks_backup_{timestamp}.json"
            shutil.copy2(self.data_file, backup_path)
            return backup_path
        except OSError as exc:
            raise StorageError(f"Gagal membuat backup: {exc}") from exc

    def list_backups(self) -> list[Path]:
        """Return available backup files sorted from newest to oldest."""
        if not self.backup_dir.exists():
            return []
        return sorted(
            self.backup_dir.glob("tasks_backup_*.json"),
            key=lambda path: path.name,
            reverse=True,
        )

    def restore_backup(self, backup_path: str | Path) -> None:
        """Replace the current database with a backup file.

        Raises:
            BackupNotFoundError: If the backup file does not exist.
            CorruptedDataError: If the backup file contains invalid JSON.
        """
        path = Path(backup_path)
        if not path.exists():
            raise BackupNotFoundError(f"File backup '{path}' tidak ditemukan.")
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CorruptedDataError(
                f"File backup '{path}' rusak dan tidak dapat direstore."
            ) from exc
        try:
            shutil.copy2(path, self.data_file)
        except OSError as exc:
            raise StorageError(f"Gagal merestore backup: {exc}") from exc

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    _EXPORT_COLUMNS = (
        "id",
        "title",
        "description",
        "category",
        "priority",
        "deadline",
        "status",
        "created_at",
    )

    def _export_path(self, extension: str) -> Path:
        """Build a timestamped export file path."""
        self.export_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime(BACKUP_TIMESTAMP_FORMAT)
        return self.export_dir / f"tasks_export_{timestamp}.{extension}"

    def export_csv(self, records: list[dict[str, Any]]) -> Path:
        """Export task dictionaries to a CSV file.

        Returns:
            Path of the created CSV file.
        """
        path = self._export_path("csv")
        try:
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(
                    handle, fieldnames=self._EXPORT_COLUMNS, extrasaction="ignore"
                )
                writer.writeheader()
                writer.writerows(records)
            return path
        except OSError as exc:
            raise StorageError(f"Gagal export CSV: {exc}") from exc

    def export_txt(self, records: list[dict[str, Any]]) -> Path:
        """Export task dictionaries to a human-readable TXT file.

        Returns:
            Path of the created TXT file.
        """
        path = self._export_path("txt")
        lines: list[str] = ["TASKFLOW CLI - EXPORT", "=" * 40, ""]
        for record in records:
            lines.append(f"[{record.get('id')}] {record.get('title')}")
            lines.append(f"    Deskripsi : {record.get('description')}")
            lines.append(f"    Kategori  : {record.get('category')}")
            lines.append(f"    Prioritas : {record.get('priority')}")
            lines.append(f"    Deadline  : {record.get('deadline')}")
            lines.append(f"    Status    : {record.get('status')}")
            lines.append(f"    Dibuat    : {record.get('created_at')}")
            lines.append("")
        try:
            path.write_text("\n".join(lines), encoding="utf-8")
            return path
        except OSError as exc:
            raise StorageError(f"Gagal export TXT: {exc}") from exc
