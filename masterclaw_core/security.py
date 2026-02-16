"""Security utilities for MasterClaw Core

This module contains security-focused validation functions to prevent
injection attacks and other security vulnerabilities.
"""

import re
from typing import Optional

# Valid session ID pattern: alphanumeric, hyphens, underscores only (1-64 chars)
# Prevents injection attacks via session_id path parameter
VALID_SESSION_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,64}$')


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
