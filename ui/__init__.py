"""
UI Components

Streamlit-based user interface components for the Migration Dashboard.
All components use model and macOS version lookups for friendly display.
"""

from .header import render_header
from .main_section import render_main_section
from .data_section import render_data_section
from .styles import get_custom_css
from .sidebar import render_sidebar

__all__ = [
    'render_header',
    'render_main_section',
    'render_data_section',
    'get_custom_css',
    'render_sidebar',
]