"""Custom exception hierarchy for TaskFlow CLI.

Every domain-specific error inherits from :class:`TaskFlowError` so the
UI layer can catch a single base class and render a friendly message.
"""


class TaskFlowError(Exception):
    """Base exception for all TaskFlow CLI errors."""


class StorageError(TaskFlowError):
    """Raised when the JSON database cannot be read or written."""


class CorruptedDataError(StorageError):
    """Raised when the JSON database file contains invalid JSON."""


class FileNotFoundStorageError(StorageError):
    """Raised when a required storage file does not exist."""


class TaskNotFoundError(TaskFlowError):
    """Raised when a task with the requested ID does not exist."""

    def __init__(self, task_id: int) -> None:
        super().__init__(f"Task dengan ID {task_id} tidak ditemukan.")
        self.task_id = task_id


class EmptyInputError(TaskFlowError):
    """Raised when a required input field is left empty."""

    def __init__(self, field_name: str) -> None:
        super().__init__(f"Input '{field_name}' tidak boleh kosong.")
        self.field_name = field_name


class InvalidDateError(TaskFlowError):
    """Raised when a date string does not match the expected format."""

    def __init__(self, value: str, expected_format: str = "YYYY-MM-DD") -> None:
        super().__init__(
            f"Tanggal '{value}' tidak valid. Gunakan format {expected_format}."
        )
        self.value = value


class InvalidPriorityError(TaskFlowError):
    """Raised when a priority value is not Low, Medium, or High."""

    def __init__(self, value: str) -> None:
        super().__init__(
            f"Prioritas '{value}' tidak valid. Pilih: Low, Medium, atau High."
        )
        self.value = value


class InvalidStatusError(TaskFlowError):
    """Raised when a status value is not Pending or Completed."""

    def __init__(self, value: str) -> None:
        super().__init__(
            f"Status '{value}' tidak valid. Pilih: Pending atau Completed."
        )
        self.value = value


class InvalidMenuChoiceError(TaskFlowError):
    """Raised when the user selects a menu option that does not exist."""

    def __init__(self, choice: str) -> None:
        super().__init__(f"Pilihan menu '{choice}' tidak tersedia.")
        self.choice = choice


class BackupNotFoundError(TaskFlowError):
    """Raised when no backup file is available to restore."""

    def __init__(self, detail: str = "Tidak ada file backup yang ditemukan.") -> None:
        super().__init__(detail)
