"""
Styles for Sub-auto GUI
Defines colors, fonts, and theme settings.
"""

import customtkinter as ctk


# Color Palette - Minimal (3-4 Core Colors, No Gradients)
COLORS = {
    # === CORE COLORS (4 only) ===
    
    # 1. Background (Blacks & Grays)
    "bg_dark": "#0b0b0b",            # Main background
    "bg_medium": "#1a1a1a",          # Cards, panels
    "bg_light": "#2a2a2a",           # Inputs, hover states
    
    # 2. Text (Light Grays)
    "text_primary": "#e8eaed",       # Main text
    "text_secondary": "#9aa0a6",     # Secondary text
    "text_muted": "#71717a",         # Muted text
    
    # 3. Accent Blue (Interactive elements)
    "accent": "#3B82F6",             # Primary accent - buttons, links, active states
    "accent_hover": "#60A5FA",       # Lighter blue for hover
    "accent_bg": "#1E3A5F",          # Dark blue background
    
    # 4. Success Green (Completion, validation)
    "success": "#00e676",            # Success state, completed items
    "success_dim": "#10b981",        # Dimmer green for subtle states
    
    # === DERIVED COLORS (from core palette) ===
    
    # Borders (from backgrounds)
    "border": "#2a2a2a",             # Same as bg_light
    "border_light": "#3a3a3a",       # Slightly lighter
    
    # Status colors (minimal, using core colors)
    "error": "#ff1744",              # Red for errors (only additional color needed)
    "warning": "#EAB308",            # Yellow for warnings (only additional color needed)
    
    # Background colors for status (using existing colors)
    "success_bg": "#14532D",         # Dark green background
    "error_bg": "#7F1D1D",           # Dark red background
    "warning_bg": "#713F12",         # Dark yellow background
    "info_bg": "#1E3A5F",            # Dark blue background (same as accent_bg)
    
    # Aliases for consistency
    "primary": "#e8eaed",            # Alias for text_primary
    "primary_hover": "#f0f0f0",      # Lighter text for hover states
    "primary_light": "#c0c0c0",      # Muted light text
    "highlight": "#e8eaed",          # Alias for text_primary
    "info": "#3B82F6",               # Alias for accent
    
    # Step states (using core colors)
    "step_inactive": "#71717a",      # text_muted
    "step_active": "#3B82F6",        # accent
    "step_completed": "#00e676",     # success
    "step_active_bg": "#1a1a1a",     # bg_medium
    
    # Syntax highlighting (using core colors)
    "syntax_number": "#60A5FA",      # accent_hover
    "syntax_timestamp": "#00e676",   # success
    "syntax_arrow": "#9aa0a6",       # text_secondary
    "syntax_text": "#e8eaed",        # text_primary
    "syntax_error": "#ff1744",       # error
    "syntax_comment": "#71717a",     # text_muted
}

# Font settings
FONTS = {
    "family": "Consolas",        # Terminal-style monospace font
    "heading_size": 14,          # Increased from 11
    "subheading_size": 12,       # Increased from 10
    "body_size": 12,             # Increased from 10
    "small_size": 11,            # Increased from 9
    "mono_family": "Consolas",   # Monospace
}

# Spacing - Enhanced System
SPACING = {
    "xxs": 2,   # Minimal spacing
    "xs": 4,    # Very tight
    "sm": 8,    # Tight
    "md": 12,   # Normal
    "lg": 16,   # Comfortable
    "xl": 24,   # Spacious
    "xxl": 32,  # Very spacious
}

# Border radius - Rounded corners (User request)
RADIUS = {
    "sm": 4,
    "md": 8,
    "lg": 16,
    "xl": 24,
}


def configure_theme():
    """Configure CustomTkinter appearance."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")


def get_button_style(variant: str = "primary") -> dict:
    """Get button styling based on variant."""
    styles = {
        "primary": {
            "fg_color": COLORS["primary"],
            "hover_color": COLORS["primary_hover"],
            "text_color": "#09090B",  # Dark text on white button
            "corner_radius": RADIUS["md"],
        },
        "secondary": {
            "fg_color": COLORS["bg_light"],
            "hover_color": COLORS["border"],
            "text_color": COLORS["text_primary"],
            "corner_radius": RADIUS["md"],
        },
        "success": {
            "fg_color": COLORS["success"],
            "hover_color": COLORS["success_bg"],
            "text_color": "#09090B",  # Dark text on green button
            "corner_radius": RADIUS["md"],
        },
        "danger": {
            "fg_color": COLORS["error"],
            "hover_color": COLORS["error_bg"],
            "text_color": COLORS["text_primary"],
            "corner_radius": RADIUS["md"],
        },
        "ghost": {
            "fg_color": "transparent",
            "hover_color": COLORS["bg_light"],
            "text_color": COLORS["text_secondary"],
            "corner_radius": RADIUS["md"],
        },
        "info": {
            "fg_color": COLORS["info"],
            "hover_color": COLORS["info_bg"],
            "text_color": COLORS["text_primary"],
            "corner_radius": RADIUS["md"],
        },
    }
    return styles.get(variant, styles["primary"])


def get_input_style() -> dict:
    """Get input field styling."""
    return {
        "fg_color": COLORS["bg_dark"],
        "border_color": COLORS["border"],
        "text_color": COLORS["text_primary"],
        "placeholder_text_color": COLORS["text_muted"],
        "corner_radius": RADIUS["md"],
        "border_width": 1,
    }


def get_option_menu_style() -> dict:
    """Get option menu styling."""
    return {
        "fg_color": COLORS["bg_dark"],
        "button_color": COLORS["bg_medium"],
        "button_hover_color": COLORS["primary_hover"],
        "text_color": COLORS["text_primary"],
        "corner_radius": RADIUS["md"],
    }


def get_frame_style(variant: str = "default") -> dict:
    """Get frame styling based on variant."""
    styles = {
        "default": {
            "fg_color": COLORS["bg_medium"],
            "corner_radius": RADIUS["lg"],
        },
        "card": {
            "fg_color": COLORS["bg_medium"],  # Changed from bg_card
            "corner_radius": RADIUS["lg"],
        },
        "transparent": {
            "fg_color": "transparent",
            "corner_radius": 0,
        },
    }
    return styles.get(variant, styles["default"])


def get_label_style(variant: str = "body") -> dict:
    """Get label styling based on variant."""
    styles = {
        "heading": {
            "text_color": COLORS["text_primary"],
            "font": (FONTS["family"], FONTS["heading_size"], "bold"),
        },
        "subheading": {
            "text_color": COLORS["text_primary"],
            "font": (FONTS["family"], FONTS["subheading_size"], "bold"),
        },
        "body": {
            "text_color": COLORS["text_primary"],
            "font": (FONTS["family"], FONTS["body_size"]),
        },
        "secondary": {
            "text_color": COLORS["text_secondary"],
            "font": (FONTS["family"], FONTS["body_size"]),
        },
        "muted": {
            "text_color": COLORS["text_muted"],
            "font": (FONTS["family"], FONTS["small_size"]),
        },
        "mono": {
            "text_color": COLORS["text_secondary"],
            "font": (FONTS["mono_family"], FONTS["small_size"]),
        },
    }
    return styles.get(variant, styles["body"])
