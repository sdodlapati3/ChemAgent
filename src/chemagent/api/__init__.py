"""
FastAPI web service for ChemAgent.

This module provides a REST API interface for ChemAgent, enabling
programmatic access to pharmaceutical research capabilities.
"""

from chemagent.api.server import app, get_chemagent

__all__ = ["app", "get_chemagent"]
