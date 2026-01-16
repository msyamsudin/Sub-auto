"""
Sub-auto: Automated MKV Subtitle Extraction, Translation & Replacement

A GUI application for automating the process of:
1. Extracting subtitles from MKV files
2. Translating subtitles using Gemini AI
3. Replacing/adding translated subtitles back to MKV

Author: Syam
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def main():
    """Main entry point for Sub-auto application."""
    try:
        # Import and run the GUI app
        from gui.app import run_app
        run_app()
    except ImportError as e:
        print(f"Error: Missing dependency - {e}")
        print("\nPlease install dependencies with:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
