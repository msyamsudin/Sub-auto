"""
Style Handler for Sub-auto
Handles preservation of ASS/SSA styling tags during translation.
"""

import re
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass


@dataclass
class StyleInfo:
    """Information about styling in a subtitle line."""
    prefix_tags: str  # Tags at the beginning (e.g., {\pos(x,y)\fs20})
    clean_text: str   # Text without any tags
    inline_tags: List[Tuple[int, str]]  # (position, tag) for inline tags
    has_complex_styling: bool  # Whether line has complex positioning/styling


class StyleHandler:
    """Handles ASS/SSA style tag preservation during translation."""
    
    # Styles that typically shouldn't be translated (signs, songs, etc.)
    SKIP_TRANSLATION_STYLES = {
        'sign', 'signs', 'op', 'ed', 'opening', 'ending', 
        'title', 'card', 'note', 'notes', 'karaoke'
    }
    
    # Tags that indicate complex positioning (usually signs)
    POSITIONING_TAGS = [r'\\pos\(', r'\\move\(', r'\\org\(', r'\\clip\(']
    
    def __init__(self):
        self.placeholder_pattern = "<<STYLE_{}>>"
        
    def should_skip_translation(self, style_name: str, text: str) -> bool:
        """
        Determine if a line should skip translation.
        
        Args:
            style_name: The style name from the subtitle
            text: The text content
            
        Returns:
            True if translation should be skipped
        """
        # Check if style name matches skip list
        if style_name.lower() in self.SKIP_TRANSLATION_STYLES:
            return True
        
        # Check if text has complex positioning (likely a sign)
        for tag_pattern in self.POSITIONING_TAGS:
            if re.search(tag_pattern, text):
                return True
                
        return False
    
    def extract_styles(self, text: str) -> StyleInfo:
        """
        Extract styling information from subtitle text.
        
        Args:
            text: Original subtitle text with ASS tags
            
        Returns:
            StyleInfo object with separated tags and clean text
        """
        # Check for complex styling
        has_complex = any(re.search(pattern, text) for pattern in self.POSITIONING_TAGS)
        
        # Extract all tags at the beginning of the line
        prefix_match = re.match(r'^(\{[^}]*\})+', text)
        prefix_tags = prefix_match.group(0) if prefix_match else ""
        
        # Remove prefix tags to get remaining text
        remaining_text = text[len(prefix_tags):] if prefix_tags else text
        
        # Find inline tags (tags within the text)
        inline_tags = []
        clean_text_parts = []
        last_pos = 0
        
        # Pattern to match inline tags like {\i1}, {\b1}, etc.
        inline_pattern = r'\{\\[^}]+\}'
        
        for match in re.finditer(inline_pattern, remaining_text):
            # Add text before this tag
            clean_text_parts.append(remaining_text[last_pos:match.start()])
            
            # Store tag with its position in clean text
            current_clean_pos = len(''.join(clean_text_parts))
            inline_tags.append((current_clean_pos, match.group(0)))
            
            last_pos = match.end()
        
        # Add remaining text after last tag
        clean_text_parts.append(remaining_text[last_pos:])
        clean_text = ''.join(clean_text_parts)
        
        return StyleInfo(
            prefix_tags=prefix_tags,
            clean_text=clean_text,
            inline_tags=inline_tags,
            has_complex_styling=has_complex
        )
    
    def prepare_for_translation(self, text: str, style_name: str = "Default") -> Tuple[str, Dict]:
        """
        Prepare text for translation by replacing tags with placeholders.
        
        Args:
            text: Original subtitle text
            style_name: Style name from subtitle
            
        Returns:
            Tuple of (text_with_placeholders, metadata_dict)
        """
        # Check if should skip
        if self.should_skip_translation(style_name, text):
            return text, {'skip': True, 'original': text}
        
        # Extract styles
        style_info = self.extract_styles(text)
        
        # If no inline tags, just return clean text
        if not style_info.inline_tags:
            return style_info.clean_text, {
                'skip': False,
                'prefix_tags': style_info.prefix_tags,
                'inline_tags': {},
                'has_complex': style_info.has_complex_styling
            }
        
        # Replace inline tags with placeholders
        text_with_placeholders = style_info.clean_text
        placeholder_map = {}
        
        # Sort inline tags by position (reverse order to maintain positions)
        sorted_tags = sorted(style_info.inline_tags, key=lambda x: x[0], reverse=True)
        
        for idx, (pos, tag) in enumerate(sorted_tags):
            placeholder = self.placeholder_pattern.format(idx)
            placeholder_map[placeholder] = tag
            
            # Insert placeholder at position
            text_with_placeholders = (
                text_with_placeholders[:pos] + 
                placeholder + 
                text_with_placeholders[pos:]
            )
        
        return text_with_placeholders, {
            'skip': False,
            'prefix_tags': style_info.prefix_tags,
            'inline_tags': placeholder_map,
            'has_complex': style_info.has_complex_styling
        }
    
    def restore_styles(self, translated_text: str, metadata: Dict) -> str:
        """
        Restore styling tags to translated text.
        
        Args:
            translated_text: The translated text (may contain placeholders)
            metadata: Metadata dict from prepare_for_translation
            
        Returns:
            Text with styles restored
        """
        # If marked to skip, return original
        if metadata.get('skip', False):
            return metadata.get('original', translated_text)
        
        result = translated_text
        
        # Restore inline tags from placeholders
        inline_tags = metadata.get('inline_tags', {})
        for placeholder, tag in inline_tags.items():
            result = result.replace(placeholder, tag)
        
        # Add prefix tags back
        prefix_tags = metadata.get('prefix_tags', '')
        if prefix_tags:
            result = prefix_tags + result
        
        return result
    
    def get_translation_hint(self, style_name: str, text: str) -> str:
        """
        Get a hint message for the translator about this line.
        
        Args:
            style_name: Style name
            text: Text content
            
        Returns:
            Hint message or empty string
        """
        if self.should_skip_translation(style_name, text):
            return f"[SKIP: {style_name}] This appears to be a sign/title - translation skipped"
        
        style_info = self.extract_styles(text)
        if style_info.has_complex_styling:
            return "[COMPLEX STYLING] Preserving positioning and formatting"
        elif style_info.inline_tags:
            return f"[INLINE STYLES] Preserving {len(style_info.inline_tags)} inline formatting tags"
        
        return ""


# Convenience functions for backward compatibility
def clean_text_for_translation(text: str, style: str = "Default") -> Tuple[str, Dict]:
    """Clean text for translation, preserving style metadata."""
    handler = StyleHandler()
    return handler.prepare_for_translation(text, style)


def restore_text_after_translation(translated: str, metadata: Dict) -> str:
    """Restore styles to translated text."""
    handler = StyleHandler()
    return handler.restore_styles(translated, metadata)
