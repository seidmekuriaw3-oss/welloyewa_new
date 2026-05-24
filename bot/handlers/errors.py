        """
        await send_to_admin(admin_message)


def is_critical_error(error: Exception) -> bool:
    """
    Check if error is critical enough to notify admins.
    
    Args:
        error: The exception that occurred
        
    Returns:
        True if critical
    """
    critical_types = (
        ConnectionError,
        TimeoutError,
        MemoryError,
        SystemError,
    )
    
    if isinstance(error, critical_types):
        return True
    
    # Check for authentication/authorization errors
    error_str = str(error).lower()
    critical_keywords = [
        "auth", "permission", "token", "unauthorized",
        "database", "connection", "timeout",
    ]
    
    for keyword in critical_keywords:
        if keyword in error_str:
            return True
    
    return False


def get_error_file(traceback_str: str) -> str:
    """
    Extract file name from traceback.
    
    Args:
        traceback_str: Full traceback string
        
    Returns:
        File name or "Unknown"
    """
    lines = traceback_str.split("\n")
    for line in lines:
        if 'File "' in line:
            import re
            match = re.search(r'File "([^"]+)"', line)
            if match:
                return match.group(1).split("/")[-1]
    return "Unknown"


def get_error_line(traceback_str: str) -> str:
    """
    Extract line number from traceback.
    
    Args:
        traceback_str: Full traceback string
        
    Returns:
        Line number or "Unknown"
    """
    lines = traceback_str.split("\n")
    for line in lines:
        if 'line ' in line:
            import re
            match = re.search(r'line (\d+)', line)
            if match:
                return match.group(1)
    return "Unknown"


def get_first_traceback_lines(traceback_str: str, num_lines: int = 3) -> str:
    """
    Get first N lines of traceback.
    
    Args:
        traceback_str: Full traceback string
        num_lines: Number of lines to return
        
    Returns:
        First N lines of traceback
    """
    lines = traceback_str.split("\n")
    return "\n".join(lines[:num_lines])


__all__ = ["error_handler"]