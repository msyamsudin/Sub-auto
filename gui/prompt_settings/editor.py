"""
Prompt editor mixin for the prompt settings tab.
Handles the editor form (name, content, live validation, placeholder insert,
and rendered preview). Combines with PromptSidebarMixin and
PromptActionsMixin into the single PromptSettingsTab widget.
"""

from datetime import datetime

import customtkinter as ctk

from ..styles import (
    COLORS, FONTS, SPACING, RADIUS,
    get_button_style, get_input_style, get_label_style
)
from core.prompt_schema import Prompt, PromptMetadata


class PromptEditorMixin:
    """Editor (right column) of the prompt settings tab."""

    PREVIEW_VALUES = {
        "source_lang": "English",
        "target_lang": "Indonesian",
        "context": "[PREV] We have to move now.\n[PREV] They're almost here.",
        "lines": "[12] Hello, how are you today?\n[13] We should get going."
    }

    def _setup_prompt_editor(self):
        """Setup the prompt editor on the right side."""
        editor_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_medium"], corner_radius=RADIUS["md"])
        editor_frame.grid(row=0, column=1, sticky="nsew")
        editor_frame.grid_rowconfigure(0, weight=1)
        editor_frame.grid_columnconfigure(0, weight=1)

        inner_frame = ctk.CTkFrame(editor_frame, fg_color="transparent")
        inner_frame.grid(row=0, column=0, sticky="nsew", padx=SPACING["xl"], pady=SPACING["md"])
        inner_frame.grid_rowconfigure(1, weight=1)
        inner_frame.grid_rowconfigure(3, weight=0)
        inner_frame.grid_columnconfigure(0, weight=1)

        header_frame = ctk.CTkFrame(inner_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, SPACING["md"]))
        header_frame.grid_columnconfigure(0, weight=1)
        header_frame.grid_columnconfigure(1, weight=0)

        self.editor_title = ctk.CTkLabel(
            header_frame,
            text="Select a prompt",
            font=(FONTS["family"], FONTS["subheading_size"], "bold"),
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        self.editor_title.grid(row=0, column=0, sticky="w")

        self.editor_meta = ctk.CTkLabel(
            header_frame,
            text="Choose a prompt from the list to edit or test it.",
            font=(FONTS["family"], FONTS["small_size"]),
            text_color=COLORS["text_muted"],
            anchor="w"
        )
        self.editor_meta.grid(row=1, column=0, sticky="w", pady=(SPACING["xs"], 0))

        self.status_badge = ctk.CTkLabel(
            header_frame,
            text="",
            font=(FONTS["family"], FONTS["small_size"], "bold"),
            text_color=COLORS["text_muted"],
            anchor="e"
        )
        self.status_badge.grid(row=0, column=1, rowspan=2, sticky="ne", padx=(SPACING["md"], 0))

        editor_card = ctk.CTkFrame(
            inner_frame,
            fg_color=COLORS["bg_dark"],
            corner_radius=RADIUS["md"],
            border_width=1,
            border_color=COLORS["border"]
        )
        editor_card.grid(row=1, column=0, sticky="nsew")
        editor_card.grid_rowconfigure(2, weight=1)
        editor_card.grid_columnconfigure(0, weight=1)

        name_frame = ctk.CTkFrame(editor_card, fg_color="transparent")
        name_frame.grid(row=0, column=0, sticky="ew", padx=SPACING["md"], pady=(SPACING["md"], SPACING["sm"]))
        name_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(name_frame, text="Name:", **get_label_style("body")).grid(row=0, column=0, sticky="w")

        self.name_entry = ctk.CTkEntry(
            name_frame,
            placeholder_text="Prompt name",
            **get_input_style()
        )
        self.name_entry.grid(row=0, column=1, sticky="ew", padx=(SPACING["md"], 0))

        # Content area
        content_label = ctk.CTkLabel(
            editor_card,
            text="Content:",
            **get_label_style("body")
        )
        content_label.grid(row=1, column=0, sticky="nw", padx=SPACING["md"], pady=(0, SPACING["xs"]))

        self.content_text = ctk.CTkTextbox(
            editor_card,
            fg_color=COLORS["bg_dark"],
            border_width=0,
            font=(FONTS["mono_family"], FONTS["body_size"]),
            wrap="word"
        )
        self.content_text.grid(row=2, column=0, sticky="nsew", padx=SPACING["md"], pady=(0, SPACING["md"]))

        feedback_card = ctk.CTkFrame(
            inner_frame,
            fg_color=COLORS["accent_bg"],
            corner_radius=RADIUS["md"]
        )
        feedback_card.grid(row=2, column=0, sticky="ew", pady=(SPACING["md"], 0))
        feedback_card.grid_columnconfigure(1, weight=1)
        feedback_card.grid_columnconfigure(2, weight=0)

        self.validation_label = ctk.CTkLabel(
            feedback_card,
            text="",
            font=(FONTS["family"], FONTS["small_size"]),
            text_color=COLORS["error"],
            anchor="w"
        )
        self.validation_label.grid(row=0, column=0, sticky="w", padx=SPACING["md"], pady=SPACING["md"])

        self.placeholder_hint = ctk.CTkLabel(
            feedback_card,
            text="",
            font=(FONTS["family"], FONTS["small_size"]),
            text_color=COLORS["text_muted"],
            anchor="w",
            justify="left"
        )
        self.placeholder_hint.grid(row=0, column=1, sticky="w", padx=(SPACING["md"], SPACING["sm"]), pady=SPACING["md"])

        placeholder_frame = ctk.CTkFrame(feedback_card, fg_color="transparent")
        placeholder_frame.grid(row=0, column=2, sticky="e", padx=SPACING["md"], pady=SPACING["sm"])

        ctk.CTkLabel(
            placeholder_frame,
            text="Insert:",
            **get_label_style("muted")
        ).pack(side="left", padx=(0, SPACING["sm"]))

        for placeholder in ("source_lang", "target_lang", "context", "lines"):
            btn = ctk.CTkButton(
                placeholder_frame,
                text=f"{{{placeholder}}}",
                width=110,
                command=lambda p=placeholder: self._insert_placeholder(p),
                **get_button_style("ghost")
            )
            btn.pack(side="left", padx=(0, SPACING["xs"]))

        preview_card = ctk.CTkFrame(
            inner_frame,
            fg_color=COLORS["bg_dark"],
            corner_radius=RADIUS["md"],
            border_width=1,
            border_color=COLORS["border"]
        )
        preview_card.grid(row=3, column=0, sticky="ew", pady=(SPACING["md"], 0))
        preview_card.grid_rowconfigure(1, weight=1)
        preview_card.grid_columnconfigure(0, weight=1)

        preview_label = ctk.CTkLabel(
            preview_card,
            text="Rendered preview:",
            **get_label_style("body")
        )
        preview_label.grid(row=0, column=0, sticky="nw", padx=SPACING["md"], pady=(SPACING["md"], SPACING["xs"]))

        self.preview_text = ctk.CTkTextbox(
            preview_card,
            fg_color=COLORS["bg_dark"],
            border_width=0,
            font=(FONTS["mono_family"], FONTS["small_size"]),
            height=110,
            state="disabled",
            wrap="word"
        )
        self.preview_text.grid(row=1, column=0, sticky="ew", padx=SPACING["md"], pady=(0, SPACING["md"]))

        button_frame = ctk.CTkFrame(inner_frame, fg_color="transparent")
        button_frame.grid(row=4, column=0, sticky="ew", pady=SPACING["md"])
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        left_actions = ctk.CTkFrame(button_frame, fg_color="transparent")
        left_actions.grid(row=0, column=0, sticky="w")

        right_actions = ctk.CTkFrame(button_frame, fg_color="transparent")
        right_actions.grid(row=0, column=1, sticky="e")

        self.save_btn = ctk.CTkButton(
            left_actions,
            text="Save",
            command=self._on_save_prompt,
            width=140,
            **get_button_style("primary")
        )
        self.save_btn.pack(side="left", padx=(0, SPACING["sm"]))

        self.duplicate_btn = ctk.CTkButton(
            left_actions,
            text="Duplicate",
            command=self._on_duplicate_prompt,
            width=140,
            **get_button_style("secondary")
        )
        self.duplicate_btn.pack(side="left", padx=(0, SPACING["sm"]))

        self.test_btn = ctk.CTkButton(
            left_actions,
            text="Test Prompt",
            command=self._on_test_prompt,
            width=140,
            **get_button_style("secondary")
        )
        self.test_btn.pack(side="left", padx=(0, SPACING["sm"]))

        self.delete_btn = ctk.CTkButton(
            right_actions,
            text="Delete",
            command=self._on_delete_prompt,
            width=140,
            **get_button_style("danger")
        )
        self.delete_btn.pack(side="right")

        self.set_active_btn = ctk.CTkButton(
            right_actions,
            text="Set Active",
            command=self._on_set_active,
            width=140,
            **get_button_style("secondary")
        )
        self.set_active_btn.pack(side="right", padx=(0, SPACING["sm"]))

        self._bind_editor_events()

        # Initially disable all controls
        self._set_editor_state(False)

    def _populate_editor(self, prompt: Prompt):
        """Populate the editor fields from the selected prompt."""
        self.editor_title.configure(text=prompt.name)
        meta_parts = []
        meta_parts.append("Default prompt" if prompt.locked else "Custom prompt")
        meta_parts.append(f"Updated {prompt.metadata.updated_at.strftime('%Y-%m-%d %H:%M')}")
        self.editor_meta.configure(text="  |  ".join(meta_parts))

        self.name_entry.configure(state="normal")
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, prompt.name)

        self.content_text.configure(state="normal")
        self.content_text.delete("1.0", "end")
        self.content_text.insert("1.0", prompt.content)

        if prompt.active and prompt.locked:
            self.status_badge.configure(
                text="● ACTIVE  🔒 LOCKED",
                text_color=COLORS["success"]
            )
        elif prompt.active:
            self.status_badge.configure(
                text="● ACTIVE",
                text_color=COLORS["success"]
            )
        elif prompt.locked:
            self.status_badge.configure(
                text="🔒 LOCKED",
                text_color=COLORS["warning"]
            )
        else:
            self.status_badge.configure(
                text="",
                text_color=COLORS["text_muted"]
            )

        if prompt.locked:
            self.name_entry.configure(state="disabled")

    def _set_editor_state(self, enabled: bool, locked: bool = False):
        """Enable or disable editor controls."""
        state = "normal" if enabled and not locked else "disabled"
        readonly_state = "normal" if enabled else "disabled"

        self.name_entry.configure(state=state)
        self.content_text.configure(state=readonly_state if locked else state)
        self.save_btn.configure(state=state)
        self.duplicate_btn.configure(state=readonly_state)
        self.test_btn.configure(state=readonly_state)
        self.delete_btn.configure(state=state)
        self.set_active_btn.configure(state=readonly_state)
        self.preview_text.configure(state=readonly_state)

    def _bind_editor_events(self):
        """Attach live validation events."""
        self.name_entry.bind("<KeyRelease>", self._on_editor_modified)
        self.content_text.bind("<KeyRelease>", self._on_editor_modified)

    def _on_editor_modified(self, _event=None):
        """Refresh live feedback while editing."""
        if self.selected_prompt:
            self._update_prompt_feedback()

    def _insert_placeholder(self, placeholder: str):
        """Insert a placeholder into the content editor."""
        if not self.selected_prompt:
            return

        self.content_text.insert("insert", f"{{{placeholder}}}")
        self._update_prompt_feedback()

    def _update_prompt_feedback(self):
        """Update validation message, placeholder checklist, and preview."""
        content = self.content_text.get("1.0", "end-1c").strip()
        if not content:
            self.validation_label.configure(text="", text_color=COLORS["error"])
            self.placeholder_hint.configure(text="")
            self._set_preview_text("")
            return

        is_valid, errors = self.prompt_manager.validate_prompt(content)
        if is_valid:
            self.validation_label.configure(text="Ready to save", text_color=COLORS["success"])
        else:
            self.validation_label.configure(text=f"❌ {errors[0]}", text_color=COLORS["error"])

        checklist = []
        for placeholder in ("source_lang", "target_lang", "context", "lines"):
            marker = "✓" if f"{{{placeholder}}}" in content else "○"
            checklist.append(f"{marker} {{{placeholder}}}")
        self.placeholder_hint.configure(text="Placeholders: " + "  ".join(checklist))

        preview = ""
        if is_valid:
            preview = self._render_preview(content)
        self._set_preview_text(preview)

    def _render_preview(self, content: str) -> str:
        """Render a prompt preview using sample values."""
        temp_prompt = Prompt(
            name="preview",
            version="1.0.0",
            active=False,
            locked=False,
            content=content,
            metadata=PromptMetadata(
                description="Preview",
                author="System",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        )
        try:
            return temp_prompt.render(self.PREVIEW_VALUES)
        except Exception as exc:
            return f"Preview unavailable: {exc}"

    def _set_preview_text(self, text: str):
        """Replace preview textbox content safely."""
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", "end")
        if text:
            self.preview_text.insert("1.0", text)
        self.preview_text.configure(state="disabled")
