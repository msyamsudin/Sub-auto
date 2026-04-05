import customtkinter as ctk
from typing import Optional, Callable, List
from .styles import (
    COLORS, FONTS, SPACING, RADIUS,
    get_button_style, get_label_style
)

class SubtitleEditor(ctk.CTkFrame):
    """
    Subtitle editor dialog for reviewing and editing translated subtitles.
    Displays the SRT content in an editable text area with save/discard options.
    Opens as a resizable window.
    """
    
    def __init__(
        self,
        master,
        subtitle_path: str,
        on_approve: Optional[Callable[[str], None]] = None,
        on_discard: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)
        
        self.subtitle_path = subtitle_path
        self.on_approve_callback = on_approve
        self.on_discard_callback = on_discard
        self.original_content = ""
        
        # Editor state
        self.undo_stack = []
        self.redo_stack = []
        self.last_content = ""
        self.search_index = "1.0"
        self.search_matches = []
        
        self._setup_ui()
        self._load_subtitle()
        
        # Setup keyboard shortcuts
        self._setup_keyboard_shortcuts()
        
        # Focus the editor
        self.after(100, lambda: self.text_editor.focus_set())
    
    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts."""
        # Bind verify specific shortcuts to the text editor
        self.text_editor.bind("<Control-s>", lambda e: self._on_approve())
        self.text_editor.bind("<Control-f>", lambda e: self._show_find_dialog())
        self.text_editor.bind("<Control-h>", lambda e: self._show_replace_dialog())
        self.text_editor.bind("<Control-g>", lambda e: self._show_goto_dialog())
        
        # Escape to discard/close
        self.text_editor.bind("<Escape>", lambda e: self.on_discard_callback() if self.on_discard_callback else None)
    
    def _setup_ui(self):
        """Setup the editor UI."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Toolbar
        self.grid_rowconfigure(1, weight=0) # Info
        self.grid_rowconfigure(2, weight=1) # Editor area gets the weight
        
        # Toolbar
        toolbar_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_medium"], corner_radius=0)
        toolbar_frame.grid(row=0, column=0, sticky="ew", pady=0)
        
        toolbar_content = ctk.CTkFrame(toolbar_frame, fg_color="transparent")
        toolbar_content.pack(fill="x", padx=SPACING["lg"], pady=SPACING["sm"])
        
        # Search button
        search_btn = ctk.CTkButton(
            toolbar_content,
            text="🔍 Find",
            width=80,
            height=28,
            command=self._show_find_dialog,
            **get_button_style("ghost")
        )
        search_btn.pack(side="left", padx=(0, SPACING["xs"]))
        
        # Replace button
        replace_btn = ctk.CTkButton(
            toolbar_content,
            text="Aa Replace",
            width=80,
            height=28,
            command=self._show_replace_dialog,
            **get_button_style("ghost")
        )
        replace_btn.pack(side="left", padx=(0, SPACING["xs"]))
        
        # Go to entry button
        goto_btn = ctk.CTkButton(
            toolbar_content,
            text="↗️ Go to",
            width=80,
            height=28,
            command=self._show_goto_dialog,
            **get_button_style("ghost")
        )
        goto_btn.pack(side="left", padx=SPACING["xs"])
        
        # Separator
        sep1 = ctk.CTkLabel(toolbar_content, text="|", text_color=COLORS["border"])
        sep1.pack(side="left", padx=SPACING["sm"])
        
        # Validate button
        validate_btn = ctk.CTkButton(
            toolbar_content,
            text="✓ Validate",
            width=90,
            height=28,
            command=self._validate_content,
            **get_button_style("ghost")
        )
        validate_btn.pack(side="left", padx=SPACING["xs"])
        
        # Separator
        sep2 = ctk.CTkLabel(toolbar_content, text="|", text_color=COLORS["border"])
        sep2.pack(side="left", padx=SPACING["sm"])
        
        # Syntax highlighting toggle
        self.syntax_enabled = True
        self.syntax_btn = ctk.CTkButton(
            toolbar_content,
            text="🎨 Syntax: ON",
            width=110,
            height=28,
            command=self._toggle_syntax,
            **get_button_style("ghost")
        )
        self.syntax_btn.pack(side="left", padx=SPACING["xs"])
        
        # Info on right side
        shortcuts_label = ctk.CTkLabel(
            toolbar_content,
            text="💡 Ctrl+S: Save | Ctrl+F: Find | Ctrl+G: Go to | Esc: Close",
            **get_label_style("muted")
        )
        shortcuts_label.pack(side="right", padx=SPACING["sm"])
        
        # Info bar
        info_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_medium"], corner_radius=0)
        info_frame.grid(row=1, column=0, sticky="ew", pady=(0, SPACING["sm"]))
        
        info_label = ctk.CTkLabel(
            info_frame,
            text="💡 Review and edit the translated subtitles below. Click 'Approve & Merge' when ready.",
            **get_label_style("body"),
            anchor="w"
        )
        info_label.pack(fill="x", padx=SPACING["md"], pady=SPACING["sm"])
        
        # Editor area
        editor_container = ctk.CTkFrame(self, fg_color="transparent")
        editor_container.grid(row=2, column=0, sticky="nsew", padx=SPACING["lg"], pady=(0, SPACING["sm"]))
        editor_container.grid_columnconfigure(0, weight=1)
        editor_container.grid_rowconfigure(0, weight=1)
        
        # Text editor
        self.text_editor = ctk.CTkTextbox(
            editor_container,
            font=(FONTS["mono_family"], FONTS["body_size"] + 1),
            fg_color=COLORS["bg_dark"],
            text_color=COLORS["text_primary"],
            border_color=COLORS["border_light"],
            border_width=2,
            wrap="word",
            activate_scrollbars=True,
            undo=True,
            maxundo=-1
        )
        self.text_editor.grid(row=0, column=0, sticky="nsew")
        
        # Bind Undo/Redo keys explicitly
        self.text_editor.bind("<Control-z>", lambda e: self.text_editor.edit_undo())
        self.text_editor.bind("<Control-y>", lambda e: self.text_editor.edit_redo())
        self.text_editor.bind("<Control-Shift-z>", lambda e: self.text_editor.edit_redo())
        
        # Configure syntax highlighting tags
        self.text_editor.tag_config("number", foreground=COLORS["syntax_number"])
        self.text_editor.tag_config("timestamp", foreground=COLORS["syntax_timestamp"])
        self.text_editor.tag_config("arrow", foreground=COLORS["syntax_arrow"])
        self.text_editor.tag_config("text", foreground=COLORS["syntax_text"])
        self.text_editor.tag_config("error", foreground=COLORS["syntax_error"], background=COLORS["error_bg"])
        self.text_editor.tag_config("search_highlight", background=COLORS["warning_bg"], foreground=COLORS["warning"])
        
        # Bind events
        self.text_editor.bind("<<Modified>>", self._on_text_modified)
        
        # Stats label
        self.stats_label = ctk.CTkLabel(
            editor_container,
            text="",
            **get_label_style("muted"),
            anchor="e"
        )
        self.stats_label.grid(row=1, column=0, sticky="e", pady=(SPACING["xs"], 0))
        
        # Footer with buttons
        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.grid(row=3, column=0, sticky="ew", pady=SPACING["lg"])
        
        # Center buttons
        btn_container = ctk.CTkFrame(footer_frame, fg_color="transparent")
        btn_container.pack()
        
        discard_btn = ctk.CTkButton(
            btn_container,
            text="Discard",
            width=120,
            height=40,
            command=self._on_discard,
            **get_button_style("secondary")
        )
        discard_btn.pack(side="left", padx=SPACING["sm"])
        
        approve_btn = ctk.CTkButton(
            btn_container,
            text="✓ Approve & Merge",
            width=180,
            height=40,
            command=self._on_approve,
            **get_button_style("success")
        )
        approve_btn.pack(side="left", padx=SPACING["sm"])
    
    def _load_subtitle(self):
        """Load subtitle content from file."""
        try:
            with open(self.subtitle_path, 'r', encoding='utf-8') as f:
                self.original_content = f.read()
            
            self.text_editor.delete("0.0", "end")
            self.text_editor.insert("0.0", self.original_content)
            
            # Update stats
            lines = self.original_content.strip().split('\n')
            subtitle_count = self.original_content.count('\n\n') + 1
            char_count = len(self.original_content)
            
            self.stats_label.configure(
                text=f"📊 {subtitle_count} entries • {char_count:,} characters • {len(lines):,} lines"
            )
            
            # Apply syntax highlighting
            self.last_content = self.original_content
            if self.syntax_enabled:
                self._apply_syntax_highlighting()
            
        except Exception as e:
            self.text_editor.insert("0.0", f"Error loading subtitle: {str(e)}")
            self.stats_label.configure(text="⚠ Error loading file")

    def _on_text_modified(self, event=None):
        """Handle text modification for syntax highlighting."""
        if self.syntax_enabled:
            current = self.text_editor.get("0.0", "end-1c")
            if current != self.last_content:
                self.last_content = current
                self.after(100, self._apply_syntax_highlighting)
    
    def _apply_syntax_highlighting(self):
        """Apply syntax highlighting to SRT format."""
        try:
            for tag in ["number", "timestamp", "arrow", "text", "error"]:
                self.text_editor.tag_remove(tag, "1.0", "end")
            
            content = self.text_editor.get("1.0", "end-1c")
            lines = content.split('\n')
            
            import re
            line_num = 1
            i = 0
            
            while i < len(lines):
                line = lines[i]
                if line.strip().isdigit():
                    self.text_editor.tag_add("number", f"{line_num}.0", f"{line_num}.end")
                elif '-->' in line:
                    timestamp_pattern = r'^\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}$'
                    if re.match(timestamp_pattern, line.strip()):
                        parts = line.split('-->')
                        if len(parts) == 2:
                            self.text_editor.tag_add("timestamp", f"{line_num}.0", f"{line_num}.{len(parts[0])}")
                            self.text_editor.tag_add("arrow", f"{line_num}.{len(parts[0])}", f"{line_num}.{len(parts[0]) + 3}")
                            self.text_editor.tag_add("timestamp", f"{line_num}.{len(parts[0]) + 3}", f"{line_num}.end")
                    else:
                        self.text_editor.tag_add("error", f"{line_num}.0", f"{line_num}.end")
                elif line.strip() and not line.strip().isdigit() and '-->' not in line:
                    self.text_editor.tag_add("text", f"{line_num}.0", f"{line_num}.end")
                line_num += 1
                i += 1
        except Exception:
            pass
    
    def _toggle_syntax(self):
        """Toggle syntax highlighting on/off."""
        self.syntax_enabled = not self.syntax_enabled
        if self.syntax_enabled:
            self.syntax_btn.configure(text="🎨 Syntax: ON")
            self._apply_syntax_highlighting()
        else:
            self.syntax_btn.configure(text="🎨 Syntax: OFF")
            for tag in ["number", "timestamp", "arrow", "text", "error"]:
                self.text_editor.tag_remove(tag, "1.0", "end")
    
    def _show_find_dialog(self):
        """Show find dialog."""
        dialog = ctk.CTkInputDialog(text="Enter text to find:", title="Find")
        search_text = dialog.get_input()
        if search_text:
            self._find_text(search_text)
    
    def _find_text(self, search_text: str):
        """Find and highlight text in editor."""
        self.text_editor.tag_remove("search_highlight", "1.0", "end")
        self.search_matches = []
        start_pos = "1.0"
        while True:
            pos = self.text_editor.search(search_text, start_pos, stopindex="end", nocase=True)
            if not pos: break
            end_pos = f"{pos}+{len(search_text)}c"
            self.text_editor.tag_add("search_highlight", pos, end_pos)
            self.search_matches.append(pos)
            start_pos = end_pos
        if self.search_matches:
            self.text_editor.see(self.search_matches[0])
            self.stats_label.configure(text=f"🔍 Found {len(self.search_matches)} matches")
        else:
            self.stats_label.configure(text="🔍 No matches found")
    
    def _show_replace_dialog(self):
        """Show replace dialog."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Find & Replace")
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        self.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - 400) // 2
        y = self.winfo_rooty() + (self.winfo_height() - 200) // 2
        dialog.geometry(f"+{x}+{y}")
        frame = ctk.CTkFrame(dialog, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(frame, text="Find what:").grid(row=0, column=0, sticky="w", pady=(0, 10))
        find_entry = ctk.CTkEntry(frame, width=250)
        find_entry.grid(row=0, column=1, pady=(0, 10))
        find_entry.focus_set()
        ctk.CTkLabel(frame, text="Replace with:").grid(row=1, column=0, sticky="w", pady=(0, 20))
        replace_entry = ctk.CTkEntry(frame, width=250)
        replace_entry.grid(row=1, column=1, pady=(0, 20))
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        def do_replace():
            find_txt = find_entry.get()
            rep_txt = replace_entry.get()
            if find_txt:
                count = self._replace_text(find_txt, rep_txt)
                dialog.destroy()
                from tkinter import messagebox
                messagebox.showinfo("Replace", f"Replaced {count} occurrences.")
                if hasattr(self, 'stats_label'):
                    self.stats_label.configure(text=f"Aa Replaced {count} occurrences")
        ctk.CTkButton(btn_frame, text="Replace All", command=do_replace, width=100).pack(side="right")
        ctk.CTkButton(btn_frame, text="Cancel", command=dialog.destroy, fg_color=COLORS["bg_light"], hover_color=COLORS["border"], width=80).pack(side="right", padx=10)

    def _replace_text(self, find_text: str, replace_text: str) -> int:
        """Replace all occurrences of text."""
        content = self.text_editor.get("1.0", "end-1c")
        new_content, count = content.replace(find_text, replace_text), content.count(find_text)
        if count > 0:
            self.text_editor.delete("1.0", "end")
            self.text_editor.insert("1.0", new_content)
            if self.syntax_enabled:
                self._apply_syntax_highlighting()
        return count

    def _show_goto_dialog(self):
        """Show go to entry dialog."""
        dialog = ctk.CTkInputDialog(text="Enter entry number to jump to:", title="Go to Entry")
        entry_num = dialog.get_input()
        if entry_num and entry_num.isdigit():
            self._goto_entry(int(entry_num))
    
    def _goto_entry(self, entry_num: int):
        """Jump to specific subtitle entry."""
        try:
            content = self.text_editor.get("1.0", "end-1c")
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.strip() == str(entry_num):
                    line_pos = f"{i + 1}.0"
                    self.text_editor.see(line_pos)
                    self.text_editor.mark_set("insert", line_pos)
                    self.stats_label.configure(text=f"↗️ Jumped to entry {entry_num}")
                    return
            self.stats_label.configure(text=f"⚠️ Entry {entry_num} not found")
        except Exception as e:
            self.stats_label.configure(text=f"⚠️ Error: {str(e)}")
    
    def _validate_content(self):
        """Validate SRT format and show errors."""
        try:
            content = self.text_editor.get("1.0", "end-1c")
            lines = content.split('\n')
            errors = []
            import re
            i, entry_count, expected_num = 0, 0, 1
            while i < len(lines):
                line = lines[i].strip()
                if not line: i += 1; continue
                if not line.isdigit():
                    errors.append(f"Line {i+1}: Expected entry number, got '{line[:30]}'"); i += 1; continue
                entry_num = int(line)
                if entry_num != expected_num:
                    errors.append(f"Line {i+1}: Entry number {entry_num} out of sequence (expected {expected_num})")
                expected_num += 1; entry_count += 1; i += 1
                if i >= len(lines): errors.append(f"Entry {entry_num}: Missing timestamp"); break
                timestamp_line = lines[i].strip()
                timestamp_pattern = r'^\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}$'
                if not re.match(timestamp_pattern, timestamp_line):
                    errors.append(f"Line {i+1}: Invalid timestamp format")
                i += 1
                has_text = False
                while i < len(lines) and lines[i].strip() and not lines[i].strip().isdigit():
                    has_text = True; i += 1
                if not has_text: errors.append(f"Entry {entry_num}: Missing subtitle text")
            if errors:
                error_msg = f"⚠️ Found {len(errors)} error(s):\n" + "\n".join(errors[:5])
                if len(errors) > 5: error_msg += f"\n... and {len(errors) - 5} more"
                from tkinter import messagebox
                messagebox.showwarning("Validation Errors", error_msg)
                self.stats_label.configure(text=f"⚠️ {len(errors)} validation error(s)")
            else:
                from tkinter import messagebox
                messagebox.showinfo("Validation", f"✓ Valid SRT format!\n{entry_count} entries checked.")
                self.stats_label.configure(text=f"✓ Valid SRT format ({entry_count} entries)")
        except Exception as e:
            self.stats_label.configure(text=f"⚠️ Validation error: {str(e)}")
    
    def _on_approve(self):
        """Handle approve button click."""
        content = self.text_editor.get("0.0", "end-1c")
        if self.on_approve_callback:
            self.on_approve_callback(content)
    
    def _on_discard(self):
        """Handle discard button click."""
        if self.on_discard_callback:
            self.on_discard_callback()
