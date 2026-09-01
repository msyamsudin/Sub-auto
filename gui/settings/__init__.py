"""Settings package: modularized settings dialog.

Split from the former ``gui/settings_dialog.py`` god file. The dialog is
composed of focused mixins (general tab, per-provider frames, shared UI
helpers) combined by :class:`SettingsDialog` (see ``dialog.py``) so the
public widget API stays identical.
"""

from .dialog import SettingsDialog

__all__ = ["SettingsDialog"]
