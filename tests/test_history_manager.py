import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from core.history_manager import HistoryManager, HistoryEntry

def test_history_manager():
    # Use a temporary history file
    test_dir = Path(__file__).parent / "temp_history"
    test_dir.mkdir(exist_ok=True)
    
    manager = HistoryManager(history_dir=str(test_dir))
    manager.clear_all()
    
    # Test adding entry
    entry1 = HistoryEntry(
        source_file="test1.mkv",
        source_file_name="test1.mkv",
        model_name="gpt-4o",
        status="completed"
    )
    manager.add_entry(entry1)
    
    entries = manager.get_entries()
    assert len(entries) == 1
    assert entries[0].source_file == "test1.mkv"
    
    # Test adding second entry (should be first in list)
    entry2 = HistoryEntry(
        source_file="test2.mkv",
        source_file_name="test2.mkv",
        model_name="claude-3-5-sonnet",
        status="completed"
    )
    manager.add_entry(entry2)
    
    entries = manager.get_entries()
    assert len(entries) == 2
    assert entries[0].source_file == "test2.mkv"
    
    # Test deletion
    id_to_delete = entries[0].id
    manager.delete_entry(id_to_delete)
    
    entries = manager.get_entries()
    assert len(entries) == 1
    assert entries[0].source_file == "test1.mkv"
    
    # Test persistence
    manager2 = HistoryManager(history_dir=str(test_dir))
    entries2 = manager2.get_entries()
    assert len(entries2) == 1
    assert entries2[0].source_file == "test1.mkv"
    
    # Clean up
    manager.clear_all()
    if (test_dir / "history.json").exists():
        (test_dir / "history.json").unlink()
    test_dir.rmdir()
    
    print("Core history manager tests passed!")

if __name__ == "__main__":
    try:
        test_history_manager()
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)
