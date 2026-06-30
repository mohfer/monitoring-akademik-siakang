"""Worker entry point: build the appropriate monitor and run it.

Configuration is read from environment variables (see :mod:`worker.config`),
which ``server/manager.py`` injects when launching this worker as a subprocess.
"""

import atexit

from .config import config
from .monitors.krs import KrsMonitor
from .monitors.nilai import GradeMonitor
from .notifications import Notifier


def build_monitor():
    """Construct the monitor matching the configured MONITOR_TYPE."""
    notifier = Notifier(config)
    if config.monitor_type == "krs":
        return KrsMonitor(config, notifier)
    return GradeMonitor(config, notifier)


def main():
    monitor = build_monitor()
    atexit.register(monitor.session.close)
    monitor.run()
