"""
Styles for Sub-auto GUI
Defines colors, fonts, and theme settings.
"""

import customtkinter as ctk


# Color Palette
COLORS = {
    # Background surfaces
    "bg_dark": "#171717",            # Main background
    "bg_medium": "#1f1f1f",          # Cards, panels
    "bg_light": "#2a2a2a",           # Inputs, hover states

    # Text
    "text_primary": "#ececec",       # Main text
    "text_secondary": "#b3b3b3",     # Secondary text
    "text_muted": "#7d7d7d",         # Muted text

    # Accent
    "accent": "#d4d4d4",             # Primary accent - subtle neutral highlight
    "accent_hover": "#f2f2f2",       # Hover accent
    "accent_bg": "#2f2f2f",          # Accent surface

    # Success
    "success": "#32d79f",            # Success state
    "success_dim": "#29b383",        # Dim success state

    # Borders / depth
    "border": "#323232",
    "border_light": "#454545",

    # Status colors
    "error": "#ff6b6b",
    "warning": "#d9b15f",

    # Status backgrounds
    "success_bg": "#173228",
    "error_bg": "#4a2528",
    "warning_bg": "#4a3a1f",
    "info_bg": "#303030",

    # Aliases
    "primary": "#ececec",
    "primary_hover": "#ffffff",
    "primary_light": "#d6d6d6",
    "highlight": "#ececec",
    "info": "#9bbcff",

    # Step states
    "step_inactive": "#707070",
    "step_active": "#ececec",
    "step_completed": "#32d79f",
    "step_active_bg": "#1f1f1f",

    # Syntax highlighting
    "syntax_number": "#9bbcff",
    "syntax_timestamp": "#32d79f",
    "syntax_arrow": "#b3b3b3",
    "syntax_text": "#ececec",
    "syntax_error": "#ff6b6b",
    "syntax_comment": "#7d7d7d",
}

# Font settings
FONTS = {
    "family": "Segoe UI",        # Softer UI font for app chrome and forms
    "heading_size": 14,          # Increased from 11
    "subheading_size": 12,       # Increased from 10
    "body_size": 12,             # Increased from 10
    "small_size": 11,            # Increased from 9
    "mono_family": "Consolas",   # Monospace for logs/editor content
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
            "text_color": "#0f1419",
            "corner_radius": RADIUS["md"],
        },
        "secondary": {
            "fg_color": COLORS["bg_light"],
            "hover_color": COLORS["border_light"],
            "text_color": COLORS["text_primary"],
            "corner_radius": RADIUS["md"],
        },
        "success": {
            "fg_color": COLORS["success"],
            "hover_color": COLORS["success_bg"],
            "text_color": "#0f1419",
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
            "text_color": "#f7fbff",
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
            "fg_color": COLORS["bg_medium"],
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
