"""
Utilities for WAN (Weighted Attention Network) frame calculations
WAN-compatible frame counts follow the pattern: 4n + 1
Example: 1, 5, 9, 13, 17, 21, 25, 29, 33, 37, 41, 45...
"""

def calculate_wan_frames(target_frames):
    """
    Round to nearest WAN-compatible frame count (4n+1)
    
    Args:
        target_frames: Desired number of frames
        
    Returns:
        Nearest valid WAN frame count
    """
    if target_frames <= 1:
        return 1
    
    # Find closest n where 4n + 1 ≈ target_frames
    n = round((target_frames - 1) / 4)
    wan_frames = 4 * n + 1
    
    return max(1, wan_frames)


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
