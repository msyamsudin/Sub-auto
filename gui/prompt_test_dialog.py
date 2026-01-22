"""
Prompt Test Dialog for Sub-auto
Allows testing prompts with sample input.
"""

import customtkinter as ctk
import threading

from .styles import COLORS, FONTS, SPACING, RADIUS, get_button_style, get_input_style, get_label_style
from core.translator import Translator
from core.subtitle_parser import SubtitleLine


class PromptTestDialog(ctk.CTkToplevel):
    """Dialog for testing a prompt with sample input."""
    
    def __init__(self, parent, prompt_content: str):
        super().__init__(parent)
        
        self.prompt_content = prompt_content
        self.title("Test Prompt")
        self.geometry("700x600")
        self.configure(fg_color=COLORS["bg_dark"])
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI."""
        # Header
        header = ctk.CTkLabel(
            self,
            text="🧪 Test Prompt",
            font=(FONTS["family"], FONTS["heading_size"], "bold"),
            text_color=COLORS["text_primary"]
        )
        header.pack(pady=SPACING["md"], padx=SPACING["md"], anchor="w")
        
        # Input section
        input_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_medium"], corner_radius=RADIUS["md"])
        input_frame.pack(fill="both", expand=True, padx=SPACING["md"], pady=(0, SPACING["sm"]))
        input_frame.grid_rowconfigure(1, weight=1)
        input_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            input_frame,
            text="Sample Input (one subtitle line):",
            **get_label_style("body")
        ).grid(row=0, column=0, sticky="w", padx=SPACING["md"], pady=(SPACING["md"], SPACING["xs"]))
        
        self.input_text = ctk.CTkTextbox(
            input_frame,
            fg_color=COLORS["bg_dark"],
            border_width=1,
            border_color=COLORS["border"],
            font=(FONTS["family"], FONTS["body_size"]),
            height=80
        )
        self.input_text.grid(row=1, column=0, sticky="nsew", padx=SPACING["md"], pady=(0, SPACING["md"]))
        self.input_text.insert("1.0", "Hello, how are you today?")
        
        # Language selection
        lang_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        lang_frame.grid(row=2, column=0, sticky="ew", padx=SPACING["md"], pady=(0, SPACING["md"]))
        
        ctk.CTkLabel(lang_frame, text="From:", **get_label_style("body")).pack(side="left", padx=(0, SPACING["sm"]))
        
        self.source_lang = ctk.CTkEntry(lang_frame, width=120, **get_input_style())
        self.source_lang.pack(side="left", padx=(0, SPACING["md"]))
        self.source_lang.insert(0, "English")
        
        ctk.CTkLabel(lang_frame, text="To:", **get_label_style("body")).pack(side="left", padx=(0, SPACING["sm"]))
        
        self.target_lang = ctk.CTkEntry(lang_frame, width=120, **get_input_style())
        self.target_lang.pack(side="left")
        self.target_lang.insert(0, "Indonesian")
        
        # Output section
        output_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_medium"], corner_radius=RADIUS["md"])
        output_frame.pack(fill="both", expand=True, padx=SPACING["md"], pady=(0, SPACING["sm"]))
        output_frame.grid_rowconfigure(1, weight=1)
        output_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            output_frame,
            text="Output:",
            **get_label_style("body")
        ).grid(row=0, column=0, sticky="w", padx=SPACING["md"], pady=(SPACING["md"], SPACING["xs"]))
        
        self.output_text = ctk.CTkTextbox(
            output_frame,
            fg_color=COLORS["bg_dark"],
            border_width=1,
            border_color=COLORS["border"],
            font=(FONTS["family"], FONTS["body_size"]),
            height=120,
            state="disabled"
        )
        self.output_text.grid(row=1, column=0, sticky="nsew", padx=SPACING["md"], pady=(0, SPACING["md"]))
        
        # Status label
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=(FONTS["family"], FONTS["small_size"]),
            text_color=COLORS["text_muted"]
        )
        self.status_label.pack(padx=SPACING["md"], pady=(0, SPACING["sm"]))
        
        # Buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=SPACING["md"], pady=SPACING["md"])
        
        self.test_btn = ctk.CTkButton(
            button_frame,
            text="Run Test",
            command=self._on_test,
            **get_button_style("primary")
        )
        self.test_btn.pack(side="left", padx=(0, SPACING["sm"]))
        
        close_btn = ctk.CTkButton(
            button_frame,
            text="Close",
            command=self.destroy,
            **get_button_style("secondary")
        )
        close_btn.pack(side="right")
    
    def _on_test(self):
        """Run the test translation."""
        # Get input
        input_text = self.input_text.get("1.0", "end-1c").strip()
        source_lang = self.source_lang.get().strip()
        target_lang = self.target_lang.get().strip()
        
        if not input_text:
            self.status_label.configure(text="❌ Please enter sample text", text_color=COLORS["error"])
            return
        
        # Disable button
        self.test_btn.configure(state="disabled", text="Testing...")
        self.status_label.configure(text="⏳ Translating...", text_color=COLORS["text_secondary"])
        
        # Run in background
        thread = threading.Thread(
            target=self._do_test,
            args=(input_text, source_lang, target_lang),
            daemon=True
        )
        thread.start()
    
    def _do_test(self, input_text: str, source_lang: str, target_lang: str):
        """Perform the test translation in background."""
        try:
            # Create a temporary translator with custom prompt
            from core.prompt_manager import PromptManager
            from core.prompt_repository import PromptRepository
            from core.prompt_schema import Prompt, PromptMetadata
            from datetime import datetime
            
            # Create temporary prompt
            temp_prompt = Prompt(
                name="__test__",
                version="1.0.0",
                active=True,
                locked=False,
                content=self.prompt_content,
                metadata=PromptMetadata(
                    description="Test prompt",
                    author="User",
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
            )
            
            # Create temporary repository with only this prompt
            class TempRepository:
                def __init__(self, prompt):
                    self._prompt = prompt
                
                def get_active(self):
                    return self._prompt
                
                def load_all(self):
                    return {self._prompt.name: self._prompt}
                
                def exists(self, name):
                    return name == self._prompt.name
                
                def get(self, name):
                    return self._prompt if name == self._prompt.name else None
            
            temp_repo = TempRepository(temp_prompt)
            temp_manager = PromptManager(repository=temp_repo)
            
            # Create translator
            translator = Translator(prompt_manager=temp_manager)
            
            # Create subtitle line
            test_line = SubtitleLine(
                index=1,
                start_time="00:00:00,000",
                end_time="00:00:05,000",
                text=input_text,
                style=""
            )
            
            # Translate
            result = translator.translate_batch(
                lines=[test_line],
                source_lang=source_lang,
                target_lang=target_lang
            )
            
            if result.success and result.translated_lines:
                output = result.translated_lines[0][1]
                self.after(0, lambda: self._on_test_complete(output, None))
            else:
                error = result.error_message or "Translation failed"
                self.after(0, lambda: self._on_test_complete(None, error))
        
        except Exception as e:
            self.after(0, lambda: self._on_test_complete(None, str(e)))
    
    def _on_test_complete(self, output: str = None, error: str = None):
        """Handle test completion."""
        self.test_btn.configure(state="normal", text="Run Test")
        
        if output:
            self.output_text.configure(state="normal")
            self.output_text.delete("1.0", "end")
            self.output_text.insert("1.0", output)
            self.output_text.configure(state="disabled")
            self.status_label.configure(text="✅ Test complete", text_color=COLORS["success"])
        else:
            self.status_label.configure(text=f"❌ Error: {error}", text_color=COLORS["error"])
