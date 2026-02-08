"""
Data models and lookup tables for Mac hardware and macOS versions.
"""

from .mac_models import get_friendly_model_name, get_model_year, get_model_chip
from .macos_versions import get_macos_friendly_name, parse_version_string

__all__ = [
    'get_friendly_model_name',
    'get_model_year',
    'get_model_chip',
    'get_macos_friendly_name',
    'parse_version_string',
]