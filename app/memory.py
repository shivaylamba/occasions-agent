"""Family memory. One private dataset per member plus a shared "household" dataset.

Access is enforced here, on the server, never by the model: a member can read only
"household" and "<member>_private". When COGNEE_API_KEY is set, facts are also written to
Cognee (one Cognee dataset per memory dataset) and recall uses Cognee search; the local copy
stays the source of truth for the permission check and the audit log.
"""
import time
import uuid

import httpx

from .config import env
from .db import db


def readable(member):
    return ["household", f"{member}_private"]


def can_read(member, dataset):
    return dataset in readable(member)


def _cognee_add(dataset, text):
    key, base = env("COGNEE_API_KEY"), env("COGNEE_BASE_URL")
    if not (key and base):
        return
    try:  # Cognee Cloud REST: add text to a dataset, then cognify. Best effort; local store is authoritative.
        h = {"Authorization": f"Bearer {key}", "X-Api-Key": key}
        httpx.post(f"{base.rstrip('/')}/api/v1/add", headers=h, timeout=10,
                   json={"datasetName": dataset, "data": [text]})
        httpx.post(f"{base.rstrip('/')}/api/v1/cognify", headers=h, timeout=10, json={"datasets": [dataset]})
    except Exception:
        pass


def remember(member, about, fact, scope="private", source="told by member"):
    dataset = "household" if scope == "household" else f"{member}_private"
    if not can_read(member, dataset):
        raise PermissionError("cannot write to that dataset")
    fid = f"m-{uuid.uuid4().hex[:8]}"
    doc = {"id": fid, "dataset": dataset, "about": about, "fact": fact, "source": source,
           "by": member, "at": time.strftime("%Y-%m-%d %H:%M")}
    db.put("memory", fid, doc, grp=dataset, seq=int(time.time() * 1000))
    _cognee_add(dataset, f"{about}: {fact} (source: {source})")
    return doc


def recall(member, about=None, purpose=""):
    """Facts this member may see, optionally about one person. Every read is logged."""
    out = []
    for ds in readable(member):
        for f in db.list("memory", grp=ds):
            if about is None or f["about"].lower() == about.lower():
                out.append(f)
    if out:
        log_access(member, about or "*", [f["id"] for f in out], purpose)
    return out


def log_access(member, about, fact_ids, purpose):
    aid = f"a-{uuid.uuid4().hex[:8]}"
    db.put("trail", aid, {"id": aid, "type": "memory_read", "member": member, "about": about,
                          "facts": fact_ids, "purpose": purpose, "at": time.strftime("%H:%M:%S")},
           grp="memory_access", seq=int(time.time() * 1000))


def access_log():
    return db.list("trail", grp="memory_access")


def visible_to(member):
    """For the memory page: what this member's agent can and cannot see (hidden facts are counted, not shown)."""
    all_facts = db.list("memory")
    mine = [f for f in all_facts if can_read(member, f["dataset"])]
    hidden = len(all_facts) - len(mine)
    return {"visible": mine, "hidden_count": hidden}
