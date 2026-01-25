"""
Global checkpoint manager for workflow state persistence
Uses MemorySaver for in-memory state persistence (survives during bot runtime)
"""
import logging
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)

# Global checkpointer instance
_checkpointer = None


async def init_checkpointer():
    """
    Initialize global checkpointer with in-memory storage
    State persists during bot runtime but lost on restart
    """
    global _checkpointer

    if _checkpointer is not None:
        logger.warning("Checkpointer already initialized")
        return

    logger.info("Initializing in-memory checkpointer...")

    _checkpointer = MemorySaver()

    logger.info("✅ Checkpointer initialized successfully (in-memory)")


def get_checkpointer():
    """
    Get global checkpointer instance

    Returns:
        MemorySaver instance or None if not initialized
    """
    if _checkpointer is None:
        logger.warning("Checkpointer not initialized. Call init_checkpointer() first.")
    return _checkpointer


async def close_checkpointer():
    """
    Close checkpointer (no-op for MemorySaver)
    """
    global _checkpointer

    if _checkpointer is not None:
        _checkpointer = None
        logger.info("Checkpointer closed")
