"""Presentation layer for TaskFlow CLI.

Contains ANSI color helpers, the ASCII banner, loading animation,
progress bar, table renderer, :class:`Dashboard`, and :class:`Menu`.
No business logic lives here — everything is delegated to
:class:`~task_manager.TaskManager` and :class:`~storage.StorageManager`.
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime

from exceptions import InvalidMenuChoiceError, TaskFlowError
from storage import StorageManager
from task import Priority, Status, Task
from task_manager import TaskManager

# Enable ANSI escape sequences on Windows terminals.
os.system("")


class Colors:
    """ANSI escape codes used across the UI."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"


BANNER = rf"""{Colors.CYAN}{Colors.BOLD}
 _____         _    _____ _
|_   _|_ _ ___| | _|  ___| | _____      __
  | |/ _` / __| |/ /| |_  | |/ _ \ \ /\ / /
  | | (_| \__ \   < |  _| | | (_) \ V  V /
  |_|\__,_|___/_|\_\|_|   |_|\___/ \_/\_/  CLI
{Colors.RESET}"""

LINE = "=" * 53

_PRIORITY_COLORS = {
    Priority.HIGH: Colors.RED,
    Priority.MEDIUM: Colors.YELLOW,
    Priority.LOW: Colors.GREEN,
}

_STATUS_COLORS = {
    Status.PENDING: Colors.YELLOW,
    Status.COMPLETED: Colors.GREEN,
}


# ----------------------------------------------------------------------
# Generic terminal helpers
# ----------------------------------------------------------------------
def clear_screen() -> None:
    """Clear the terminal screen (Windows and POSIX)."""
    os.system("cls" if os.name == "nt" else "clear")


def show_loading(message: str = "Memproses", duration: float = 0.6) -> None:
    """Render a short spinner animation with a message."""
    frames = ["|", "/", "-", "\\"]
    end_time = time.time() + duration
    index = 0
    while time.time() < end_time:
        sys.stdout.write(f"\r{Colors.CYAN}{message} {frames[index % 4]}{Colors.RESET}")
        sys.stdout.flush()
        time.sleep(0.08)
        index += 1
    sys.stdout.write("\r" + " " * (len(message) + 4) + "\r")
    sys.stdout.flush()


def render_progress_bar(completed: int, total: int, width: int = 30) -> str:
    """Build a colored progress bar string for task completion."""
    ratio = completed / total if total else 0.0
    filled = int(width * ratio)
    bar = "█" * filled + "░" * (width - filled)
    return f"{Colors.GREEN}[{bar}]{Colors.RESET} {ratio * 100:.1f}%"


def truncate(text: str, width: int) -> str:
    """Truncate text with an ellipsis so it fits a table column."""
    return text if len(text) <= width else text[: width - 1] + "…"


def print_success(message: str) -> None:
    """Print a green success message."""
    print(f"{Colors.GREEN}[OK] {message}{Colors.RESET}")


def print_error(message: str) -> None:
    """Print a red error message."""
    print(f"{Colors.RED}[ERROR] {message}{Colors.RESET}")


def print_info(message: str) -> None:
    """Print a cyan informational message."""
    print(f"{Colors.CYAN}[INFO] {message}{Colors.RESET}")


def print_task_table(tasks: list[Task]) -> None:
    """Render tasks as a formatted terminal table."""
    if not tasks:
        print_info("Belum ada task untuk ditampilkan.")
        return

    header = (
        f"{'ID':<4} {'Judul':<26} {'Kategori':<12} "
        f"{'Prioritas':<10} {'Deadline':<12} {'Status':<10}"
    )
    print(Colors.BOLD + header + Colors.RESET)
    print("-" * len(header))
    for task in tasks:
        priority_color = _PRIORITY_COLORS[task.priority]
        status_color = _STATUS_COLORS[task.status]
        overdue_mark = f" {Colors.RED}!{Colors.RESET}" if task.is_overdue() else ""
        print(
            f"{task.id:<4} "
            f"{truncate(task.title, 26):<26} "
            f"{truncate(task.category, 12):<12} "
            f"{priority_color}{task.priority.value:<10}{Colors.RESET} "
            f"{task.deadline:<12} "
            f"{status_color}{task.status.value:<10}{Colors.RESET}"
            f"{overdue_mark}"
        )


def print_task_detail(task: Task) -> None:
    """Render a single task with all of its fields."""
    print(f"{Colors.BOLD}Task #{task.id}{Colors.RESET}")
    print(f"  Judul      : {task.title}")
    print(f"  Deskripsi  : {task.description or '-'}")
    print(f"  Kategori   : {task.category}")
    print(f"  Prioritas  : {task.priority.value}")
    print(f"  Deadline   : {task.deadline}")
    print(f"  Status     : {task.status.value}")
    print(f"  Dibuat     : {task.created_at}")
    print(f"  Diperbarui : {task.updated_at or '-'}")
    print(f"  Selesai    : {task.completed_at or '-'}")


# ----------------------------------------------------------------------
# Input helpers
# ----------------------------------------------------------------------
def prompt(label: str) -> str:
    """Read a raw input with a colored prompt label."""
    return input(f"{Colors.CYAN}{label}{Colors.RESET} ").strip()


def prompt_int(label: str) -> int:
    """Read an integer, re-prompting until valid."""
    while True:
        value = prompt(label)
        try:
            return int(value)
        except ValueError:
            print_error(f"'{value}' bukan angka yang valid.")


def prompt_confirm(label: str) -> bool:
    """Ask a yes/no confirmation. Returns ``True`` for 'y'."""
    return prompt(f"{label} (y/n):").lower() == "y"


class Dashboard:
    """Render the dashboard header with live statistics."""

    def __init__(self, manager: TaskManager) -> None:
        self._manager = manager

    def render(self) -> None:
        """Print banner, current time, statistics, and progress bar."""
        stats = self._manager.get_statistics()
        now = datetime.now().strftime("%A, %d %B %Y %H:%M:%S")
        print(BANNER)
        print(LINE)
        print(f"  Waktu Sekarang   : {now}")
        print(f"  Total Task       : {stats['total']}")
        print(f"  Completed        : {Colors.GREEN}{stats['completed']}{Colors.RESET}")
        print(f"  Pending          : {Colors.YELLOW}{stats['pending']}{Colors.RESET}")
        print(f"  Deadline Hari Ini: {Colors.RED}{stats['due_today']}{Colors.RESET}")
        print(f"  Progress         : "
              f"{render_progress_bar(int(stats['completed']), int(stats['total']))}")
        print(LINE)
        self._render_notifications()

    def _render_notifications(self) -> None:
        """Show deadline notifications for due-today and overdue tasks."""
        due_today = [
            task
            for task in self._manager.tasks
            if task.is_due_today() and not task.is_completed()
        ]
        overdue = [task for task in self._manager.tasks if task.is_overdue()]
        for task in due_today:
            print(
                f"{Colors.YELLOW}  [DEADLINE HARI INI] "
                f"#{task.id} {task.title}{Colors.RESET}"
            )
        for task in overdue:
            print(
                f"{Colors.RED}  [TERLAMBAT] #{task.id} {task.title} "
                f"(deadline {task.deadline}){Colors.RESET}"
            )
        if due_today or overdue:
            print(LINE)


class Menu:
    """Interactive menu loop — the application's controller."""

    def __init__(
        self,
        manager: TaskManager | None = None,
        storage: StorageManager | None = None,
    ) -> None:
        self._storage = storage or StorageManager()
        self._manager = manager or TaskManager(self._storage)
        self._dashboard = Dashboard(self._manager)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    def run(self) -> None:
        """Run the main application loop until the user exits."""
        while True:
            clear_screen()
            self._dashboard.render()
            print("  1. Dashboard")
            print("  2. Task")
            print("  3. Statistics")
            print("  4. Backup")
            print("  5. Export")
            print("  0. Exit")
            print(LINE)
            choice = prompt("Pilih menu:")
            try:
                if choice == "1":
                    continue  # Dashboard is re-rendered on every loop.
                elif choice == "2":
                    self._task_menu()
                elif choice == "3":
                    self._show_statistics()
                elif choice == "4":
                    self._backup_menu()
                elif choice == "5":
                    self._export_menu()
                elif choice == "0":
                    print_info("Sampai jumpa! Data tersimpan otomatis.")
                    break
                else:
                    raise InvalidMenuChoiceError(choice)
            except TaskFlowError as exc:
                print_error(str(exc))
                self._pause()

    # ------------------------------------------------------------------
    # Task submenu
    # ------------------------------------------------------------------
    def _task_menu(self) -> None:
        """Handle the Task submenu (CRUD, search, complete, sort, filter)."""
        actions = {
            "1": self._add_task,
            "2": self._view_tasks,
            "3": self._update_task,
            "4": self._delete_task,
            "5": self._search_tasks,
            "6": self._complete_task,
            "7": self._sort_tasks,
            "8": self._filter_tasks,
        }
        while True:
            clear_screen()
            print(f"{Colors.BOLD}--- MENU TASK ---{Colors.RESET}")
            print("  1. Tambah Task")
            print("  2. Lihat Semua Task")
            print("  3. Update Task")
            print("  4. Hapus Task")
            print("  5. Cari Task")
            print("  6. Tandai Selesai")
            print("  7. Sorting")
            print("  8. Filter")
            print("  0. Kembali")
            choice = prompt("Pilih menu:")
            if choice == "0":
                return
            action = actions.get(choice)
            try:
                if action is None:
                    raise InvalidMenuChoiceError(choice)
                action()
            except TaskFlowError as exc:
                print_error(str(exc))
            self._pause()

    def _add_task(self) -> None:
        """Prompt for task fields and create a new task."""
        print(f"\n{Colors.BOLD}Tambah Task Baru{Colors.RESET}")
        title = prompt("Judul       :")
        description = prompt("Deskripsi   :")
        category = prompt("Kategori    :")
        deadline = prompt("Deadline (YYYY-MM-DD):")
        priority = prompt("Prioritas (Low/Medium/High):")
        show_loading("Menyimpan task")
        task = self._manager.add_task(title, description, category, priority, deadline)
        print_success(f"Task #{task.id} '{task.title}' berhasil ditambahkan.")

    def _view_tasks(self) -> None:
        """Show every task in a table."""
        print()
        print_task_table(self._manager.tasks)

    def _update_task(self) -> None:
        """Prompt for a task ID and update its fields (blank = skip)."""
        task_id = prompt_int("ID task yang akan diupdate:")
        task = self._manager.get_task(task_id)
        print_task_detail(task)
        print_info("Kosongkan input untuk mempertahankan nilai lama.")
        changes = {
            "title": prompt("Judul baru      :"),
            "description": prompt("Deskripsi baru  :"),
            "category": prompt("Kategori baru   :"),
            "priority": prompt("Prioritas baru  :"),
            "deadline": prompt("Deadline baru   :"),
            "status": prompt("Status baru     :"),
        }
        show_loading("Memperbarui task")
        updated = self._manager.update_task(task_id, **changes)
        print_success(f"Task #{updated.id} berhasil diperbarui.")

    def _delete_task(self) -> None:
        """Delete a task after explicit confirmation."""
        task_id = prompt_int("ID task yang akan dihapus:")
        task = self._manager.get_task(task_id)
        print_task_detail(task)
        if not prompt_confirm(f"Yakin ingin menghapus task #{task.id}?"):
            print_info("Penghapusan dibatalkan.")
            return
        show_loading("Menghapus task")
        self._manager.delete_task(task_id)
        print_success(f"Task #{task_id} berhasil dihapus.")

    def _search_tasks(self) -> None:
        """Search tasks by title, category, priority, or status."""
        fields = {"1": "title", "2": "category", "3": "priority", "4": "status"}
        print("  1. Judul  2. Kategori  3. Prioritas  4. Status")
        choice = prompt("Cari berdasarkan:")
        field = fields.get(choice)
        if field is None:
            raise InvalidMenuChoiceError(choice)
        keyword = prompt("Kata kunci:")
        results = self._manager.search_tasks(field, keyword)
        print_info(f"Ditemukan {len(results)} task.")
        print_task_table(results)

    def _complete_task(self) -> None:
        """Mark a task as completed."""
        task_id = prompt_int("ID task yang selesai:")
        show_loading("Menandai selesai")
        task = self._manager.mark_completed(task_id)
        print_success(f"Task #{task.id} '{task.title}' ditandai Completed.")

    def _sort_tasks(self) -> None:
        """Show tasks sorted by deadline, priority, or created_at."""
        keys = {"1": "deadline", "2": "priority", "3": "created_at"}
        print("  1. Deadline  2. Prioritas  3. Tanggal Dibuat")
        choice = prompt("Urutkan berdasarkan:")
        key = keys.get(choice)
        if key is None:
            raise InvalidMenuChoiceError(choice)
        print_task_table(self._manager.sort_tasks(key))

    def _filter_tasks(self) -> None:
        """Show tasks filtered by category, status, or priority."""
        fields = {"1": "category", "2": "status", "3": "priority"}
        print("  1. Kategori  2. Status  3. Prioritas")
        choice = prompt("Filter berdasarkan:")
        field = fields.get(choice)
        if field is None:
            raise InvalidMenuChoiceError(choice)
        value = prompt("Nilai filter:")
        results = self._manager.filter_tasks(field, value)
        print_info(f"Ditemukan {len(results)} task.")
        print_task_table(results)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------
    def _show_statistics(self) -> None:
        """Render the full statistics view."""
        stats = self._manager.get_statistics()
        clear_screen()
        print(f"{Colors.BOLD}--- STATISTIK ---{Colors.RESET}")
        print(f"  Total Task        : {stats['total']}")
        print(f"  Completed         : {Colors.GREEN}{stats['completed']}{Colors.RESET}")
        print(f"  Pending           : {Colors.YELLOW}{stats['pending']}{Colors.RESET}")
        print(f"  High Priority     : {Colors.RED}{stats['high_priority']}{Colors.RESET}")
        print(f"  Deadline Hari Ini : {stats['due_today']}")
        print(f"  Terlambat         : {stats['overdue']}")
        print(f"  Penyelesaian      : "
              f"{render_progress_bar(int(stats['completed']), int(stats['total']))}")
        self._pause()

    # ------------------------------------------------------------------
    # Backup submenu
    # ------------------------------------------------------------------
    def _backup_menu(self) -> None:
        """Handle backup creation and restore."""
        clear_screen()
        print(f"{Colors.BOLD}--- BACKUP ---{Colors.RESET}")
        print("  1. Buat Backup")
        print("  2. Restore Backup")
        print("  0. Kembali")
        choice = prompt("Pilih menu:")
        if choice == "1":
            show_loading("Membuat backup")
            path = self._storage.create_backup()
            print_success(f"Backup dibuat: {path}")
        elif choice == "2":
            self._restore_backup()
        elif choice != "0":
            raise InvalidMenuChoiceError(choice)
        if choice != "0":
            self._pause()

    def _restore_backup(self) -> None:
        """List available backups and restore the chosen one."""
        backups = self._storage.list_backups()
        if not backups:
            print_error("Belum ada file backup di folder backup/.")
            return
        for index, path in enumerate(backups, start=1):
            print(f"  {index}. {path.name}")
        number = prompt_int("Pilih nomor backup:")
        if not 1 <= number <= len(backups):
            raise InvalidMenuChoiceError(str(number))
        if not prompt_confirm("Data saat ini akan ditimpa. Lanjutkan?"):
            print_info("Restore dibatalkan.")
            return
        show_loading("Merestore backup")
        self._storage.restore_backup(backups[number - 1])
        self._manager.reload()
        print_success("Backup berhasil direstore.")

    # ------------------------------------------------------------------
    # Export submenu
    # ------------------------------------------------------------------
    def _export_menu(self) -> None:
        """Export tasks to CSV or TXT."""
        clear_screen()
        print(f"{Colors.BOLD}--- EXPORT ---{Colors.RESET}")
        print("  1. Export ke CSV")
        print("  2. Export ke TXT")
        print("  0. Kembali")
        choice = prompt("Pilih menu:")
        records = [task.to_dict() for task in self._manager.tasks]
        if choice == "1":
            show_loading("Mengekspor CSV")
            print_success(f"Export selesai: {self._storage.export_csv(records)}")
        elif choice == "2":
            show_loading("Mengekspor TXT")
            print_success(f"Export selesai: {self._storage.export_txt(records)}")
        elif choice != "0":
            raise InvalidMenuChoiceError(choice)
        if choice != "0":
            self._pause()

    @staticmethod
    def _pause() -> None:
        """Wait for the user before returning to the previous screen."""
        input(f"\n{Colors.DIM}Tekan Enter untuk melanjutkan...{Colors.RESET}")
