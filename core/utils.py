import re
import os

def extract_anime_title(filepath: str) -> str:
    """
    Extracts the likely anime title from a typical release filename.
    
    Examples:
    [SubsPlease] Sousou no Frieren - 01 (1080p).mkv -> Sousou no Frieren
    [Erai-raws] Frieren - 01 [1080p].mkv -> Frieren
    Frieren Episode 1.mkv -> Frieren Episode 1
    
    Args:
        filepath: Full path or filename of the video/subtitle file.
        
    Returns:
        The extracted title, or the original filename (without extension) if extraction fails.
    """
    # Get just the filename without extension
    filename = os.path.basename(filepath)
    name_without_ext = os.path.splitext(filename)[0]
    
    # Heuristics for typical anime naming
    # 1. Remove group tags like [SubsPlease], (Erai-raws) at the start
    cleaned = re.sub(r'^\[.*?\]\s*|^\(.*?\)\s*', '', name_without_ext)
    
    # 2. Extract everything before typical episode numbering patterns
    # e.g., " - 01", " - 12v2", " 01", " S2 - 01"
    # Match " - " followed by numbers, or " " followed by numbers and maybe "vX"
    # We use a non-greedy match to get the title
    match = re.search(r'^(.*?)(?:\s+-\s+\d+|\s+\d{2,}|\s+S\d+\s+-\s+\d+)', cleaned)
    
    if match and match.group(1).strip():
         title = match.group(1).strip()
    else:
         # Fallback: remove trailing resolution, source, audio tags
         title = re.sub(r'(\(|\[)(1080p|720p|480p|4K|BD|Web|AAC|FLAC).*?(\)|\])', '', cleaned).strip()
         
    return title or name_without_ext
