from .nodes.av_handles_add import AVHandlesAdd
from .nodes.av_handles_trim import AVHandlesTrim

NODE_CLASS_MAPPINGS = {
    "AVHandlesAdd": AVHandlesAdd,
    "AVHandlesTrim": AVHandlesTrim,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AVHandlesAdd": "AV Handles (Add)",
    "AVHandlesTrim": "AV Handles (Trim)",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
