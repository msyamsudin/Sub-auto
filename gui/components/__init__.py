"""
Modularized GUI Components for Sub-auto
"""

from .base import TrackListItem, StatusBadge, SettingsRow
from .layout import (
    CollapsibleFrame, 
    VerticalStepperItem, VerticalStepper, 
    HorizontalStepperItem, HorizontalStepper,
    ContentProgressHeader
)
from .file import FileDropZone
from .progress import SegmentedProgressBar, ProgressPanel
from .api import APIKeyPanel, ModelSelectorDialog
from .window import CustomTitleBar, SummaryWindow
from .log_panel import LogPanel

# Import these from their original locations (they were already in separate files)
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ..step_card import StepCard
from ..subtitle_review_panel import SubtitleReviewPanel

# Re-exporting for backward compatibility
__all__ = [
    'TrackListItem', 'StatusBadge', 'SettingsRow',
    'CollapsibleFrame', 'VerticalStepperItem', 'VerticalStepper',
    'HorizontalStepperItem', 'HorizontalStepper', 'ContentProgressHeader',
    'FileDropZone',
    'SegmentedProgressBar', 'ProgressPanel',
    'APIKeyPanel', 'ModelSelectorDialog',
    'CustomTitleBar', 'SummaryWindow',
    'LogPanel',
    'StepCard',
    'SubtitleReviewPanel'
]
