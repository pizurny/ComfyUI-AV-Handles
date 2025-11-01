import torch
from ..utils.wan_utils import is_wan_compatible


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
                "handle_frames": ("INT", {
                    "default": 8,
                    "min": 0,
                    "max": 100,
                    "step": 1,
                    "display": "number"
                }),
            },
            "optional": {
                "images": ("IMAGE",),
                "audio": ("AUDIO",),
                "manual_fps": ("FLOAT", {
                    "default": 0.0,
                    "min": 0.0,
                    "max": 120.0,
                    "step": 0.01,
                    "display": "number",
                    "tooltip": "Manual FPS override (0 = auto-detect from video/audio)"
                }),
            }
        }
    
    def trim_handles(self, handle_frames, images=None, audio=None, manual_fps=0.0):
        """
        Remove frame handles and audio silence
        
        Args:
            images: Input image tensor [B, H, W, C]
            handle_frames: Number of frames to remove from beginning
            audio: Optional audio dict with 'waveform' and 'sample_rate'
            manual_fps: Manual FPS override (0 = auto-detect)
            
        Returns:
            Tuple of (images, audio, remaining_frames, info_string)
        """
        # Handle image processing if provided
        images_out = None
        original_frames = 0
        remaining_frames = 0
        
        if images is not None and images.shape[0] > 0:
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
        else:
            # Audio-only mode
            if manual_fps <= 0:
                print("[AVHandlesTrim] Warning: Audio-only mode requires manual_fps to be set")
                manual_fps = 30.0  # Default fallback
        
        # Process audio if provided
        audio_out = None
        if audio is not None:
            try:
                original_waveform = audio["waveform"]
                sample_rate = audio["sample_rate"]
                
                # Store original shape to restore later
                original_shape = original_waveform.shape
                waveform = original_waveform
                
                # Handle both 2D and 3D tensor shapes for processing
                was_3d = False
                if len(waveform.shape) == 3:
                    # Shape: [batch, channels, samples] - take first batch
                    was_3d = True
                    batch_size = waveform.shape[0]
                    waveform = waveform[0]
                elif len(waveform.shape) == 1:
                    # Shape: [samples] - add channel dimension
                    waveform = waveform.unsqueeze(0)
                # Now waveform should be [channels, samples]
                
                num_channels = waveform.shape[0]
                total_samples = waveform.shape[1]
                
                # Determine FPS: use manual if provided, otherwise auto-detect
                audio_duration = total_samples / sample_rate  # Duration in seconds
                
                if manual_fps > 0:
                    # Use manual FPS override
                    fps = manual_fps
                    fps_source = "manual"
                elif original_frames == 0:
                    # Audio-only mode requires manual FPS
                    if manual_fps <= 0:
                        print(f"[AVHandlesTrim] Warning: Audio-only mode using default 30 FPS. Set manual_fps for accurate timing.")
                        fps = 30.0
                    else:
                        fps = manual_fps
                    fps_source = "manual/default"
                elif audio_duration < 0.001:
                    # Audio too short to calculate FPS
                    print(f"[AVHandlesTrim] Warning: Audio duration too short ({audio_duration:.6f}s)")
                    fps = 30.0  # Default to 30 FPS
                    fps_source = "default"
                else:
                    # Auto-detect FPS from audio/video relationship
                    fps = original_frames / audio_duration  # Frames per second
                    fps_source = "auto-detected"
                
                # Calculate samples to trim based on handle frames duration
                trim_duration = handle_frames / fps  # Duration in seconds
                trim_samples = int(trim_duration * sample_rate)
                
                # Debug output
                print(f"[AVHandlesTrim] Trimming {handle_frames} handle frames")
                print(f"[AVHandlesTrim] Input audio shape: {original_shape}")
                print(f"[AVHandlesTrim] Processing shape: {waveform.shape} (channels={num_channels}, samples={total_samples})")
                print(f"[AVHandlesTrim] FPS: {fps:.2f} ({fps_source})")
                if fps_source == "auto-detected":
                    print(f"[AVHandlesTrim] Auto-detected from: {original_frames} frames / {audio_duration:.3f}s")
                print(f"[AVHandlesTrim] Audio: trimming {trim_duration:.3f}s ({trim_samples} samples at {sample_rate}Hz)")
                
                # Trim audio from beginning
                audio_waveform_out = waveform[:, trim_samples:]
                
                # Restore original shape format
                if was_3d:
                    # Expand back to 3D [batch, channels, samples]
                    audio_waveform_out = audio_waveform_out.unsqueeze(0).repeat(batch_size, 1, 1)
                elif len(original_shape) == 1:
                    # Remove channel dimension if original was 1D
                    audio_waveform_out = audio_waveform_out.squeeze(0)
                
                print(f"[AVHandlesTrim] Output audio shape: {audio_waveform_out.shape}")
                
                audio_out = {
                    "waveform": audio_waveform_out,
                    "sample_rate": sample_rate
                }
            except Exception as e:
                print(f"Warning: Could not process audio: {str(e)}")
                audio_out = audio  # Return original audio on error
        
        # Build info string
        if images_out is not None:
            info_parts = [
                f"Original frames: {original_frames}",
                f"Frames trimmed: {handle_frames}",
                f"Remaining frames: {remaining_frames}",
            ]
            
            # Check if result is WAN-compatible
            if is_wan_compatible(remaining_frames):
                info_parts.append("✓ WAN-compatible")
        else:
            # Audio-only mode
            info_parts = [
                f"Audio-only mode",
                f"Handle frames trimmed: {handle_frames}",
                f"FPS: {manual_fps:.2f}",
            ]
        
        if audio is not None and audio_out is not None:
            orig_waveform = audio["waveform"]
            out_waveform = audio_out["waveform"]
            
            # Get the samples dimension correctly based on tensor shape
            if len(orig_waveform.shape) == 3:
                # [batch, channels, samples]
                orig_samples = orig_waveform.shape[2]
                new_samples = out_waveform.shape[2]
            elif len(orig_waveform.shape) == 2:
                # [channels, samples]
                orig_samples = orig_waveform.shape[1]
                new_samples = out_waveform.shape[1]
            else:
                # [samples]
                orig_samples = orig_waveform.shape[0]
                new_samples = out_waveform.shape[0]
            
            orig_duration = orig_samples / audio["sample_rate"]
            new_duration = new_samples / audio_out["sample_rate"]
            
            # Use more precision for short durations
            if orig_duration < 10 and new_duration < 10:
                info_parts.append(f"Audio: {orig_duration:.3f}s → {new_duration:.3f}s")
            else:
                info_parts.append(f"Audio: {orig_duration:.2f}s → {new_duration:.2f}s")
        
        info_string = " | ".join(info_parts)
        
        return (images_out, audio_out, remaining_frames, info_string)
    
    @classmethod
    def VALIDATE_INPUTS(cls, handle_frames, **kwargs):
        """Validate node inputs"""
        if handle_frames < 0:
            return "Handle frames must be non-negative"
        
        return True
