import torch
from ..utils.wan_utils import calculate_wan_frames, is_wan_compatible


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
                "round_to_wan": ("BOOLEAN", {
                    "default": False,
                    "label_on": "enabled",
                    "label_off": "disabled"
                }),
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
    
    def add_handles(self, handle_frames, images=None, audio=None, round_to_wan=False, manual_fps=0.0):
        """
        Add frame handles and audio silence
        
        Args:
            images: Input image tensor [B, H, W, C]
            handle_frames: Number of frames to add
            audio: Optional audio dict with 'waveform' and 'sample_rate'
            round_to_wan: Round total frames to WAN-compatible count
            manual_fps: Manual FPS override (0 = auto-detect)
            
        Returns:
            Tuple of (images, audio, total_frames, info_string)
        """
        # Handle image processing if provided
        images_out = None
        original_frames = 0
        actual_handles = handle_frames
        
        if images is not None and images.shape[0] > 0:
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
        else:
            # Audio-only mode
            if manual_fps <= 0:
                print("[AVHandlesAdd] Warning: Audio-only mode requires manual_fps to be set")
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
                        print(f"[AVHandlesAdd] Warning: Audio-only mode using default 30 FPS. Set manual_fps for accurate timing.")
                        fps = 30.0
                    else:
                        fps = manual_fps
                    fps_source = "manual/default"
                elif audio_duration < 0.001:
                    # Audio too short to calculate FPS
                    print(f"[AVHandlesAdd] Warning: Audio duration too short ({audio_duration:.6f}s)")
                    fps = 30.0  # Default to 30 FPS
                    fps_source = "default"
                else:
                    # Auto-detect FPS from audio/video relationship
                    fps = original_frames / audio_duration  # Frames per second
                    fps_source = "auto-detected"
                
                # Calculate silence duration to match handle frames duration
                silence_duration = actual_handles / fps  # Duration in seconds
                silence_samples = int(silence_duration * sample_rate)
                
                # Debug output
                print(f"[AVHandlesAdd] Adding {actual_handles} handle frames")
                print(f"[AVHandlesAdd] Input audio shape: {original_shape}")
                print(f"[AVHandlesAdd] Processing shape: {waveform.shape} (channels={num_channels}, samples={total_samples})")
                print(f"[AVHandlesAdd] FPS: {fps:.2f} ({fps_source})")
                if fps_source == "auto-detected":
                    print(f"[AVHandlesAdd] Auto-detected from: {original_frames} frames / {audio_duration:.3f}s")
                print(f"[AVHandlesAdd] Audio: {silence_duration:.3f}s of silence ({silence_samples} samples at {sample_rate}Hz)")
                
                # Create silence with same shape as waveform channels
                silence = torch.zeros(num_channels, silence_samples, 
                                     dtype=waveform.dtype, device=waveform.device)
                
                # Concatenate silence at beginning
                audio_waveform_out = torch.cat([silence, waveform], dim=1)
                
                # Restore original shape format
                if was_3d:
                    # Expand back to 3D [batch, channels, samples]
                    audio_waveform_out = audio_waveform_out.unsqueeze(0).repeat(batch_size, 1, 1)
                elif len(original_shape) == 1:
                    # Remove channel dimension if original was 1D
                    audio_waveform_out = audio_waveform_out.squeeze(0)
                
                print(f"[AVHandlesAdd] Output audio shape: {audio_waveform_out.shape}")
                
                audio_out = {
                    "waveform": audio_waveform_out,
                    "sample_rate": sample_rate
                }
            except Exception as e:
                print(f"Warning: Could not process audio: {str(e)}")
                audio_out = audio  # Return original audio on error
        
        # Calculate final frame count
        if images_out is not None:
            final_frames = images_out.shape[0]
        else:
            # Audio-only mode: calculate virtual frame count
            final_frames = actual_handles if original_frames == 0 else original_frames + actual_handles
        
        # Build info string
        if images_out is not None:
            info_parts = [
                f"Original frames: {original_frames}",
                f"Handle frames added: {actual_handles}",
                f"Total frames: {final_frames}",
            ]
        else:
            # Audio-only mode
            info_parts = [
                f"Audio-only mode",
                f"Handle frames: {actual_handles}",
                f"FPS: {manual_fps:.2f}",
            ]
        
        if round_to_wan and images_out is not None:
            wan_status = "✓ WAN-compatible" if is_wan_compatible(final_frames) else "✗ Not WAN-compatible"
            info_parts.append(wan_status)
        
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
        
        return (images_out, audio_out, final_frames, info_string)
    
    @classmethod
    def VALIDATE_INPUTS(cls, handle_frames, **kwargs):
        """Validate node inputs"""
        if handle_frames < 0:
            return "Handle frames must be non-negative"
        
        return True
