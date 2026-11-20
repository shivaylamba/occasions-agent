"""Senso: check a seller's claims against verified facts (the trusted context).

Live mode (SENSO_API_KEY + SENSO_ORG_ID): each claim goes through Senso's fact check
(senso_check_text on the MCP server at SENSO_MCP_URL, default https://apiv2.senso.ai/mcp), and the
verdicts come back with the knowledge-base source. Local mode: the same check runs against
seed.VERIFIED_FACTS, which is exactly the content we load into the Senso knowledge base.

Returns one verdict per claim: supported | contradicted | unsupported, with the source.
"""
import json

import httpx

from .config import env
from .seed import VERIFIED_FACTS


def _local_verdict(listing, claim):
    facts = VERIFIED_FACTS.get(listing["id"], {})
    src = facts.get("source", "no verified source")
    k, v = claim["kind"], claim["value"]
    if k == "ships_in_days" and "ships_in_days" in facts:
        real = facts["ships_in_days"]
        if real <= v:
            return "supported", f"verified: ships in {real} days", src
        return "contradicted", f"verified: ships in {real} days, not {v}", src
    if k == "material" and "material" in facts:
        ok = v in facts["material"]
        return ("supported" if ok else "contradicted"), f"verified materials: {', '.join(facts['material'])}", src
    if k == "authentic_brand" and "authentic_brand_sellers" in facts:
        sellers = facts["authentic_brand_sellers"].get(v, [])
        if listing["seller"] in sellers:
            return "supported", f"{listing['seller']} is an authorized {v} seller", src
        return "contradicted", f"{listing['seller']} is not an authorized {v} seller", src
    if k == "warranty_years" and "warranty_years" in facts:
        real = facts["warranty_years"]
        if v <= real:
            return "supported", f"warranty is {real} year(s)", src
        return "contradicted", f"warranty is {real} year(s), not {v}", src
    if k == "serves" and "serves" in facts:
        real = facts["serves"]
        return ("supported" if real >= v else "contradicted"), f"label says serves {real}", src
    if k == "diet" and "diet" in facts:
        ok = v in facts["diet"]
        extra = f" (contains {', '.join(facts.get('contains', []))})" if facts.get("contains") else ""
        return ("supported" if ok else "contradicted"), f"label diet: {', '.join(facts['diet']) or 'none'}{extra}", src
    return "unsupported", "no verified fact covers this claim", src


def _live_check(text):
    """Call Senso's MCP server (JSON-RPC over streamable HTTP). Returns the raw tool result or None."""
    key, org = env("SENSO_API_KEY"), env("SENSO_ORG_ID")
    url = env("SENSO_MCP_URL", "https://apiv2.senso.ai/mcp")
    if not (key and org):
        return None
    try:
        r = httpx.post(url, timeout=20, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                                                 "Accept": "application/json, text/event-stream"},
                       json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                             "params": {"name": "senso_check_text", "arguments": {"org_id": org, "text": text}}})
        return r.text if r.status_code == 200 else None
    except Exception:
        return None


def check_listing(listing):
    verdicts = []
    for c in listing.get("claims", []):
        status, why, src = _local_verdict(listing, c)
        live = _live_check(f"{listing['title']} sold by {listing['seller']}: {c['text']}")
        verdicts.append({"claim": c["text"], "verdict": status, "why": why, "source": src,
                         "engine": "senso" if live else "senso-local"})
    return verdicts


def kb_documents():
    """The verified facts as markdown docs, ready to load into Senso (senso_create_doc)."""
    return [{"title": f"Verified facts: {lid}", "text": json.dumps(f, indent=1)} for lid, f in VERIFIED_FACTS.items()]
