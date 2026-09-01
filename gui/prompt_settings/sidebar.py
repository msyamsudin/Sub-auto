"""
Prompt sidebar mixin for the prompt settings tab.
Handles the prompt list, active-prompt indicator, item rendering, and
selection visuals. Combines with PromptEditorMixin and PromptActionsMixin
into the single PromptSettingsTab widget.
"""

from typing import Optional, Dict

import customtkinter as ctk

from ..styles import COLORS, FONTS, SPACING, RADIUS, get_button_style, get_label_style
from core.prompt_schema import Prompt


class PromptSidebarMixin:
    """Sidebar (left column) of the prompt settings tab."""

    SIDEBAR_TIME_FORMAT = "%d %b %H:%M"

    def _setup_prompt_list(self):
        """Setup the prompt list on the left side."""
        list_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_medium"], corner_radius=RADIUS["md"])
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, SPACING["md"]))
        list_frame.grid_rowconfigure(2, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkLabel(
            list_frame,
            text="📝 Prompts",
            font=(FONTS["family"], FONTS["subheading_size"], "bold"),
            text_color=COLORS["text_primary"]
        )
        header.grid(row=0, column=0, sticky="w", padx=SPACING["md"], pady=(SPACING["md"], SPACING["xs"]))

        # Active prompt indicator banner
        self.active_indicator_frame = ctk.CTkFrame(
            list_frame,
            fg_color=COLORS["success_bg"],
            corner_radius=RADIUS["sm"]
        )
        self.active_indicator_frame.grid(row=1, column=0, sticky="ew", padx=SPACING["sm"], pady=(0, SPACING["xs"]))
        self.active_indicator_frame.grid_columnconfigure(0, weight=1)

        self.active_indicator_label = ctk.CTkLabel(
            self.active_indicator_frame,
            text="No active prompt",
            font=(FONTS["family"], FONTS["small_size"]),
            text_color=COLORS["success"],
            anchor="w"
        )
        self.active_indicator_label.grid(row=0, column=0, sticky="ew", padx=SPACING["sm"], pady=SPACING["xs"])

        # Scrollable list
        self.prompt_scroll = ctk.CTkScrollableFrame(
            list_frame,
            fg_color="transparent"
        )
        self.prompt_scroll.grid(row=2, column=0, sticky="nsew", padx=SPACING["sm"], pady=(0, SPACING["sm"]))
        self.prompt_scroll.grid_columnconfigure(0, weight=1)

        # Internal container for items to allow safe clearing
        self.prompt_list_container = ctk.CTkFrame(self.prompt_scroll, fg_color="transparent")
        self.prompt_list_container.pack(fill="x", expand=True, anchor="n")
        self.prompt_list_container.grid_columnconfigure(0, weight=1)

        # New prompt button
        new_btn = ctk.CTkButton(
            list_frame,
            text="+ New Prompt",
            command=self._on_new_prompt,
            **get_button_style("primary")
        )
        new_btn.grid(row=3, column=0, sticky="ew", padx=SPACING["md"], pady=SPACING["md"])

    def _load_prompts(self):
        """Load all prompts into the list."""
        # Clear existing safely from container
        for widget in self.prompt_list_container.winfo_children():
            widget.destroy()

        self.prompt_widgets = {}
        prompts = self.prompt_manager.get_all_prompts()

        if self.selected_prompt and self.selected_prompt.name in prompts:
            self.selected_prompt = prompts[self.selected_prompt.name]

        for i, (name, prompt) in enumerate(prompts.items()):
            self._create_prompt_item(prompt, row=i)

        # Update active indicator banner
        self._update_active_indicator(prompts)

        # Reselect if exists
        if self.selected_prompt and self.selected_prompt.name in prompts:
            self._update_selection_visuals(self.selected_prompt.name)

    def _create_prompt_item(self, prompt: Prompt, row: int = 0):
        """Create a prompt list item."""
        item_frame = ctk.CTkFrame(
            self.prompt_list_container,
            fg_color=COLORS["bg_dark"],
            corner_radius=RADIUS["sm"],
            border_width=1,
            border_color=COLORS["border"],
            height=60
        )
        item_frame.pack(fill="x", padx=SPACING["xs"], pady=SPACING["xs"], anchor="n")
        item_frame.pack_propagate(False)

        row_container = ctk.CTkFrame(item_frame, fg_color="transparent")
        row_container.pack(fill="both", expand=True, padx=SPACING["md"], pady=5)

        text_frame = ctk.CTkFrame(row_container, fg_color="transparent")
        text_frame.pack(side="left", fill="both", expand=True, anchor="center")

        badge_frame = ctk.CTkFrame(row_container, fg_color="transparent", width=30)
        badge_frame.pack(side="right", anchor="center")
        badge_frame.pack_propagate(False)

        name_label = ctk.CTkLabel(
            text_frame,
            text=self._format_display_name(prompt),
            font=(FONTS["family"], FONTS["body_size"], "bold" if prompt.active else "normal"),
            text_color=COLORS["primary"] if prompt.active else COLORS["text_primary"],
            anchor="w"
        )
        name_label.pack(anchor="w")

        meta_label = ctk.CTkLabel(
            text_frame,
            text=self._format_sidebar_meta(prompt),
            font=(FONTS["family"], FONTS["small_size"]),
            text_color=COLORS["text_muted"],
            anchor="w"
        )
        meta_label.pack(anchor="w", pady=(2, 0))

        if prompt.active:
            active_pill = ctk.CTkFrame(
                badge_frame,
                fg_color=COLORS["success_bg"],
                corner_radius=RADIUS["sm"]
            )
            active_pill.pack(side="left", padx=SPACING["xs"])
            active_badge = ctk.CTkLabel(
                active_pill,
                text="ACTIVE",
                font=(FONTS["family"], FONTS["small_size"] - 1, "bold"),
                text_color=COLORS["success"]
            )
            active_badge.pack(padx=SPACING["xs"], pady=1)
        else:
            active_pill = None
            active_badge = None

        if prompt.locked:
            lock_label = ctk.CTkLabel(
                badge_frame,
                text="🔒",
                text_color=COLORS["text_muted"],
                font=(FONTS["family"], FONTS["small_size"])
            )
            lock_label.pack(side="left")
        else:
            lock_label = None

        self.prompt_widgets[prompt.name] = {
            "frame": item_frame,
            "label": name_label,
            "meta": meta_label,
            "prompt": prompt
        }

        self._bind_prompt_item_click(
            [item_frame, row_container, text_frame, name_label, meta_label, badge_frame, active_pill, active_badge, lock_label],
            prompt
        )

    def _format_display_name(self, prompt: Prompt) -> str:
        """Format prompt name for the sidebar item."""
        display_name = prompt.name
        if len(display_name) > 28:
            return display_name[:25] + "..."
        return display_name

    def _format_sidebar_meta(self, prompt: Prompt) -> str:
        """Format prompt metadata for the sidebar item."""
        prompt_type = "Default" if prompt.locked else "Custom"
        updated_at = prompt.metadata.updated_at.strftime(self.SIDEBAR_TIME_FORMAT)
        return f"{prompt_type}  |  {updated_at}"

    def _update_active_indicator(self, prompts: dict):
        """Update the sidebar active-prompt indicator banner."""
        active_prompt = next((p for p in prompts.values() if p.active), None)
        if active_prompt:
            name = active_prompt.name
            display = name if len(name) <= 24 else name[:21] + "..."
            self.active_indicator_label.configure(
                text=f"✓ Active: {display}",
                text_color=COLORS["success"]
            )
            self.active_indicator_frame.configure(fg_color=COLORS["success_bg"])
            if self.on_active_prompt_change:
                self.on_active_prompt_change(name)
        else:
            self.active_indicator_label.configure(
                text="No active prompt",
                text_color=COLORS["text_muted"]
            )
            self.active_indicator_frame.configure(fg_color=COLORS["accent_bg"])
            if self.on_active_prompt_change:
                self.on_active_prompt_change("")

    def _bind_prompt_item_click(self, widgets, prompt: Prompt):
        """Bind click behavior across the full prompt item."""
        for widget in widgets:
            if widget is None:
                continue
            widget.bind("<Button-1>", lambda e, p=prompt: self._on_select_prompt(p))
            widget.configure(cursor="hand2")

    def _update_selection_visuals(self, selected_name: str):
        """Update visual state of prompt list items."""
        for name, widgets in self.prompt_widgets.items():
            is_selected = (name == selected_name)
            prompt = widgets["prompt"]

            bg_color = COLORS["bg_light"] if is_selected else COLORS["bg_dark"]
            widgets["frame"].configure(fg_color=bg_color, border_color=COLORS["border_light"] if is_selected else COLORS["border"])
            widgets["meta"].configure(text_color=COLORS["text_secondary"] if is_selected else COLORS["text_muted"])
            widgets["label"].configure(text=self._format_display_name(prompt))
            widgets["meta"].configure(text=self._format_sidebar_meta(prompt))
            widgets["label"].configure(
                text_color=COLORS["primary"] if prompt.active else COLORS["text_primary"],
                font=(FONTS["family"], FONTS["body_size"], "bold" if prompt.active else "normal")
            )

    def _on_select_prompt(self, prompt: Prompt):
        """Handle prompt selection."""
        self.selected_prompt = prompt

        self._set_editor_state(True, locked=prompt.locked)
        self._populate_editor(prompt)
        self._update_prompt_feedback()
        self._update_selection_visuals(prompt.name)
