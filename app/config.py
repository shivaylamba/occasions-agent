"""Settings. Every sponsor integration is optional: with no key, a local stand-in runs instead.

Keys are read from .env (chmod 600) or the environment. They are never logged or sent to the browser.
"""
import os
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_env():
    f = ROOT / ".env"
    if not f.exists():
        return
    for line in f.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env()


def env(name, default=""):
    return os.environ.get(name, default)


# Demo clock: pin "today" so the calendar triggers fire on stage. Empty = real date.
TODAY = date.fromisoformat(env("DEMO_TODAY", "2026-11-20"))

DB_PATH = Path(env("DB_PATH", str(ROOT / "data" / "occasions.db")))
STORE_SIGNING_SECRET = env("STORE_SIGNING_SECRET", "local-dev-signing-secret")
PUBLIC_BASE_URL = env("PUBLIC_BASE_URL", "http://localhost:8700")

# Main reasoning model: any OpenAI-compatible endpoint (Arcee, Nebius Token Factory, ...).
LLM_BASE_URL = env("LLM_BASE_URL") or env("ARCEE_BASE_URL")
LLM_API_KEY = env("LLM_API_KEY") or env("ARCEE_API_KEY")
LLM_MODEL_SMALL = env("LLM_MODEL_SMALL") or env("ARCEE_MODEL_SMALL")
LLM_MODEL_LARGE = env("LLM_MODEL_LARGE") or env("ARCEE_MODEL_LARGE")


def integrations():
    """Which sponsors are live vs running on the local stand-in (for the UI, no secrets)."""
    return {
        "senso": bool(env("SENSO_API_KEY")),
        "firedrill": bool(env("FIREDRILL_API_KEY")),
        "singlestore": bool(env("SINGLESTORE_URL")),
        "cognee": bool(env("COGNEE_API_KEY")),
        "sie": bool(env("SIE_API_KEY")),
        "llm (arcee/openai-compatible)": bool(LLM_API_KEY and LLM_BASE_URL),
        "persona": bool(env("PERSONA_API_KEY")),
        "statsig": bool(env("STATSIG_SERVER_SECRET")),
        "amplitude": bool(env("AMPLITUDE_API_KEY")),
        "stripe": bool(env("STRIPE_SECRET_KEY")),
    }
