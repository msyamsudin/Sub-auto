"""
History View for Sub-auto
Displays a list of past translation sessions and their details.
"""

import customtkinter as ctk
from pathlib import Path
from typing import Optional, List, Callable, Dict
from datetime import datetime

from .styles import (
    COLORS, FONTS, SPACING, RADIUS,
    get_button_style, get_frame_style, get_label_style
)
from core.history_manager import get_history_manager, HistoryEntry


class HistoryEntryItem(ctk.CTkFrame):
    """A single row in the history list."""
    
    def __init__(
        self,
        master,
        entry: HistoryEntry,
        on_click: Callable[[HistoryEntry], None],
        on_delete: Callable[[str], None],
        on_select: Callable[[str, bool], None],
        **kwargs
    ):
        super().__init__(master, fg_color=COLORS["bg_dark"], corner_radius=RADIUS["md"], **kwargs)
        
        self.entry = entry
        self.on_click = on_click
        self.on_delete = on_delete
        self.on_select = on_select
        self.is_selected_var = ctk.BooleanVar(value=False)
        
        self._setup_ui()
        self._bind_click_recursive(self)
        
    def _setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Checkbox for bulk selection
        self.checkbox = ctk.CTkCheckBox(
            self,
            text="",
            variable=self.is_selected_var,
            command=self._on_checkbox_change,
            width=24,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            border_color=COLORS["text_muted"]
        )
        self.checkbox.grid(row=0, column=0, padx=(SPACING["sm"], 0), sticky="w")
        
        # Info container
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=0, column=1, sticky="nsew", padx=SPACING["sm"], pady=SPACING["sm"])
        
        # Title (Filename)
        title_lbl = ctk.CTkLabel(
            info_frame,
            text=self.entry.source_file_name or Path(self.entry.source_file).name,
            **get_label_style("body")
        )
        title_lbl.pack(anchor="w")
        
        # Meta info
        try:
            dt = datetime.fromisoformat(self.entry.timestamp)
            date_str = dt.strftime("%Y-%m-%d %H:%M")
        except:
            date_str = self.entry.timestamp
            
        meta_text = f"{date_str} • {self.entry.source_lang} → {self.entry.target_lang} • {self.entry.model_name}"
        meta_lbl = ctk.CTkLabel(
            info_frame,
            text=meta_text,
            **get_label_style("muted")
        )
        meta_lbl.pack(anchor="w")
        
        # Status Badge (Small)
        status_color = COLORS["success"] if self.entry.status == "completed" else COLORS["warning"]
        status_text = self.entry.status.upper()
        
        status_lbl = ctk.CTkLabel(
            self,
            text=status_text,
            font=(FONTS["family"], 10, "bold"),
            text_color=status_color,
            fg_color=COLORS["bg_medium"],
            corner_radius=4,
            width=70,
            height=20
        )
        status_lbl.grid(row=0, column=2, padx=SPACING["sm"])
        
        # Delete button
        self.delete_btn = ctk.CTkButton(
            self,
            text="✕", # Keep consistent with title bar, but ensure it's standard
            width=24,
            height=24,
            fg_color="transparent",
            hover_color=COLORS["error"],
            text_color=COLORS["text_muted"],
            command=lambda: self.on_delete(self.entry.id)
        )
        self.delete_btn.grid(row=0, column=3, padx=SPACING["sm"])

    def _on_checkbox_change(self):
        self.on_select(self.entry.id, self.is_selected_var.get())

    def _bind_click_recursive(self, widget):
        if widget not in [self.checkbox, self.delete_btn]:
            widget.bind("<Button-1>", lambda e: self.on_click(self.entry))
            if hasattr(widget, "configure"):
                widget.configure(cursor="hand2")
                
        for child in widget.winfo_children():
            self._bind_click_recursive(child)


class HistoryView(ctk.CTkFrame):
    """Full-screen history view."""
    
    def __init__(
        self,
        master,
        on_close: Callable,
        **kwargs
    ):
        super().__init__(master, fg_color=COLORS["bg_dark"], **kwargs)
        
        self.on_close = on_close
        self.history_manager = get_history_manager()
        self.selected_ids = set()
        
        self._setup_ui()
        self._load_entries()
        
    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # --- Header ---
        header_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_medium"], height=60, corner_radius=0)
        header_frame.grid(row=0, column=0, sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)
        
        back_btn = ctk.CTkButton(
            header_frame,
            text="← Back",
            width=80,
            command=self.on_close,
            **get_button_style("secondary")
        )
        back_btn.grid(row=0, column=0, padx=SPACING["md"], pady=SPACING["sm"])
        
        title_lbl = ctk.CTkLabel(
            header_frame,
            text="Translation History",
            **get_label_style("heading")
        )
        title_lbl.grid(row=0, column=1, sticky="w", padx=SPACING["md"])
        
        # Bulk actions
        actions_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        actions_frame.grid(row=0, column=2, padx=SPACING["md"])
        
        self.delete_selected_btn = ctk.CTkButton(
            actions_frame,
            text="Delete Selected",
            width=120,
            state="disabled",
            command=self._delete_selected,
            **get_button_style("secondary")
        )
        self.delete_selected_btn.pack(side="left", padx=SPACING["xs"])
        
        clear_all_btn = ctk.CTkButton(
            actions_frame,
            text="Clear All",
            width=100,
            command=self._clear_all,
            **get_button_style("secondary")
        )
        clear_all_btn.pack(side="left", padx=SPACING["xs"])
        
        # --- Main Content (Split View) ---
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.grid(row=1, column=0, sticky="nsew", padx=SPACING["md"], pady=SPACING["md"])
        content_frame.grid_columnconfigure(0, weight=4) # List
        content_frame.grid_columnconfigure(1, weight=3) # Details
        content_frame.grid_rowconfigure(0, weight=1)
        
        # Left: Scrollable List
        list_container = ctk.CTkFrame(content_frame, **get_frame_style("card"))
        list_container.grid(row=0, column=0, sticky="nsew", padx=(0, SPACING["md"]))
        list_container.grid_columnconfigure(0, weight=1)
        list_container.grid_rowconfigure(0, weight=1)
        
        self.scroll_frame = ctk.CTkScrollableFrame(
            list_container,
            fg_color="transparent"
        )
        self.scroll_frame.grid(row=0, column=0, sticky="nsew", padx=SPACING["xs"], pady=SPACING["xs"])
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        
        # Right: Detail View
        self.detail_frame = ctk.CTkFrame(content_frame, **get_frame_style("card"))
        self.detail_frame.grid(row=0, column=1, sticky="nsew")
        self._show_empty_details()
        
    def _show_empty_details(self):
        for widget in self.detail_frame.winfo_children():
            widget.destroy()
            
        empty_lbl = ctk.CTkLabel(
            self.detail_frame,
            text="Select an entry to view details",
            **get_label_style("muted")
        )
        empty_lbl.place(relx=0.5, rely=0.5, anchor="center")
        
    def _show_entry_details(self, entry: HistoryEntry):
        for widget in self.detail_frame.winfo_children():
            widget.destroy()
            
        self.detail_frame.grid_columnconfigure(0, weight=1)
        self.detail_frame.grid_rowconfigure(0, weight=1)
        
        # Scrollable area for details
        d_scroll = ctk.CTkScrollableFrame(self.detail_frame, fg_color="transparent")
        d_scroll.pack(fill="both", expand=True, padx=SPACING["md"], pady=SPACING["md"])
        d_scroll.grid_columnconfigure(0, weight=1)
        
        # --- Header Section (Large Icon + Filename) ---
        header_card = ctk.CTkFrame(d_scroll, fg_color=COLORS["bg_dark"], corner_radius=RADIUS["md"])
        header_card.pack(fill="x", pady=(0, SPACING["md"]))
        header_card.grid_columnconfigure(1, weight=1)
        
        icon_lbl = ctk.CTkLabel(header_card, text="🎬", font=(FONTS["family"], 32))
        icon_lbl.grid(row=0, column=0, rowspan=2, padx=SPACING["md"], pady=SPACING["md"])
        
        name_lbl = ctk.CTkLabel(
            header_card, 
            text=entry.source_file_name or Path(entry.source_file).name,
            font=(FONTS["family"], FONTS["body_size"] + 2, "bold"),
            text_color=COLORS["accent"],
            wraplength=250,
            anchor="w"
        )
        name_lbl.grid(row=0, column=1, sticky="sw", padx=(0, SPACING["md"]), pady=(SPACING["md"], 0))
        
        try:
            dt = datetime.fromisoformat(entry.timestamp)
            date_str = dt.strftime("%B %d, %Y at %H:%M")
        except:
            date_str = entry.timestamp
            
        date_lbl = ctk.CTkLabel(
            header_card,
            text=date_str,
            **get_label_style("muted")
        )
        date_lbl.grid(row=1, column=1, sticky="nw", padx=(0, SPACING["md"]), pady=(0, SPACING["md"]))

        # --- Helper for Info Cards ---
        def create_card(parent, title, icon):
            card = ctk.CTkFrame(parent, fg_color="transparent")
            card.pack(fill="x", pady=SPACING["sm"])
            
            title_frame = ctk.CTkFrame(card, fg_color="transparent")
            title_frame.pack(fill="x", pady=(0, 2))
            ctk.CTkLabel(title_frame, text=icon, font=(FONTS["family"], 14)).pack(side="left")
            ctk.CTkLabel(title_frame, text=title, font=(FONTS["family"], 12, "bold"), text_color=COLORS["text_secondary"]).pack(side="left", padx=5)
            
            content = ctk.CTkFrame(card, fg_color=COLORS["bg_medium"], corner_radius=RADIUS["sm"], border_width=1, border_color=COLORS["border"])
            content.pack(fill="x")
            content.grid_columnconfigure(1, weight=1)
            return content

        def add_row(parent, label, value, row_idx):
            lbl = ctk.CTkLabel(parent, text=f"{label}:", width=100, anchor="w", **get_label_style("muted"))
            lbl.grid(row=row_idx, column=0, padx=(SPACING["md"], 5), pady=SPACING["xxs"], sticky="w")
            val = ctk.CTkLabel(parent, text=str(value), anchor="w", wraplength=200, **get_label_style("body"))
            val.grid(row=row_idx, column=1, padx=(0, SPACING["md"]), pady=SPACING["xxs"], sticky="w")

        # --- Session Card ---
        session_card = create_card(d_scroll, "Session Info", "📂")
        add_row(session_card, "Path", entry.source_file, 0)
        add_row(session_card, "Output", entry.output_file or "N/A", 1)
        add_row(session_card, "Language", f"{entry.source_lang} → {entry.target_lang}", 2)
        add_row(session_card, "Track ID", f"#{entry.track_id}", 3)
        
        # --- AI Card ---
        ai_card = create_card(d_scroll, "AI & Prompt", "🤖")
        add_row(ai_card, "Model", entry.model_name, 0)
        add_row(ai_card, "Provider", entry.provider.capitalize(), 1)
        add_row(ai_card, "Prompt", entry.prompt_name or "Standard", 2)
        
        # --- Performance Card ---
        perf_card = create_card(d_scroll, "Performance", "⚡")
        add_row(perf_card, "Status", entry.status.upper(), 0)
        add_row(perf_card, "Lines", f"{entry.lines_translated} / {entry.total_lines}", 1)
        
        duration_str = f"{entry.duration_seconds:.1f}s"
        if entry.duration_seconds > 60:
            duration_str = f"{entry.duration_seconds/60:.1f}m"
        add_row(perf_card, "Duration", duration_str, 2)
        
        # Tokens & Cost
        total_tokens = entry.prompt_tokens + entry.completion_tokens
        token_info = f"{total_tokens:,} (P: {entry.prompt_tokens:,} | O: {entry.completion_tokens:,})"
        add_row(perf_card, "Tokens", token_info, 3)
        
        if entry.estimated_cost is not None:
            add_row(perf_card, "Est. Cost", f"${entry.estimated_cost:.4f}", 4)
            
        if entry.error_message:
            error_card = create_card(d_scroll, "Error Info", "⚠️")
            add_row(error_card, "Message", entry.error_message, 0)

    def _load_entries(self):
        # Clear scroll frame
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
            
        entries = self.history_manager.get_entries()
        
        if not entries:
            ctk.CTkLabel(
                self.scroll_frame,
                text="No history found",
                **get_label_style("muted")
            ).pack(pady=SPACING["xl"])
            return
            
        for entry in entries:
            item = HistoryEntryItem(
                self.scroll_frame,
                entry=entry,
                on_click=self._show_entry_details,
                on_delete=self._delete_single,
                on_select=self._on_item_select
            )
            item.pack(fill="x", pady=SPACING["xs"], padx=SPACING["xs"])
            
    def _on_item_select(self, entry_id: str, is_selected: bool):
        if is_selected:
            self.selected_ids.add(entry_id)
        else:
            self.selected_ids.discard(entry_id)
            
        self.delete_selected_btn.configure(
            state="normal" if self.selected_ids else "disabled",
            text=f"Delete Selected ({len(self.selected_ids)})" if self.selected_ids else "Delete Selected"
        )
        
    def _delete_single(self, entry_id: str):
        self.history_manager.delete_entry(entry_id)
        self.selected_ids.discard(entry_id)
        self._load_entries()
        self._show_empty_details()
        self._on_item_select("", False) # Update button state
        
    def _delete_selected(self):
        if not self.selected_ids:
            return
        self.history_manager.delete_entries(list(self.selected_ids))
        self.selected_ids.clear()
        self._load_entries()
        self._show_empty_details()
        self._on_item_select("", False)
        
    def _clear_all(self):
        from tkinter import messagebox
        if messagebox.askyesno("Clear All History", "Are you sure you want to delete ALL history entries?"):
            self.history_manager.clear_all()
            self.selected_ids.clear()
            self._load_entries()
            self._show_empty_details()
            self._on_item_select("", False)
