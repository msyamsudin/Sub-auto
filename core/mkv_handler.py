"""
MKV Handler for Sub-auto
Wrapper for MKVToolnix CLI tools (mkvmerge, mkvextract).
"""

import json
import subprocess
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from .config_manager import get_config


@dataclass
class SubtitleTrack:
    """Represents a subtitle track in an MKV file."""
    track_id: int
    codec: str
    language: str
    track_name: str
    default_track: bool
    forced_track: bool
    
    @property
    def display_name(self) -> str:
        """Get a human-readable display name for this track."""
        parts = [f"Track {self.track_id}"]
        if self.track_name:
            parts.append(f"- {self.track_name}")
        if self.language and self.language != "und":
            parts.append(f"({self.language})")
        if self.codec:
            parts.append(f"[{self.codec}]")
        if self.default_track:
            parts.append("*Default*")
        return " ".join(parts)
    
    @property
    def file_extension(self) -> str:
        """Get the appropriate file extension based on codec."""
        codec_lower = self.codec.lower()
        if "subrip" in codec_lower or "srt" in codec_lower:
            return ".srt"
        elif "ass" in codec_lower or "ssa" in codec_lower:
            return ".ass"
        elif "vobsub" in codec_lower:
            return ".sub"
        elif "pgs" in codec_lower or "hdmv" in codec_lower:
            return ".sup"
        else:
            return ".srt"  # Default to SRT


class MKVHandler:
    """Handler for MKVToolnix CLI operations."""
    
    def __init__(self, mkvtoolnix_path: Optional[str] = None):
        """
        Initialize MKVHandler.
        
        Args:
            mkvtoolnix_path: Path to MKVToolnix installation. If None, uses config.
        """
        if mkvtoolnix_path:
            self.mkvtoolnix_path = Path(mkvtoolnix_path)
        else:
            self.mkvtoolnix_path = Path(get_config().mkvtoolnix_path)
    
    @property
    def mkvmerge_path(self) -> Path:
        """Get path to mkvmerge.exe."""
        return self.mkvtoolnix_path / "mkvmerge.exe"
    
    @property
    def mkvextract_path(self) -> Path:
        """Get path to mkvextract.exe."""
        return self.mkvtoolnix_path / "mkvextract.exe"
    
    def check_installation(self) -> tuple[bool, str]:
        """
        Check if MKVToolnix is properly installed.
        
        Returns:
            Tuple of (is_installed, message)
        """
        if not self.mkvtoolnix_path.exists():
            return False, f"MKVToolnix directory not found: {self.mkvtoolnix_path}"
        
        if not self.mkvmerge_path.exists():
            return False, f"mkvmerge.exe not found in: {self.mkvtoolnix_path}"
        
        if not self.mkvextract_path.exists():
            return False, f"mkvextract.exe not found in: {self.mkvtoolnix_path}"
        
        # Try to run mkvmerge --version to verify it works
        try:
            result = subprocess.run(
                [str(self.mkvmerge_path), "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0] if result.stdout else "Unknown version"
                return True, f"MKVToolnix installed: {version_line}"
            else:
                return False, f"mkvmerge returned error: {result.stderr}"
        except subprocess.TimeoutExpired:
            return False, "mkvmerge timed out"
        except Exception as e:
            return False, f"Error running mkvmerge: {e}"
    
    def get_file_info(self, mkv_path: str) -> Dict[str, Any]:
        """
        Get detailed information about an MKV file.
        
        Args:
            mkv_path: Path to the MKV file
            
        Returns:
            Dictionary containing file information (parsed JSON from mkvmerge -J)
        """
        mkv_path = Path(mkv_path)
        
        if not mkv_path.exists():
            raise FileNotFoundError(f"MKV file not found: {mkv_path}")
        
        try:
            result = subprocess.run(
                [str(self.mkvmerge_path), "-J", str(mkv_path)],
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8'
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"mkvmerge error: {result.stderr}")
            
            return json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse mkvmerge output: {e}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("mkvmerge timed out while reading file info")
    
    def get_subtitle_tracks(self, mkv_path: str) -> List[SubtitleTrack]:
        """
        Get list of subtitle tracks in an MKV file.
        
        Args:
            mkv_path: Path to the MKV file
            
        Returns:
            List of SubtitleTrack objects
        """
        file_info = self.get_file_info(mkv_path)
        tracks = []
        
        for track in file_info.get("tracks", []):
            if track.get("type") == "subtitles":
                properties = track.get("properties", {})
                
                subtitle_track = SubtitleTrack(
                    track_id=track.get("id", 0),
                    codec=track.get("codec", "unknown"),
                    language=properties.get("language", "und"),
                    track_name=properties.get("track_name", ""),
                    default_track=properties.get("default_track", False),
                    forced_track=properties.get("forced_track", False)
                )
                tracks.append(subtitle_track)
        
        return tracks
    
    def extract_subtitle(
        self, 
        mkv_path: str, 
        track_id: int, 
        output_path: Optional[str] = None
    ) -> str:
        """
        Extract a subtitle track from an MKV file.
        
        Args:
            mkv_path: Path to the MKV file
            track_id: ID of the subtitle track to extract
            output_path: Path for the extracted subtitle. If None, auto-generates.
            
        Returns:
            Path to the extracted subtitle file
        """
        mkv_path = Path(mkv_path)
        
        if not mkv_path.exists():
            raise FileNotFoundError(f"MKV file not found: {mkv_path}")
        
        # Get track info to determine file extension
        tracks = self.get_subtitle_tracks(str(mkv_path))
        track = next((t for t in tracks if t.track_id == track_id), None)
        
        if track is None:
            raise ValueError(f"Subtitle track {track_id} not found in {mkv_path}")
        
        # Generate output path if not provided
        if output_path is None:
            output_path = mkv_path.parent / f"{mkv_path.stem}_track{track_id}{track.file_extension}"
        else:
            output_path = Path(output_path)
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Run mkvextract
        try:
            result = subprocess.run(
                [
                    str(self.mkvextract_path),
                    "tracks",
                    str(mkv_path),
                    f"{track_id}:{output_path}"
                ],
                capture_output=True,
                text=True,
                timeout=120,
                encoding='utf-8'
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"mkvextract error: {result.stderr}")
            
            if not output_path.exists():
                raise RuntimeError("Extraction completed but output file not found")
            
            return str(output_path)
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("mkvextract timed out during extraction")
    
    def merge_subtitle(
        self,
        mkv_path: str,
        subtitle_path: str,
        output_path: str,
        language: str = "ind",
        track_name: str = "Indonesian",
        default_track: bool = True,
        remove_existing_subs: bool = False
    ) -> str:
        """
        Merge a subtitle file into an MKV file.
        
        Args:
            mkv_path: Path to the source MKV file
            subtitle_path: Path to the subtitle file to merge
            output_path: Path for the output MKV file
            language: Language code for the subtitle (default: "ind" for Indonesian)
            track_name: Name for the subtitle track
            default_track: Whether to set this as the default subtitle track
            remove_existing_subs: Whether to remove existing subtitle tracks
            
        Returns:
            Path to the output MKV file
        """
        mkv_path = Path(mkv_path)
        subtitle_path = Path(subtitle_path)
        output_path = Path(output_path)
        
        if not mkv_path.exists():
            raise FileNotFoundError(f"MKV file not found: {mkv_path}")
        
        if not subtitle_path.exists():
            raise FileNotFoundError(f"Subtitle file not found: {subtitle_path}")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build mkvmerge command
        cmd = [str(self.mkvmerge_path), "-o", str(output_path)]
        
        # Remove existing subtitles if requested
        if remove_existing_subs:
            cmd.extend(["--no-subtitles"])
        
        # Add source MKV
        cmd.append(str(mkv_path))
        
        # Add subtitle with options
        cmd.extend([
            "--language", f"0:{language}",
            "--track-name", f"0:{track_name}"
        ])
        
        if default_track:
            cmd.extend(["--default-track", "0:yes"])
        
        cmd.append(str(subtitle_path))
        
        # Run mkvmerge
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout for large files
                encoding='utf-8'
            )
            
            # mkvmerge returns 0 for success, 1 for warnings, 2 for errors
            if result.returncode == 2:
                raise RuntimeError(f"mkvmerge error: {result.stderr}")
            
            if not output_path.exists():
                raise RuntimeError("Merge completed but output file not found")
            
            return str(output_path)
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("mkvmerge timed out during merge")
    
    def replace_subtitle(
        self,
        mkv_path: str,
        subtitle_path: str,
        output_path: Optional[str] = None,
        language: str = "ind",
        track_name: str = "Indonesian (Translated)",
        remove_existing_subs: bool = False
    ) -> str:
        """
        Replace subtitles in an MKV file with a new subtitle file.
        Creates a new file with the translated subtitle.
        
        Args:
            mkv_path: Path to the source MKV file
            subtitle_path: Path to the new subtitle file
            output_path: Path for output. If None, creates with "_translated" suffix
            language: Language code for the new subtitle
            track_name: Name for the new subtitle track
            remove_existing_subs: If True, removes all existing subtitle tracks
            
        Returns:
            Path to the output MKV file
        """
        mkv_path = Path(mkv_path)
        
        if output_path is None:
            output_path = mkv_path.parent / f"{mkv_path.stem}_translated{mkv_path.suffix}"
        
        return self.merge_subtitle(
            mkv_path=str(mkv_path),
            subtitle_path=subtitle_path,
            output_path=str(output_path),
            language=language,
            track_name=track_name,
            default_track=True,
            remove_existing_subs=remove_existing_subs
        )

