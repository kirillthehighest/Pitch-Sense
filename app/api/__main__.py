"""Start the local server: ``python -m app.api [--port N]``.

The server listens on this computer only (127.0.0.1). With port 0 (the default) the system picks
a free port; the first line written is ``PITCHSENSE_PORT=<port>``, which the desktop shell reads
to find the server. The predictions of every league are then computed in the worker process.
"""

import multiprocessing
import socket
import sys

import uvicorn

from app.api.backend import Backend
from app.api.server import create_app
from app.data.live import copy_bundled_live
from app.data.paths import copy_bundled_results
from app.services.processes import stop_processes

HOST = "127.0.0.1"


def port_of(arguments: list[str]) -> int:
    """The port asked for with ``--port N``; 0 lets the system choose."""
    if "--port" not in arguments:
        return 0
    index = arguments.index("--port")
    try:
        return int(arguments[index + 1])
    except IndexError, ValueError:
        raise SystemExit("--port needs a number") from None


def main(arguments: list[str]) -> int:
    copy_bundled_results()  # a package ships its prediction logs read-only
    copy_bundled_live()  # and a snapshot of the season in progress
    backend = Backend.from_database()
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind((HOST, port_of(arguments)))
    print(f"PITCHSENSE_PORT={listener.getsockname()[1]}", flush=True)
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
