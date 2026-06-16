"""
Prompt Settings Tab for Sub-auto
Manages translation prompts with testing capability.
"""

import customtkinter as ctk
from typing import Optional, Callable

from .styles import COLORS, FONTS, SPACING, RADIUS, get_button_style, get_input_style, get_label_style
from .prompt_test_dialog import PromptTestDialog
from core.prompt_manager import PromptManager
from core.prompt_schema import Prompt, PromptMetadata
from datetime import datetime


class PromptSettingsTab(ctk.CTkFrame):
    """Tab for managing translation prompts."""

    PREVIEW_VALUES = {
        "source_lang": "English",
        "target_lang": "Indonesian",
        "context": "[PREV] We have to move now.\n[PREV] They're almost here.",
        "lines": "[12] Hello, how are you today?\n[13] We should get going."
    }
    SIDEBAR_TIME_FORMAT = "%d %b %H:%M"
    
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
    
    def _on_select_prompt(self, prompt: Prompt):
        """Handle prompt selection."""
        self.selected_prompt = prompt

        self._set_editor_state(True, locked=prompt.locked)
        self._populate_editor(prompt)
        self._update_prompt_feedback()
        self._update_selection_visuals(prompt.name)

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
    
    def _on_save_prompt(self):
        """Save the current prompt."""
        if not self.selected_prompt:
            return
        
        # Get values
        old_name = self.selected_prompt.name
        new_name = self.name_entry.get().strip()
        new_content = self.content_text.get("1.0", "end-1c").strip()
        
        if not new_name:
            self.validation_label.configure(text="❌ Name cannot be empty", text_color=COLORS["error"])
            return
            
        # Check for name collision if renaming
        if new_name != old_name and self.prompt_manager.get_all_prompts().get(new_name):
            self.validation_label.configure(text="❌ A prompt with this name already exists", text_color=COLORS["error"])
            return
        
        updated_prompt = Prompt(
            name=new_name,
            version=self.selected_prompt.version,
            active=self.selected_prompt.active,
            locked=self.selected_prompt.locked,
            content=new_content,
            metadata=self.selected_prompt.metadata
        )

        success, message = self.prompt_manager.update_prompt(old_name, updated_prompt)
        
        if success:
            self.selected_prompt = updated_prompt
            self.validation_label.configure(text="✅ Saved successfully", text_color=COLORS["success"])
            self._load_prompts()
            self._on_select_prompt(self.selected_prompt) # Refresh selection
        else:
            self.validation_label.configure(text=f"❌ {message}", text_color=COLORS["error"])
    
    def _on_duplicate_prompt(self):
        """Duplicate the current prompt."""
        if not self.selected_prompt:
            return
        
        # Generate new name
        base_name = self.selected_prompt.name
        new_name = f"{base_name} (Copy)"
        counter = 1
        
        while self.prompt_manager.get_all_prompts().get(new_name):
            counter += 1
            new_name = f"{base_name} (Copy {counter})"
        
        # Duplicate
        success, message = self.prompt_manager.duplicate_prompt(self.selected_prompt.name, new_name)
        
        if success:
            self.validation_label.configure(text=f"✅ {message}", text_color=COLORS["success"])
            self._load_prompts()
        else:
            self.validation_label.configure(text=f"❌ {message}", text_color=COLORS["error"])
    
    def _on_delete_prompt(self):
        """Delete the current prompt."""
        if not self.selected_prompt:
            return
        
        # Confirm deletion
        dialog = ctk.CTkInputDialog(
            text=f"Type '{self.selected_prompt.name}' to confirm deletion:",
            title="Confirm Delete"
        )
        confirmation = dialog.get_input()
        
        if confirmation == self.selected_prompt.name:
            success, message = self.prompt_manager.delete_prompt(self.selected_prompt.name)
            
            if success:
                self.validation_label.configure(text="✅ Deleted", text_color=COLORS["success"])
                self.selected_prompt = None
                self._set_editor_state(False)
                self.editor_title.configure(text="Select a prompt")
                self.status_badge.configure(text="")
                self._load_prompts()
            else:
                self.validation_label.configure(text=f"❌ {message}", text_color=COLORS["error"])
    
    def _on_set_active(self):
        """Set the current prompt as active."""
        if not self.selected_prompt:
            return
        
        selected_name = self.selected_prompt.name
        success, message = self.prompt_manager.set_active(selected_name)
        
        if success:
            prompts = self.prompt_manager.get_all_prompts()
            self.selected_prompt = prompts.get(selected_name, self.selected_prompt)
            self.validation_label.configure(text=f"✅ {message}", text_color=COLORS["success"])
            self._load_prompts()
            self._on_select_prompt(self.selected_prompt)  # Refresh view
        else:
            self.validation_label.configure(text=f"❌ {message}", text_color=COLORS["error"])
    
    def _on_new_prompt(self):
        """Create a new prompt."""
        # Generate unique name
        base_name = "New Prompt"
        new_name = base_name
        counter = 1
        
        while self.prompt_manager.get_all_prompts().get(new_name):
            counter += 1
            new_name = f"{base_name} {counter}"
        
        # Create new prompt
        now = datetime.now()
        new_prompt = Prompt(
            name=new_name,
            version="1.0.0",
            active=False,
            locked=False,
            content="You are a professional translator. Translate from {source_lang} to {target_lang}.\n\nCONTEXT:\n{context}\n\nTRANSLATE:\n{lines}\n\nOUTPUT:\n[NUMBER] translated text",
            metadata=PromptMetadata(
                description="Custom prompt",
                author="User",
                created_at=now,
                updated_at=now
            )
        )
        
        success, message = self.prompt_manager.save_prompt(new_prompt)
        
        if success:
            self._load_prompts()
            self._on_select_prompt(new_prompt)
            self.validation_label.configure(text="Ready to edit", text_color=COLORS["text_muted"])
        else:
            self.validation_label.configure(text=f"❌ {message}", text_color=COLORS["error"])
    
    def _on_test_prompt(self):
        """Open test dialog for the current prompt."""
        if not self.selected_prompt:
            return
        
        # Get current content from editor (may be unsaved)
        test_content = self.content_text.get("1.0", "end-1c").strip()
        
        # Validate first
        is_valid, errors = self.prompt_manager.validate_prompt(test_content)
        if not is_valid:
            self.validation_label.configure(
                text=f"❌ Cannot test: {errors[0]}", 
                text_color=COLORS["error"]
            )
            return
        
        # Open test dialog
        PromptTestDialog(self, test_content)
