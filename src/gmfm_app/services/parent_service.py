"""Parent data service — cloud-direct, read-only.

A parent never authors data and has nothing in their local SQLite. The cloud RLS
policies (``user_has_student_access`` on students, ``user_can_access_session`` on
sessions) already scope every query to exactly the children a parent is linked to
via ``student_access``, so this service simply reads Supabase under the parent's
own session and groups sessions under each linked child.

Fails soft: returns ``None`` when offline/unauthenticated so the UI shows an
empty state rather than crashing.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ParentSession:
    date: str                 # YYYY-MM-DD
    scale: str
    score: Optional[float]
    notes: str = ""


@dataclass
class ParentChild:
    given_name: str
    family_name: str
    dob: Optional[str] = None
    identifier: Optional[str] = None
    sessions: List[ParentSession] = field(default_factory=list)  # newest first

    @property
    def full_name(self) -> str:
        name = f"{self.given_name} {self.family_name}".strip()
        return name or self.identifier or "Child"

    @property
    def latest_score(self) -> Optional[float]:
        return self.sessions[0].score if self.sessions else None


class ParentService:
    """Reads a parent's linked children + their sessions directly from the cloud."""

    def __init__(self, sync_service):
        self.sync = sync_service

    def _client(self):
        """Authenticated Supabase client, or None when offline/unauthenticated."""
        if not self.sync:
            return None
        try:
            if not self.sync.ensure_auth():
                return None
            return self.sync._get_client()
        except Exception:
            return None

    def is_available(self) -> bool:
        return self._client() is not None

    def children(self) -> Optional[List[ParentChild]]:
        """Linked children with their session history. None if offline."""
        client = self._client()
        if not client:
            return None
        try:
            # RLS scopes both queries to just the children this parent may see.
            students = client.table("students").select("*").eq("deleted", False).execute().data or []
            sessions = client.table("sessions").select("*").eq("deleted", False).execute().data or []
        except Exception:
            return None

        by_child = defaultdict(list)
        for s in sessions:
            by_child[(s.get("created_by"), s.get("student_local_id", 0))].append(s)

        result: List[ParentChild] = []
        for st in students:
            ch = ParentChild(
                given_name=st.get("given_name", "") or "",
                family_name=st.get("family_name", "") or "",
                dob=st.get("dob"), identifier=st.get("identifier"),
            )
            rows = sorted(
                by_child.get((st.get("created_by"), st.get("local_id", 0)), []),
                key=lambda r: (r.get("created_at") or ""), reverse=True,
            )
            ch.sessions = [
                ParentSession(
                    date=(r.get("created_at") or "")[:10],
                    scale=r.get("scale", "88") or "88",
                    score=r.get("total_score"),
                    notes=r.get("notes") or "",
                )
                for r in rows
            ]
            result.append(ch)

        result.sort(key=lambda c: c.full_name.lower())
        return result
