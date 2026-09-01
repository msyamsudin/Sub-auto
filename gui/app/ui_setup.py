"""
UI setup mixin for the main application window.
Builds the title bar, content area, step fragments, step controller, and
footer. Combined into SubAutoApp via mixins.
"""

import customtkinter as ctk

from ..constants import APP_TITLE, APP_VERSION, WINDOW_SIZE, MIN_SIZE
from ..window_utils import setup_window_style
from ..styles import SPACING
from ..components import CustomTitleBar, ContentProgressHeader
from ..processing_view import ProcessingView
from ..views.file_selection_view import FileSelectionView
from ..views.configuration_view import ConfigurationView
from ..views.footer_view import FooterView
from ..views.review_view import ReviewView
from ..controllers.step_controller import StepController


class UISetupMixin:
    """Window/chrome construction for SubAutoApp."""

    APP_TITLE = APP_TITLE
    APP_VERSION = APP_VERSION
    WINDOW_SIZE = WINDOW_SIZE
    MIN_SIZE = MIN_SIZE

    def _setup_window_style(self):
        """Setup Windows-specific window styling."""
        setup_window_style(self)

    def _setup_ui(self):
        """Setup the main UI - Top Nav + Content layout."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Custom Title Bar
        self.title_bar = CustomTitleBar(self, title=self.APP_TITLE, version=self.APP_VERSION, on_settings=self._open_settings, on_history=self._open_history, show_settings=True, show_history=True)
        self.title_bar.grid(row=0, column=0, sticky="ew")
        
        # Set initial active prompt status on title bar
        active_prompt = self.prompt_manager.get_active_prompt_name()
        self.title_bar.set_active_prompt(active_prompt)
        
        # Main container
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=1, column=0, sticky="nsew")
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(1, weight=1)

        self.progress_header = ContentProgressHeader(
            self.main_container,
            steps=["Select File", "Configuration", "Translation", "Review"],
            current_step=1,
            on_step_change=self._on_step_change
        )
        self.progress_header.grid(row=0, column=0, sticky="ew", padx=SPACING["lg"], pady=(SPACING["md"], 0))

        self.content_area = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_area.grid(row=1, column=0, sticky="nsew", padx=SPACING["lg"], pady=SPACING["md"])
        self.content_area.grid_columnconfigure(0, weight=1)
        self.content_area.grid_rowconfigure(0, weight=1)

        # Processing View
        self.processing_view = ProcessingView(self.content_area, logger_instance=self.logger, on_pause=self._pause_translation, on_cancel=self._cancel_translation)
        self.translation_controller.processing_view = self.processing_view
        
        # Initialize Step Fragments
        view1 = self._create_step1_fragment()
        view2 = self._create_step2_fragment()
        view4 = self._create_step4_fragment()
        
        # Note: Step 3 is the processing_view itself
        self.step_frames = [view1, view2, self.processing_view, view4]
        
        # Step Controller
        self.step_controller = StepController(self.app_state, self.progress_header, self.step_frames)
        self.step_controller.set_callback(self._on_handle_step_change_ui)

        # Footer
        self._create_footer()
        
        # Link API Controller
        self.api_controller.set_ui_elements(self.model_dropdown, self.model_status, self.validate_btn, self.title_bar, self.after)
        
        # Show first step
        self.step_controller.show_step(1)
        
    def _on_handle_step_change_ui(self, step_index: int):
        self._update_step_states()
        self._update_action_buttons()

    def _create_step1_fragment(self):
        view = FileSelectionView(self.content_area, on_file_selected=self._on_file_selected)
        self.file_drop = view.file_drop
        return view

    def _create_step2_fragment(self):
        view = ConfigurationView(
            self.content_area, 
            on_model_change=self._on_model_change, 
            on_validate_api=self._validate_api,
            on_external_subtitle=self._select_external_subtitle,
            on_start=self._start_translation,
            on_reset=self._reset_app
        )
        self.tracks_frame = view.tracks_frame
        self.no_tracks_label = view.no_tracks_label
        self.source_lang_row = view.source_lang_row
        self.target_lang_row = view.target_lang_row
        self.model_dropdown = view.model_dropdown
        self.model_status = view.model_status
        self.cost_estimate_label = view.cost_estimate_label
        self.validate_btn = view.validate_btn
        self.track_items = view.track_items
        
        # Link action buttons directly to app instance
        self.start_btn = view.start_btn
        self.reset_btn = view.reset_btn
        return view

    def _create_step4_fragment(self):
        return ReviewView(self.content_area, on_approve=self._on_review_approved, on_discard=self._on_review_discarded)

    def _on_step_change(self, step_index: int):
        self.step_controller.handle_step_change(step_index)
    
    def _create_footer(self):
        """Create footer with action buttons (FULL WIDTH)."""
        self.footer = FooterView(
            self,
            on_resume=self._resume_translation,
            on_show_summary=self._show_last_summary,
            on_pause=self._pause_translation,
            on_cancel=self._cancel_translation
        )
        self.footer.grid(row=2, column=0, sticky="ew", padx=SPACING["md"], pady=(0, SPACING["md"]))
        
        # Link references for backward compatibility
        self.resume_btn = self.footer.resume_btn
        self.status_label = self.footer.status_label
        self.show_summary_btn = self.footer.summary_btn
        
        # Initial state
        if hasattr(self, 'start_btn'):
            self.start_btn.configure(state="disabled")
