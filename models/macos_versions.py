"""
macOS Version Lookup Table

Converts version codes to marketing names with support for multiple input formats.
Handles: "Version 26.2", "15.2", "26.2", etc.

Based on official macOS version/Darwin kernel mappings:
- Darwin 22.x = macOS 13.x (Ventura)
- Darwin 23.x = macOS 14.x (Sonoma)
- Darwin 24.x = macOS 15.x (Sequoia)
- Darwin 25.x = macOS 26.x (Tahoe)
"""

from typing import Optional
import re

# macOS Version Lookup Dictionary
# Maps Darwin kernel version → macOS marketing version and name
# Darwin versions are what appear in audit reports (e.g., "Version 24.5")
MACOS_VERSION_LOOKUP = {
    # ============================================================================
    # macOS 26 Tahoe - Darwin 25.x (Preview/Beta as of Feb 2026)
    # ============================================================================
    "25.0": ("26.0", "macOS 26 Tahoe 26.0"),
    "25.1": ("26.1", "macOS 26 Tahoe 26.1"),
    "25.2": ("26.2", "macOS 26 Tahoe 26.2"),
    "25.3": ("26.3", "macOS 26 Tahoe 26.3"),
    
    # ============================================================================
    # macOS 15 Sequoia - Darwin 24.x
    # ============================================================================
    "24.0": ("15.0", "macOS 15 Sequoia 15.0"),
    "24.1": ("15.1", "macOS 15 Sequoia 15.1"),
    "24.2": ("15.2", "macOS 15 Sequoia 15.2"),
    "24.3": ("15.3", "macOS 15 Sequoia 15.3"),
    "24.4": ("15.4", "macOS 15 Sequoia 15.4"),
    "24.5": ("15.5", "macOS 15 Sequoia 15.5"),
    "24.6": ("15.6", "macOS 15 Sequoia 15.6"),
    "24.7": ("15.7", "macOS 15 Sequoia 15.7"),
    
    # ============================================================================
    # macOS 14 Sonoma - Darwin 23.x
    # ============================================================================
    "23.0": ("14.0", "macOS 14 Sonoma 14.0"),
    "23.1": ("14.1", "macOS 14 Sonoma 14.1"),
    "23.2": ("14.2", "macOS 14 Sonoma 14.2"),
    "23.3": ("14.3", "macOS 14 Sonoma 14.3"),
    "23.4": ("14.4", "macOS 14 Sonoma 14.4"),
    "23.5": ("14.5", "macOS 14 Sonoma 14.5"),
    "23.6": ("14.6", "macOS 14 Sonoma 14.6"),
    "23.7": ("14.7", "macOS 14 Sonoma 14.7"),
    "23.8": ("14.8", "macOS 14 Sonoma 14.8"),
    
    # ============================================================================
    # macOS 13 Ventura - Darwin 22.x
    # ============================================================================
    "22.0": ("13.0", "macOS 13 Ventura 13.0"),
    "22.1": ("13.1", "macOS 13 Ventura 13.1"),
    "22.2": ("13.2", "macOS 13 Ventura 13.2"),
    "22.3": ("13.3", "macOS 13 Ventura 13.3"),
    "22.4": ("13.4", "macOS 13 Ventura 13.4"),
    "22.5": ("13.5", "macOS 13 Ventura 13.5"),
    "22.6": ("13.6", "macOS 13 Ventura 13.6"),
    "22.7": ("13.7", "macOS 13 Ventura 13.7"),
    
    # ============================================================================
    # macOS 12 Monterey - Darwin 21.x (Legacy support)
    # ============================================================================
    "21.0": ("12.0", "macOS 12 Monterey 12.0"),
    "21.1": ("12.1", "macOS 12 Monterey 12.1"),
    "21.2": ("12.2", "macOS 12 Monterey 12.2"),
    "21.3": ("12.3", "macOS 12 Monterey 12.3"),
    "21.4": ("12.4", "macOS 12 Monterey 12.4"),
    "21.5": ("12.5", "macOS 12 Monterey 12.5"),
    "21.6": ("12.6", "macOS 12 Monterey 12.6"),
    
    # ============================================================================
    # macOS 11 Big Sur - Darwin 20.x (Legacy support)
    # ============================================================================
    "20.0": ("11.0", "macOS 11 Big Sur 11.0"),
    "20.1": ("11.1", "macOS 11 Big Sur 11.1"),
    "20.2": ("11.2", "macOS 11 Big Sur 11.2"),
    "20.3": ("11.3", "macOS 11 Big Sur 11.3"),
    "20.4": ("11.4", "macOS 11 Big Sur 11.4"),
    "20.5": ("11.5", "macOS 11 Big Sur 11.5"),
    "20.6": ("11.6", "macOS 11 Big Sur 11.6"),
    
    # ============================================================================
    # macOS 10.15 Catalina - Darwin 19.x (Legacy support)
    # ============================================================================
    "19.0": ("10.15.0", "macOS 10.15 Catalina 10.15"),
    "19.2": ("10.15.2", "macOS 10.15 Catalina 10.15.2"),
    "19.3": ("10.15.3", "macOS 10.15 Catalina 10.15.3"),
    "19.4": ("10.15.4", "macOS 10.15 Catalina 10.15.4"),
    "19.5": ("10.15.5", "macOS 10.15 Catalina 10.15.5"),
    "19.6": ("10.15.6", "macOS 10.15 Catalina 10.15.6"),
}

# Direct macOS version → name mapping (for cases where we get "15.2" directly)
DIRECT_VERSION_LOOKUP = {
    # Tahoe (macOS 26)
    "26.0": "macOS 26 Tahoe 26.0",
    "26.1": "macOS 26 Tahoe 26.1",
    "26.2": "macOS 26 Tahoe 26.2",
    "26.3": "macOS 26 Tahoe 26.3",
    
    # Sequoia (macOS 15)
    "15.0": "macOS 15 Sequoia 15.0",
    "15.1": "macOS 15 Sequoia 15.1",
    "15.2": "macOS 15 Sequoia 15.2",
    "15.3": "macOS 15 Sequoia 15.3",
    "15.4": "macOS 15 Sequoia 15.4",
    "15.5": "macOS 15 Sequoia 15.5",
    "15.6": "macOS 15 Sequoia 15.6",
    "15.7": "macOS 15 Sequoia 15.7",
    
    # Sonoma (macOS 14)
    "14.0": "macOS 14 Sonoma 14.0",
    "14.1": "macOS 14 Sonoma 14.1",
    "14.2": "macOS 14 Sonoma 14.2",
    "14.3": "macOS 14 Sonoma 14.3",
    "14.4": "macOS 14 Sonoma 14.4",
    "14.5": "macOS 14 Sonoma 14.5",
    "14.6": "macOS 14 Sonoma 14.6",
    "14.7": "macOS 14 Sonoma 14.7",
    "14.8": "macOS 14 Sonoma 14.8",
    
    # Ventura (macOS 13)
    "13.0": "macOS 13 Ventura 13.0",
    "13.1": "macOS 13 Ventura 13.1",
    "13.2": "macOS 13 Ventura 13.2",
    "13.3": "macOS 13 Ventura 13.3",
    "13.4": "macOS 13 Ventura 13.4",
    "13.5": "macOS 13 Ventura 13.5",
    "13.6": "macOS 13 Ventura 13.6",
    "13.7": "macOS 13 Ventura 13.7",
    
    # Monterey (macOS 12)
    "12.0": "macOS 12 Monterey 12.0",
    "12.1": "macOS 12 Monterey 12.1",
    "12.2": "macOS 12 Monterey 12.2",
    "12.3": "macOS 12 Monterey 12.3",
    "12.4": "macOS 12 Monterey 12.4",
    "12.5": "macOS 12 Monterey 12.5",
    "12.6": "macOS 12 Monterey 12.6",
    "12.7": "macOS 12 Monterey 12.7",
    
    # Big Sur (macOS 11)
    "11.0": "macOS 11 Big Sur 11.0",
    "11.1": "macOS 11 Big Sur 11.1",
    "11.2": "macOS 11 Big Sur 11.2",
    "11.3": "macOS 11 Big Sur 11.3",
    "11.4": "macOS 11 Big Sur 11.4",
    "11.5": "macOS 11 Big Sur 11.5",
    "11.6": "macOS 11 Big Sur 11.6",
    "11.7": "macOS 11 Big Sur 11.7",
    
    # Catalina (macOS 10.15)
    "10.15": "macOS 10.15 Catalina 10.15",
    "10.15.0": "macOS 10.15 Catalina 10.15",
    "10.15.1": "macOS 10.15 Catalina 10.15.1",
    "10.15.2": "macOS 10.15 Catalina 10.15.2",
    "10.15.3": "macOS 10.15 Catalina 10.15.3",
    "10.15.4": "macOS 10.15 Catalina 10.15.4",
    "10.15.5": "macOS 10.15 Catalina 10.15.5",
    "10.15.6": "macOS 10.15 Catalina 10.15.6",
    "10.15.7": "macOS 10.15 Catalina 10.15.7",
}


def parse_version_string(version_str: str) -> Optional[str]:
    """
    Parse various version string formats to extract the version number.
    
    Handles:
        - "Version 24.5" → "24.5" (Darwin kernel version)
        - "15.2" → "15.2" (macOS version)
        - "macOS Sequoia 15.2" → "15.2"
        
    Args:
        version_str: Raw version string from audit
        
    Returns:
        Parsed version number or None if unparseable
        
    Examples:
        >>> parse_version_string("Version 24.2")
        '24.2'
        >>> parse_version_string("15.2")
        '15.2'
        >>> parse_version_string("macOS Sequoia 15.2")
        '15.2'
    """
    if not version_str or not isinstance(version_str, str):
        return None
    
    clean = version_str.strip()
    
    # Handle "Version X.X" format (Darwin kernel version)
    if clean.lower().startswith("version "):
        clean = clean[8:].strip()
    
    # Extract version number pattern: X.X or X.X.X
    match = re.search(r'(\d+\.\d+(?:\.\d+)?)', clean)
    if match:
        return match.group(1)
    
    return None


def get_macos_friendly_name(version_string: str) -> str:
    """
    Convert macOS version string to friendly name.
    
    Handles multiple input formats:
        - "Version 24.2" → "macOS 15 Sequoia 15.2"
        - "15.2" → "macOS 15 Sequoia 15.2"
        - "24.2" → "macOS 15 Sequoia 15.2"
        
    Args:
        version_string: Raw version from audit
        
    Returns:
        Friendly version name with marketing name
        
    Examples:
        >>> get_macos_friendly_name("Version 24.2")
        'macOS 15 Sequoia 15.2'
        >>> get_macos_friendly_name("14.6")
        'macOS 14 Sonoma 14.6'
        >>> get_macos_friendly_name("25.2")
        'macOS 26 Tahoe 26.2'
    """
    if not version_string or not isinstance(version_string, str):
        return "—"
    
    parsed = parse_version_string(version_string)
    if not parsed:
        return version_string.strip()
    
    # Try direct macOS version lookup first (e.g., "15.2")
    # Strip to major.minor for lookup
    version_parts = parsed.split('.')
    if len(version_parts) >= 2:
        major_minor = f"{version_parts[0]}.{version_parts[1]}"
        
        if major_minor in DIRECT_VERSION_LOOKUP:
            return DIRECT_VERSION_LOOKUP[major_minor]
        
        # Also try with patch version
        if parsed in DIRECT_VERSION_LOOKUP:
            return DIRECT_VERSION_LOOKUP[parsed]
    
    # Try Darwin kernel version lookup (e.g., "24.2")
    if parsed in MACOS_VERSION_LOOKUP:
        _, friendly = MACOS_VERSION_LOOKUP[parsed]
        return friendly
    
    # Graceful degradation: return original
    return version_string.strip()


def supports_apple_intelligence(version_string: str) -> bool:
    """
    Check if the macOS version supports Apple Intelligence.
    
    Apple Intelligence is available on:
    - macOS 15 Sequoia (15.1+)
    - macOS 26 Tahoe (all versions)
    
    Args:
        version_string: Raw version from audit
        
    Returns:
        True if version supports Apple Intelligence
        
    Examples:
        >>> supports_apple_intelligence("Version 24.2")
        True  # macOS 15.2 Sequoia
        >>> supports_apple_intelligence("14.6")
        False  # macOS 14 Sonoma
    """
    parsed = parse_version_string(version_string)
    if not parsed:
        return False
    
    try:
        parts = parsed.split('.')
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
        
        # macOS 26 Tahoe (all versions)
        if major >= 26:
            return True
        
        # macOS 15 Sequoia (15.1+)
        if major == 15 and minor >= 1:
            return True
        
        # Darwin 25.x (macOS 26 Tahoe)
        if major == 25:
            return True
            
        # Darwin 24.x (macOS 15 Sequoia) - need to check minor version
        # Darwin 24.1+ = macOS 15.1+
        if major == 24 and minor >= 1:
            return True
            
        return False
    except (ValueError, IndexError):
        return False


def get_macos_generation(version_string: str) -> str:
    """
    Get the macOS generation/name only.
    
    Args:
        version_string: Raw version from audit
        
    Returns:
        Generation name (e.g., "Tahoe", "Sequoia", "Sonoma")
        
    Examples:
        >>> get_macos_generation("Version 24.2")
        'Sequoia'
        >>> get_macos_generation("25.2")
        'Tahoe'
    """
    friendly = get_macos_friendly_name(version_string)
    
    if "Tahoe" in friendly:
        return "Tahoe"
    elif "Sequoia" in friendly:
        return "Sequoia"
    elif "Sonoma" in friendly:
        return "Sonoma"
    elif "Ventura" in friendly:
        return "Ventura"
    elif "Monterey" in friendly:
        return "Monterey"
    elif "Big Sur" in friendly:
        return "Big Sur"
    elif "Catalina" in friendly:
        return "Catalina"
    else:
        return "Unknown"