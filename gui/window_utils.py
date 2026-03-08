"""
Window utility functions for the Sub-auto GUI.
"""

import ctypes
from core.logger import get_logger

logger = get_logger()

def setup_window_style(window):
    """Setup Windows-specific window styling (shadows and rounded corners)."""
    try:
        # Get window handle
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        
        # Enable shadow effect
        DWMWA_NCRENDERING_POLICY = 2
        DWMNCRP_ENABLED = 2
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_NCRENDERING_POLICY,
            ctypes.byref(ctypes.c_int(DWMNCRP_ENABLED)),
            ctypes.sizeof(ctypes.c_int)
        )

        # Enable rounded corners (Windows 11)
        DWMWA_WINDOW_CORNER_PREFERENCE = 33
        DWMWCP_ROUND = 2
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(ctypes.c_int(DWMWCP_ROUND)),
            ctypes.sizeof(ctypes.c_int)
        )
        
        # Show in taskbar - set window as tool window then back to normal
        GWL_EXSTYLE = -20
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_APPWINDOW = 0x00040000
        
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style = style & ~WS_EX_TOOLWINDOW | WS_EX_APPWINDOW
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        
        # Force window to refresh
        ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
        ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW
    except Exception as e:
        logger.warning(f"Failed to setup window style: {e}")
