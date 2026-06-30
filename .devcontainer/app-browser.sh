#!/bin/bash
# Cloudflare Quick Tunnel for GitHub Codespaces (token-gated).
#
# Publishes the app's reachable URLs into app.physicar (one per line), which the
# browser-preview extension opens as the Studio bookmark. The extension tries the
# lines in order and locks onto whichever actually renders.
#
# Lines are written incrementally, as each transport becomes available:
#   line 1: <name>-8000.app.github.dev   -- as soon as uvicorn:8000 is listening
#   line 2: <label>.trycloudflare.com    -- once the quick tunnel is reachable
# github.dev port-forwarding is fast but intermittently flaky, so the tunnel is
# offered as a second option; the extension picks whichever works.
#
# The tunnel URL is public, so to prevent unauthorized access if it leaks we mint
# a per-session 512-bit token, written to /tmp/pc-token; the FastAPI middleware
# (_TunnelTokenGate) checks it on trycloudflare traffic. github.dev is gated by
# GitHub's own auth, so its line carries no token.
#
# Managed by supervisord (codespace-only). Each (re)start re-publishes the
# bookmark and re-tunnels until reachable, so a dropped tunnel self-heals.
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

# Wait until uvicorn is actually listening on localhost:$PORT. curl exits 0 once
# it gets any HTTP response (even 404), non-zero while the connection is refused.
wait_port() {
  while ! curl -s -o /dev/null --max-time 2 "http://localhost:${PORT}/"; do
    sleep 1
  done
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

# 1) Clear the bookmark so a stale URL from a previous run never lingers.
write_bookmark ""
set_gate_token ""

# 2) As soon as uvicorn is listening on :8000, publish line 1 (the GitHub
#    Codespaces port-forward). It doesn't depend on the tunnel, so the extension
#    can start trying it immediately while the tunnel comes up below. No token --
#    github.dev is gated by GitHub's own auth, not _TunnelTokenGate.
GH_URL="https://${CODESPACE_NAME}-${PORT}.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}/"
wait_port
write_bookmark "$GH_URL"
echo "[app-browser] line 1 published (github.dev)"

# 3) Bring up the trycloudflare tunnel; once its hostname is actually reachable
#    from the public internet, append line 2. Keep (re)tunneling until reachable
#    rather than publishing a not-yet-live hostname (which the browser would
#    negative-cache as NXDOMAIN).
# -a: treat the log as text -- once the app's SSE streams flow through the tunnel,
# cloudflared's log can pick up non-UTF8 bytes and grep would print "Binary file
# matches" instead of the URL. The host is matched as multi-label (>=2 hyphen-
# joined words) so the control endpoint api.trycloudflare.com is never mistaken
# for the tunnel URL.
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

  if wait_reachable "$URL" 120; then
    set_gate_token "$TOKEN"
    # Line 2: trycloudflare (token-gated). The extension derives the blocked-
    # network fallback from this line, so it isn't written here.
    CF_URL="${URL}/?token=${TOKEN}"
    write_bookmark "$(printf '%s\n%s' "$GH_URL" "$CF_URL")"
    echo "[app-browser] line 2 published (trycloudflare)"
    break
  fi
  echo "[app-browser] ${URL} not reachable after 120s; re-tunneling" >&2
done

# Stay tied to the tunnel so supervisord can supervise/restart it.
wait "$CF_PID"
