import torch
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.wan_utils import is_wan_compatible


class AVHandlesTrim:
    """
    Removes frame handles and audio silence from beginning of sequence.
    Companion node to AV Handles Add for removing stabilization frames.
    """
    
    CATEGORY = "video/handles"
    RETURN_TYPES = ("IMAGE", "AUDIO", "INT", "STRING")
    RETURN_NAMES = ("images", "audio", "remaining_frames", "info")
    FUNCTION = "trim_handles"
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "handle_frames": ("INT", {
                    "default": 8,
                    "min": 0,
                    "max": 100,
                    "step": 1,
                    "display": "number"
                }),
            },
            "optional": {
                "audio": ("AUDIO",),
            }
        }
    
    def trim_handles(self, images, handle_frames, audio=None):
        """
        Remove frame handles and audio silence
        
        Args:
            images: Input image tensor [B, H, W, C]
            handle_frames: Number of frames to remove from beginning
            audio: Optional audio dict with 'waveform' and 'sample_rate'
            
        Returns:
            Tuple of (images, audio, remaining_frames, info_string)
        """
        # Validate inputs
        if images is None or images.shape[0] == 0:
            raise ValueError("Images tensor is empty")
        
        batch_size = images.shape[0]
        original_frames = batch_size
        
        # Validate we have enough frames to trim
        if handle_frames > original_frames:
            raise ValueError(
                f"Cannot trim {handle_frames} frames from sequence of {original_frames} frames"
            )
        
        # Handle zero trim case
        if handle_frames == 0:
            info_string = f"No frames trimmed | Total frames: {original_frames}"
            return (images, audio, original_frames, info_string)
        
        # Trim frames
        images_out = images[handle_frames:]
        remaining_frames = images_out.shape[0]
        
        # Process audio if provided
        audio_out = None
        if audio is not None:
            try:
                waveform = audio["waveform"]  # Shape: [channels, samples]
                sample_rate = audio["sample_rate"]
                
                total_samples = waveform.shape[1]
                
                # Calculate samples to trim proportional to frames
                samples_per_frame = total_samples / original_frames
                trim_samples = int(handle_frames * samples_per_frame)
                
                # Trim audio from beginning
                audio_waveform_out = waveform[:, trim_samples:]
                
                audio_out = {
                    "waveform": audio_waveform_out,
                    "sample_rate": sample_rate
                }
            except Exception as e:
                print(f"Warning: Could not process audio: {str(e)}")
                audio_out = audio  # Return original audio on error
        
        # Build info string
        info_parts = [
            f"Original frames: {original_frames}",
            f"Frames trimmed: {handle_frames}",
            f"Remaining frames: {remaining_frames}",
        ]
        
        # Check if result is WAN-compatible
        if is_wan_compatible(remaining_frames):
            info_parts.append("✓ WAN-compatible")
        
        if audio is not None and audio_out is not None:
            orig_duration = audio["waveform"].shape[1] / audio["sample_rate"]
            new_duration = audio_out["waveform"].shape[1] / audio_out["sample_rate"]
            info_parts.append(f"Audio: {orig_duration:.2f}s → {new_duration:.2f}s")
        
        info_string = " | ".join(info_parts)
        
        return (images_out, audio_out, remaining_frames, info_string)
    
    @classmethod
    def VALIDATE_INPUTS(cls, images, handle_frames, **kwargs):
        """Validate node inputs"""
        if images is None:
            return "Images input is required"
        
        if handle_frames < 0:
            return "Handle frames must be non-negative"
        
        # Note: We can't check if handle_frames > batch_size here because
        # we don't have access to the actual tensor shape in validation
        
        return True
