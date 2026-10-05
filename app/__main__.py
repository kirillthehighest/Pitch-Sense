"""Start PitchSense with ``python -m app``; also the entry point of the packaged application.

``--self-test`` opens the window off-screen, uses every tab once and exits with 0 when
everything worked (see ``app/ui/self_test.py``).
"""

import sys

from app.data.paths import use_persistent_matplotlib_cache

use_persistent_matplotlib_cache()  # before anything imports matplotlib

from app.ui.main_window import main  # noqa: E402
from app.ui.self_test import run_self_test  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(run_self_test() if "--self-test" in sys.argv[1:] else main())
