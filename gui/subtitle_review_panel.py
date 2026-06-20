"""Essential structured subtitle review editor."""

import re
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox
from typing import Callable, List, Optional

import customtkinter as ctk

from core.subtitle_parser import SubtitleParser
from .styles import COLORS, FONTS, SPACING, get_button_style, get_label_style


@dataclass
class ReviewEntry:
    """One editable subtitle event with an optional source reference."""

    event_index: int
    display_number: int
    source_text: str
    text: str
    start_ms: int
    end_ms: int
    original_text: str
    original_start_ms: int
    original_end_ms: int

    @property
    def modified(self) -> bool:
        return (
            self.text != self.original_text
            or self.start_ms != self.original_start_ms
            or self.end_ms != self.original_end_ms
        )

    @property
    def text_modified(self) -> bool:
        return self.text != self.original_text

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms

    @property
    def clean_preview(self) -> str:
        text = re.sub(r"\{[^}]*\}", "", self.text)
        return text.replace(r"\N", " ").replace("\n", " ").strip()


@dataclass(frozen=True)
class ReviewIssue:
    entry_number: int
    severity: str
    message: str


class ReviewDocument:
    """Single source of truth for review state, validation, and export."""

    def __init__(
        self,
        subtitle_path: str,
        source_path: Optional[str] = None,
        translation_issues: Optional[List[dict]] = None,
    ):
        self.parser = SubtitleParser()
        translated_lines = self.parser.load(subtitle_path)
        source_lines = self._load_source_lines(source_path)
        self.entries: List[ReviewEntry] = []
        self.translation_issues = {
            issue.get("entry_index"): issue
            for issue in (translation_issues or [])
            if issue.get("entry_index") is not None
        }

        for position, line in enumerate(translated_lines):
            source_text = (
                source_lines[position].text
                if position < len(source_lines)
                else line.text
            )
            self.entries.append(
                ReviewEntry(
                    event_index=line.index,
                    display_number=position + 1,
                    source_text=source_text,
                    text=line.text,
                    start_ms=line.start_ms,
                    end_ms=line.end_ms,
                    original_text=line.text,
                    original_start_ms=line.start_ms,
                    original_end_ms=line.end_ms,
                )
            )

    @staticmethod
    def _load_source_lines(source_path: Optional[str]):
        if not source_path or not Path(source_path).exists():
            return []
        try:
            return SubtitleParser().load(source_path)
        except Exception:
            return []

    @property
    def dirty(self) -> bool:
        return any(entry.modified for entry in self.entries)

    def issues_for(self, entry: ReviewEntry) -> List[ReviewIssue]:
        issues: List[ReviewIssue] = []
        text = entry.clean_preview

        translation_issue = self.translation_issues.get(entry.event_index)
        if translation_issue and not entry.text_modified:
            issues.append(
                ReviewIssue(
                    entry.display_number,
                    translation_issue.get("severity", "error"),
                    translation_issue.get("reason", "Translation failed"),
                )
            )

        if not text:
            issues.append(ReviewIssue(entry.display_number, "error", "Translation is empty"))
        if entry.start_ms < 0:
            issues.append(ReviewIssue(entry.display_number, "error", "Start time is negative"))
        if entry.end_ms <= entry.start_ms:
            issues.append(ReviewIssue(entry.display_number, "error", "End time must be after start"))

        if 0 < entry.duration_ms < 500:
            issues.append(ReviewIssue(entry.display_number, "warning", "Duration is under 0.5 seconds"))
        elif entry.duration_ms > 10000:
            issues.append(ReviewIssue(entry.display_number, "warning", "Duration exceeds 10 seconds"))

        if entry.duration_ms > 0 and text:
            cps = len(text) / (entry.duration_ms / 1000)
            if cps > 25:
                issues.append(ReviewIssue(entry.display_number, "warning", f"Reading speed is {cps:.0f} CPS"))

        position = entry.display_number - 1
        if position > 0:
            previous = self.entries[position - 1]
            if entry.start_ms < previous.end_ms:
                issues.append(ReviewIssue(entry.display_number, "warning", "Timing overlaps previous subtitle"))

        return issues

    def validate(self) -> List[ReviewIssue]:
        return [issue for entry in self.entries for issue in self.issues_for(entry)]

    def export(self) -> str:
        if self.parser.subs is None:
            raise RuntimeError("Subtitle document is not loaded")

        entries_by_index = {entry.event_index: entry for entry in self.entries}
        for event_index, event in enumerate(self.parser.subs):
            entry = entries_by_index.get(event_index)
            if entry is None:
                continue
            event.text = entry.text
            event.start = entry.start_ms
            event.end = entry.end_ms

        return self.parser.subs.to_string(self.parser.original_format)


class SubtitleReviewPanel(ctk.CTkFrame):
    """One focused editor for reviewing text and timing before merge."""

    TIME_PATTERN = re.compile(r"^(\d{2}):(\d{2}):(\d{2})[,.](\d{3})$")

    def __init__(
        self,
        master,
        subtitle_path: str,
        on_approve: Callable[[str], None],
        on_discard: Callable[[], None],
        source_path: Optional[str] = None,
        translation_issues: Optional[List[dict]] = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_approve = on_approve
        self.on_discard = on_discard
        self.document = ReviewDocument(subtitle_path, source_path, translation_issues)
        self.filtered_entries: List[ReviewEntry] = list(self.document.entries)
        self.current_entry: Optional[ReviewEntry] = None
        self.filter_value = "All"
        self._loading_entry = False

        self._setup_ui()
        self._update_summary()
        if self.document.validate():
            self.filter_control.set("Issues")
            self._set_filter("Issues")
        else:
            self._refresh_list(select_entry=self.filtered_entries[0] if self.filtered_entries else None)

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, SPACING["sm"]))
        toolbar.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            toolbar,
            placeholder_text="Search source or translation...",
            fg_color=COLORS["bg_dark"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, SPACING["sm"]))
        self.search_entry.bind("<KeyRelease>", self._on_filter_changed)

        self.filter_control = ctk.CTkSegmentedButton(
            toolbar,
            values=["All", "Issues", "Edited"],
            command=self._set_filter,
            fg_color=COLORS["bg_medium"],
            selected_color=COLORS["accent_bg"],
            selected_hover_color=COLORS["border_light"],
            unselected_color=COLORS["bg_medium"],
            unselected_hover_color=COLORS["bg_light"],
        )
        self.filter_control.grid(row=0, column=1)
        self.filter_control.set("All")

        body = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_medium"],
            border_width=1,
            border_color=COLORS["border"],
        )
        body.grid(row=1, column=0, sticky="nsew")
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=3)
        body.grid_rowconfigure(0, weight=1)

        self._setup_list(body)
        self._setup_editor(body)

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", pady=(SPACING["sm"], 0))
        footer.grid_columnconfigure(1, weight=1)

        self.discard_button = ctk.CTkButton(
            footer,
            text="Discard",
            command=self._handle_discard,
            width=100,
            **get_button_style("danger"),
        )
        self.discard_button.grid(row=0, column=0)

        self.summary_label = ctk.CTkLabel(footer, text="", **get_label_style("muted"))
        self.summary_label.grid(row=0, column=1, padx=SPACING["md"])

        self.approve_button = ctk.CTkButton(
            footer,
            text="Approve & Merge",
            command=self._handle_approve,
            width=150,
            **get_button_style("success"),
        )
        self.approve_button.grid(row=0, column=2)

    def _setup_list(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=COLORS["bg_dark"], corner_radius=0)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 1))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            frame,
            text="Subtitles   E: error   W: warning   *: edited",
            anchor="w",
            **get_label_style("subheading"),
        ).grid(row=0, column=0, sticky="ew", padx=SPACING["md"], pady=SPACING["sm"])

        list_frame = tk.Frame(frame, bg=COLORS["bg_dark"], highlightthickness=0)
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(0, weight=1)

        self.listbox = tk.Listbox(
            list_frame,
            bg=COLORS["bg_dark"],
            fg=COLORS["text_secondary"],
            selectbackground=COLORS["accent_bg"],
            selectforeground=COLORS["text_primary"],
            activestyle="none",
            borderwidth=0,
            highlightthickness=0,
            font=(FONTS["mono_family"], 10),
            exportselection=False,
        )
        self.listbox.grid(row=0, column=0, sticky="nsew")
        self.listbox.bind("<<ListboxSelect>>", self._on_list_select)

        scrollbar = ctk.CTkScrollbar(list_frame, command=self.listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=scrollbar.set)

    def _setup_editor(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=COLORS["bg_medium"], corner_radius=0)
        frame.grid(row=0, column=1, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(4, weight=1)

        timing = ctk.CTkFrame(frame, fg_color="transparent")
        timing.grid(row=0, column=0, sticky="ew", padx=SPACING["md"], pady=SPACING["md"])
        self.start_input = self._time_input(timing, "Start", (0, SPACING["sm"]))
        self.end_input = self._time_input(timing, "End")

        self.entry_status = ctk.CTkLabel(timing, text="", **get_label_style("muted"))
        self.entry_status.pack(side="left", padx=SPACING["md"])

        navigation = ctk.CTkFrame(timing, fg_color="transparent")
        navigation.pack(side="right")
        ctk.CTkButton(
            navigation, text="Previous", width=75, command=lambda: self._move_selection(-1),
            **get_button_style("secondary")
        ).pack(side="left", padx=(0, SPACING["xs"]))
        ctk.CTkButton(
            navigation, text="Next", width=75, command=lambda: self._move_selection(1),
            **get_button_style("secondary")
        ).pack(side="left")
        ctk.CTkButton(
            navigation,
            text="Next Issue",
            width=85,
            command=self._move_to_next_issue,
            **get_button_style("secondary"),
        ).pack(side="left", padx=(SPACING["xs"], 0))

        ctk.CTkLabel(frame, text="Source (read-only)", anchor="w", **get_label_style("muted")).grid(
            row=1, column=0, sticky="ew", padx=SPACING["md"]
        )
        self.source_text = ctk.CTkTextbox(
            frame,
            height=90,
            wrap="word",
            fg_color=COLORS["bg_dark"],
            border_color=COLORS["border"],
            text_color=COLORS["text_secondary"],
            font=(FONTS["family"], FONTS["body_size"]),
        )
        self.source_text.grid(row=2, column=0, sticky="ew", padx=SPACING["md"], pady=(SPACING["xs"], SPACING["md"]))
        self.source_text.configure(state="disabled")

        ctk.CTkLabel(frame, text="Translation", anchor="w", **get_label_style("muted")).grid(
            row=3, column=0, sticky="ew", padx=SPACING["md"]
        )
        self.translation_text = ctk.CTkTextbox(
            frame,
            wrap="word",
            undo=True,
            fg_color=COLORS["bg_dark"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            font=(FONTS["family"], 14),
        )
        self.translation_text.grid(row=4, column=0, sticky="nsew", padx=SPACING["md"], pady=(SPACING["xs"], SPACING["md"]))
        self.translation_text.bind("<KeyRelease>", self._on_text_changed)

    def _time_input(self, parent, label: str, padding=(0, 0)):
        group = ctk.CTkFrame(parent, fg_color="transparent")
        group.pack(side="left", padx=padding)
        ctk.CTkLabel(group, text=label, **get_label_style("muted")).pack(anchor="w")
        entry = ctk.CTkEntry(
            group,
            width=115,
            font=(FONTS["mono_family"], 11),
            fg_color=COLORS["bg_dark"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
        )
        entry.pack()
        entry.bind("<FocusOut>", self._on_timing_changed)
        entry.bind("<Return>", self._on_timing_changed)
        return entry

    @staticmethod
    def _format_time(milliseconds: int) -> str:
        hours, remainder = divmod(milliseconds, 3600000)
        minutes, remainder = divmod(remainder, 60000)
        seconds, millis = divmod(remainder, 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

    @classmethod
    def _parse_time(cls, value: str) -> int:
        match = cls.TIME_PATTERN.fullmatch(value.strip())
        if not match:
            raise ValueError("Use HH:MM:SS,mmm")
        hours, minutes, seconds, millis = map(int, match.groups())
        if minutes > 59 or seconds > 59:
            raise ValueError("Minutes and seconds must be below 60")
        return ((hours * 60 + minutes) * 60 + seconds) * 1000 + millis

    def _set_filter(self, value: str):
        self.filter_value = value
        self._apply_filter()

    def _on_filter_changed(self, _event=None):
        self._apply_filter()

    def _apply_filter(self):
        query = self.search_entry.get().strip().lower()
        entries = self.document.entries

        if query:
            entries = [
                entry for entry in entries
                if query in entry.text.lower() or query in entry.source_text.lower()
            ]
        if self.filter_value == "Issues":
            issue_numbers = {issue.entry_number for issue in self.document.validate()}
            entries = [entry for entry in entries if entry.display_number in issue_numbers]
        elif self.filter_value == "Edited":
            entries = [entry for entry in entries if entry.modified]

        self.filtered_entries = entries
        selected = self.current_entry if self.current_entry in entries else (entries[0] if entries else None)
        self._refresh_list(select_entry=selected)

    def _row_text(self, entry: ReviewEntry) -> str:
        issues = self.document.issues_for(entry)
        if any(issue.severity == "error" for issue in issues):
            marker = "E"
        elif issues:
            marker = "W"
        else:
            marker = "*" if entry.modified else " "
        preview = entry.clean_preview[:54]
        return f"{marker} {entry.display_number:04d}  {self._format_time(entry.start_ms)}  {preview}"

    def _refresh_list(self, select_entry: Optional[ReviewEntry] = None):
        self.listbox.delete(0, "end")
        for index, entry in enumerate(self.filtered_entries):
            self.listbox.insert("end", self._row_text(entry))
            issues = self.document.issues_for(entry)
            if any(issue.severity == "error" for issue in issues):
                self.listbox.itemconfig(index, foreground=COLORS["error"])
            elif issues:
                self.listbox.itemconfig(index, foreground=COLORS["warning"])

        if select_entry and select_entry in self.filtered_entries:
            index = self.filtered_entries.index(select_entry)
            self.listbox.selection_set(index)
            self.listbox.activate(index)
            self.listbox.see(index)
            self._select_entry(select_entry)
        elif not self.filtered_entries:
            self.current_entry = None
            self._clear_editor()

    def _on_list_select(self, _event=None):
        selection = self.listbox.curselection()
        if selection:
            self._select_entry(self.filtered_entries[selection[0]])

    def _select_entry(self, entry: ReviewEntry):
        self.current_entry = entry
        self._loading_entry = True
        try:
            self.start_input.delete(0, "end")
            self.start_input.insert(0, self._format_time(entry.start_ms))
            self.end_input.delete(0, "end")
            self.end_input.insert(0, self._format_time(entry.end_ms))

            self.source_text.configure(state="normal")
            self.source_text.delete("0.0", "end")
            self.source_text.insert("0.0", entry.source_text.replace(r"\N", "\n"))
            self.source_text.configure(state="disabled")

            self.translation_text.delete("0.0", "end")
            self.translation_text.insert("0.0", entry.text.replace(r"\N", "\n"))
            self.translation_text.edit_reset()
        finally:
            self._loading_entry = False
        self._update_entry_status()

    def _clear_editor(self):
        self.source_text.configure(state="normal")
        self.source_text.delete("0.0", "end")
        self.source_text.configure(state="disabled")
        self.translation_text.delete("0.0", "end")
        self.entry_status.configure(text="No matching subtitles", text_color=COLORS["text_muted"])

    def _on_text_changed(self, _event=None):
        if self._loading_entry or not self.current_entry:
            return
        self.current_entry.text = self.translation_text.get("0.0", "end-1c").replace("\n", r"\N")
        self._entry_was_changed()

    def _on_timing_changed(self, _event=None):
        if self._loading_entry or not self.current_entry:
            return
        try:
            self._commit_timing()
            self._entry_was_changed()
        except ValueError as error:
            self.start_input.configure(border_color=COLORS["error"])
            self.end_input.configure(border_color=COLORS["error"])
            self.entry_status.configure(text=str(error), text_color=COLORS["error"])

    def _commit_timing(self):
        if not self.current_entry:
            return
        start_ms = self._parse_time(self.start_input.get())
        end_ms = self._parse_time(self.end_input.get())
        self.current_entry.start_ms = start_ms
        self.current_entry.end_ms = end_ms
        self.start_input.configure(border_color=COLORS["border"])
        self.end_input.configure(border_color=COLORS["border"])

    def _entry_was_changed(self):
        self._update_entry_status()
        self._update_summary()
        if (
            self.filter_value == "All"
            and not self.search_entry.get().strip()
            and self.current_entry in self.filtered_entries
        ):
            index = self.filtered_entries.index(self.current_entry)
            self.listbox.delete(index)
            self.listbox.insert(index, self._row_text(self.current_entry))
            issues = self.document.issues_for(self.current_entry)
            if any(issue.severity == "error" for issue in issues):
                self.listbox.itemconfig(index, foreground=COLORS["error"])
            elif issues:
                self.listbox.itemconfig(index, foreground=COLORS["warning"])
            self.listbox.selection_set(index)
            self.listbox.activate(index)
        else:
            self._apply_filter()

    def _update_entry_status(self):
        if not self.current_entry:
            return
        issues = self.document.issues_for(self.current_entry)
        if issues:
            severity = "error" if any(issue.severity == "error" for issue in issues) else "warning"
            self.entry_status.configure(
                text=f"Entry {self.current_entry.display_number}: {issues[0].message}",
                text_color=COLORS["error"] if severity == "error" else COLORS["warning"],
            )
        else:
            duration = self.current_entry.duration_ms / 1000
            self.entry_status.configure(text=f"{duration:.2f}s", text_color=COLORS["text_muted"])

    def _update_summary(self):
        issues = self.document.validate()
        errors = sum(issue.severity == "error" for issue in issues)
        warnings = sum(issue.severity == "warning" for issue in issues)
        edited = sum(entry.modified for entry in self.document.entries)
        self.summary_label.configure(
            text=f"{len(self.document.entries)} entries | {edited} edited | {errors} errors | {warnings} warnings",
            text_color=COLORS["error"] if errors else (COLORS["warning"] if warnings else COLORS["text_muted"]),
        )

    def _move_selection(self, offset: int):
        if not self.filtered_entries:
            return
        try:
            current = self.filtered_entries.index(self.current_entry)
        except ValueError:
            current = 0
        target = max(0, min(len(self.filtered_entries) - 1, current + offset))
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(target)
        self.listbox.see(target)
        self._select_entry(self.filtered_entries[target])

    def _move_to_next_issue(self):
        issue_entries = [
            entry for entry in self.document.entries
            if self.document.issues_for(entry)
        ]
        if not issue_entries:
            messagebox.showinfo(
                "Subtitle validation",
                "No remaining subtitle issues.",
                parent=self.winfo_toplevel(),
            )
            return

        self.filter_control.set("Issues")
        self.filter_value = "Issues"
        self.filtered_entries = issue_entries
        try:
            current = issue_entries.index(self.current_entry)
            target = issue_entries[(current + 1) % len(issue_entries)]
        except ValueError:
            target = issue_entries[0]
        self._refresh_list(select_entry=target)

    def _handle_discard(self):
        detail = (
            "All manual subtitle edits in this review will be lost."
            if self.document.dirty
            else "The translated subtitle will be discarded."
        )
        if not messagebox.askyesno(
            "Discard changes?",
            detail,
            parent=self.winfo_toplevel(),
        ):
            return
        self.on_discard()

    def _handle_approve(self):
        if self.current_entry:
            try:
                self._commit_timing()
            except ValueError as error:
                messagebox.showerror("Invalid timing", str(error), parent=self.winfo_toplevel())
                return

        issues = self.document.validate()
        errors = [issue for issue in issues if issue.severity == "error"]
        warnings = [issue for issue in issues if issue.severity == "warning"]

        if errors:
            details = "\n".join(
                f"Entry {issue.entry_number}: {issue.message}" for issue in errors[:6]
            )
            messagebox.showerror(
                "Cannot merge subtitles",
                f"Fix {len(errors)} validation error(s) before merging.\n\n{details}",
                parent=self.winfo_toplevel(),
            )
            self.filter_control.set("Issues")
            self._set_filter("Issues")
            return

        if warnings and not messagebox.askyesno(
            "Merge with warnings?",
            f"The subtitle has {len(warnings)} warning(s). Continue with merge?",
            parent=self.winfo_toplevel(),
        ):
            self.filter_control.set("Issues")
            self._set_filter("Issues")
            return

        try:
            self.on_approve(self.document.export())
        except Exception as error:
            messagebox.showerror("Export failed", str(error), parent=self.winfo_toplevel())
