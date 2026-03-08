from typing import Optional, Dict, Any, Callable
from pathlib import Path
import os
from gui.state.app_state import AppState
from gui.styles import COLORS
from core.translator import TokenUsage

class TranslationController:
    """Controller for handling translation events, UI updates, and workflow."""
    
    def __init__(self, state: AppState, processing_view: any, toast: any, after_func: Callable):
        self.state = state
        self.processing_view = processing_view
        self.toast = toast
        self.after_func = after_func
        self.on_complete_callback = None
        self.on_show_review_callback = None
        self.on_show_summary_callback = None

    def set_callbacks(self, on_complete, on_show_review, on_show_summary):
        self.on_complete_callback = on_complete
        self.on_show_review_callback = on_show_review
        self.on_show_summary_callback = on_show_summary

    def on_progress(self, current: int, total: int, status: str, token_usage: TokenUsage):
        """Handle translation progress updates."""
        status_color = None
        if status:
            if "Retrying" in status:
                status_color = COLORS["warning"]
            elif "Finalizing" in status:
                status_color = COLORS["success"]
        
        self.after_func(0, lambda: self.processing_view.update_progress_summary(
            current=current,
            total=total,
            status=status,
            status_color=status_color,
            tokens=token_usage
        ))

    def on_orchestrator_complete(self, payload: dict):
        """Handle completion from orchestrator before review."""
        self.state.is_processing = False
        self.state.merge_payload = payload
        if self.on_show_review_callback:
            self.after_func(0, lambda: self.on_show_review_callback(payload))

    def on_error(self, error: str):
        """Handle translation errors."""
        self.state.is_processing = False
        self.processing_view.set_error(error[:50])
        self.toast.error(f"Translation failed: {error}")
        if self.on_complete_callback:
            self.after_func(3000, self.on_complete_callback)

    def finalize_translation(self, summary: dict, provider: str):
        """Handle final completion after merge/review."""
        self.state.is_processing = False
        self.processing_view.set_completed()
        
        tokens = summary.get("tokens")
        if tokens:
            self.toast.success(f"Translation complete! {tokens.total_tokens:,} tokens used")
        else:
            self.toast.success("Translation complete!")
        
        self.state.last_summary_data = {
            "output_path": summary.get("output_path", ""),
            "lines_translated": summary.get("lines_translated", 0),
            "model_used": summary.get("model_used", ""),
            "duration_seconds": summary.get("duration_seconds", 0),
            "removed_old_subs": summary.get("removed_old_subs", False),
            "prompt_tokens": tokens.prompt_tokens if tokens else 0,
            "completion_tokens": tokens.completion_tokens if tokens else 0,
            "total_tokens": tokens.total_tokens if tokens else 0,
            "estimated_cost": summary.get("estimated_cost", 0),
            "provider": provider
        }
        
        if self.on_show_summary_callback:
            self.on_show_summary_callback(self.state.last_summary_data)
