"""Start PitchSense with ``python -m app``; also the entry point of the packaged application.

``--self-test`` opens the window off-screen, uses every screen once and exits with 0 when
everything worked (see ``app/ui/self_test.py``). ``--update`` downloads the season in progress,
as the window's "Actualizează datele" button does, and exits with 0 when it worked (see
``app/data/update.py``); a package then keeps the files in the user's folder.
"""

import sys

from app.data.paths import use_persistent_matplotlib_cache


def run(arguments: list[str]) -> int:
    """Run what the command line asks for and return the exit code; the window by default."""
    if "--update" in arguments:
        from app.data.update import main as update

        return update()
    use_persistent_matplotlib_cache()  # before anything imports matplotlib
    if "--self-test" in arguments:
        from app.ui.self_test import run_self_test

        return run_self_test()
    from app.ui.main_window import main

    return main()


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
