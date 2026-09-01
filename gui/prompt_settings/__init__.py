"""Prompt settings package: sidebar, editor, and action mixins.

Split from the former ``gui/prompt_settings_tab.py`` god file. The mixins are
combined by :class:`PromptSettingsTab` (see ``tab.py``) so the public widget
API stays identical while each concern lives in its own module.
"""

from .tab import PromptSettingsTab

__all__ = ["PromptSettingsTab"]
