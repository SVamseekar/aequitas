"""Google OAuth + multi-tenant auth package — replaces the old Supabase-JWT auth.py.

During Plans 02–03, ``verify_supabase_jwt`` remains re-exported for routers not
yet migrated. Plan 04 removes those call sites and Plan 07 deletes the module.
"""

from aequitas.api.auth.supabase_jwt import verify_supabase_jwt

__all__ = ["verify_supabase_jwt"]
