from core.mkv_handler import MKVHandler


def test_parse_gui_mode_progress():
    assert MKVHandler._parse_merge_progress("#GUI#progress 42%") == 42


def test_parse_console_progress():
    assert MKVHandler._parse_merge_progress("Progress: 7%\r") == 7


def test_parse_progress_ignores_other_output_and_clamps_value():
    assert MKVHandler._parse_merge_progress("Muxing track 1") is None
    assert MKVHandler._parse_merge_progress("#GUI#progress 105%") == 100
