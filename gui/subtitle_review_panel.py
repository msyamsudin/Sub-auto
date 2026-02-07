import customtkinter as ctk
import tkinter as tk
from typing import List, Optional, Callable, Dict, Any, Tuple
import datetime
from dataclasses import dataclass, field
import pysubs2
from pathlib import Path
import re

from .styles import COLORS, FONTS, SPACING, RADIUS, get_button_style, get_label_style
from core.subtitle_parser import SubtitleParser, SubtitleLine

@dataclass
class ReviewEntry:
    """Data structure for a single subtitle entry in the review panel."""
    index: int  # 0-based index
    original_line: SubtitleLine
    style_info: Dict[str, Any] = field(default_factory=dict)
    
    # Editable fields
    text: str = ""
    start_ms: int = 0
    end_ms: int = 0
    actor: str = ""
    style: str = ""
    
    def __post_init__(self):
        if not self.text:
            self.text = self.original_line.text
        if self.start_ms == 0:
            self.start_ms = self.original_line.start_ms
        if self.end_ms == 0:
            self.end_ms = self.original_line.end_ms
        if not self.actor:
            self.actor = self.original_line.actor
        if not self.style:
            self.style = self.original_line.style

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms
        
    @property
    def start_time_str(self) -> str:
        return self._ms_to_str(self.start_ms)
        
    @property
    def end_time_str(self) -> str:
        return self._ms_to_str(self.end_ms)
    
    @property
    def duration_str(self) -> str:
        s = self.duration_ms / 1000.0
        return f"{s:.2f}s"

    @staticmethod
    def _ms_to_str(ms: int) -> str:
        # Format HH:MM:SS.mm
        s = ms / 1000.0
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        return f"{int(h):02d}:{int(m):02d}:{s:05.2f}"

    def update_from_timings(self, start_str: str, end_str: str):
        """Parse string back to ms."""
        def parse(t_str):
            t_str = t_str.replace(',', '.')
            parts = t_str.split(':')
            h = int(parts[0])
            m = int(parts[1])
            s = float(parts[2])
            return int((h * 3600 + m * 60 + s) * 1000)
        
        try:
            self.start_ms = parse(start_str)
            self.end_ms = parse(end_str)
        except:
            pass # Keep old if fail

class SubtitleRow(ctk.CTkFrame):
    """
    A single row in the Structured Editor list.
    Layout: [Index] [Start] [End] [Speaker] [Text Preview]
    """
    def __init__(
        self, 
        master, 
        entry: ReviewEntry, 
        on_click: Callable[[ReviewEntry], None],
        is_selected: bool = False,
        **kwargs
    ):
        super().__init__(master, fg_color=COLORS["bg_medium"] if not is_selected else COLORS["bg_light"], corner_radius=0, height=30, **kwargs)
        self.entry = entry
        self.on_click = on_click
        self.is_selected = is_selected
        
        self.pack_propagate(False) # Enforce height
        self._setup_ui()
        self._bind_events()
        
    def _setup_ui(self):
        # Grid layout for columns
        self.grid_columnconfigure(4, weight=1) # Text expands
        
        # Style helper
        font_mono = (FONTS["mono_family"], 11)
        font_ui = (FONTS["family"], 11)
        text_col = COLORS["text_primary"] if self.is_selected else COLORS["text_secondary"]
        
    def _setup_ui(self):
        # Grid layout for columns
        self.grid_columnconfigure(4, weight=1) # Text expands
        
        # Style helper
        font_mono = (FONTS["mono_family"], 11)
        font_ui = (FONTS["family"], 11)
        text_col = COLORS["text_primary"] if self.is_selected else COLORS["text_secondary"]
        
        # 1. Index
        l1 = ctk.CTkLabel(self, text=str(self.entry.index + 1), width=40, font=font_mono, text_color=COLORS["text_muted"])
        l1.grid(row=0, column=0, sticky="w", padx=2)
        
        # 2. Start
        l2 = ctk.CTkLabel(self, text=self.entry.start_time_str, width=90, font=font_mono, text_color=text_col)
        l2.grid(row=0, column=1, sticky="w", padx=2)
        
        # 3. End
        l3 = ctk.CTkLabel(self, text=self.entry.end_time_str, width=90, font=font_mono, text_color=text_col)
        l3.grid(row=0, column=2, sticky="w", padx=2)
        
        # 4. Speaker/Actor (Shortened)
        actor = self.entry.actor or "-"
        l4 = ctk.CTkLabel(self, text=actor[:10], width=80, font=font_ui, text_color=COLORS["accent"])
        l4.grid(row=0, column=3, sticky="w", padx=4)
        
        # 5. Text Preview (Strip tags)
        clean_text = re.sub(r'\{.*?\}', '', self.entry.text).replace(r'\N', ' ')
        l5 = ctk.CTkLabel(self, text=clean_text, font=font_ui, text_color=text_col, anchor="w")
        l5.grid(row=0, column=4, sticky="ew", padx=4)
        
        # Store labels to bind events later
        self.labels = [l1, l2, l3, l4, l5]
        
    def _bind_events(self):
        for w in self.winfo_children():
            w.bind("<Button-1>", self._on_clicked)
        self.bind("<Button-1>", self._on_clicked)
        
    def bind_scroll(self, handler):
        """Bind scroll event to self and all children."""
        self.bind("<MouseWheel>", handler)
        for w in self.labels:
            w.bind("<MouseWheel>", handler)
        
    def _on_clicked(self, event):
        self.on_click(self.entry)


class SubtitleDetailPanel(ctk.CTkFrame):
    """
    Right panel for editing the selected SubtitleRow.
    """
    def __init__(self, master, on_change: Callable[[ReviewEntry], None], **kwargs):
        super().__init__(master, fg_color=COLORS["bg_dark"], **kwargs)
        self.on_change = on_change
        self.current_entry: Optional[ReviewEntry] = None
        
        self._setup_ui()
        
    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1) # Text area expands
        
        # 1. Header (Timing)
        self.timing_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.timing_frame.grid(row=0, column=0, sticky="ew", padx=SPACING["md"], pady=SPACING["md"])
        
        self.start_input = self._create_time_input(self.timing_frame, "Start")
        self.start_input.pack(side="left", padx=(0, 10))
        
        self.end_input = self._create_time_input(self.timing_frame, "End")
        self.end_input.pack(side="left")
        
        # Duration Label
        self.duration_lbl = ctk.CTkLabel(self.timing_frame, text="", text_color=COLORS["text_muted"])
        self.duration_lbl.pack(side="left", padx=10)
        
        # Validation Label
        self.validation_lbl = ctk.CTkLabel(self.timing_frame, text="", text_color=COLORS["warning"], font=(FONTS["family"], 11))
        self.validation_lbl.pack(side="left", padx=5)
        
        # 2. Metadata (Actor / Style)
        self.meta_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.meta_frame.grid(row=1, column=0, sticky="ew", padx=SPACING["md"], pady=(0, SPACING["md"]))
        
        self.actor_entry = ctk.CTkEntry(self.meta_frame, placeholder_text="Actor", width=120)
        self.actor_entry.pack(side="left", padx=(0, 10))
        self.actor_entry.bind("<FocusOut>", self._on_meta_change)
        
        self.style_var = ctk.StringVar(value="Default")
        self.style_menu = ctk.CTkOptionMenu(self.meta_frame, variable=self.style_var, values=["Default"])
        self.style_menu.pack(side="left")
        
        # 3. Toolbar (Formatting)
        self.toolbar = ctk.CTkFrame(self, fg_color="transparent", height=30)
        self.toolbar.grid(row=2, column=0, sticky="ew", padx=SPACING["md"])
        
        # Bold
        ctk.CTkButton(self.toolbar, text="B", width=30, fg_color="transparent", border_width=1, command=lambda: self._insert_tag("{\\b1}", "{\\b0}")).pack(side="left", padx=2)
        # Italic
        ctk.CTkButton(self.toolbar, text="I", width=30, fg_color="transparent", border_width=1, command=lambda: self._insert_tag("{\\i1}", "{\\i0}")).pack(side="left", padx=2)
        
        # 4. Text Editor
        self.text_editor = ctk.CTkTextbox(self, font=(FONTS["family"], 14), wrap="word")
        self.text_editor.grid(row=3, column=0, sticky="nsew", padx=SPACING["md"], pady=(0, SPACING["md"]))
        self.text_editor.bind("<KeyRelease>", self._on_text_change)
        
        # Save Trigger on Focus Out or similar? 
        # For now, explicit KeyRelease updates model
        
    def _create_time_input(self, parent, label):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        ctk.CTkLabel(f, text=label, font=(FONTS["family"], 10)).pack(anchor="w")
        e = ctk.CTkEntry(f, width=110, font=(FONTS["mono_family"], 12))
        e.bind("<FocusOut>", self._on_timing_change)
        e.bind("<Return>", self._on_timing_change)
        e.pack()
        return e

    def set_entry(self, entry: ReviewEntry):
        self.current_entry = entry
        
        # Update UI without triggering events
        self.text_editor.delete("0.0", "end")
        self.text_editor.insert("0.0", entry.text.replace(r'\N', '\n'))
        
        self.start_input.delete(0, "end")
        self.start_input.insert(0, entry.start_time_str)
        
        self.end_input.delete(0, "end")
        self.end_input.insert(0, entry.end_time_str)
        
        self.actor_entry.delete(0, "end")
        self.actor_entry.insert(0, entry.actor)
        
        self.style_var.set(entry.style)
        self.duration_lbl.configure(text=f"{entry.duration_str}")

    def _insert_tag(self, start_tag, end_tag):
        # Insert at cursor or around selection
        try:
            sel_start = self.text_editor.index("sel.first")
            sel_end = self.text_editor.index("sel.last")
            text = self.text_editor.get(sel_start, sel_end)
            self.text_editor.delete(sel_start, sel_end)
            self.text_editor.insert(sel_start, f"{start_tag}{text}{end_tag}")
        except:
            self.text_editor.insert("insert", f"{start_tag}{end_tag}")
        self._on_text_change()

    def _validate(self):
        if not self.current_entry: return
        msgs = []
        # Duration check
        if self.current_entry.duration_ms < 500:
            msgs.append("Duration too short (<0.5s)")
        elif self.current_entry.duration_ms > 10000:
            msgs.append("Duration too long (>10s)")
            
        # Overlap check (needs access to other entries, requires callback or passing list? For now just duration)
        
        if msgs:
            self.validation_lbl.configure(text=" • ".join(msgs), text_color=COLORS["warning"])
        else:
            self.validation_lbl.configure(text="", text_color=COLORS["success"])

    def _on_text_change(self, event=None):
        if self.current_entry:
            val = self.text_editor.get("0.0", "end-1c")
            self.current_entry.text = val.replace('\n', r'\N')
            self._validate()
            self.on_change(self.current_entry)
            
    def _on_timing_change(self, event=None):
        if self.current_entry:
            self.current_entry.update_from_timings(self.start_input.get(), self.end_input.get())
            self.duration_lbl.configure(text=self.current_entry.duration_str)
            self._validate()
            self.on_change(self.current_entry)
            
    def _on_meta_change(self, event=None):
        if self.current_entry:
            self.current_entry.actor = self.actor_entry.get()
            self.on_change(self.current_entry)


class VirtualizedListView(ctk.CTkFrame):
    """
    Vertical list of SubtitleRows.
    """
    def __init__(self, master, entries: List[ReviewEntry], on_select: Callable[[ReviewEntry], None], **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.entries = entries
        self.on_select = on_select
        self.row_height = 30
        
        self.active_widgets = {} # index -> (widget, window_id)
        self.selected_index = -1
        
        # Canvas Setup
        self.scrollbar = ctk.CTkScrollbar(self, command=self._on_scroll)
        self.scrollbar.pack(side="right", fill="y")
        
        self.canvas = tk.Canvas(self, bg=COLORS["bg_dark"], highlightthickness=0, yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        
        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self._update_scroll_region()

    def set_entries(self, entries: List[ReviewEntry]):
        self.entries = entries
        self.deselect()
        self._update_scroll_region()
        self._refresh_visible(force_redraw=True)
        
    def deselect(self):
        self.selected_index = -1
        # Refresh to remove highlight
        self._refresh_visible(force_redraw=True)

    def select_index(self, index: int):
        self.selected_index = index
        self._refresh_visible(force_redraw=True)

    def _update_scroll_region(self):
        h = len(self.entries) * self.row_height
        self.canvas.configure(scrollregion=(0, 0, self.winfo_width(), h))

    def _on_scroll(self, *args):
        self.canvas.yview(*args)
        self._refresh_visible()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self._refresh_visible()

    def _on_resize(self, event):
        self.canvas.itemconfig("all", width=event.width)
        self._refresh_visible()

    def _refresh_visible(self, force_redraw=False):
        if not self.entries: return
        
        # Get visible range
        try:
            top_y = self.canvas.yview()[0] * (len(self.entries) * self.row_height)
            height = self.canvas.winfo_height()
        except:
             return

        start_idx = max(0, int(top_y // self.row_height))
        end_idx = min(len(self.entries), start_idx + (height // self.row_height) + 2)
        
        visible_indices = set(range(start_idx, end_idx))
        
        # Cleanup invisible
        if not force_redraw:
            for idx in list(self.active_widgets.keys()):
                if idx not in visible_indices:
                    w, wid = self.active_widgets.pop(idx)
                    self.canvas.delete(wid)
                    w.destroy()
        else:
            # Clear all if forced
            self.canvas.delete("all")
            self.active_widgets = {}

        # Create new
        width = self.canvas.winfo_width()
        for i in visible_indices:
            if i in self.active_widgets and not force_redraw:
                continue
                
            y = i * self.row_height
            entry = self.entries[i]
            
            row = SubtitleRow(
                self.canvas, 
                entry=entry, 
                on_click=lambda e: self.on_select(e),
                is_selected=(i == self.selected_index),
                width=width
            )
            row.bind_scroll(self._on_mousewheel)
            
            wid = self.canvas.create_window(0, y, window=row, anchor="nw", width=width, height=self.row_height)
            self.active_widgets[i] = (row, wid)


class SubtitleReviewPanel(ctk.CTkFrame):
    """
    Main Editor Component v2.
    """
    def __init__(self, master, subtitle_path: str, on_approve: Callable[[str], None], on_discard: Callable[[], None], **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.subtitle_path = subtitle_path
        self.on_approve = on_approve
        self.on_discard = on_discard
        
        self.parser = SubtitleParser()
        self.entries: List[ReviewEntry] = []
        
        self.list_view: Optional[VirtualizedListView] = None
        
        self._setup_ui()
        self._load_data()
        
    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Tab View
        self.tabview = ctk.CTkTabview(self, anchor="nw")
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=SPACING["sm"])
        
        self.tab_structured = self.tabview.add("Structured")
        self.tab_raw = self.tabview.add("Raw ASS")
        
        self._setup_structured_tab()
        self._setup_raw_tab()
        
    def _setup_structured_tab(self):
        t = self.tab_structured
        t.grid_columnconfigure(0, weight=1) # List
        t.grid_columnconfigure(1, weight=1) # Detail
        t.grid_rowconfigure(0, weight=1)
        
        # 1. Split Left (List)
        self.list_frame = ctk.CTkFrame(t, fg_color="transparent")
        self.list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, SPACING["md"]))
        self.list_frame.grid_columnconfigure(0, weight=1)
        self.list_frame.grid_rowconfigure(1, weight=1)
        
        # Search/Filter
        self.search_entry = ctk.CTkEntry(self.list_frame, placeholder_text="Search...")
        self.search_entry.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.search_entry.bind("<KeyRelease>", self._on_search)
        
        # List Container (will hold VirtualizedListView)
        self.list_container = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        self.list_container.grid(row=1, column=0, sticky="nsew")

        # 2. Split Right (Review/Edit)
        self.detail_panel = SubtitleDetailPanel(t, on_change=self._on_entry_changed)
        self.detail_panel.grid(row=0, column=1, sticky="nsew")
        
        # 3. Actions Footer (Bottom of Tab)
        self.footer = ctk.CTkFrame(t, height=40, fg_color="transparent")
        self.footer.grid(row=1, column=0, columnspan=2, sticky="ew", pady=10)
        
        ctk.CTkButton(self.footer, text="Discard", command=self.on_discard, fg_color=COLORS["error"]).pack(side="left")
        ctk.CTkButton(self.footer, text="Approve & Merge", command=self._handle_approve, fg_color=COLORS["success"]).pack(side="right")
        
    def _setup_raw_tab(self):
        t = self.tab_raw
        t.grid_columnconfigure(0, weight=1)
        t.grid_rowconfigure(0, weight=1)
        
        self.raw_text = ctk.CTkTextbox(t, font=(FONTS["mono_family"], 12), wrap="none")
        self.raw_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
    def _load_data(self):
        try:
            # Load Data
            self.parser.load(self.subtitle_path)
            
            # Populate Entries
            self.entries = []
            for line in self.parser.load(self.subtitle_path):
                 self.entries.append(ReviewEntry(
                    index=line.index,
                    original_line=line,
                    text=line.text,
                    start_ms=line.start_ms,
                    end_ms=line.end_ms
                ))
            
            # Styles for dropdown
            styles = []
            if self.parser.subs and hasattr(self.parser.subs, 'styles'):
                styles = list(self.parser.subs.styles.keys())
            if styles:
                self.detail_panel.style_menu.configure(values=styles)
                
            # Populate List
            self.list_view = VirtualizedListView(
                self.list_container, 
                self.entries, 
                on_select=self._on_row_selected
            )
            self.list_view.pack(fill="both", expand=True)
            
            # Populate Raw
            if self.parser.subs:
                self.raw_text.insert("0.0", self.parser.subs.to_string(self.parser.original_format))
                
        except Exception as e:
            print(f"Error loading: {e}")

    def _on_row_selected(self, entry: ReviewEntry):
        if self.list_view:
            self.list_view.select_index(entry.index)
        self.detail_panel.set_entry(entry)
        
    def _on_entry_changed(self, entry: ReviewEntry):
        # Update entry in list (visual refresh not full reload)
        # Ideally we'd update just the row, but full redraw for now is safer/simpler
        if self.list_view:
             # self.list_view._refresh_visible(force_redraw=True)
             # Optimization: _refresh_visible re-creates widgets. 
             # Maybe enough to just keep data in sync.
             pass

    def _on_search(self, event):
        q = self.search_entry.get().lower()
        if not q:
            if self.list_view: self.list_view.set_entries(self.entries)
        else:
            filtered = [e for e in self.entries if q in e.text.lower()]
            if self.list_view: self.list_view.set_entries(filtered)
            
    def _handle_approve(self):
        try:
            # Sync back entries to Parser
            if self.parser.subs:
                # Create a map for fast lookup: absolute_index -> ReviewEntry
                updates = {e.index: e for e in self.entries}
                
                for i, evt in enumerate(self.parser.subs):
                    if i in updates:
                        # This is a dialogue event we have edited
                        entry = updates[i]
                        evt.text = entry.text
                        evt.start = entry.start_ms
                        evt.end = entry.end_ms
                        evt.name = entry.actor
                        evt.style = entry.style
                        
            # Get String
            output = self.parser.subs.to_string(self.parser.original_format)
            self.on_approve(output)
            
        except Exception as e:
            print(f"Export error: {e}")
