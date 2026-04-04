from typing import List, Callable
from gui.state.app_state import AppState

class StepController:
    """Controller for managing wizard steps and stepper logic."""
    
    def __init__(self, state: AppState, stepper: any, step_frames: List[any]):
        self.state = state
        self.stepper = stepper
        self.step_frames = step_frames
        self.on_step_change_callback = None

    def set_callback(self, on_step_change: Callable):
        self.on_step_change_callback = on_step_change

    def show_step(self, step_index: int):
        """Show a specific step frame."""
        # Hide all
        for frame in self.step_frames:
            frame.grid_remove()
        
        # Show target
        if 1 <= step_index <= len(self.step_frames):
            self.step_frames[step_index-1].grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
            self.stepper.set_step(step_index)

    def handle_step_change(self, step_index: int):
        """Handle user clicking a step in the stepper."""
        # Selection validation
        if step_index == 2:
            if not self.state.current_file:
                self.stepper.set_step(1)
                return False
        elif step_index == 3:
            if not self.state.current_file or self.state.selected_track_id is None:
                self.stepper.set_step(2)
                return False
        
        self.show_step(step_index)
        if self.on_step_change_callback:
            self.on_step_change_callback(step_index)
        return True

    def update_stepper_logic(self, api_manager: any):
        """Update stepper descriptions and completion marks."""
        # Step 1: File
        if self.state.current_file:
            from pathlib import Path
            self.stepper.update_step(1, description=Path(self.state.current_file).name, is_complete=True)
        else:
            self.stepper.update_step(1, description="Select MKV video file", is_complete=False)

        # Step 2: Config
        if self.state.selected_track_id is not None:
            track_info = f"Track {self.state.selected_track_id}"
            if self.state.selected_model:
                # Get short name from manager if possible
                info = api_manager.get_selected_model_info()
                model_name = info.short_name if info else self.state.selected_model
                track_info += f" • {model_name}"
            
            self.stepper.update_step(2, description=track_info, is_complete=True)
        else:
            self.stepper.update_step(2, description="Configure tracks & API", is_complete=False)

        # Step 3: Progress
        if self.state.is_processing:
            self.stepper.update_step(3, description="Translating...", is_complete=False)
        else:
             # If step 4 (review) or 5 (summary) is active, step 3 is "complete"
             is_done = self.stepper.current_step > 3
             self.stepper.update_step(3, description="Translation process", is_complete=is_done)
