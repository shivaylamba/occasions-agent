# Occasions: your family's shopping agent, with receipts

Each family member has their own agent. It watches the family calendar, and days before an
occasion (a birthday, a dinner party, a trip) it finds the right thing, fact-checks every seller
claim against trusted context, buys it within that person's mandate, and shows its receipts:
what it knew, what it checked, and what it did.

Family members share one memory layer (private facts stay private) and can reach it from the
agent they already use (Claude, ChatGPT, ...) over MCP.

## What it does (demo)

1. **Set up once:** each member signs a mandate (gift $75, groceries $150, ...) and verifies with Persona.
2. **The calendar fires** ("Mom's birthday in 7 days"). Nobody asks the agent anything.
3. **It recalls** what the family knows about Mom: loves pottery, has gloves, allergic to wool.
4. **It checks 8 listings**, and rejects:
   - a garden set whose "arrives in 2 days" is contradicted by the shipping policy (9 days);
   - a wool kneeling pad, because of the allergy;
   - a glaze kit whose review contains a prompt injection;
   - gloves she already owns;
   - a "Genuine ClayCraft" set from an unauthorized seller;
   - a $140 wheel, which is over the limit.
5. **It buys** the pottery tool set through a signed Personal Agent Protocol (Poppy) request,
   and claims the occasion so Dad's agent won't buy a second gift.
6. **Dad's own Claude**, connected over MCP, sees that Mom's gift is handled and orders flowers.
   It never sees Shivay's private "surprise trip" fact.

## Sponsors

| Sponsor | Role |
|---|---|
| Senso | Trusted context: verified product facts and policies; every seller claim gets a supported, contradicted or unsupported verdict (`app/senso.py`) |
| Firedrill | Synthetic Calendar (triggers), Gmail (receipts), Stripe (checkout), and attack scenarios |
| Cognee | Per-member and household memory, with server-enforced access and an access log (`app/memory.py`) |
| SingleStore | Catalog, orders, claims, trail (`app/db.py`, SQLite fallback) |
| Superlinked SIE / Arcee | Small models read listings; a larger model decides (`app/models.py`) |
| Persona + Poppy | A verified human behind every mandate; signed agent requests to the store (`app/persona.py`, `app/store.py`) |
| Statsig / Amplitude | Agent settings as config; agent event funnel (`app/telemetry.py`) |
| Tokens& | `tests/test_agent.py`: the rules the agent must never break |

Each integration runs a local stand-in until its key is in `.env`. The UI shows which ones are live.

## Run

```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
./run.sh                 # web :8700, MCP :8701
.venv/bin/python -m pytest -q tests
```

Connect a member's own agent over MCP: `http://<host>:8701/mcp` with header
`Authorization: Bearer <that member's token from MEMBER_TOKENS in .env>`.

### `.env` keys (all optional)
`SENSO_API_KEY SENSO_ORG_ID SENSO_MCP_URL FIREDRILL_API_KEY SINGLESTORE_URL COGNEE_API_KEY COGNEE_BASE_URL
SIE_API_KEY SIE_ENDPOINT LLM_BASE_URL LLM_API_KEY LLM_MODEL_SMALL LLM_MODEL_LARGE (or ARCEE_*)
PERSONA_API_KEY PERSONA_TEMPLATE_ID STATSIG_SERVER_SECRET AMPLITUDE_API_KEY STRIPE_SECRET_KEY (sk_test_ only)
DEMO_TODAY PUBLIC_BASE_URL MEMBER_TOKENS`
