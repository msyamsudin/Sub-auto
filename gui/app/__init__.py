"""Application package: modularized main window.

Split from the former ``gui/app.py`` god file. The window is composed of
focused mixins (UI setup, state sync, overlays, file selection, translation
flow, finalization) combined by :class:`SubAutoApp` (see ``app.py``). The
public API (``SubAutoApp`` and ``run_app``) stays identical, so ``main.py``
and any other importer keep working unchanged.
"""

from .app import SubAutoApp, run_app

__all__ = ["SubAutoApp", "run_app"]
