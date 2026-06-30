"""Worker entry point for Siakang Academic Monitoring.

This thin wrapper preserves the historical ``python main.py`` entry point that
``server/manager.py`` uses to spawn worker subprocesses. The implementation now
lives in the :mod:`worker` package (config, logging, notifications, monitors).
"""

from worker.runner import main

if __name__ == "__main__":
    main()
