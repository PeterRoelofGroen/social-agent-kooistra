# src/tools/state_manager.py
from typing import Optional, Dict

# In-memory storage: { "whatsapp_number": { "image": "path", "caption": "text" } }
# Does reset on restart, but should be fine for most usecases
_DRAFTS: Dict[str, dict] = {}

def save_draft(user_id: str, image_path: str, caption: str):
    """Saves or overwrites a draft for a user."""
    _DRAFTS[user_id] = {
        "image_path": image_path,
        "caption": caption
    }
    print(f"Draft saved for {user_id}")

def get_draft(user_id: str) -> Optional[dict]:
    """Retrieves the current draft."""
    return _DRAFTS.get(user_id)

def update_draft_caption(user_id: str, new_caption: str):
    """Updates just the caption of an existing draft."""
    if user_id in _DRAFTS:
        _DRAFTS[user_id]["caption"] = new_caption
        print(f"Draft updated for {user_id}")

def clear_draft(user_id: str):
    """Removes the draft after posting or cancelling."""
    if user_id in _DRAFTS:
        del _DRAFTS[user_id]
        print(f"Draft cleared for {user_id}")