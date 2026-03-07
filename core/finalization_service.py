"""
Finalization Service for Sub-auto
Handles MKV merging, history recording, and temporary file cleanup.
"""

import os
import time
from pathlib import Path
from typing import Optional, Dict, Any

from .mkv_handler import MKVHandler
from .history_manager import HistoryEntry, get_history_manager
from .state_manager import get_state_manager
from .logger import get_logger
from .translator import TokenUsage

class FinalizationService:
    """Service for post-translation finalization tasks."""
    
    def __init__(self, mkv_handler: MKVHandler):
        self.mkv_handler = mkv_handler
        self.history_manager = get_history_manager()
        self.state_manager = get_state_manager()
        self.logger = get_logger()

    def finalize_merge(self, payload: Dict[str, Any], remove_old_subs: bool = True) -> Dict[str, Any]:
        """
        Finalize the merge process: MKV merge, cleanup, and history.
        
        Args:
            payload: Translation results and metadata
            remove_old_subs: Whether to remove existing subtitles from MKV
            
        Returns:
            Summary dictionary for UI display
        """
        try:
            input_path = payload["input_path"]
            output_dir = payload["output_dir"]
            sanitized_model = payload["sanitized_model"]
            model_used = payload["model_used"]
            current_file = payload["current_file"]
            translated_sub_path = payload["translated_sub_path"]
            
            output_mkv_path = Path(output_dir) / f"{input_path.stem}_{sanitized_model}_translated.mkv"
            
            # 1. MKV Merge
            self.mkv_handler.replace_subtitle(
                mkv_path=current_file,
                subtitle_path=translated_sub_path,
                output_path=str(output_mkv_path),
                language="ind",
                track_name=f"Indonesian ({model_used})",
                remove_existing_subs=remove_old_subs
            )
            
            # 2. Cleanup Temporary Files
            self.cleanup_temp_files(payload)
            
            # 3. Calculate Duration
            duration = time.time() - payload["start_time"]
            
            # 4. Save to History
            final_tokens = payload.get("final_tokens", TokenUsage())
            estimated_cost = self._calculate_cost(payload, final_tokens)
            
            self._save_history(payload, output_mkv_path, duration, final_tokens, estimated_cost)
            
            # 5. Clear State
            self.state_manager.clear()
            
            # 6. Return Summary
            return {
                "output_path": str(output_mkv_path),
                "lines_translated": payload.get("lines_count", 0),
                "model_used": model_used,
                "duration_seconds": duration,
                "removed_old_subs": remove_old_subs,
                "tokens": final_tokens,
                "estimated_cost": estimated_cost
            }
            
        except Exception as e:
            self.logger.error(f"Finalization failed: {e}")
            raise e

    def cleanup_temp_files(self, payload: Dict[str, Any]):
        """Clean up temporary files generated during translation."""
        try:
            # Remove extracted subtitle file
            extracted_path = payload.get("extracted_path")
            if extracted_path and Path(extracted_path).exists():
                Path(extracted_path).unlink()
                self.logger.info(f"Cleaned up extracted file: {extracted_path}")
            
            # Remove translated subtitle file
            translated_sub_path = payload.get("translated_sub_path")
            if translated_sub_path and Path(translated_sub_path).exists():
                Path(translated_sub_path).unlink()
                self.logger.info(f"Cleaned up translated file: {translated_sub_path}")
        except Exception as e:
            self.logger.warning(f"Failed to clean up temp files: {e}")

    def _calculate_cost(self, payload: Dict[str, Any], tokens: TokenUsage) -> Optional[float]:
        """Calculate cost if applicable."""
        api_manager = payload.get("api_manager")
        if api_manager:
            model_info = api_manager.get_selected_model_info()
            if model_info:
                return model_info.calculate_cost(
                    tokens.prompt_tokens,
                    tokens.completion_tokens
                )
        return None

    def _save_history(
        self, 
        payload: Dict[str, Any], 
        output_path: Path, 
        duration: float, 
        tokens: TokenUsage,
        estimated_cost: Optional[float]
    ):
        """Record the translation job in history."""
        try:
            entry = HistoryEntry(
                source_file=str(payload["current_file"]),
                source_file_name=payload["input_path"].name,
                output_file=str(output_path),
                track_id=payload.get("track_id", -1),
                source_lang=payload.get("source_lang", ""),
                target_lang="ind",
                model_name=payload.get("model_used", ""),
                provider=payload.get("provider", ""),
                prompt_name=payload.get("prompt_used", ""),
                total_lines=payload.get("total_lines", 0),
                lines_translated=payload.get("lines_count", 0),
                duration_seconds=duration,
                prompt_tokens=tokens.prompt_tokens,
                completion_tokens=tokens.completion_tokens,
                estimated_cost=estimated_cost,
                status="completed"
            )
            self.history_manager.add_entry(entry)
        except Exception as e:
            self.logger.warning(f"Failed to save history: {e}")
