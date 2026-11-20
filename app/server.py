"""HTTP API + web app + Poppy store + background trigger loop.

Run: uvicorn app.server:app --host 0.0.0.0 --port 8700
"""
import asyncio
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from . import agent, chat, memory, persona, store, telemetry
from .config import TODAY, integrations
from .db import db
from .seed import MEMBERS

app = FastAPI(title="Occasions")
WEB = Path(__file__).resolve().parent.parent / "web"
SCAN_EVERY = int(os.environ.get("SCAN_EVERY_SECONDS", "0"))  # 0 = only on demand (demo control)


def _member(m):
    if m not in MEMBERS:
        raise HTTPException(404, "unknown member")
    return m


@app.on_event("startup")
async def startup():
    if not db.list("memory"):
        agent.reset()
    if SCAN_EVERY > 0:
        async def loop():
            while True:
                await asyncio.to_thread(agent.scan_calendar)
                await asyncio.sleep(SCAN_EVERY)
        asyncio.create_task(loop())


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


@app.get("/api/state")
def state(member: str = "shivay"):
    _member(member)
    return {"today": TODAY.isoformat(), "member": member, "members": MEMBERS,
            "verified": persona.status(member), "occasions": agent.list_occasions(),
            "integrations": integrations(), "settings": telemetry.settings(member)}


@app.post("/api/scan")
def scan():
    """The Firedrill calendar tick. Runs on a timer when SCAN_EVERY_SECONDS > 0."""
    return {"ran": agent.scan_calendar(), "occasions": agent.list_occasions()}


@app.post("/api/occasions/{oid}/run")
def run_now(oid: str, member: str = "shivay"):
    if not agent.get_occasion(oid):
        raise HTTPException(404)
    return agent.run(oid, _member(member), trigger=f"run now by {member}")


@app.post("/api/occasions/{oid}/approve")
def approve(oid: str, member: str = "shivay"):
    return agent.approve(oid, _member(member))


@app.get("/api/occasions/{oid}")
def occasion(oid: str, member: str = "shivay"):
    o = agent.get_occasion(oid)
    if not o:
        raise HTTPException(404)
    # Receipts never leak another member's private facts to whoever is viewing.
    o["knew"] = [k for k in o.get("knew", []) if memory.can_read(_member(member), k["dataset"])]
    return o


@app.post("/api/verify")
def verify(member: str = "shivay"):
    return persona.start(_member(member))


@app.get("/api/memory")
def mem(member: str = "shivay"):
    v = memory.visible_to(_member(member))
    v["access_log"] = [a for a in memory.access_log()][-30:]
    return v


@app.post("/api/chat")
async def post_chat(req: Request, member: str = "shivay"):
    body = await req.json()
    return {"reply": chat.handle(_member(member), body.get("text", "")), "history": chat.history(member)}


@app.get("/api/chat")
def get_chat(member: str = "shivay"):
    return chat.history(_member(member))


@app.get("/api/events")
def events():
    return telemetry.recent_events()


@app.post("/api/reset")
def reset():
    agent.reset()
    return {"ok": True}


# ---- Demo Market (Poppy) ----
@app.get("/.well-known/poppy.json")
def poppy():
    return store.discovery()


@app.get("/store/catalog")
def store_catalog(slot: str | None = None):
    return [{k: v for k, v in c.items() if k != "claims"} | {"claims": [x["text"] for x in c["claims"]]}
            for c in store.catalog(slot)]


@app.post("/store/orders")
async def store_order(req: Request):
    body = await req.json()
    res = store.place_order({k: req.headers.get(k, "") for k in
                             ("Poppy-Session", "Poppy-User", "Poppy-Speaker", "Poppy-Signature")}, body)
    return JSONResponse(res, status_code=200 if res.get("ok") else 401)
