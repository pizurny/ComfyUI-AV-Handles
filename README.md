# ComfyUI-AV-Handles

**Audio/Video handle management for ComfyUI workflows**

Add and remove stabilization frames with synchronized audio for video diffusion models.

---

## 🎯 What This Does

Video diffusion models (AnimateDiff, etc.) often need a few frames to stabilize before producing quality output. This node pack lets you:

- **Add** repeated first frames as "handles" before your sequence
- **Sync** audio silence to keep A/V perfectly aligned  
- **Trim** handles after processing to restore original length
- **Round** frame counts to WAN-compatible values (4n+1 pattern)

**Typical workflow:**
```
24 frames → Add 8 handles (32 frames) → Process → Trim 8 handles → 24 frames
```

---

## 📦 Installation

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/yourusername/ComfyUI-AV-Handles.git
# Restart ComfyUI
```

Nodes will appear under: **`video/handles`**

---

## 🔧 Nodes

### AV Handles (Add)

Adds handle frames by repeating the first frame + audio silence.

**Inputs:**
- `images` (IMAGE) - Input image batch
- `handle_frames` (INT) - Frames to add (default: 8, range: 0-100)
- `audio` (AUDIO, optional) - Audio to sync
- `round_to_wan` (BOOL) - Round to WAN-compatible count (4n+1)

**Outputs:** `images`, `audio`, `total_frames`, `info`

### AV Handles (Trim)

Removes handle frames + audio silence from beginning.

**Inputs:**
- `images` (IMAGE) - Image batch with handles
- `handle_frames` (INT) - Frames to remove (default: 8, range: 0-100)
- `audio` (AUDIO, optional) - Audio to trim

**Outputs:** `images`, `audio`, `remaining_frames`, `info`

---

## 💡 Usage Examples

### Basic Workflow
```
Load Images (24 frames)
    ↓
AV Handles Add (handle_frames: 8)
    ↓
AnimateDiff or Video Model (32 frames)
    ↓
AV Handles Trim (handle_frames: 8)
    ↓
Save Output (24 frames)
```

### With Audio Sync
```
Load Video (60 frames) + Load Audio (2.0s)
    ↓
AV Handles Add (handle_frames: 12, audio connected)
Output: 72 frames, 2.4s audio
    ↓
Process
    ↓
AV Handles Trim (handle_frames: 12, audio connected)
Output: 60 frames, 2.0s audio ✓
```

### WAN Compatibility
```
Load Images (47 frames)
    ↓
AV Handles Add (handle_frames: 8, round_to_wan: ✓)
Output: 57 frames (rounded to 4×14+1, actually added 10 handles)
    ↓
Process with WAN model
    ↓
AV Handles Trim (handle_frames: 10) ← Check info output!
Output: 47 frames
```

---

## 🔢 WAN Frame Pattern

WAN models work best with frame counts: **4n + 1**

Valid counts: `1, 5, 9, 13, 17, 21, 25, 29, 33, 37, 41, 45, 49, 53, 57, 61, 65...`

When `round_to_wan` is enabled, the node adjusts to the nearest valid count.

---

## 🔊 How Audio Sync Works

Audio silence duration is calculated proportionally:

```python
samples_per_frame = total_audio_samples / total_frames
silence_samples = handle_frames × samples_per_frame
```

**Example:**
- 60 frames, 96,000 audio samples
- Add 12 handles: 12 × 1,600 = 19,200 silence samples
- Result: 72 frames, 115,200 samples (perfect sync ✓)

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| Audio out of sync | Use same `handle_frames` in Add and Trim nodes |
| "Cannot trim X frames" error | Verify handle count matches what was added |
| Wrong output frame count | Check if WAN rounding is enabled, read `info` output |
| Audio is None | Audio is optional - expected for image-only workflows |

**Pro tip:** Always check the `info` output string - it shows exactly what happened, especially important when using WAN rounding.

---

## 🛠️ Technical Details

- **Zero dependencies** - Uses ComfyUI's PyTorch
- **Memory efficient** - Tensor operations, no quality loss
- **Device aware** - Automatic CPU/CUDA compatibility
- **Error handling** - Graceful failures with clear messages
- **Audio format** - Standard ComfyUI audio dict `{"waveform": tensor, "sample_rate": int}`

---

## 📄 License

MIT License - Free to use and modify

---

## 🤝 Contributing

Issues and pull requests welcome! This is a simple utility pack, so let's keep it minimal and focused.

---

**Made for the ComfyUI community** | v1.0.0
