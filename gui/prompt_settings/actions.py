"""
Prompt action mixin for the prompt settings tab.
Handles save, duplicate, delete, set-active, create-new, and test actions.
Combines with PromptSidebarMixin and PromptEditorMixin into the single
PromptSettingsTab widget.
"""

from datetime import datetime

import customtkinter as ctk

from ..styles import COLORS, get_button_style
from ..prompt_test_dialog import PromptTestDialog
from core.prompt_schema import Prompt, PromptMetadata


class PromptActionsMixin:
    """Business actions for managing prompts."""

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
            self._on_select_prompt(self.selected_prompt)  # Refresh selection
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
