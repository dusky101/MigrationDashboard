"""
File Helper Utilities

Common file system operations with error handling.
"""

import os
from pathlib import Path
from typing import Optional


def ensure_directory_exists(directory_path: str) -> bool:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory_path: Path to directory
        
    Returns:
        True if directory exists or was created successfully, False otherwise
        
    Examples:
        >>> ensure_directory_exists("data/exports")
        True
    """
    try:
        os.makedirs(directory_path, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creating directory {directory_path}: {e}")
        return False


def get_file_modification_time(file_path: str) -> Optional[float]:
    """
    Get the modification time of a file.
    
    Args:
        file_path: Path to file
        
    Returns:
        Modification time as float (timestamp), or None if file doesn't exist
        
    Examples:
        >>> mtime = get_file_modification_time("data/audit.csv")
        >>> if mtime:
        ...     print(f"File modified at: {mtime}")
    """
    try:
        if os.path.exists(file_path):
            return os.path.getmtime(file_path)
        return None
    except Exception as e:
        print(f"Error getting modification time for {file_path}: {e}")
        return None


def safe_file_read(file_path: str, encoding: str = "utf-8") -> Optional[str]:
    """
    Safely read a text file with error handling.
    
    Args:
        file_path: Path to file
        encoding: File encoding (default: utf-8)
        
    Returns:
        File contents as string, or None if read fails
        
    Examples:
        >>> content = safe_file_read("config.txt")
        >>> if content:
        ...     print(content)
    """
    try:
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None


def safe_file_write(file_path: str, content: str, encoding: str = "utf-8") -> bool:
    """
    Safely write content to a text file with error handling.
    
    Args:
        file_path: Path to file
        content: Content to write
        encoding: File encoding (default: utf-8)
        
    Returns:
        True if write was successful, False otherwise
        
    Examples:
        >>> success = safe_file_write("output.txt", "Hello, World!")
        >>> if success:
        ...     print("File written successfully")
    """
    try:
        # Ensure parent directory exists
        parent_dir = os.path.dirname(file_path)
        if parent_dir:
            ensure_directory_exists(parent_dir)
        
        with open(file_path, "w", encoding=encoding) as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"Error writing file {file_path}: {e}")
        return False


def get_file_size_mb(file_path: str) -> Optional[float]:
    """
    Get the size of a file in megabytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in MB, or None if file doesn't exist
        
    Examples:
        >>> size = get_file_size_mb("large_file.csv")
        >>> if size:
        ...     print(f"File is {size:.2f} MB")
    """
    try:
        if not os.path.exists(file_path):
            return None
        
        size_bytes = os.path.getsize(file_path)
        size_mb = size_bytes / (1024 * 1024)
        return size_mb
    except Exception as e:
        print(f"Error getting file size for {file_path}: {e}")
        return None


def list_files_with_extension(directory: str, extension: str) -> list[str]:
    """
    List all files in a directory with a specific extension.
    
    Args:
        directory: Directory to search
        extension: File extension (e.g., ".csv", ".xlsx")
        
    Returns:
        List of full file paths matching the extension
        
    Examples:
        >>> csv_files = list_files_with_extension("data/", ".csv")
        >>> print(f"Found {len(csv_files)} CSV files")
    """
    try:
        if not os.path.isdir(directory):
            return []
        
        # Ensure extension starts with a dot
        if not extension.startswith("."):
            extension = f".{extension}"
        
        files = []
        for filename in os.listdir(directory):
            if filename.lower().endswith(extension.lower()):
                files.append(os.path.join(directory, filename))
        
        return sorted(files)
    except Exception as e:
        print(f"Error listing files in {directory}: {e}")
        return []


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing or replacing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for file system
        
    Examples:
        >>> safe_name = sanitize_filename("User: John/Jane <admin>")
        >>> print(safe_name)  # "User John_Jane admin"
    """
    # Replace invalid characters with underscore
    invalid_chars = '<>:"/\\|?*'
    sanitized = filename
    
    for char in invalid_chars:
        sanitized = sanitized.replace(char, "_")
    
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(". ")
    
    # Replace multiple underscores with single
    while "__" in sanitized:
        sanitized = sanitized.replace("__", "_")
    
    return sanitized if sanitized else "untitled"


def get_relative_path(file_path: str, base_path: str) -> str:
    """
    Get the relative path of a file from a base directory.
    
    Args:
        file_path: Full path to file
        base_path: Base directory path
        
    Returns:
        Relative path from base to file
        
    Examples:
        >>> rel = get_relative_path("/home/user/project/data/file.csv", "/home/user/project")
        >>> print(rel)  # "data/file.csv"
    """
    try:
        file_path_obj = Path(file_path).resolve()
        base_path_obj = Path(base_path).resolve()
        return str(file_path_obj.relative_to(base_path_obj))
    except Exception:
        # If relative path can't be computed, return the original
        return file_path


def create_backup_filename(original_path: str) -> str:
    """
    Create a backup filename by appending timestamp.
    
    Args:
        original_path: Original file path
        
    Returns:
        Backup file path with timestamp
        
    Examples:
        >>> backup = create_backup_filename("data.csv")
        >>> print(backup)  # "data_backup_20260207_143022.csv"
    """
    from datetime import datetime
    
    path = Path(original_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    backup_name = f"{path.stem}_backup_{timestamp}{path.suffix}"
    
    if path.parent:
        return str(path.parent / backup_name)
    
    return backup_name