"""
Kadi Teeri Online — Database Client Facade

Backward-compatibility entry point re-exporting the Supabase client instance
from the `db` package.
"""

from __future__ import annotations

from db import supabase

__all__ = ["supabase"]
