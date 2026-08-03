"""TaskFlow CLI — application entry point.

Keeps the entry point thin: all logic lives in the ``ui``,
``task_manager``, and ``storage`` modules.
"""

import sys

from exceptions import TaskFlowError
from ui import Menu, print_error


def main() -> int:
    """Bootstrap and run the TaskFlow CLI application."""
    try:
        Menu().run()
    except TaskFlowError as exc:
        print_error(f"Aplikasi berhenti: {exc}")
        return 1
    except KeyboardInterrupt:
        print("\nKeluar. Data tersimpan otomatis.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
