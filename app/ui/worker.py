"""Run slow work off the user-interface thread and deliver the outcome on the UI thread.

``run_in_background`` executes a function in Qt's global thread pool. The result (or the error
message) travels back through a signal to an object created on the UI thread, so the callbacks
always run on the UI thread and worker threads never touch widgets. ``run_now`` does the same
work immediately; tests use it.

A thread still shares the interpreter with the window: a long computation in Python makes every
step of the window wait for it, and the window stutters. ``compute_in_process`` runs such a job
in a separate process instead (Phase 21) and returns its result pickled, so the window decides
when to spend the moment of unpickling it. ``compute_here`` does the same in the calling
process; tests use it.
"""

import multiprocessing
import pickle
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

Runner = Callable[[Callable[[], Any], Callable[[Any], None], Callable[[str], None]], None]

_pending: set[_Delivery] = set()  # keeps each delivery object alive until its task ends


class _Delivery(QObject):
    """Lives on the UI thread; its slots call the callbacks there."""

    finished = Signal(object)
    failed = Signal(str)

    def __init__(
        self, on_finished: Callable[[Any], None], on_failed: Callable[[str], None]
    ) -> None:
        super().__init__()
        self._on_finished = on_finished
        self._on_failed = on_failed
        self.finished.connect(self._deliver_result)
        self.failed.connect(self._deliver_error)

    @Slot(object)
    def _deliver_result(self, result: Any) -> None:
        _pending.discard(self)
        self._on_finished(result)

    @Slot(str)
    def _deliver_error(self, message: str) -> None:
        _pending.discard(self)
        self._on_failed(message)


class _Task(QRunnable):
    def __init__(self, function: Callable[[], Any], delivery: _Delivery) -> None:
        super().__init__()
        self._function = function
        self._delivery = delivery

    def run(self) -> None:
        try:
            result = self._function()
        except Exception as error:  # every failure is reported to the window, none is lost
            self._delivery.failed.emit(str(error))
            return
        self._delivery.finished.emit(result)


def run_in_background(
    function: Callable[[], Any],
    on_finished: Callable[[Any], None],
    on_failed: Callable[[str], None],
) -> None:
    """Run ``function`` on a worker thread; call one of the callbacks on the UI thread."""
    delivery = _Delivery(on_finished, on_failed)
    _pending.add(delivery)
    QThreadPool.globalInstance().start(_Task(function, delivery))


def run_now(
    function: Callable[[], Any],
    on_finished: Callable[[Any], None],
    on_failed: Callable[[str], None],
) -> None:
    """Run ``function`` immediately on the calling thread, with the same callbacks."""
    try:
        result = function()
    except Exception as error:  # same contract as run_in_background
        on_failed(str(error))
        return
    on_finished(result)


Computer = Callable[[Callable[[], Any]], bytes]

_processes: ProcessPoolExecutor | None = None


def compute_in_process(job: Callable[[], Any]) -> bytes:
    """Run a picklable ``job`` in the worker process and wait for it (call from a worker
    thread); returns the pickled result. One process serves every job, one at a time."""
    global _processes
    if _processes is None:
        _processes = ProcessPoolExecutor(
            max_workers=1, mp_context=multiprocessing.get_context("spawn")
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


def _pickled(job: Callable[[], Any]) -> bytes:
    return pickle.dumps(job(), protocol=pickle.HIGHEST_PROTOCOL)
