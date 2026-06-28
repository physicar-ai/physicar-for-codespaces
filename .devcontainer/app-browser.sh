#!/bin/bash
# Cloudflare Quick Tunnel for GitHub Codespaces (token-gated).
#
# GitHub Codespaces port forwarding ("<name>-8000.app.github.dev") is unreliable
# and intermittently returns 404 even when the port is up. To work around this we
# expose uvicorn:8000 through a trycloudflare.com quick tunnel and write the
# resulting public URL into app.physicar (the browser-preview extension opens
# this URL as the Studio bookmark).
#
# The tunnel URL is public, so to prevent unauthorized access if it leaks we mint
# a per-session 512-bit token. The token is written to /tmp/pc-token and the
# FastAPI middleware (_TunnelTokenGate) checks it on every request. There is no
# nginx, so no reload is needed.
#
# Managed by supervisord (codespace-only). Each (re)start mints a fresh URL/token
# and rewrites the bookmark, so a dropped tunnel self-heals. If a freshly-minted
# tunnel does not become reachable in time, it is discarded and a new one is
# minted (re-tunneling) rather than falling back to the flaky github.dev URL.
set -uo pipefail

APP_FILE="$HOME/physicar_ws/app.physicar"
LOG="/tmp/cloudflared.log"
TOKEN_FILE="/tmp/pc-token"
PORT=8000

# Codespaces only — no-op elsewhere.
[ -z "${CODESPACE_NAME:-}" ] && exit 0

# Write $1 into the (immutable) bookmark file.
write_bookmark() {
  sudo chattr -i "$APP_FILE" 2>/dev/null || true
  chmod u+w "$APP_FILE" 2>/dev/null || true
  printf '%s\n' "$1" > "$APP_FILE"
  chmod 444 "$APP_FILE" 2>/dev/null || true
  sudo chattr +i "$APP_FILE" 2>/dev/null || true
}

# Set the gate token. The middleware reads this file. Empty token -> empty file
# -> tunnel traffic is denied (non-tunnel hosts always bypass the gate).
set_gate_token() {
  local tok="$1"
  printf '%s' "$tok" > "$TOKEN_FILE"
}

# Wait until the tunnel URL is actually reachable from the public internet, up to
# $2 seconds (default 120). A freshly-minted quick-tunnel hostname is printed to
# the log BEFORE its DNS has propagated / the edge route is live. If we publish
# the bookmark immediately the Simple Browser auto-opens it, hits NXDOMAIN, and
# negative-caches the failure so the URL keeps failing there even after it goes
# live. We poll until cloudflared's edge returns ANY HTTP status (even 502
# app-not-up or 403 gate) -- a non-000 code means DNS resolved and the edge is
# routing, so the browser will succeed.
wait_reachable() {
  local url="$1" code
  local deadline=$(( $(date +%s) + ${2:-120} ))
  while [ "$(date +%s)" -lt "$deadline" ]; do
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "${url}/" 2>/dev/null)
    [ -n "$code" ] && [ "$code" != "000" ] && return 0
    sleep 2
  done
  return 1
}

# (Re)start cloudflared, killing any previous instance first.
#
# --protocol http2 (TCP) instead of the default quic (UDP). In Codespaces the QUIC
# data path is unreliable: cloudflared registers the connection and the URL is
# minted, but the public hostname stays unreachable (curl returns 000 / "refused to
# connect" in the browser) -- the UDP egress is throttled/dropped. This made
# wait_reachable below fail for 120s on every tunnel and re-tunnel forever, leaving
# app.physicar empty. Forcing HTTP/2 (TCP) makes the quick tunnel reachable within
# seconds. (The "failed to increase receive buffer size" QUIC warning in the log is
# harmless and unrelated.)
start_tunnel() {
  [ -n "${CF_PID:-}" ] && kill "$CF_PID" 2>/dev/null
  : > "$LOG"
  cloudflared tunnel --url "http://localhost:${PORT}" --no-autoupdate --protocol http2 > "$LOG" 2>&1 &
  CF_PID=$!
}

# Propagate stop signals to whatever tunnel is currently running.
trap 'kill "$CF_PID" 2>/dev/null' TERM INT

# Mint one session token up-front (it is independent of the tunnel hostname, so it
# survives re-tunneling below).
TOKEN="$(openssl rand -hex 64)"

# 1) Seed an empty bookmark first so a stale trycloudflare URL from a previous
#    run never lingers while the new tunnel is coming up.
write_bookmark ""
set_gate_token ""

# 2) Keep (re)tunneling until we have a URL that is actually reachable. A fresh
#    quick-tunnel hostname can take a while to propagate; rather than fall back to
#    the flaky github.dev URL, we give each tunnel up to ~120s to become reachable
#    and otherwise discard it and mint a new one. trycloudflare is reliable, so
#    this normally succeeds on the first round.
# -a: treat the log as text. Once Studio opens its SSE streams through the tunnel,
# cloudflared's log can pick up non-UTF8 bytes; without -a grep prints "Binary
# file matches" instead of the URL and extraction silently fails.
# The host is matched as multi-label (>=2 hyphen-joined words) so cloudflared's
# control endpoint api.trycloudflare.com is never mistaken for the tunnel URL.
while true; do
  start_tunnel

  # Wait for cloudflared to print the public URL (up to ~30s).
  URL=""
  for _ in $(seq 1 30); do
    URL=$(grep -aoE 'https://[a-z0-9]+(-[a-z0-9]+)+\.trycloudflare\.com' "$LOG" | head -1)
    [ -n "$URL" ] && break
    kill -0 "$CF_PID" 2>/dev/null || break
    sleep 1
  done
  if [ -z "$URL" ]; then
    echo "[app-browser] no tunnel URL after 30s; re-tunneling" >&2
    continue
  fi

  # Publish only once the edge actually answers, so the browser never
  # negative-caches an NXDOMAIN for the not-yet-propagated hostname.
  if wait_reachable "$URL" 120; then
    set_gate_token "$TOKEN"
    write_bookmark "${URL}/?token=${TOKEN}"
    echo "[app-browser] public URL: ${URL}/ (token-gated)"
    break
  fi
  echo "[app-browser] ${URL} not reachable after 120s; re-tunneling" >&2
done

# 3) Stay tied to the tunnel so supervisord can supervise/restart it.
wait "$CF_PID"

# 5) Stay tied to the tunnel so supervisord can supervise/restart it.
wait "$CF_PID"
