"""Start the local server: ``python -m app.api [--port N] [--preferences FILE] [--with-window]``,
check it: ``python -m app.api --self-test`` (``app/api/self_test.py``), or download the season in
progress and exit: ``python -m app.api --update`` (0 on success; the packages are checked with it).

The server listens on this computer only (127.0.0.1). With port 0 (the default) the system picks
a free port; the first line written is ``PITCHSENSE_PORT=<port>``, which the desktop shell reads
to find the server. The port is announced only once it accepts connections: the interface asks
at once, and before the fix the Windows package refused its first questions. The predictions
of every league are then read from the cache or computed in the worker process.
With ``--with-window`` (the desktop shell's option) the server ends when its standard input
closes, which happens when the window's process ends in any way, even killed.
"""

import io
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
from app.api.self_test import run_self_test
from app.api.server import create_app
from app.data.live import copy_bundled_live
from app.data.paths import copy_bundled_results
from app.services.processes import stop_processes
from app.services.updates import summary_text, update_season

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


def open_listener(port: int, host: str = HOST) -> socket.socket:
    """A socket bound to ``port`` (0: the system picks) and already listening, so connections
    made as soon as its port is known wait in its queue until uvicorn takes them; a socket only
    bound refuses them."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if os.name != "nt":  # a port just freed can be bound again; on Windows this would share it
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((host, port))
    listener.listen(socket.SOMAXCONN)
    return listener


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


def write_utf8() -> None:
    """Write the Romanian of --update and --self-test whatever the console's code page (Windows
    consoles are cp1252, which has no ș or ț)."""
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8", errors="replace")


def copy_bundled() -> None:
    """Copy what a package ships read-only to the user's folder: its prediction logs and its
    snapshot of the season in progress. A failure is reported and start-up goes on with what
    the folder holds."""
    for copy, failure in (
        (copy_bundled_results, "Jurnalele predicțiilor nu au putut fi copiate"),
        (copy_bundled_live, "Sezonul în desfășurare nu a putut fi copiat"),
    ):
        try:
            copy()
        except OSError as error:
            print(f"{failure}: {error}", file=sys.stderr, flush=True)


def main(arguments: list[str]) -> int:
    write_utf8()
    copy_bundled()
    if "--update" in arguments:
        print(summary_text(update_season()), flush=True)
        return 0
    preferences = option(arguments, "--preferences")  # developers: a file of their own
    try:
        backend = Backend.from_database(None if preferences is None else Path(preferences))
    except FileNotFoundError as error:  # the window shows this line (web/src-tauri/src/lib.rs)
        print(
            "Baza de date nu a fost găsită. Construiți-o cu python -m app.data.build_database și "
            f"porniți aplicația din nou. ({error})",
            file=sys.stderr,
            flush=True,
        )
        return 1
    if "--self-test" in arguments:
        try:
            return run_self_test(backend)
        finally:
            stop_processes()
    listener = open_listener(port_of(arguments))
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
