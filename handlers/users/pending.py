# In-memory storage for pending forwarded messages (per user)
# Structure: {user_id: {"text": str | None, "is_forward": bool}}
pending_messages: dict = {}
