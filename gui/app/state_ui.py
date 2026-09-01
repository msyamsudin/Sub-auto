"""
State/UI sync mixin for the main application window.
Keeps the stepper, action buttons, and token estimate in sync with app state.
Combined into SubAutoApp via mixins.
"""

from core.translator import get_api_manager


class StateUIMixin:
    """Step states, action buttons, and token estimate updates."""

    def _update_step_states(self):
        """Update UI states based on current progress."""
        self.api_controller.sync_api_state()
        manager = get_api_manager()
        if hasattr(self, 'step_controller'):
            self.step_controller.update_stepper_logic(manager)
        self._update_action_buttons()
        self._update_token_estimate()
    
    # Removed legacy _sync_api_state and _update_stepper_logic

    def _update_action_buttons(self):
        """Enable/disable action buttons in footer."""
        has_file = self.app_state.current_file is not None
        has_track = self.app_state.selected_track_id is not None
        api_ready = self.app_state.api_validated
        
        can_start = has_file and has_track and api_ready and not self.app_state.is_processing
        if hasattr(self, 'start_btn'):
            self.start_btn.configure(state="normal" if can_start else "disabled")
        
        # Update cost estimate
        self._update_token_estimate()
    
    def _update_token_estimate(self):
        """Calculate and display estimated tokens for OpenRouter translations."""
        # Only show for OpenRouter/Groq with file, track, and API ready
        if (self.config.provider not in ["openrouter", "groq"] or 
            not self.app_state.current_file or 
            self.app_state.selected_track_id is None or
            not self.app_state.api_validated or
            self.app_state.is_processing): # Don't estimate while already processing
            if hasattr(self, 'cost_estimate_label'):
                self.cost_estimate_label.configure(text="")
            return
        
        try:
            api_manager = get_api_manager()
            model_info = api_manager.get_selected_model_info()
            
            if not model_info:
                if hasattr(self, 'cost_estimate_label'):
                    self.cost_estimate_label.configure(text="")
                return
            
            # Use the estimation service
            from core.estimation_service import EstimationService
            
            if not hasattr(self, 'estimation_service'):
                self.estimation_service = EstimationService(self.mkv_handler)
                
            def on_result(total_chars, line_count):
                self.after(0, lambda: self._display_token_estimate(model_info, total_chars, line_count))
                
            def on_error(e):
                self.after(0, lambda: self.cost_estimate_label.configure(text=""))
                
            started = self.estimation_service.estimate_tokens_async(
                self.app_state.current_file,
                self.app_state.selected_track_id,
                on_result,
                on_error,
                external_subtitle_path=self.app_state.external_subtitle_path
            )
            
            if started and hasattr(self, 'cost_estimate_label'):
                 self.cost_estimate_label.configure(text="💰 Calculating...")
            
        except Exception as e:
            self.logger.warning(f"Failed to estimate list: {e}")
            if hasattr(self, 'cost_estimate_label'):
                self.cost_estimate_label.configure(text="")
    
    def _display_token_estimate(self, model_info, total_chars: int, line_count: int):
        """Display the token estimate based on cached subtitle data."""
        if not hasattr(self, 'estimation_service'):
            from core.estimation_service import EstimationService
            self.estimation_service = EstimationService(self.mkv_handler)
            
        total_estimated_tokens = self.estimation_service.calculate_tokens(total_chars, line_count)
        
        # Format token count
        if total_estimated_tokens >= 1000:
            token_text = f"{total_estimated_tokens / 1000:.1f}K"
        else:
            token_text = f"{total_estimated_tokens}"
        
        # Display only tokens, NO cost
        display_text = f"💰 ~{token_text} tokens"
        
        if hasattr(self, 'cost_estimate_label'):
            self.cost_estimate_label.configure(text=display_text)
