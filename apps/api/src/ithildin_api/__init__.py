"""Ithildin API service package."""

from ithildin_api.app import create_app
from ithildin_api.config import Settings

__all__ = ["Settings", "__version__", "create_app"]

__version__ = "0.1.0"
