# Phone Scanner Setup

Phase 3B adds a phone scanner flow for pairing a mobile browser with a POS station.

## Pairing Flow

1. A cashier opens a scanner session from the POS backend with `POST /api/v1/scanner/sessions`.
2. The API returns a two-minute pairing token and QR path: `/scanner?pair=TOKEN`.
3. The phone opens the QR URL and exchanges the one-time token at `POST /api/v1/scanner/pair`.
4. The phone stores the returned `scn_...` device token in session storage and sends scans with `X-Scanner-Device-Token`.

Device tokens are scoped to scanner APIs and are rejected by normal user auth endpoints.

## HTTPS Requirement

Camera APIs require HTTPS on real phones. The first scanner page is manual-entry only, but deploy it behind HTTPS now so camera scanning can be added later without changing the URL.

## Local Caddy Reverse Proxy

Example `Caddyfile` for a LAN development hostname:

```caddyfile
pos.local {
  reverse_proxy /api/* localhost:8000
  reverse_proxy /ws/* localhost:8000
  reverse_proxy localhost:5173
}
```

Then run:

```bash
caddy run --config Caddyfile
```

Trust Caddy's local CA on the phone or use a real DNS name with ACME certificates.

## Redis

WebSocket station events use in-process fan-out by default. If Redis is reachable at `REDIS_URL`, the backend also publishes station events through Redis pub/sub so multiple API workers can share scan events.

## PIN Decision

WASTE mode requires a PIN. If `users.pin_hash` is set, the scanner validates that PIN. For the current single-operator setup where no PIN seed exists yet, the operator password is accepted as the PIN.
