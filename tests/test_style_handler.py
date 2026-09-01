"""
Test cases for style_handler.py
Covers ASS/SSA styling scenarios: skip styles, positioning, inline tags,
prefix tags, plain text, and karaoke/opening lines.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.style_handler import StyleHandler


def test_op_ed_karaoke_styles_are_skipped():
    """Opening/ending/karaoke styles must be skipped from translation."""
    handler = StyleHandler()
    for style in ("OP", "ED", "opening", "ending", "karaoke"):
        assert handler.should_skip_translation(style, "some text") is True, style


def test_signs_are_not_skipped():
    """Sign styles with positioning must still be translated (current behavior)."""
    handler = StyleHandler()
    text = r"{\fad(948,1)\bord3\fs15\fnArial Black\an7\c&H233B4B&\pos(39.5,74)}Dig Deep!"
    assert handler.should_skip_translation("Signs", text) is False


def test_complex_sign_prefix_preserved():
    """A positioning tag block stays as prefix; translation uses clean text."""
    handler = StyleHandler()
    text = r"{\fad(948,1)\bord3\fs15\an7\pos(39.5,74)}Dig Deep!\NChase the Impawsible!!"
    prepared, metadata = handler.prepare_for_translation(text, "Signs")

    assert metadata["skip"] is False
    assert metadata["prefix_tags"] == r"{\fad(948,1)\bord3\fs15\an7\pos(39.5,74)}"
    assert metadata["has_complex"] is True
    assert "{\\" not in prepared  # tags replaced by clean text
    assert "Dig Deep!" in prepared

    restored = handler.restore_styles("Menggali Dalam!", metadata)
    assert restored == r"{\fad(948,1)\bord3\fs15\an7\pos(39.5,74)}Menggali Dalam!"


def test_inline_styling_roundtrip():
    """Inline italic/bold tags become placeholders and are restored after translation."""
    handler = StyleHandler()
    text = r"This is {\i1}italic{\i0} and {\b1}bold{\b0} text"
    prepared, metadata = handler.prepare_for_translation(text, "Default")

    assert "<<STYLE_" in prepared
    assert "{\\i1}" not in prepared  # tags hidden from the model
    assert metadata["inline_tags"], "inline tags should be recorded"

    translated = prepared.replace("italic", "miring").replace("bold", "tebal")
    restored = handler.restore_styles(translated, metadata)

    assert r"{\i1}miring{\i0}" in restored
    assert r"{\b1}tebal{\b0}" in restored
    assert "<<" not in restored  # no leftover placeholders


def test_prefix_only_restore():
    """Prefix tags are re-attached to the translated text."""
    handler = StyleHandler()
    text = r"{\fs20\c&HFFFFFF&}Simple dialogue here"
    prepared, metadata = handler.prepare_for_translation(text, "Default")

    assert prepared == "Simple dialogue here"
    assert metadata["prefix_tags"] == r"{\fs20\c&HFFFFFF&}"

    restored = handler.restore_styles("Dialog sederhana di sini", metadata)
    assert restored == r"{\fs20\c&HFFFFFF&}Dialog sederhana di sini"


def test_no_styling_identity():
    """Plain text is passed through untouched."""
    handler = StyleHandler()
    text = "Just plain text"
    prepared, metadata = handler.prepare_for_translation(text, "Default")

    assert prepared == text
    assert metadata["prefix_tags"] == ""
    assert handler.restore_styles("Hanya teks biasa", metadata) == "Hanya teks biasa"


def test_opening_song_preserved_verbatim():
    """Karaoke opening lines are returned unchanged."""
    handler = StyleHandler()
    text = r"{\k50}Ki{\k30}mi{\k40} no{\k35} na{\k45} wa"
    prepared, metadata = handler.prepare_for_translation(text, "OP")

    assert metadata["skip"] is True
    assert prepared == text
    assert handler.restore_styles(prepared, metadata) == text
