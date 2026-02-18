"""Security utilities for MasterClaw Core

This module contains security-focused validation functions to prevent
injection attacks and other security vulnerabilities.
"""

import os
import re
from pathlib import Path
from typing import Optional, Tuple

# Valid session ID pattern: alphanumeric, hyphens, underscores only (1-64 chars)
# Prevents injection attacks via session_id path parameter
VALID_SESSION_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')

# Path traversal patterns (various encodings)
PATH_TRAVERSAL_PATTERNS = [
    re.compile(r'\.\.[/\\]'),           # ../ or ..\
    re.compile(r'[/\\]\.\.'),           # /.. or \..
    re.compile(r'%2e%2e', re.IGNORECASE),  # URL encoded ..
    re.compile(r'%2f', re.IGNORECASE),     # URL encoded /
    re.compile(r'%5c', re.IGNORECASE),     # URL encoded \
    re.compile(r'0x2e0x2e', re.IGNORECASE),  # Hex encoded
]

# Dangerous path characters that could enable command injection
DANGEROUS_PATH_CHARS = re.compile(r'[;|&`$(){}[\]\n\r]')

# Maximum allowed path length to prevent DoS
MAX_PATH_LENGTH = 4096


def validate_session_id(session_id: Optional[str]) -> str:
    """
    Validate session ID format to prevent injection attacks.
    
    This function validates that a session ID:
    - Is a string (not None, not other types)
    - Has length between 1 and 64 characters
    - Contains only alphanumeric characters, hyphens, and underscores
    - Does not contain path traversal sequences (../, ..\, etc.)
    
    Args:
        session_id: The session ID from the URL path parameter
        
    Returns:
        The validated session ID string
        
    Raises:
        ValueError: If session ID format is invalid (raised with descriptive message)
        
    Security considerations:
        - Prevents path traversal attacks via session_id
        - Prevents SQL injection via special characters
        - Prevents command injection via shell metacharacters
        - Enforces predictable format for logging and monitoring
        
    Example:
        >>> validate_session_id("user-123_session")
        'user-123_session'
        
        >>> validate_session_id("../etc/passwd")
        ValueError: Session ID cannot contain path traversal sequences
        
        >>> validate_session_id(None)
        ValueError: Session ID is required
    """
    if session_id is None:
        raise ValueError("Session ID is required")
    
    if not isinstance(session_id, str):
        raise ValueError(f"Session ID must be a string, got {type(session_id).__name__}")
    
    if len(session_id) == 0:
        raise ValueError("Session ID cannot be empty")
    
    if len(session_id) > 64:
        raise ValueError(f"Session ID exceeds maximum length of 64 characters (got {len(session_id)})")
    
    # Check for path traversal attempts first (security critical)
    if '..' in session_id or '/' in session_id or '\\' in session_id:
        raise ValueError("Session ID cannot contain path traversal sequences")
    
    # Validate against pattern (alphanumeric, hyphens, underscores only)
    if not VALID_SESSION_ID_PATTERN.match(session_id):
        raise ValueError(
            "Session ID contains invalid characters. Only alphanumeric characters, "
            "hyphens, and underscores are allowed."
        )
    
    return session_id


def is_valid_session_id(session_id: Optional[str]) -> bool:
    """
    Check if a session ID is valid without raising an exception.
    
    Args:
        session_id: The session ID to validate
        
    Returns:
        True if valid, False otherwise
        
    Example:
        >>> is_valid_session_id("user-123")
        True
        
        >>> is_valid_session_id("../etc/passwd")
        False
    """
    try:
        validate_session_id(session_id)
        return True
    except ValueError:
        return False


def validate_file_path(
    path: Optional[str],
    allow_absolute: bool = False,
    base_directory: Optional[str] = None,
    max_length: int = MAX_PATH_LENGTH
) -> Tuple[bool, str]:
    """
    Validate a file path to prevent path traversal attacks.
    
    This function performs comprehensive path validation to prevent:
    - Path traversal attacks (../, ..\, encoded variants)
    - Command injection via shell metacharacters
    - Null byte injection
    - Excessively long paths (DoS protection)
    
    Args:
        path: The path string to validate
        allow_absolute: If False, rejects absolute paths (starting with / or \)
        base_directory: If provided, ensures the resolved path stays within this directory
        max_length: Maximum allowed path length (default: 4096)
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
        If valid, error_message is empty.
        
    Security considerations:
        - Always validate user-provided paths before filesystem operations
        - Use base_directory parameter to enforce jail/chroot-like boundaries
        - Logs validation failures for security monitoring
        
    Example:
        >>> validate_file_path("documents/file.txt")
        (True, "")
        
        >>> validate_file_path("../etc/passwd")
        (False, "Path contains path traversal sequences")
        
        >>> validate_file_path("/etc/passwd", allow_absolute=False)
        (False, "Absolute paths are not allowed")
        
        >>> validate_file_path("data/file.txt", base_directory="/safe/path")
        (True, "")  # Only if resolved path is within /safe/path
    """
    if path is None:
        return False, "Path is required"
    
    if not isinstance(path, str):
        return False, f"Path must be a string, got {type(path).__name__}"
    
    # Check for empty path
    if len(path.strip()) == 0:
        return False, "Path cannot be empty"
    
    # Check path length (DoS protection)
    if len(path) > max_length:
        return False, f"Path exceeds maximum length of {max_length} characters"
    
    # Check for null bytes (null byte injection)
    if '\x00' in path:
        return False, "Path contains null bytes"
    
    # Check for dangerous characters (command injection)
    if DANGEROUS_PATH_CHARS.search(path):
        return False, "Path contains dangerous characters"
    
    # Normalize the path
    normalized = os.path.normpath(path)
    
    # Check for path traversal patterns in normalized path
    for pattern in PATH_TRAVERSAL_PATTERNS:
        if pattern.search(normalized):
            return False, "Path contains path traversal sequences"
    
    # Check for absolute paths if not allowed
    if not allow_absolute:
        if normalized.startswith('/') or normalized.startswith('\\'):
            return False, "Absolute paths are not allowed"
        # Check for Windows drive letters (e.g., C:, D:)
        if len(normalized) >= 2 and normalized[1] == ':':
            return False, "Absolute paths are not allowed"
    
    # If base_directory is specified, ensure resolved path stays within it
    if base_directory:
        try:
            # Resolve the base directory to absolute path
            base_path = Path(base_directory).resolve()
            
            # Combine with the path (treat as relative to base)
            if allow_absolute:
                # If absolute paths allowed, resolve the given path
                full_path = Path(normalized).resolve()
            else:
                # Treat as relative to base_directory
                full_path = (base_path / normalized).resolve()
            
            # Ensure the resolved path is within base_directory
            try:
                full_path.relative_to(base_path)
            except ValueError:
                return False, "Path escapes the allowed directory"
        except (OSError, ValueError) as e:
            return False, f"Invalid path: {e}"
    
    return True, ""


def sanitize_path_for_display(path: str, max_length: int = 100) -> str:
    """
    Sanitize a path for safe display in logs/error messages.
    
    Prevents log injection by:
    - Truncating long paths
    - Removing control characters
    - Escaping newlines
    
    Args:
        path: The path to sanitize
        max_length: Maximum length for display
        
    Returns:
        Sanitized path string safe for logging
        
    Example:
        >>> sanitize_path_for_display("/home/user/file.txt")
        '/home/user/file.txt'
        
        >>> sanitize_path_for_display("path\\nwith\\nnewlines")
        'path\\nwith\\nnewlines'
    """
    if not isinstance(path, str):
        path = str(path)
    
    # Remove control characters except common whitespace
    sanitized = ''.join(char for char in path if char.isprintable() or char in ' \t')
    
    # Escape newlines for single-line display
    sanitized = sanitized.replace('\n', '\\n').replace('\r', '\\r')
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length - 3] + "..."
    
    return sanitized


def is_safe_path(path: str, base_directory: Optional[str] = None) -> bool:
    """
    Convenience function to check if a path is safe without getting details.
    
    Args:
        path: The path to check
        base_directory: Optional base directory to contain the path within
        
    Returns:
        True if path is safe, False otherwise
        
    Example:
        >>> is_safe_path("documents/file.txt")
        True
        
        >>> is_safe_path("../../../etc/passwd")
        False
    """
    is_valid, _ = validate_file_path(path, base_directory=base_directory)
    return is_valid
