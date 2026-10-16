"""Start the local server: ``python -m app.api [--port N] [--preferences FILE] [--with-window]``.

The server listens on this computer only (127.0.0.1). With port 0 (the default) the system picks
a free port; the first line written is ``PITCHSENSE_PORT=<port>``, which the desktop shell reads
to find the server. The predictions of every league are then computed in the worker process.
With ``--with-window`` (the desktop shell's option) the server ends when its standard input
closes, which happens when the window's process ends in any way, even killed.
"""

import multiprocessing
import os
import socket
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO

import uvicorn

from app.api.backend import Backend
from app.api.server import create_app
from app.data.live import copy_bundled_live
from app.data.paths import copy_bundled_results
from app.services.processes import stop_processes

HOST = "127.0.0.1"


def option(arguments: list[str], name: str) -> str | None:
    """The value given after ``name`` on the command line, if any."""
    if name not in arguments:
        return None
    index = arguments.index(name)
    if index + 1 >= len(arguments):
        raise SystemExit(f"{name} needs a value")
    return arguments[index + 1]


def port_of(arguments: list[str]) -> int:
    """The port asked for with ``--port N``; 0 lets the system choose."""
    value = option(arguments, "--port")
    try:
        return 0 if value is None else int(value)
    except ValueError:
        raise SystemExit("--port needs a number") from None


def end_server() -> None:
    """End this process at once: uvicorn would wait for open connections, and nobody is left."""
    stop_processes()
    os._exit(0)


def exit_with_window(window: BinaryIO, end: Callable[[], None] = end_server) -> threading.Thread:
    """Watch ``window`` (the pipe from the window's process) and call ``end`` when it closes."""

    def watch() -> None:
        window.read()  # returns only when the window's end of the pipe closes
        end()

    watcher = threading.Thread(target=watch, name="window-watch", daemon=True)
    watcher.start()
    return watcher


def main(arguments: list[str]) -> int:
    copy_bundled_results()  # a package ships its prediction logs read-only
    copy_bundled_live()  # and a snapshot of the season in progress
    preferences = option(arguments, "--preferences")  # developers: a file of their own
    backend = Backend.from_database(None if preferences is None else Path(preferences))
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind((HOST, port_of(arguments)))
    print(f"PITCHSENSE_PORT={listener.getsockname()[1]}", flush=True)
    if "--with-window" in arguments:
        exit_with_window(sys.stdin.buffer)
    backend.prepare_all()
    server = uvicorn.Server(uvicorn.Config(create_app(backend), log_level="warning"))
    try:
        server.run(sockets=[listener])
    finally:
        stop_processes()
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()  # a package starts its worker process through this file
    raise SystemExit(main(sys.argv[1:]))
