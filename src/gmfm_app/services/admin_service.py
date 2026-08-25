"""Admin console data service — cloud-backed multi-user overview.

The admin console cannot be assembled from local SQLite: cloud rows are keyed
``(created_by, local_id)`` and two users can legitimately share a ``local_id``,
so pulling every user's data into one local database would collide. Instead this
service reads Supabase directly under the admin's authenticated session (RLS
``is_admin()`` returns every row) and joins the tables in Python.

Every method fails soft: when offline or unauthenticated, reads return ``None``
and writes return ``(False, message)`` so the UI can show an empty state instead
of crashing. The admin console is online-only by design.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Optional


# ── Value objects the view renders ───────────────────────────────────────────

@dataclass
class ChildInfo:
    """A student record plus its resolved relationships and session stats."""

    id: int                       # cloud students.id (BIGINT)
    created_by: str               # owner teacher's profile UUID
    local_id: int                 # the owner's local student id
    given_name: str
    family_name: str
    dob: Optional[str] = None
    identifier: Optional[str] = None
    owner_name: str = ""
    session_count: int = 0
    avg_score: Optional[float] = None
    last_assessment: Optional[str] = None
    teacher_ids: List[str] = field(default_factory=list)  # owner + edit-linked
    parent_ids: List[str] = field(default_factory=list)   # view-linked

    @property
    def full_name(self) -> str:
        name = f"{self.given_name} {self.family_name}".strip()
        return name or self.identifier or f"Student #{self.local_id}"


@dataclass
class PersonInfo:
    """A teacher or parent account plus the children connected to it."""

    id: str                       # profiles.id (UUID)
    full_name: str
    username: str
    email: str
    role: str
    children: List[ChildInfo] = field(default_factory=list)
    session_count: int = 0        # teachers only (own authored sessions)
    avg_score: Optional[float] = None
    last_assessment: Optional[str] = None

    @property
    def display_name(self) -> str:
        return self.full_name.strip() or self.username.strip() or self.email.strip() or "Unknown"


@dataclass
class AdminSnapshot:
    """The full cross-user picture, joined and ready to render."""

    teachers: List[PersonInfo]
    parents: List[PersonInfo]
    children: List[ChildInfo]
    accounts: List[dict]          # every profile row (all roles)
    profiles_by_id: dict


def _display(profile: Optional[dict]) -> str:
    if not profile:
        return "Unknown"
    return (
        (profile.get("full_name") or "").strip()
        or (profile.get("username") or "").strip()
        or (profile.get("email") or "").strip()
        or "Unknown"
    )


def _aggregate(rows: list) -> tuple:
    """(count, avg_total_score, last_created_at_iso) over a list of session dicts."""
    if not rows:
        return 0, None, None
    scores = [r.get("total_score") for r in rows if r.get("total_score") is not None]
    avg = (sum(scores) / len(scores)) if scores else None
    last = max((r.get("created_at") or "") for r in rows) or None
    return len(rows), avg, last


class AdminService:
    """Reads/writes the cloud overview under the admin's authenticated session."""

    VALID_ROLES = ("admin", "teacher", "parent", "sponsor")

    def __init__(self, sync_service):
        self.sync = sync_service

    # ── connection ───────────────────────────────────────────────────────────

    def _client(self):
        """Return an authenticated Supabase client, or None when offline/unauth."""
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

    # ── read ───────────────────────────────────────────────────────────────

    def snapshot(self) -> Optional[AdminSnapshot]:
        """Fetch profiles/students/sessions/access and join them. None if offline."""
        client = self._client()
        if not client:
            return None
        try:
            profiles = client.table("profiles").select("*").execute().data or []
            students = client.table("students").select("*").eq("deleted", False).execute().data or []
            sessions = client.table("sessions").select("*").eq("deleted", False).execute().data or []
            access = client.table("student_access").select("*").execute().data or []
        except Exception:
            return None

        profiles_by_id = {p["id"]: p for p in profiles}

        # Index students into ChildInfo objects.
        children_by_id: dict = {}
        for s in students:
            ci = ChildInfo(
                id=s["id"], created_by=s.get("created_by", ""), local_id=s.get("local_id", 0),
                given_name=s.get("given_name", "") or "", family_name=s.get("family_name", "") or "",
                dob=s.get("dob"), identifier=s.get("identifier"),
            )
            ci.owner_name = _display(profiles_by_id.get(ci.created_by))
            if ci.created_by:
                ci.teacher_ids.append(ci.created_by)  # owner is always a teacher of the child
            children_by_id[ci.id] = ci

        # Aggregate sessions by child (owner_uid, student_local_id) and by teacher.
        by_child: dict = defaultdict(list)
        by_teacher: dict = defaultdict(list)
        for ss in sessions:
            by_child[(ss.get("created_by"), ss.get("student_local_id", 0))].append(ss)
            by_teacher[ss.get("created_by")].append(ss)

        for ci in children_by_id.values():
            n, avg, last = _aggregate(by_child.get((ci.created_by, ci.local_id), []))
            ci.session_count, ci.avg_score, ci.last_assessment = n, avg, last

        # Fold in the relationship links.
        for a in access:
            ci = children_by_id.get(a.get("student_id"))
            if not ci:
                continue
            level, uid = a.get("access_level"), a.get("user_id")
            if not uid:
                continue
            if level == "view":
                if uid not in ci.parent_ids:
                    ci.parent_ids.append(uid)
            elif level in ("edit", "owner"):
                if uid not in ci.teacher_ids:
                    ci.teacher_ids.append(uid)

        children = sorted(children_by_id.values(), key=lambda c: c.full_name.lower())

        # Teachers: caseload owners; attach owned children + own-session stats.
        teachers: List[PersonInfo] = []
        for p in profiles:
            if p.get("role") != "teacher":
                continue
            ti = PersonInfo(id=p["id"], full_name=p.get("full_name", "") or "",
                            username=p.get("username", "") or "", email=p.get("email", "") or "",
                            role=p.get("role", ""))
            ti.children = [c for c in children if c.created_by == p["id"]]
            ti.session_count, ti.avg_score, ti.last_assessment = _aggregate(by_teacher.get(p["id"], []))
            teachers.append(ti)
        teachers.sort(key=lambda t: t.display_name.lower())

        # Parents / sponsors: attach the children they're linked to (view).
        parents: List[PersonInfo] = []
        for p in profiles:
            if p.get("role") not in ("parent", "sponsor"):
                continue
            pi = PersonInfo(id=p["id"], full_name=p.get("full_name", "") or "",
                            username=p.get("username", "") or "", email=p.get("email", "") or "",
                            role=p.get("role", ""))
            pi.children = [c for c in children if p["id"] in c.parent_ids]
            parents.append(pi)
        parents.sort(key=lambda p: p.display_name.lower())

        accounts = sorted(profiles, key=lambda p: (p.get("role", ""), _display(p).lower()))

        return AdminSnapshot(teachers=teachers, parents=parents, children=children,
                             accounts=accounts, profiles_by_id=profiles_by_id)

    # ── write ────────────────────────────────────────────────────────────────

    _OFFLINE = "You're offline — connect to the internet to manage assignments."

    def _insert_access(self, student_id: int, user_uid: str, level: str) -> tuple:
        client = self._client()
        if not client:
            return False, self._OFFLINE
        try:
            client.table("student_access").insert({
                "student_id": student_id,
                "user_id": user_uid,
                "access_level": level,
                "granted_by": self.sync._user_id,
            }).execute()
            return True, "Saved"
        except Exception as e:
            msg = str(e).lower()
            # UNIQUE(student_id, user_id): the pair already exists — treat as success.
            if any(k in msg for k in ("duplicate", "unique", "conflict", "23505")):
                return True, "Already assigned"
            return False, f"Failed: {str(e)[:80]}"

    def assign_parent(self, student_id: int, parent_uid: str) -> tuple:
        """Link a parent to a child (read-only 'view' access)."""
        return self._insert_access(student_id, parent_uid, "view")

    def add_coteacher(self, student_id: int, teacher_uid: str) -> tuple:
        """Link a co-teacher to a child (writable 'edit' access)."""
        return self._insert_access(student_id, teacher_uid, "edit")

    def remove_access(self, student_id: int, user_uid: str) -> tuple:
        """Unlink a parent or co-teacher from a child."""
        client = self._client()
        if not client:
            return False, self._OFFLINE
        try:
            client.table("student_access").delete().eq("student_id", student_id).eq("user_id", user_uid).execute()
            return True, "Removed"
        except Exception as e:
            return False, f"Failed: {str(e)[:80]}"

    def set_role(self, uid: str, role: str) -> tuple:
        """Promote/demote an account. Cloud trigger enforces admin-only role change."""
        if role not in self.VALID_ROLES:
            return False, "Invalid role"
        client = self._client()
        if not client:
            return False, self._OFFLINE
        try:
            client.table("profiles").update({"role": role}).eq("id", uid).execute()
            return True, "Role updated"
        except Exception as e:
            return False, f"Failed: {str(e)[:80]}"
