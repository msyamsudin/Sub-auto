from core.mkv_handler import MKVHandler
from core.translation_orchestrator import TranslationOrchestrator
from gui.state.app_state import AppState

class TranslationSession:
    """Service for managing the lifecycle of a translation session."""
    
    def __init__(self, mkv_handler: MKVHandler, state: AppState):
        self.mkv_handler = mkv_handler
        self.state = state
        self.orchestrator = None
        
    def init_orchestrator(self, on_progress, on_complete, on_error):
        """Initialize or get the orchestrator with callbacks."""
        if not self.orchestrator:
            self.orchestrator = TranslationOrchestrator(self.mkv_handler)
            
        self.orchestrator.set_callbacks(
            on_progress=on_progress,
            on_complete=on_complete,
            on_error=on_error
        )
        return self.orchestrator

    def start(self, file_path, track_id, source_lang, target_lang, model, anime_title):
        """Start a new translation."""
        if not self.orchestrator:
            raise RuntimeError("Orchestrator not initialized")
            
        self.state.is_processing = True
        self.orchestrator.start_translation(
            file_path, track_id, source_lang, target_lang, model, anime_title
        )

    def pause(self) -> bool:
        """Pause the current translation. Returns True if paused."""
        if self.orchestrator:
            self.state.is_paused = True
            self.state.should_cancel = True
            self.orchestrator.pause()
            return True
        return False

    def resume(self):
        """Resume a paused translation."""
        if self.orchestrator:
            self.state.is_paused = False
            self.state.should_cancel = False
            self.state.is_processing = True
            self.orchestrator.resume()

    def cancel(self):
        """Cancel the current translation."""
        self.state.should_cancel = True
        self.state.is_processing = False
        if self.orchestrator:
            self.orchestrator.cancel()
