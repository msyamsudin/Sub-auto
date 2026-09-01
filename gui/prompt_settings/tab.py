"""
Prompt Settings Tab for Sub-auto.
Composes the sidebar, editor, and action mixins into the full tab widget.
"""

from typing import Optional, Callable

import customtkinter as ctk

from ..styles import COLORS, SPACING, RADIUS
from core.prompt_manager import PromptManager
from core.prompt_schema import Prompt

from .sidebar import PromptSidebarMixin
from .editor import PromptEditorMixin
from .actions import PromptActionsMixin


class PromptSettingsTab(PromptSidebarMixin, PromptEditorMixin, PromptActionsMixin, ctk.CTkFrame):
    """Tab for managing translation prompts."""

    def __init__(
        self,
        parent,
        prompt_manager: PromptManager,
        on_active_prompt_change: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.prompt_manager = prompt_manager
        self.on_active_prompt_change = on_active_prompt_change
        self.selected_prompt: Optional[Prompt] = None

        self._setup_ui()
        self._load_prompts()

    def _setup_ui(self):
        """Setup the UI layout."""
        # Main container with two columns
        self.grid_columnconfigure(0, weight=1, minsize=260)  # Reduced minsize slightly
        self.grid_columnconfigure(1, weight=3)  # Balanced ratio back to 1:3 for a more standard look
        self.grid_rowconfigure(0, weight=1)

        # Left: Prompt List
        self._setup_prompt_list()

        # Right: Prompt Editor
        self._setup_prompt_editor()
