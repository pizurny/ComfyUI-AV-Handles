"""
Utilities for WAN (Weighted Attention Network) frame calculations
WAN-compatible frame counts follow the pattern: 4n + 1
Example: 1, 5, 9, 13, 17, 21, 25, 29, 33, 37, 41, 45...
"""
import math


def calculate_wan_frames(target_frames):
    """
    Round UP to next WAN-compatible frame count (4n+1)
    Always rounds up to ensure sufficient frames for WAN models.

    Args:
        target_frames: Desired number of frames

    Returns:
        Next valid WAN frame count (always >= target_frames)
    """
    if target_frames <= 1:
        return 1

    # Find next n where 4n + 1 >= target_frames (always round up)
    n = math.ceil((target_frames - 1) / 4)
    wan_frames = 4 * n + 1

    return max(1, wan_frames)


def calculate_next_wan_frames(current_frames):
    """
    Calculate the next WAN-compatible frame count ABOVE current_frames.
    If current_frames is already WAN-compatible, returns the same value.

    Args:
        current_frames: Current number of frames

    Returns:
        Next WAN-compatible frame count
    """
    if current_frames < 1:
        return 1

    # If already WAN-compatible, return as-is
    if is_wan_compatible(current_frames):
        return current_frames

    # Find next WAN value above current
    n = math.ceil((current_frames - 1) / 4)
    return 4 * n + 1


def get_wan_sequence(max_frames=200):
    """
    Generate list of WAN-compatible frame counts up to max_frames
    
    Args:
        max_frames: Maximum frame count to generate
        
    Returns:
        List of valid WAN frame counts
    """
    return [4 * n + 1 for n in range((max_frames - 1) // 4 + 1)]


def is_wan_compatible(frames):
    """
    Check if frame count is WAN-compatible (4n+1)
    
    Args:
        frames: Frame count to check
        
    Returns:
        True if WAN-compatible, False otherwise
    """
    if frames < 1:
        return False
    return (frames - 1) % 4 == 0
