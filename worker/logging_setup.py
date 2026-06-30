"""Console logging for the worker: timestamped, tag-colored output.

This replaces the previous anti-pattern of overriding the builtin ``print``.
Call ``log(...)`` instead of ``print(...)`` - the builtin stays untouched.
"""

import sys
from datetime import datetime

from colorama import Fore, Style, init

init(autoreset=True)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Tags are checked in order; the first one present colors the message,
# matching the original if/elif behavior.
_TAG_COLORS = (
    ("[ERROR]", Fore.RED),
    ("[GAGAL]", Fore.RED),
    ("[SUCCESS]", Fore.GREEN),
    ("[SUKSES]", Fore.GREEN),
    ("[WARNING]", Fore.YELLOW),
    ("[PERINGATAN]", Fore.YELLOW),
    ("[INFO]", Fore.CYAN),
    ("[UPDATE]", Fore.CYAN),
    ("[STATUS]", Fore.BLUE),
    ("[ALERT]", Fore.MAGENTA),
    ("[COMPLETE]", Fore.GREEN + Style.BRIGHT),
)


def log(*args, **kwargs):
    """Print a timestamped, tag-colored line to stdout."""
    now = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    msg = " ".join(str(arg) for arg in args)

    colored_msg = msg
    for tag, color in _TAG_COLORS:
        if tag in colored_msg:
            colored_msg = colored_msg.replace(tag, f"{color}{tag}{Style.RESET_ALL}")
            break

    print(f"{Fore.WHITE}{now}{Style.RESET_ALL}", colored_msg, **kwargs)
