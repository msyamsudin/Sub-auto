"""
Finalization mixin for the main application window.
Handles completion, summary, review editor, merge approval, and discard flows.
Combined into SubAutoApp via mixins.
"""

import os
import threading
from pathlib import Path

from ..components import SummaryWindow


class FinalizationMixin:
    """Post-translation completion, review, and merge flows."""

    def _on_translation_complete(self, summary: dict):
        """Handle validation after merge complete."""
        self.translation_controller.finalize_translation(summary, self.config.provider)
    
    def _on_translation_summary_ready(self, summary_data: dict):
        """Callback from translation controller when summary is ready for UI."""
        self.progress_header.set_step(5)
        self.summary_view = SummaryWindow(
            self,
            **summary_data,
            on_open_folder=lambda: os.startfile(Path(summary_data["output_path"]).parent) if summary_data.get("output_path") else None,
            on_close=self._close_summary
        )
        self.summary_view.grid(row=1, column=0, rowspan=2, sticky="nsew")
        self.summary_view.lift()
        
        if self.app_state_manager:
            self.app_state_manager.clear()
            
        self.after(2000, self._exit_processing_mode)
    
    def _close_summary(self):
        """Close summary view and reset app for next file."""
        if hasattr(self, 'summary_view') and self.summary_view:
            self.summary_view.destroy()
            self.summary_view = None
            
        self._reset_app()

    def _on_translation_error(self, error: str):
        # This is now handled by controller, but kept as placeholder if needed
        pass
    
    def _show_review_editor(self, payload: dict):
        """Show the subtitle review editor."""
        self.app_state.is_processing = False
        self._exit_processing_mode()
        self.app_state.merge_payload = payload
        
        # Update view
        view = self.step_frames[3]
        view.show_payload(payload)
        
        # Update Stepper
        self.step_controller.show_step(4)
        self.toast.info("Translation complete! Please review the subtitles.")
    
    def _on_review_approved(self, content: str):
        """Handle review approval - save edited content and merge."""
        payload = self.app_state.merge_payload
        if not payload:
            self.step_frames[3].reset_merge_progress()
            self.toast.error("Merge failed: review data is no longer available")
            return

        self.app_state.is_processing = True
        self.toast.info("Finalizing merge into video...")

        def update_progress(percent: int):
            self.after(0, lambda value=percent: self.step_frames[3].set_merge_progress(value))

        def run_merge():
            try:
                # Persist the reviewed subtitle before handing it to mkvmerge.
                with open(payload["translated_sub_path"], 'wt', encoding='utf-8') as f:
                    f.write(content)

                summary = self.finalization_service.finalize_merge(
                    payload,
                    remove_old_subs=self.app_state.remove_old_subs,
                    progress_callback=update_progress,
                )
                self.after(0, lambda: self._on_review_merge_complete(summary))
            except Exception as error:
                self.logger.error(f"Finalize merge error: {error}")
                self.after(0, lambda message=str(error): self._on_review_merge_error(message))

        threading.Thread(target=run_merge, daemon=True).start()

    def _on_review_merge_complete(self, summary: dict):
        self.app_state.is_processing = False
        self._on_translation_complete(summary)

    def _on_review_merge_error(self, error: str):
        self.app_state.is_processing = False
        self.step_frames[3].reset_merge_progress()
        self.toast.error(f"Merge failed: {error}")
            
    def _on_review_discarded(self):
        """Handle review discard - clean up and reset."""
        self.finalization_service.cleanup_temp_files(self.app_state.merge_payload) 
        if self.app_state_manager:
            self.app_state_manager.clear()
        self.app_state.merge_payload = None
        self._on_step_change(2) # Back to config
        self.toast.info("Translation discarded")
    
    def _show_last_summary(self):
        """Re-open the last summary window."""
        if self.app_state.last_summary_data:
            output_path = Path(self.app_state.last_summary_data["output_path"])
            
            if hasattr(self, 'summary_view') and self.summary_view:
                self.summary_view.destroy()
            
            self.summary_view = SummaryWindow(
                self,
                **self.app_state.last_summary_data,
                on_open_folder=lambda: os.startfile(output_path.parent),
                on_close=self._close_summary
            )
            self.summary_view.grid(row=1, column=0, rowspan=2, sticky="nsew")
            self.summary_view.lift()
