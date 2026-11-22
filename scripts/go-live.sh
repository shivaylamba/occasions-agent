#!/usr/bin/env bash
# Start the app with fresh public Cloudflare tunnels. Run on the server from the app folder.
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p logs
for pid in $(pgrep -f "[c]loudflared tunnel --no-autoupdate --url http://localhost:870"); do kill "$pid"; done
for p in 8700 8701; do nohup ~/bin/cloudflared tunnel --no-autoupdate --url "http://localhost:$p" > "logs/cf-$p.log" 2>&1 & done
for i in $(seq 1 30); do
  W=$(grep -o "https://[a-z0-9-]*\.trycloudflare\.com" logs/cf-8700.log | head -1)
  M=$(grep -o "https://[a-z0-9-]*\.trycloudflare\.com" logs/cf-8701.log | head -1)
  [ -n "$W" ] && [ -n "$M" ] && break; sleep 1
done
umask 077
python3 - "$W" "$M" <<'PY'
import secrets, sys
W, M = sys.argv[1], sys.argv[2]
lines = open(".env").read().splitlines()
env = dict(l.split("=", 1) for l in lines if "=" in l and not l.startswith("#"))
toks = dict(p.split(":") for p in env.get("MEMBER_TOKENS", "").split(",") if ":" in p)
for m in ("ann", "shivay", "yash", "shane", "dad"):
    toks.setdefault(m, secrets.token_hex(16))
env["MEMBER_TOKENS"] = ",".join(f"{k}:{v}" for k, v in toks.items())
env["PUBLIC_BASE_URL"], env["PUBLIC_MCP_URL"] = W, M
open(".env", "w").write("".join(f"{k}={v}\n" for k, v in env.items()))
PY
chmod 600 .env
./run.sh | tail -2
echo "web $W"
echo "mcp $M"
