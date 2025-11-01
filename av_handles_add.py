import torch
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.wan_utils import calculate_wan_frames, is_wan_compatible


class AVHandlesAdd:
    """
    Adds frame handles by repeating first frame and adds silence to audio.
    Useful for video diffusion models that need stabilization frames.
    """
    
    CATEGORY = "video/handles"
    RETURN_TYPES = ("IMAGE", "AUDIO", "INT", "STRING")
    RETURN_NAMES = ("images", "audio", "total_frames", "info")
    FUNCTION = "add_handles"
    
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
                "round_to_wan": ("BOOLEAN", {
                    "default": False,
                    "label_on": "enabled",
                    "label_off": "disabled"
                }),
            }
        }
    
    def add_handles(self, images, handle_frames, audio=None, round_to_wan=False):
        """
        Add frame handles and audio silence
        
        Args:
            images: Input image tensor [B, H, W, C]
            handle_frames: Number of frames to add
            audio: Optional audio dict with 'waveform' and 'sample_rate'
            round_to_wan: Round total frames to WAN-compatible count
            
        Returns:
            Tuple of (images, audio, total_frames, info_string)
        """
        # Validate inputs
        if images is None or images.shape[0] == 0:
            raise ValueError("Images tensor is empty")
        
        batch_size = images.shape[0]
        original_frames = batch_size
        
        # Calculate target frame count
        target_frames = original_frames + handle_frames
        
        # Round to WAN if requested
        if round_to_wan:
            wan_frames = calculate_wan_frames(target_frames)
            actual_handles = wan_frames - original_frames
            # Ensure we don't go negative
            if actual_handles < 0:
                wan_frames = calculate_wan_frames(original_frames)
                actual_handles = wan_frames - original_frames
        else:
            actual_handles = handle_frames
            wan_frames = target_frames
        
        # Add frame handles by repeating first frame
        if actual_handles > 0:
            first_frame = images[0:1]  # Keep dimensions [1, H, W, C]
            repeated_frames = first_frame.repeat(actual_handles, 1, 1, 1)
            images_out = torch.cat([repeated_frames, images], dim=0)
        else:
            images_out = images
        
        # Process audio if provided
        audio_out = None
        if audio is not None:
            try:
                waveform = audio["waveform"]  # Shape: [channels, samples]
                sample_rate = audio["sample_rate"]
                
                total_samples = waveform.shape[1]
                
                # Calculate silence duration proportional to frame handles
                # silence_samples = (actual_handles / original_frames) * total_samples
                samples_per_frame = total_samples / original_frames
                silence_samples = int(actual_handles * samples_per_frame)
                
                # Create silence with same number of channels
                num_channels = waveform.shape[0]
                silence = torch.zeros(num_channels, silence_samples, 
                                     dtype=waveform.dtype, device=waveform.device)
                
                # Concatenate silence at beginning
                audio_waveform_out = torch.cat([silence, waveform], dim=1)
                
                audio_out = {
                    "waveform": audio_waveform_out,
                    "sample_rate": sample_rate
                }
            except Exception as e:
                print(f"Warning: Could not process audio: {str(e)}")
                audio_out = audio  # Return original audio on error
        
        # Calculate final frame count
        final_frames = images_out.shape[0]
        
        # Build info string
        info_parts = [
            f"Original frames: {original_frames}",
            f"Handle frames added: {actual_handles}",
            f"Total frames: {final_frames}",
        ]
        
        if round_to_wan:
            wan_status = "✓ WAN-compatible" if is_wan_compatible(final_frames) else "✗ Not WAN-compatible"
            info_parts.append(wan_status)
        
        if audio is not None and audio_out is not None:
            orig_duration = audio["waveform"].shape[1] / audio["sample_rate"]
            new_duration = audio_out["waveform"].shape[1] / audio_out["sample_rate"]
            info_parts.append(f"Audio: {orig_duration:.2f}s → {new_duration:.2f}s")
        
        info_string = " | ".join(info_parts)
        
        return (images_out, audio_out, final_frames, info_string)
    
    @classmethod
    def VALIDATE_INPUTS(cls, images, handle_frames, **kwargs):
        """Validate node inputs"""
        if images is None:
            return "Images input is required"
        
        if handle_frames < 0:
            return "Handle frames must be non-negative"
        
        return True
