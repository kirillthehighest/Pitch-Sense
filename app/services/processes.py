"""Long computations in a separate process (Phase 21).

A thread shares the Python interpreter with the program that started it: a long computation in
Python makes every step of a window, or every answer of a server, wait for it.
``compute_in_process`` runs a job in one worker process instead and returns its result pickled,
so the caller decides when to spend the moment of unpickling it. ``compute_here`` does the same
in the calling process; tests use it. The worker ends with the process that started it, even
when that one is killed.
"""

import multiprocessing
import multiprocessing.connection
import os
import pickle
import threading
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from typing import Any

Computer = Callable[[Callable[[], Any]], bytes]

_processes: ProcessPoolExecutor | None = None


def compute_in_process(job: Callable[[], Any]) -> bytes:
    """Run a picklable ``job`` in the worker process and wait for it (call from a worker
    thread); returns the pickled result. One process serves every job, one at a time."""
    global _processes
    if _processes is None:
        _processes = ProcessPoolExecutor(
            max_workers=1,
            mp_context=multiprocessing.get_context("spawn"),
            initializer=_exit_with_parent,
        )
    return _processes.submit(_pickled, job).result()


def compute_here(job: Callable[[], Any]) -> bytes:
    """Run ``job`` in this process, with the same contract as ``compute_in_process``."""
    return _pickled(job)


def stop_processes() -> None:
    """Stop the worker process at once, with any job it runs (the window is closing)."""
    global _processes
    if _processes is None:
        return
    processes = list(getattr(_processes, "_processes", {}).values())
    _processes.shutdown(wait=False, cancel_futures=True)
    for process in processes:
        process.terminate()
    _processes = None


def _exit_with_parent() -> None:
    """In the worker process: end it as soon as the window's process ends, even when that one
    was killed and could not stop it (an orphan would go on computing)."""
    parent = multiprocessing.parent_process()
    if parent is None:
        return

    def watch() -> None:
        multiprocessing.connection.wait([parent.sentinel])
        os._exit(0)

    threading.Thread(target=watch, daemon=True).start()


def _pickled(job: Callable[[], Any]) -> bytes:
    return pickle.dumps(job(), protocol=pickle.HIGHEST_PROTOCOL)
