"""Access scoping — resolves what a logged-in user may see and do.

This is the local counterpart to the cloud RLS policies. It reads the unified
`student_access` relationship table (owner/edit/view) plus the legacy
`students.user_id` owner column and produces an :class:`AccessScope` that the
repositories consume to filter reads and gate writes.

Roles:
- ``admin``   — unrestricted local read/write (cross-user overview is cloud-backed).
- ``teacher`` — owns + co-taught children; may read and write them.
- ``parent``  — only explicitly linked children; read-only.
- ``sponsor`` — aggregate viewer; read-only, treated like parent for scoping.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Set

from gmfm_app.data.database import DatabaseContext


@dataclass
class AccessScope:
    """The resolved data-access boundary for one user."""

    user_id: Optional[int]
    # None  -> not id-restricted; combine with `unrestricted` to disambiguate:
    #   unrestricted=True  -> admin: see everything (predicate 1=1).
    #   unrestricted=False -> legacy per-user scoping via user_id.
    # set() -> restricted to exactly these local student ids (empty = nothing).
    visible_ids: Optional[Set[int]]
    can_write: bool
    is_admin: bool
    role: str
    # True only for admin: local reads are unrestricted regardless of user_id.
    unrestricted: bool = False


class AccessService:
    """Builds :class:`AccessScope` objects from the local database."""

    def __init__(self, db_context: Optional[DatabaseContext] = None):
        self.db_context = db_context or DatabaseContext()

    def visible_student_ids(self, user_id: Optional[int]) -> Set[int]:
        """Local student ids the user may see: owned ∪ linked (one query)."""
        if not user_id:
            return set()
        try:
            with self.db_context.connect() as conn:  # type: ignore[misc]
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT id FROM students WHERE user_id = ?
                    UNION
                    SELECT student_id FROM student_access WHERE user_id = ?
                    """,
                    (user_id, user_id),
                )
                return {int(r[0]) for r in cur.fetchall()}
        except Exception:
            # Fail closed: an error resolving scope must never widen access.
            return set()

    def scope_for(self, user) -> AccessScope:
        """Resolve the access scope for an authenticated user (or a guest)."""
        role = (getattr(user, "role", None) or "teacher") if user else "teacher"
        uid = int(user.id) if user and getattr(user, "id", None) else None

        if role == "admin":
            # Unrestricted locally; the multi-user overview reads Supabase directly.
            return AccessScope(user_id=uid, visible_ids=None, can_write=True,
                               is_admin=True, role=role, unrestricted=True)

        if role in ("parent", "sponsor"):
            # Read-only, restricted to explicitly linked children.
            return AccessScope(user_id=uid, visible_ids=self.visible_student_ids(uid),
                               can_write=False, is_admin=False, role=role)

        # teacher (default): owned + co-taught children, writable.
        return AccessScope(user_id=uid, visible_ids=self.visible_student_ids(uid),
                           can_write=True, is_admin=False, role=role)
