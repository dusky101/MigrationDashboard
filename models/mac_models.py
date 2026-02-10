"""
Mac Model Identifier Lookup Table

Converts cryptic model identifiers (e.g. Mac16,7) to friendly names.
Covers models from 2020-2025 including Intel and Apple Silicon (M1-M5).

Data sources: Apple Support, AppleDB, EveryMac, verified Feb 2026
"""

from typing import Optional

# Comprehensive Mac Model Lookup Dictionary
# Format: "ModelIdentifier": "Friendly Name"
MAC_MODEL_LOOKUP = {
    # ============================================================================
    # MacBook Air (Apple Silicon) - 2020-2025
    # ============================================================================
    # M4 (2025)
    "Mac16,12": "MacBook Air 13-inch (M4, 2025)",
    "Mac16,13": "MacBook Air 15-inch (M4, 2025)",
    
    # M3 (2024)
    "Mac15,12": "MacBook Air 13-inch (M3, 2024)",
    "Mac15,13": "MacBook Air 15-inch (M3, 2024)",
    
    # M2 (2022-2023)
    "Mac14,2": "MacBook Air 13-inch (M2, 2022)",
    "Mac14,15": "MacBook Air 15-inch (M2, 2023)",
    
    # M1 (2020)
    "MacBookAir10,1": "MacBook Air 13-inch (M1, 2020)",
    
    # ============================================================================
    # MacBook Air (Intel) - 2020
    # ============================================================================
    "MacBookAir9,1": "MacBook Air 13-inch (Retina, 2020)",
    "MacBookAir8,2": "MacBook Air 13-inch (Retina, 2019)",
    "MacBookAir8,1": "MacBook Air 13-inch (Retina, 2018)",
    
    # ============================================================================
    # MacBook Pro 13-inch (Apple Silicon) - 2020-2022
    # ============================================================================
    "MacBookPro17,1": "MacBook Pro 13-inch (M1, 2020)",
    "Mac14,7": "MacBook Pro 13-inch (M2, 2022)",
    
    # ============================================================================
    # MacBook Pro 14-inch (Apple Silicon) - 2021-2025
    # ============================================================================
    # M5 (2025)
    "Mac17,1": "MacBook Pro 14-inch (M5, Oct 2025)",
    "Mac17,3": "MacBook Pro 14-inch (M5 Pro, Oct 2025)",
    "Mac17,5": "MacBook Pro 14-inch (M5 Max, Oct 2025)",
    
    # M4 (2024)
    "Mac16,1": "MacBook Pro 14-inch (M4, Nov 2024)",
    "Mac16,6": "MacBook Pro 14-inch (M4 Pro, Nov 2024)",
    "Mac16,8": "MacBook Pro 14-inch (M4 Max, Nov 2024)",
    "Mac16,10": "MacBook Pro 14-inch (M4 Max, Nov 2024)",
    
    # M3 (2023)
    "Mac15,3": "MacBook Pro 14-inch (M3, Nov 2023)",
    "Mac15,6": "MacBook Pro 14-inch (M3 Pro, Nov 2023)",
    "Mac15,8": "MacBook Pro 14-inch (M3 Max, Nov 2023)",
    "Mac15,10": "MacBook Pro 14-inch (M3 Max, Nov 2023)",
    
    # M2 (2023)
    "Mac14,5": "MacBook Pro 14-inch (M2 Pro, 2023)",
    "Mac14,9": "MacBook Pro 14-inch (M2 Max, 2023)",
    
    # M1 (2021)
    "MacBookPro18,3": "MacBook Pro 14-inch (M1 Pro, 2021)",
    "MacBookPro18,4": "MacBook Pro 14-inch (M1 Max, 2021)",
    
    # ============================================================================
    # MacBook Pro 16-inch (Apple Silicon) - 2021-2025
    # ============================================================================
    # M5 (2025)
    "Mac17,2": "MacBook Pro 16-inch (M5 Pro, Oct 2025)",
    "Mac17,4": "MacBook Pro 16-inch (M5 Max, Oct 2025)",
    "Mac17,6": "MacBook Pro 16-inch (M5 Max, Oct 2025)",
    
    # M4 (2024)
    "Mac16,5": "MacBook Pro 16-inch (M4 Pro, Nov 2024)",
    "Mac16,7": "MacBook Pro 16-inch (M4 Max, Nov 2024)",
    "Mac16,9": "MacBook Pro 16-inch (M4 Max, Nov 2024)",
    
    # M3 (2023)
    "Mac15,7": "MacBook Pro 16-inch (M3 Pro, Nov 2023)",
    "Mac15,9": "MacBook Pro 16-inch (M3 Max, Nov 2023)",
    "Mac15,11": "MacBook Pro 16-inch (M3 Max, Nov 2023)",
    
    # M2 (2023)
    "Mac14,6": "MacBook Pro 16-inch (M2 Pro, 2023)",
    "Mac14,10": "MacBook Pro 16-inch (M2 Max, 2023)",
    
    # M1 (2021)
    "MacBookPro18,1": "MacBook Pro 16-inch (M1 Pro, 2021)",
    "MacBookPro18,2": "MacBook Pro 16-inch (M1 Max, 2021)",
    
    # ============================================================================
    # MacBook Pro (Intel) - Late Models Still in Use
    # ============================================================================
    "MacBookPro16,1": "MacBook Pro 16-inch (2019)",
    "MacBookPro16,2": "MacBook Pro 13-inch (2020)",
    "MacBookPro16,3": "MacBook Pro 13-inch (2020)",
    "MacBookPro16,4": "MacBook Pro 16-inch (2019)",
    "MacBookPro15,1": "MacBook Pro 15-inch (2018-2019)",
    "MacBookPro15,2": "MacBook Pro 13-inch (2018-2019)",
    "MacBookPro15,3": "MacBook Pro 15-inch (2019)",
    "MacBookPro15,4": "MacBook Pro 13-inch (2019)",
    
    # ============================================================================
    # Mac Studio - 2022-2025
    # ============================================================================
    # 2025 (March)
    "Mac16,14": "Mac Studio (M4 Max, 2025)",
    "Mac15,14": "Mac Studio (M3 Ultra, 2025)",
    
    # 2023
    "Mac14,13": "Mac Studio (M2 Max, 2023)",
    "Mac14,14": "Mac Studio (M2 Ultra, 2023)",
    
    # 2022
    "Mac13,1": "Mac Studio (M1 Max, 2022)",
    "Mac13,2": "Mac Studio (M1 Ultra, 2022)",
    
    # ============================================================================
    # Mac Mini - 2020-2024
    # ============================================================================
    # M4 (2024)
    "Mac16,3": "Mac mini (M4, 2024)",
    "Mac16,11": "Mac mini (M4 Pro, 2024)",
    
    # M2 (2023)
    "Mac14,3": "Mac mini (M2, 2023)",
    "Mac14,12": "Mac mini (M2 Pro, 2023)",
    
    # M1 (2020)
    "Macmini9,1": "Mac mini (M1, 2020)",
    
    # Intel (2018-2020)
    "Macmini8,1": "Mac mini (2018)",
    
    # ============================================================================
    # iMac - 2021-2024
    # ============================================================================
    # M4 (2024)
    "Mac16,2": "iMac 24-inch (M4, Two ports, 2024)",
    "Mac16,3": "iMac 24-inch (M4, Four ports, 2024)",
    
    # M3 (2023)
    "Mac15,4": "iMac 24-inch (M3, Two ports, 2023)",
    "Mac15,5": "iMac 24-inch (M3, Four ports, 2023)",
    
    # M1 (2021)
    "iMac21,1": "iMac 24-inch (M1, Two ports, 2021)",
    "iMac21,2": "iMac 24-inch (M1, Four ports, 2021)",
    
    # Intel (Late Models)
    "iMac20,1": "iMac 27-inch (Retina 5K, 2020)",
    "iMac20,2": "iMac 27-inch (Retina 5K, 2020)",
    "iMac19,1": "iMac 27-inch (Retina 5K, 2019)",
    "iMac19,2": "iMac 21.5-inch (Retina 4K, 2019)",
    
    # ============================================================================
    # Mac Pro - 2019-2023
    # ============================================================================
    "Mac14,8": "Mac Pro (2023)",
    "MacPro7,1": "Mac Pro (2019)",
    
    # ============================================================================
    # iMac Pro - 2017
    # ============================================================================
    "iMacPro1,1": "iMac Pro (2017)",
}


def get_friendly_model_name(model_identifier: str) -> str:
    """
    Convert Mac model identifier to friendly name.
    
    Args:
        model_identifier: Raw model ID (e.g., "Mac16,7", "MacBookPro18,1")
        
    Returns:
        Friendly model name or original with warning if unknown
        
    Examples:
        >>> get_friendly_model_name("Mac16,7")
        'MacBook Pro 16-inch (M4 Max, Nov 2024)'
        >>> get_friendly_model_name("Mac17,1")
        'MacBook Pro 14-inch (M5, Oct 2025)'
        >>> get_friendly_model_name("Mac15,12")
        'MacBook Air 13-inch (M3, 2024)'
        >>> get_friendly_model_name("UnknownModel")
        'UnknownModel ⚠️ (Unknown Model)'
    """
    if not model_identifier or not isinstance(model_identifier, str):
        return "—"
    
    clean_id = model_identifier.strip()
    
    if clean_id in MAC_MODEL_LOOKUP:
        return MAC_MODEL_LOOKUP[clean_id]
    
    # Graceful degradation
    return f"{clean_id} ⚠️ (Unknown Model)"


def get_model_year(model_identifier: str) -> Optional[int]:
    """
    Extract the year from a model identifier's friendly name.
    
    Args:
        model_identifier: Raw model ID
        
    Returns:
        Year as integer, or None if unknown
        
    Examples:
        >>> get_model_year("Mac16,7")
        2024
        >>> get_model_year("Mac17,1")
        2025
        >>> get_model_year("MacBookPro18,1")
        2021
    """
    friendly = get_friendly_model_name(model_identifier)
    
    if "⚠️" in friendly:
        return None
    
    # Extract year from patterns like "(2024)", "(M1, 2020)", "(Nov 2023)", "(Oct 2025)"
    import re
    match = re.search(r'\(.*?(\d{4})\)', friendly)
    if match:
        return int(match.group(1))
    
    return None


def get_model_chip(model_identifier: str) -> str:
    """
    Determine the processor type (Intel vs Apple Silicon).
    
    Args:
        model_identifier: Raw model ID
        
    Returns:
        Chip designation: "M1", "M2", "M3", "M4", "M5", "Intel", or "Unknown"
        
    Examples:
        >>> get_model_chip("Mac16,7")
        'M4'
        >>> get_model_chip("Mac17,1")
        'M5'
        >>> get_model_chip("MacBookPro18,1")
        'M1'
        >>> get_model_chip("MacBookPro16,1")
        'Intel'
    """
    friendly = get_friendly_model_name(model_identifier)
    
    if "⚠️" in friendly:
        return "Unknown"
    
    # Check for Apple Silicon generations
    if "M5" in friendly:
        return "M5"
    elif "M4" in friendly:
        return "M4"
    elif "M3" in friendly:
        return "M3"
    elif "M2" in friendly:
        return "M2"
    elif "M1" in friendly:
        return "M1"
    else:
        return "Intel"


def get_model_chip_variant(model_identifier: str) -> str:
    """
    Get the specific chip variant (e.g., "M1 Pro", "M2 Max", "M4").
    
    Args:
        model_identifier: Raw model ID
        
    Returns:
        Chip variant (e.g., "M5 Pro", "M4 Pro", "M3 Max", "M2", "Intel")
        
    Examples:
        >>> get_model_chip_variant("Mac16,7")
        'M4 Max'
        >>> get_model_chip_variant("Mac17,1")
        'M5'
        >>> get_model_chip_variant("Mac15,6")
        'M3 Pro'
    """
    friendly = get_friendly_model_name(model_identifier)
    
    if "⚠️" in friendly:
        return "Unknown"
    
    # Extract chip variant with regex
    import re
    # Match patterns like "M5 Max", "M4 Max", "M3 Pro", "M2", "M1 Ultra"
    match = re.search(r'(M[1-5](?:\s+(?:Pro|Max|Ultra))?)', friendly)
    if match:
        return match.group(1)
    
    return "Intel" if "Intel" not in friendly or any(m in friendly for m in ["M1", "M2", "M3", "M4", "M5"]) else "Intel"


def is_apple_silicon(model_identifier: str) -> bool:
    """
    Check if the model uses Apple Silicon.
    
    Args:
        model_identifier: Raw model ID
        
    Returns:
        True if Apple Silicon (M1/M2/M3/M4/M5), False otherwise
    """
    chip = get_model_chip(model_identifier)
    return chip in ("M1", "M2", "M3", "M4", "M5")


def get_model_screen_size(model_identifier: str) -> Optional[str]:
    """
    Extract screen size from model identifier.
    
    Args:
        model_identifier: Raw model ID
        
    Returns:
        Screen size (e.g., "13-inch", "16-inch", "24-inch") or None
        
    Examples:
        >>> get_model_screen_size("Mac16,7")
        '16-inch'
        >>> get_model_screen_size("Mac15,12")
        '13-inch'
    """
    friendly = get_friendly_model_name(model_identifier)
    
    if "⚠️" in friendly:
        return None
    
    import re
    match = re.search(r'(\d{2}(?:\.\d)?-inch)', friendly)
    if match:
        return match.group(1)
    
    return None

def get_model_product_name(model_identifier: str) -> str:
    """
    Extract just the product name (e.g., "MacBook Pro", "iMac", "Mac Studio").
    
    Args:
        model_identifier: Raw model ID
        
    Returns:
        Product name without size/year/chip details
        
    Examples:
        >>> get_model_product_name("Mac16,7")
        'MacBook Pro'
        >>> get_model_product_name("Mac15,12")
        'MacBook Air'
        >>> get_model_product_name("Mac16,2")
        'iMac'
    """
    friendly = get_friendly_model_name(model_identifier)
    
    if "⚠️" in friendly:
        return friendly  # Return full unknown message
    
    # Extract product name before size or chip details
    import re
    
    # Match product names
    if "MacBook Pro" in friendly:
        return "MacBook Pro"
    elif "MacBook Air" in friendly:
        return "MacBook Air"
    elif "Mac Studio" in friendly:
        return "Mac Studio"
    elif "Mac mini" in friendly:
        return "Mac mini"
    elif "Mac Pro" in friendly:
        return "Mac Pro"
    elif "iMac Pro" in friendly:
        return "iMac Pro"
    elif "iMac" in friendly:
        return "iMac"
    else:
        return friendly


def supports_apple_intelligence_hardware(model_identifier: str) -> bool:
    """
    Check if the hardware supports Apple Intelligence.
    
    Apple Intelligence requires M1 or newer Apple Silicon.
    
    Args:
        model_identifier: Raw model ID
        
    Returns:
        True if hardware supports Apple Intelligence
    """
    return is_apple_silicon(model_identifier)


def get_model_generation(model_identifier: str) -> str:
    """
    Get the Mac model generation/family.
    
    Args:
        model_identifier: Raw model ID
        
    Returns:
        Generation string (e.g., "M5 Generation", "M4 Generation", "Intel")
    """
    chip = get_model_chip(model_identifier)
    
    if chip in ("M1", "M2", "M3", "M4", "M5"):
        return f"{chip} Generation"
    elif chip == "Intel":
        return "Intel Generation"
    else:
        return "Unknown Generation"