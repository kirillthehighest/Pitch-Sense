"""The server's self-test (``pitchsense-server --self-test``, ``python -m app.api --self-test``):
the server on a free port of this computer, over the real data, answering every kind of question
the interface asks, with every league's predictions computed in the worker process as in use.
It prints one line per check and returns 0 when all pass; the packages are checked with it,
since the window itself needs a screen."""

import json
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable

import uvicorn

from app.api.backend import Backend
from app.api.server import create_app
from app.services.images import stadium_teams

HOST = "127.0.0.1"
READY_WAIT = 600  # seconds for every league's predictions (about 8 s each)


def run_self_test(backend: Backend, report: Callable[[str], None] = print) -> int:
    """Serve ``backend`` and ask it everything; 0 when every check passes."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind((HOST, 0))
    base = f"http://{HOST}:{listener.getsockname()[1]}"
    server = uvicorn.Server(uvicorn.Config(create_app(backend), log_level="warning"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    failures = 0

    def get(path: str) -> tuple[bytes, str]:
        try:
            with urllib.request.urlopen(base + path, timeout=120) as answer:
                return answer.read(), answer.headers.get("content-type", "")
        except urllib.error.HTTPError as error:
            error.close()  # its answer is open until closed
            raise RuntimeError(f"{error.code} {error.reason}: {path}") from None

    def check(name: str, test: Callable[[], str]) -> None:
        nonlocal failures
        try:
            report(f"ok      {name}: {test()}")
        except Exception as error:  # every check reports, the next ones still run
            failures += 1
            report(f"FAILED  {name}: {error}")

    def answer(path: str) -> dict | list:
        return json.loads(get(path)[0])

    try:
        while not server.started:
            time.sleep(0.05)
        backend.prepare_all()
        deadline = time.monotonic() + READY_WAIT
        while backend.preparing() is not None or not all(
            backend.is_prepared(code) or backend.failure(code) for code in backend.competitions
        ):
            if time.monotonic() > deadline:
                break
            time.sleep(0.5)
        status = answer("/api/status")
        check("predictions", lambda: _prepared(status))
        leagues = answer("/api/leagues")
        code = leagues[0]["code"]
        check("leagues", lambda: f"{len(leagues)} ({', '.join(item['code'] for item in leagues)})")
        days = answer("/api/days")
        day = answer(f"/api/day/{days['next_day']}?league={code}")
        check(
            "day",
            lambda: (
                f"{days['next_day']}, {sum(len(g['forecasts']) for g in day['leagues'])} matches"
            ),
        )
        forecast = day["leagues"][0]["forecasts"][0]
        query = urllib.parse.urlencode(
            {
                "season": forecast["season"],
                "day": forecast["date"],
                "home": forecast["home_team"],
                "away": forecast["away_team"],
            }
        )
        check("match", lambda: _match(answer(f"/api/match/{forecast['competition']}?{query}")))
        check("standings", lambda: f"{len(answer(f'/api/standings/{code}')['rows'])} teams")
        check("team", lambda: answer(f"/api/team/{code}")["team"])
        model = urllib.parse.quote("Logistic regression")
        check(
            "predictions review",
            lambda: f"{answer(f'/api/review/{code}?model={model}')['matches']} matches",
        )
        check("evaluation", lambda: _evaluation(answer(f"/api/evaluation/{code}")))
        check(
            "leagues comparison", lambda: f"{answer('/api/leagues-comparison')['matches']} matches"
        )
        check("explanations", lambda: f"{len(answer('/api/about')['explanations'])} cards")
        team = forecast["home_team"]
        pictured = stadium_teams()  # a club with a stadium photo, this one when it has one
        stadium = team if team in pictured or not pictured else pictured[0]
        for kind, path in (
            ("crest", f"/api/images/crest/{urllib.parse.quote(team)}"),
            ("league image", f"/api/images/league/{code}"),
            ("stadium photo", f"/api/images/stadium/{urllib.parse.quote(stadium)}"),
        ):
            check(kind, lambda path=path: _image(*get(path)))
    finally:
        server.should_exit = True
        thread.join(timeout=10)
    report("all checks passed" if failures == 0 else f"{failures} checks failed")
    return 0 if failures == 0 else 1


def _prepared(status: dict) -> str:
    missing = [code for code, done in status["prepared"].items() if not done]
    if missing:
        raise RuntimeError(f"not prepared: {', '.join(missing)}; failures {status['failures']}")
    return f"{len(status['prepared'])} leagues"


def _match(page: dict) -> str:
    if not page["forecast"]["predictions"]:
        raise RuntimeError("no model predicted the match")
    return f"{page['forecast']['home_team']} – {page['forecast']['away_team']}, {page['status']}"


def _evaluation(evaluation: dict) -> str:
    if evaluation["problem"] or not evaluation["models"]:
        raise RuntimeError(evaluation["problem"] or "no prediction log")
    return f"{evaluation['matches']} matches, {len(evaluation['models'])} models"


def _image(data: bytes, kind: str) -> str:
    if not kind.startswith("image/") or not data:
        raise RuntimeError(f"not an image: {kind}")
    return f"{kind}, {len(data) // 1024} KB"
