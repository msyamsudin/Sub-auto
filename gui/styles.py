"""
Styles for Sub-auto GUI
Defines colors, fonts, and theme settings.
"""

import customtkinter as ctk


# Color Palette - Minimal Gray Theme (Ultra Clean with High Contrast)
COLORS = {
    # Primary colors - White accent on dark
    "primary": "#FAFAFA",            # Pure White
    "primary_hover": "#E4E4E7",      # Light Gray hover
    "primary_light": "#D4D4D8",      # Zinc 300
    
    # Background colors - True blacks
    "bg_dark": "#09090B",            # Zinc 950 (True Black)
    "bg_medium": "#18181B",          # Zinc 900
    "bg_light": "#27272A",           # Zinc 800
    "bg_card": "#18181B",            # Zinc 900
    
    # Text colors
    "text_primary": "#FAFAFA",       # Zinc 50 (White)
    "text_secondary": "#A1A1AA",     # Zinc 400 (Gray)
    "text_muted": "#71717A",         # Zinc 500 (Muted)
    
    # Status colors
    "success": "#22C55E",            # Green 500
    "success_bg": "#14532D",         # Green 900
    "warning": "#EAB308",            # Yellow 500
    "warning_bg": "#713F12",         # Yellow 900
    "error": "#EF4444",              # Red 500
    "error_bg": "#7F1D1D",           # Red 900
    "info": "#3B82F6",               # Blue 500
    "info_bg": "#1E3A5F",            # Blue 900
    
    # Border colors
    "border": "#3F3F46",             # Zinc 700
    "border_light": "#52525B",       # Zinc 600
    
    # Special
    "accent": "#A1A1AA",             # Zinc 400
    "highlight": "#FAFAFA",          # White highlight
    
    # Step states
    "step_inactive": "#3F3F46",      # Zinc 700 - dimmed
    "step_active": "#3B82F6",        # Blue 500 - current step
    "step_completed": "#22C55E",     # Green 500 - done
    "step_active_bg": "#1E293B",     # Slate 800 - active background
}

# Font settings
FONTS = {
    "family": "Segoe UI",
    "heading_size": 16,     # Reduced from 18
    "subheading_size": 13,  # Reduced from 14
    "body_size": 12,
    "small_size": 10,
    "mono_family": "Consolas",
}

# Spacing
# Spacing - Ultra Compact Mode
SPACING = {
    "xs": 2,
    "sm": 4,
    "md": 4,   # Extra Compact
    "lg": 6,   # Extra Compact
    "xl": 8,   # Extra Compact
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
            "fg_color": COLORS["bg_card"],
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
