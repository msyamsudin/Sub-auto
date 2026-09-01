"""
Import smoke test for the GUI package.

Importing the GUI modules does not require a display, so this test catches
broken imports/typos caused by GUI refactors (e.g. module moves, package
splits) without needing a window. It is skipped automatically when
customtkinter (and therefore tkinter) is unavailable -- e.g. on CI runners
without a Tk build.
"""

import importlib
import sys
from pathlib import Path

import pytest

pytest.importorskip("customtkinter", reason="customtkinter/tkinter not available")


def test_all_gui_modules_import():
    root = Path(__file__).parent.parent
    sys.path.insert(0, str(root))

    gui_pkg = root / "gui"
    modules = []
    for py in sorted(gui_pkg.rglob("*.py")):
        if py.name == "__init__.py":
            continue
        rel = py.relative_to(root).with_suffix("")
        modules.append(".".join(rel.parts))

    assert modules, "no GUI modules discovered"

    failed = []
    for module in modules:
        try:
            importlib.import_module(module)
        except Exception as exc:  # noqa: BLE001 - report every broken module
            failed.append(f"{module}: {type(exc).__name__}: {exc}")

    assert not failed, "GUI modules failed to import:\n" + "\n".join(failed)


def test_prompt_settings_package_reexports_tab():
    from gui.prompt_settings import PromptSettingsTab  # noqa: F401
    from gui.prompt_settings.tab import PromptSettingsTab as Direct  # noqa: F401
    assert PromptSettingsTab is Direct
