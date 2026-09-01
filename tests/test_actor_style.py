
import unittest
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.subtitle_parser import SubtitleParser, SubtitleLine

class TestActorStylePreservation(unittest.TestCase):
    def setUp(self):
        # Create a dummy ASS file for testing
        self.test_ass = Path("test_actor.ass")
        with open(self.test_ass, "w", encoding="utf-8") as f:
            f.write("""[Script Info]
ScriptType: v4.00+

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1
Style: Person1,Arial,20,&H000000FF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:05.00,Default,Actor A,0,0,0,,Hello world
Dialogue: 0,0:00:05.00,0:00:10.00,Person1,Actor B,0,0,0,,Style test
Comment: 0,0:00:00.00,0:00:00.00,Default,,0,0,0,,This is a comment
Dialogue: 0,0:00:10.00,0:00:15.00,Default,Actor A,0,0,0,,Another line
""")

    def tearDown(self):
        if self.test_ass.exists():
            os.remove(self.test_ass)
            
    def test_actor_style_loading(self):
        parser = SubtitleParser()
        lines = parser.load(str(self.test_ass))
        
        # Verify lines loaded
        self.assertEqual(len(lines), 3) # 3 dialogues, 1 comment (ignored)
        
        # Verify Actor A
        self.assertEqual(lines[0].actor, "Actor A")
        self.assertEqual(lines[0].style, "Default")
        
        # Verify Actor B and Style
        self.assertEqual(lines[1].actor, "Actor B")
        self.assertEqual(lines[1].style, "Person1")
        
        # Verify indices (should match original file order event indices)
        # Events: Dialogue(0), Dialogue(1), Comment(2), Dialogue(3) within the [Events] section?
        # pysubs2 loads all events. enumerate() gives index in the events list.
        # Let's verify what indices we get.
        print(f"Indices: {[l.index for l in lines]}")
        
    def test_apply_translations_indexing(self):
        parser = SubtitleParser()
        lines = parser.load(str(self.test_ass))
        
        # Original texts
        original_texts = [l.text for l in lines]
        
        # Simulate translations
        # We need to use the indices from the loaded lines
        translations = [
            (lines[0].index, "Halo dunia"),
            (lines[1].index, "Tes gaya"),
            (lines[2].index, "Baris lain")
        ]
        
        # Apply
        parser.apply_translations(translations)
        
        # Check if events updated correctly in self.subs
        # We need to iterate self.subs to check
        dialogues = [e for e in parser.subs if e.type == "Dialogue"]
        
        self.assertEqual(dialogues[0].text, "Halo dunia")
        self.assertEqual(dialogues[1].text, "Tes gaya")
        self.assertEqual(dialogues[2].text, "Baris lain")
        
        # Verify style and actor preserved in the underlying events
        self.assertEqual(dialogues[1].style, "Person1")
        self.assertEqual(dialogues[1].name, "Actor B")
        
        print("✅ apply_translations correctly matched indices and updated text")

if __name__ == '__main__':
    unittest.main()
