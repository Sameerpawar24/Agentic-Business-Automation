from langgraph.checkpoint.memory import MemorySaver
from typing import Dict

# Module-level MemorySaver — shared across all sessions in the same process.
# For production, swap this with a PostgresSaver or RedisSaver.
_checkpointer = MemorySaver()


def get_checkpointer() -> MemorySaver:
    """Return the shared in-memory LangGraph checkpointer."""
    return _checkpointer


def build_config(session_id: str) -> Dict:
    """
    Build the LangGraph run config dict for a given session.
    The 'thread_id' key is LangGraph's way of scoping memory per conversation.
    """
    return {"configurable": {"thread_id": session_id}}
