"""
Prompt Settings Tab for Sub-auto
Manages translation prompts with testing capability.
"""

import customtkinter as ctk
from typing import Optional, Callable
import threading

from .styles import COLORS, FONTS, SPACING, RADIUS, get_button_style, get_input_style, get_label_style
from .prompt_test_dialog import PromptTestDialog
from core.prompt_manager import PromptManager
from core.prompt_schema import Prompt, PromptMetadata
from datetime import datetime


class PromptSettingsTab(ctk.CTkFrame):
    """Tab for managing translation prompts."""
    
    def __init__(
        self,
        parent,
        prompt_manager: PromptManager,
        **kwargs
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)
        
        self.prompt_manager = prompt_manager
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
        list_frame.grid_rowconfigure(1, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # Header
        header = ctk.CTkLabel(
            list_frame,
            text="📝 Prompts",
            font=(FONTS["family"], FONTS["subheading_size"], "bold"),
            text_color=COLORS["text_primary"]
        )
        header.grid(row=0, column=0, sticky="w", padx=SPACING["md"], pady=SPACING["md"])
        
        # Scrollable list
        self.prompt_scroll = ctk.CTkScrollableFrame(
            list_frame,
            fg_color="transparent"
        )
        self.prompt_scroll.grid(row=1, column=0, sticky="nsew", padx=SPACING["sm"], pady=(0, SPACING["sm"]))
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
        new_btn.grid(row=2, column=0, sticky="ew", padx=SPACING["md"], pady=SPACING["md"])
    
    def _setup_prompt_editor(self):
        """Setup the prompt editor on the right side."""
        editor_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_medium"], corner_radius=RADIUS["md"])
        editor_frame.grid(row=0, column=1, sticky="nsew")
        editor_frame.grid_rowconfigure(0, weight=1)
        editor_frame.grid_columnconfigure(0, weight=1)
        
        # Inner container to constrain width and add "breathing room"
        inner_frame = ctk.CTkFrame(editor_frame, fg_color="transparent")
        inner_frame.grid(row=0, column=0, sticky="nsew", padx=SPACING["xl"], pady=SPACING["md"])
        inner_frame.grid_rowconfigure(3, weight=1)
        inner_frame.grid_columnconfigure(0, weight=1)

        # Header with status
        header_frame = ctk.CTkFrame(inner_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, SPACING["md"]))
        header_frame.grid_columnconfigure(0, weight=1)
        
        self.editor_title = ctk.CTkLabel(
            header_frame,
            text="Select a prompt",
            font=(FONTS["family"], FONTS["subheading_size"], "bold"),
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        self.editor_title.grid(row=0, column=0, sticky="w")
        
        self.status_badge = ctk.CTkLabel(
            header_frame,
            text="",
            font=(FONTS["family"], FONTS["small_size"], "bold"),
            text_color=COLORS["text_muted"],
            anchor="e"
        )
        self.status_badge.grid(row=0, column=1, sticky="e", padx=(SPACING["md"], 0))
        
        # Name field
        name_frame = ctk.CTkFrame(inner_frame, fg_color="transparent")
        name_frame.grid(row=1, column=0, sticky="ew", pady=(0, SPACING["sm"]))
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
            inner_frame,
            text="Content:",
            **get_label_style("body")
        )
        content_label.grid(row=2, column=0, sticky="nw", pady=(0, SPACING["xs"]))
        
        self.content_text = ctk.CTkTextbox(
            inner_frame,
            fg_color=COLORS["bg_dark"],
            border_width=1,
            border_color=COLORS["border"],
            font=(FONTS["family"], FONTS["body_size"]),
            wrap="word"
        )
        self.content_text.grid(row=3, column=0, sticky="nsew", pady=(0, SPACING["md"]))
        
        # Validation feedback
        self.validation_label = ctk.CTkLabel(
            inner_frame,
            text="",
            font=(FONTS["family"], FONTS["small_size"]),
            text_color=COLORS["error"],
            anchor="w"
        )
        self.validation_label.grid(row=4, column=0, sticky="w")
        
        # Action buttons
        button_frame = ctk.CTkFrame(inner_frame, fg_color="transparent")
        button_frame.grid(row=5, column=0, sticky="ew", pady=SPACING["md"])
        
        self.save_btn = ctk.CTkButton(
            button_frame,
            text="Save",
            command=self._on_save_prompt,
            **get_button_style("primary")
        )
        self.save_btn.pack(side="left", padx=(0, SPACING["sm"]))
        
        self.duplicate_btn = ctk.CTkButton(
            button_frame,
            text="Duplicate",
            command=self._on_duplicate_prompt,
            **get_button_style("secondary")
        )
        self.duplicate_btn.pack(side="left", padx=(0, SPACING["sm"]))
        
        self.test_btn = ctk.CTkButton(
            button_frame,
            text="Test Prompt",
            command=self._on_test_prompt,
            **get_button_style("secondary")
        )
        self.test_btn.pack(side="left", padx=(0, SPACING["sm"]))
        
        self.delete_btn = ctk.CTkButton(
            button_frame,
            text="Delete",
            command=self._on_delete_prompt,
            fg_color="transparent",
            hover_color=COLORS["bg_light"],
            text_color=COLORS["error"],
            border_width=1,
            border_color=COLORS["error"]
        )
        self.delete_btn.pack(side="right")
        
        self.set_active_btn = ctk.CTkButton(
            button_frame,
            text="Set Active",
            command=self._on_set_active,
            **get_button_style("secondary")
        )
        self.set_active_btn.pack(side="right", padx=(0, SPACING["sm"]))
        
        # Initially disable all controls
        self._set_editor_state(False)
    
    def _load_prompts(self):
        """Load all prompts into the list."""
        # Clear existing safely from container
        for widget in self.prompt_list_container.winfo_children():
            widget.destroy()
        
        self.prompt_widgets = {}
        prompts = self.prompt_manager.get_all_prompts()
        
        for i, (name, prompt) in enumerate(prompts.items()):
            self._create_prompt_item(prompt, row=i)
            
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
            height=60  # Explicit height to prevent weird stretching
        )
        item_frame.grid(row=row, column=0, sticky="ew", pady=SPACING["xs"], padx=SPACING["xs"])
        item_frame.grid_propagate(False) # Force fixed height
        item_frame.grid_columnconfigure(0, weight=1)
        item_frame.grid_rowconfigure(0, weight=1)
        
        name_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        name_frame.grid(row=0, column=0, sticky="nsew", padx=SPACING["md"])
        name_frame.grid_columnconfigure(0, weight=1)
        name_frame.grid_rowconfigure(0, weight=1)
        
        display_name = prompt.name
        if len(display_name) > 28:
            display_name = display_name[:25] + "..."
            
        name_label = ctk.CTkLabel(
            name_frame,
            text=display_name,
            font=(FONTS["family"], FONTS["body_size"], "bold" if prompt.active else "normal"),
            text_color=COLORS["primary"] if prompt.active else COLORS["text_primary"],
            anchor="w"
        )
        name_label.grid(row=0, column=0, sticky="w")
        
        # Badges
        badge_frame = ctk.CTkFrame(name_frame, fg_color="transparent")
        badge_frame.grid(row=0, column=1, sticky="e")
        
        if prompt.active:
            active_badge = ctk.CTkLabel(
                badge_frame,
                text="●",
                font=(FONTS["family"], FONTS["body_size"], "bold"),
                text_color=COLORS["success"]
            )
            active_badge.pack(side="left", padx=SPACING["xs"])
        
        if prompt.locked:
            lock_label = ctk.CTkLabel(
                badge_frame,
                text="🔒",
                text_color=COLORS["text_muted"],
                font=(FONTS["family"], FONTS["small_size"])
            )
            lock_label.pack(side="left")
        
        self.prompt_widgets[prompt.name] = {
            "frame": item_frame,
            "label": name_label
        }
        
        # Make clickable
        for widget in [item_frame, name_frame, name_label, badge_frame]:
            widget.bind("<Button-1>", lambda e, p=prompt: self._on_select_prompt(p))
            widget.configure(cursor="hand2")
    
    def _on_select_prompt(self, prompt: Prompt):
        """Handle prompt selection."""
        self.selected_prompt = prompt
        
        # Update editor
        self.editor_title.configure(text=prompt.name)
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, prompt.name)
        self.content_text.delete("1.0", "end")
        self.content_text.insert("1.0", prompt.content)
        
        # Update status badge
        badges = []
        if prompt.active:
            badges.append("● ACTIVE")
        if prompt.locked:
            badges.append("🔒 LOCKED")
        self.status_badge.configure(text=" ".join(badges))
        
        # Enable/disable controls based on locked status
        self._set_editor_state(True, locked=prompt.locked)
        
        # Clear validation
        self.validation_label.configure(text="")
        
        # Update selection visuals
        self._update_selection_visuals(prompt.name)
        
    def _update_selection_visuals(self, selected_name: str):
        """Update visual state of prompt list items."""
        for name, widgets in self.prompt_widgets.items():
            is_selected = (name == selected_name)
            
            # Change background color
            bg_color = COLORS["bg_light"] if is_selected else COLORS["bg_dark"]
            widgets["frame"].configure(fg_color=bg_color, border_color=COLORS["accent"] if is_selected else COLORS["border"])
            
            # Highlight text slightly if selected, but respect active color
            # We don't change text color here to preserve the "Active" Green logic,
            # but the frame border and bg change is enough feedback.
    
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
    
    def _on_save_prompt(self):
        """Save the current prompt."""
        if not self.selected_prompt:
            return
        
        # Get values
        new_name = self.name_entry.get().strip()
        new_content = self.content_text.get("1.0", "end-1c").strip()
        
        if not new_name:
            self.validation_label.configure(text="❌ Name cannot be empty", text_color=COLORS["error"])
            return
        
        # Validate content
        is_valid, errors = self.prompt_manager.validate_prompt(new_content)
        if not is_valid:
            self.validation_label.configure(
                text=f"❌ {errors[0]}", 
                text_color=COLORS["error"]
            )
            return
        
        # Update prompt
        self.selected_prompt.name = new_name
        self.selected_prompt.content = new_content
        
        # Save
        success, message = self.prompt_manager.save_prompt(self.selected_prompt)
        
        if success:
            self.validation_label.configure(text="✅ Saved successfully", text_color=COLORS["success"])
            self._load_prompts()
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
        
        success, message = self.prompt_manager.set_active(self.selected_prompt.name)
        
        if success:
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
