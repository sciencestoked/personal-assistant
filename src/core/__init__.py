"""
Core module for the personal assistant.
Contains configuration, LLM manager, and core business logic.
"""

from .config import Settings, get_settings

__all__ = ["Settings", "get_settings"]
