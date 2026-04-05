import customtkinter as ctk
from typing import Optional, Callable, List
from .styles import (
    COLORS, FONTS, SPACING, RADIUS,
    get_button_style, get_input_style, get_frame_style, get_label_style
)

class CollapsibleFrame(ctk.CTkFrame):
    """
    A frame that can be collapsed/expanded with a header click.
    """
    def __init__(self, master, title, expanded=True, **kwargs):
        super().__init__(master, **get_frame_style("card"), **kwargs)
        self.expanded = expanded
        self.title = title
        self.configure(border_width=1, border_color=COLORS["border"])
        
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)  # Content row

        # Header Frame
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent", height=40)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=SPACING["md"], pady=(SPACING["sm"], 0))
        self.header_frame.columnconfigure(2, weight=1)

        self.accent_bar = ctk.CTkFrame(
            self.header_frame,
            width=4,
            height=22,
            corner_radius=RADIUS["sm"],
            fg_color=COLORS["accent"]
        )
        self.accent_bar.grid(row=0, column=0, sticky="w", padx=(0, SPACING["sm"]))

        # Toggle Button (Arrow)
        self.toggle_btn = ctk.CTkButton(
            self.header_frame,
            text="▼" if expanded else "▶",
            width=24,
            height=24,
            fg_color="transparent",
            hover_color=COLORS["bg_light"],
            text_color=COLORS["text_secondary"],
            command=self.toggle,
            font=(FONTS["family"], 16)
        )
        self.toggle_btn.grid(row=0, column=1, sticky="w")
        
        # Title Label
        self.title_lbl = ctk.CTkLabel(
            self.header_frame, 
            text=title,
            **get_label_style("subheading")
        )
        self.title_lbl.grid(row=0, column=2, sticky="w", padx=SPACING["sm"])

        # Content Frame
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        if expanded:
            self.content_frame.grid(row=1, column=0, sticky="nsew", padx=SPACING["md"], pady=SPACING["md"])
            
        # Bind click on header to toggle
        self.title_lbl.bind("<Button-1>", lambda e: self.toggle())
        self.header_frame.bind("<Button-1>", lambda e: self.toggle())

    def toggle(self):
        if self.expanded:
            self.content_frame.grid_forget()
            self.toggle_btn.configure(text="▶")
            self.expanded = False
        else:
            self.content_frame.grid(row=1, column=0, sticky="nsew", padx=SPACING["md"], pady=SPACING["md"])
            self.toggle_btn.configure(text="▼")
            self.expanded = True
            
    def add_widget_to_header(self, widget, **grid_kwargs):
        """Add a widget (like a badge) to the header (right side)."""
        widget.grid(row=0, column=4 + len(self.header_frame.grid_slaves(row=0)), **grid_kwargs)
        widget.lift()


class VerticalStepperItem(ctk.CTkFrame):
    """
    A single step item for the vertical stepper.
    """
    def __init__(
        self,
        master,
        step_number: int,
        title: str,
        description: Optional[str] = None,
        is_active: bool = False,
        is_completed: bool = False,
        is_last: bool = False,
        on_click: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.step_number = step_number
        self.title = title
        self.description = description
        self.is_active = is_active
        self.is_completed = is_completed
        self.is_last = is_last
        self.on_click = on_click
        
        self._setup_ui()
        
    def _setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        
        # Colors based on state
        if self.is_active:
            icon_color = COLORS["accent"] # Changed from primary (text color) to accent (blue)
            text_color = COLORS["text_primary"]
            desc_color = COLORS["text_secondary"]
            font_weight = "bold"
        elif self.is_completed:
            icon_color = COLORS["success"]
            text_color = COLORS["text_primary"]
            desc_color = COLORS["text_muted"]
            font_weight = "normal"
        else:
            icon_color = COLORS["border"]
            text_color = COLORS["text_muted"]
            desc_color = COLORS["text_muted"]
            font_weight = "normal"
            
        # Icon / Number
        self.icon_frame = ctk.CTkFrame(
            self,
            width=32,
            height=32,
            corner_radius=16,
            fg_color=icon_color
        )
        self.icon_frame.grid(row=0, column=0, sticky="n")
        
        # Center the number/check
        icon_text = "✓" if self.is_completed and not self.is_active else str(self.step_number)
        
        self.icon_label = ctk.CTkLabel(
            self.icon_frame,
            text=icon_text,
            font=(FONTS["family"], 14, "bold"),
            text_color="white" if self.is_active or self.is_completed else COLORS["text_secondary"]
        )
        self.icon_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # Title
        self.title_label = ctk.CTkLabel(
            self,
            text=self.title,
            font=(FONTS["family"], FONTS["body_size"], font_weight),
            text_color=text_color
        )
        self.title_label.grid(row=0, column=1, sticky="w", padx=SPACING["md"], pady=(2, 0))
        
        # Description (Subtitle)
        if self.description:
            self.desc_label = ctk.CTkLabel(
                self,
                text=self.description,
                font=(FONTS["family"], FONTS["small_size"]),
                text_color=desc_color,
                wraplength=160,
                justify="left"
            )
            self.desc_label.grid(row=1, column=1, sticky="w", padx=SPACING["md"], pady=(0, 4))
        
        # Connector Line (if not last)
        if not self.is_last:
            self.line = ctk.CTkFrame(
                self,
                width=2,
                height=15, # Minimum height
                fg_color=COLORS["success"] if self.is_completed else COLORS["border"]
            )
            
            # If description exists, line needs to span more rows or be placed differently
            # Simple grid approach: place in row 1 (and 2 if desc)
            row_span = 2 if self.description else 1
            self.line.grid(row=1, column=0, rowspan=row_span, sticky="n", pady=(2, 0))
            # Ensure line stretches to fill height
            self.grid_rowconfigure(1, weight=1)
            
        # Click event
        if self.on_click:
            for widget in [self, self.title_label, self.icon_frame, self.icon_label]:
                widget.bind("<Button-1>", lambda e: self.on_click(self.step_number))
            if self.description:
                self.desc_label.bind("<Button-1>", lambda e: self.on_click(self.step_number))
            
            # Cursor
            self.configure(cursor="hand2")
            self.title_label.configure(cursor="hand2")
            self.icon_frame.configure(cursor="hand2")
            self.icon_label.configure(cursor="hand2")
            if self.description:
                self.desc_label.configure(cursor="hand2")


class VerticalStepper(ctk.CTkFrame):
    """
    Vertical stepper navigation component.
    """
    def __init__(
        self,
        master,
        steps: List[str],
        current_step: int = 1,
        on_step_change: Optional[Callable[[int], None]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.steps = steps
        self.current_step = current_step
        self.on_step_change = on_step_change
        self.step_descriptions = {} # step_idx -> text
        self.completed_steps = set() # Set of completed step indices
        self.items = []
        
        self._refresh()
        
    def _refresh(self):
        # Clear
        for widget in self.winfo_children():
            widget.destroy()
        self.items = []
        
        for i, title in enumerate(self.steps, 1):
            is_active = (i == self.current_step)
            is_completed = (i in self.completed_steps) or (i < self.current_step)
            is_last = (i == len(self.steps))
            
            desc = self.step_descriptions.get(i)
            
            item = VerticalStepperItem(
                self,
                step_number=i,
                title=title,
                description=desc,
                is_active=is_active,
                is_completed=is_completed,
                is_last=is_last,
                on_click=self._handle_click
            )
            item.pack(fill="x", pady=0)
            self.items.append(item)
            
    def _handle_click(self, step_number: int):
        # Prevent jumping ahead to incomplete steps if desired
        # For now, allow navigation to any previous step or the current step
        if self.on_step_change:
            self.on_step_change(step_number)
            
    def set_step(self, step_number: int):
        if 1 <= step_number <= len(self.steps):
            self.current_step = step_number
            self._refresh()

    def update_step(self, step_number: int, description: str = None, is_complete: bool = False):
        """Update a step's description and completion status."""
        if 1 <= step_number <= len(self.steps):
            if description is not None:
                self.step_descriptions[step_number] = description
            
            if is_complete:
                self.completed_steps.add(step_number)
            else:
                self.completed_steps.discard(step_number)
            
            self._refresh()
            
    def update_step_description(self, step_number: int, description: str):
        """Update the description/subtitle for a step."""
        if 1 <= step_number <= len(self.steps):
            self.step_descriptions[step_number] = description
            self._refresh()
            
    def clear_step_description(self, step_number: int):
        """Clear description for a step."""
        if step_number in self.step_descriptions:
            del self.step_descriptions[step_number]
            self._refresh()
            
    def set_completed_steps(self, steps: List[int]):
        """Set the list of completed steps."""
        self.completed_steps = set(steps)
        self._refresh()


class HorizontalStepperItem(ctk.CTkFrame):
    """
    A single step item for the horizontal stepper.
    """
    def __init__(
        self,
        master,
        step_number: int,
        title: str,
        is_active: bool = False,
        is_completed: bool = False,
        is_last: bool = False,
        on_click: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.step_number = step_number
        self.title = title
        self.is_active = is_active
        self.is_completed = is_completed
        self.is_last = is_last
        self.on_click = on_click
        
        self._setup_ui()
        
    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)

        if self.is_active:
            text_color = COLORS["text_primary"]
            font_weight = "bold"
            underline_color = COLORS["accent"]
        elif self.is_completed:
            text_color = COLORS["text_primary"]
            font_weight = "normal"
            underline_color = COLORS["success_dim"]
        else:
            text_color = COLORS["text_muted"]
            font_weight = "normal"
            underline_color = COLORS["border"]

        self.configure(
            fg_color="transparent",
            corner_radius=0,
            border_width=0,
            height=28
        )
        self.grid_propagate(False)

        self.title_label = ctk.CTkLabel(
            self,
            text=self.title,
            font=(FONTS["family"], FONTS["body_size"] - 1, font_weight),
            text_color=text_color
        )
        self.title_label.grid(row=0, column=0, sticky="w", padx=(0, SPACING["md"]), pady=(0, 3))

        self.underline = ctk.CTkFrame(
            self,
            height=2 if self.is_active else 1,
            corner_radius=0,
            fg_color=underline_color,
            width=1
        )
        self.underline.grid(row=1, column=0, sticky="ew", padx=(0, SPACING["md"]))
            
        # Click binding
        if self.on_click:
            self.bind("<Button-1>", lambda e: self.on_click(self.step_number))
            self.title_label.bind("<Button-1>", lambda e: self.on_click(self.step_number))
            self.underline.bind("<Button-1>", lambda e: self.on_click(self.step_number))
            
            self.configure(cursor="hand2")
            self.title_label.configure(cursor="hand2")
            self.underline.configure(cursor="hand2")


class HorizontalStepper(ctk.CTkFrame):
    """
    Horizontal stepper navigation component.
    """
    def __init__(
        self,
        master,
        steps: List[str],
        current_step: int = 1,
        on_step_change: Optional[Callable[[int], None]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        self.steps = steps
        self.current_step = current_step
        self.on_step_change = on_step_change
        self.completed_steps = set()
        self.step_descriptions = {} # Ignored but kept for interface compatibility
        
        self._refresh()
        
    def _refresh(self):
        # Clear existing
        for widget in self.winfo_children():
            widget.destroy()
            
        # Centering container
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(side="left", anchor="center")
        
        for i, title in enumerate(self.steps, 1):
            is_active = (i == self.current_step)
            is_completed = (i in self.completed_steps) or (i < self.current_step)
            is_last = (i == len(self.steps))
            
            item = HorizontalStepperItem(
                container,
                step_number=i,
                title=title,
                is_active=is_active,
                is_completed=is_completed,
                is_last=is_last,
                on_click=self._handle_click
            )
            item.pack(side="left", padx=(0, SPACING["md"]), pady=0)
            
    def _handle_click(self, step_number: int):
        if self.on_step_change:
            self.on_step_change(step_number)
            
    def set_step(self, step_number: int):
        # Allow len + 1 to indicate "all steps completed"
        if 1 <= step_number <= len(self.steps) + 1:
            self.current_step = step_number
            self._refresh()

    def update_step(self, step_number: int, description: str = None, is_complete: bool = False):
        """Update a step's status (description is ignored in horizontal layout)."""
        if 1 <= step_number <= len(self.steps):
            if is_complete:
                self.completed_steps.add(step_number)
            else:
                self.completed_steps.discard(step_number)
            
            # Note: description is kept for compatibility but not displayed
            if description is not None:
                self.step_descriptions[step_number] = description
                
            self._refresh()
            
    def update_step_description(self, step_number: int, description: str):
        # Not used in horizontal layout
        pass
            
    def clear_step_description(self, step_number: int):
        pass
            
    def set_completed_steps(self, steps: List[int]):
        self.completed_steps = set(steps)
        self._refresh()


class ContentProgressHeader(ctk.CTkFrame):
    """Lightweight progress header shown above page content."""

    def __init__(
        self,
        master,
        steps: List[str],
        current_step: int = 1,
        on_step_change: Optional[Callable[[int], None]] = None,
        **kwargs
    ):
        super().__init__(
            master,
            fg_color=COLORS["bg_medium"],
            corner_radius=RADIUS["lg"],
            border_width=1,
            border_color=COLORS["border"],
            **kwargs
        )
        self.steps = steps
        self.current_step = current_step
        self.on_step_change = on_step_change
        self.completed_steps = set()
        self.step_descriptions = {}

        self.grid_columnconfigure(0, weight=1)
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        self.kicker_label = ctk.CTkLabel(
            self,
            text="",
            font=(FONTS["family"], FONTS["small_size"], "bold"),
            text_color=COLORS["accent_hover"]
        )
        self.kicker_label.grid(row=0, column=0, sticky="w", padx=SPACING["lg"], pady=(SPACING["md"], 0))

        self.title_label = ctk.CTkLabel(
            self,
            text="",
            font=(FONTS["family"], FONTS["heading_size"] + 4, "bold"),
            text_color=COLORS["text_primary"]
        )
        self.title_label.grid(row=1, column=0, sticky="w", padx=SPACING["lg"], pady=(SPACING["xs"], 0))

        self.description_label = ctk.CTkLabel(
            self,
            text="",
            font=(FONTS["family"], FONTS["body_size"]),
            text_color=COLORS["text_secondary"]
        )
        self.description_label.grid(row=2, column=0, sticky="w", padx=SPACING["lg"], pady=(SPACING["xs"], SPACING["sm"]))

        self.nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.nav_frame.grid(row=3, column=0, sticky="w", padx=SPACING["lg"], pady=(0, SPACING["md"]))

    def _refresh(self):
        safe_step = min(max(self.current_step, 1), len(self.steps))
        title = self.steps[safe_step - 1]
        description = self.step_descriptions.get(safe_step, self._default_description(safe_step))

        self.kicker_label.configure(text=f"STEP {safe_step} OF {len(self.steps)}")
        self.title_label.configure(text=title)
        self.description_label.configure(text=description)

        for widget in self.nav_frame.winfo_children():
            widget.destroy()

        for index, step_title in enumerate(self.steps, 1):
            is_active = index == safe_step
            is_completed = (index in self.completed_steps) or (index < safe_step)

            if is_active:
                text_color = COLORS["text_primary"]
                fg_color = COLORS["bg_light"]
            elif is_completed:
                text_color = COLORS["success"]
                fg_color = "transparent"
            else:
                text_color = COLORS["text_muted"]
                fg_color = "transparent"

            label = ctk.CTkLabel(
                self.nav_frame,
                text=step_title,
                font=(FONTS["family"], FONTS["small_size"], "bold" if is_active else "normal"),
                text_color=text_color,
                fg_color=fg_color,
                corner_radius=RADIUS["sm"],
                padx=SPACING["sm"],
                pady=3
            )
            label.pack(side="left")

            if self.on_step_change:
                label.bind("<Button-1>", lambda e, step=index: self.on_step_change(step))
                label.configure(cursor="hand2")

            if index < len(self.steps):
                sep = ctk.CTkLabel(
                    self.nav_frame,
                    text="/",
                    font=(FONTS["family"], FONTS["small_size"]),
                    text_color=COLORS["text_muted"]
                )
                sep.pack(side="left", padx=(SPACING["xs"], SPACING["xs"]))

    def _default_description(self, step_index: int) -> str:
        defaults = {
            1: "Choose the MKV file you want to process.",
            2: "Pick subtitle track and translation settings.",
            3: "Run the translation process and monitor progress.",
            4: "Review translated subtitles before final merge.",
        }
        return defaults.get(step_index, "")

    def set_step(self, step_number: int):
        if 1 <= step_number <= len(self.steps) + 1:
            self.current_step = step_number
            self._refresh()

    def update_step(self, step_number: int, description: str = None, is_complete: bool = False):
        if 1 <= step_number <= len(self.steps):
            if description is not None:
                self.step_descriptions[step_number] = description
            if is_complete:
                self.completed_steps.add(step_number)
            else:
                self.completed_steps.discard(step_number)
            self._refresh()

    def update_step_description(self, step_number: int, description: str):
        if 1 <= step_number <= len(self.steps):
            self.step_descriptions[step_number] = description
            self._refresh()

    def clear_step_description(self, step_number: int):
        if step_number in self.step_descriptions:
            del self.step_descriptions[step_number]
            self._refresh()

    def set_completed_steps(self, steps: List[int]):
        self.completed_steps = set(steps)
        self._refresh()
