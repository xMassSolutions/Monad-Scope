# Monad Scope

Production-grade Python backend for Monad smart-contract intelligence.

- Ingests Monad mainnet (chain id **143**) in near real time over WebSocket.
- Detects newly deployed contracts from receipts, enriches them, classifies them,
  scores risk + confidence, and groups them into projects.
- Maintains a public case library of free deterministic analysis.
- Optional paid deep-analysis layer through **Fortytwo Prime** (off by default,
  env-flag gated, OpenAI-compatible API).
- Controlled self-evolution: outcome tracking, drift detection, offline ruleset
  recalibration, versioned promotion. **No live mutation of scoring rules.**

## Quick start

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env: DATABASE_URL, REDIS_URL, MONAD_RPC_HTTP, MONAD_RPC_WS

# bootstrap a recent block range
python scripts/bootstrap_chain.py --from-block 1000 --to-block 1200

# start the live listener
python scripts/run_listener.py

# start the rescan scheduler
python scripts/run_scheduler.py

# serve the API
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Architecture overview

```
   Monad WSS ─► ws_listener ─► block queue ─► workers/blocks ─► receipts.extract
                                                                       │
                                                                       ▼
                                                              contract shell row
                                                                       │
                                                                       ▼
                                                  workers/enrichment ─► verifier
                                                                     │  classifier
                                                                     │  feature_static
                                                                     │  findings
                                                                     ▼  scoring
                                                                grouping → project
                                                                     │
                                                                     ▼
                                                         schedule next refresh
```

### Why `newHeads` not `monadNewHeads`?

Monad supports two header subscription families:

- `newHeads` / `logs` — fire when a block reaches the **Voted** phase. MonadBFT
  guarantees no reorgs at this point, so the data is final-enough for indexing
  with no rewrite logic.
- `monadNewHeads` / `monadLogs` — fire at **Proposed** (speculative; ~1 s
  sooner). Payloads include `blockId` and `commitState`.

We default to `newHeads` because it is the safe choice and requires no special
state-handling. Set `MONAD_WS_SUBSCRIPTION=monadNewHeads` to opt into faster
speculative detection.

### Prime billing safety

The endpoint `POST /contracts/{address}/prime` follows this order strictly:

1. Acquire Redis lock `prime:lock:{impl-or-contract-key}` (SET NX PX 60 s).
2. Re-query the Prime cache (impl-hash → contract-key).
3. Re-query active jobs (running / queued).
4. **Only if both miss** — confirm payment, create the job row, release the
   lock, enqueue the worker.

This means: under concurrent purchase requests for the same contract, exactly
one charge happens; later requests see `in_progress` and pay nothing.

### Self-evolution boundary

`services/scoring.py` is pure: `(features, findings, ruleset) → verdict`.
Production reads the row from `rulesets` where `status='active'`. Recalibration
writes new rows with `status='proposed'` and a metrics report. Promotion to
`active` requires an explicit admin POST. There is no path by which
production scoring mutates itself.

## Environment variables

See `.env.example` for the full list. The most important toggles:

| variable | default | meaning |
|----------|---------|---------|
| `MONAD_WS_SUBSCRIPTION` | `newHeads` | `newHeads` (Voted) or `monadNewHeads` (Proposed) |
| `FORTYTWO_PRIME_ENABLED` | `false` | enable real Fortytwo Prime calls |
| `FORTYTWO_API_KEY` | empty | Fortytwo bearer key (only used by platform wallet) |
| `PRIME_PRICE_USD` | `6` | per-contract deep-analysis price |

## User wallet auth (Privy)

The frontend uses [`@privy-io/react-auth`](https://docs.privy.io/) for wallet
connect / login. Users connect a wallet there; Privy issues an access token
(JWT, ES256) which the frontend sends as `Authorization: Bearer <token>`.
The backend verifies the JWT against Privy's JWKS and resolves the user's
linked wallets via the Privy admin API.

End users **never** sign anything for Fortytwo. The platform wallet is the
only signer in the x402 flow (see *Prime billing safety* above). Privy is
purely user-side auth for Monad Scope itself.

### Backend setup
Set in `.env`:
```
PRIVY_APP_ID=<your-privy-app-id>
PRIVY_APP_SECRET=<your-privy-app-secret>   # server-side only, never sent to clients
PRIVY_REQUIRED=true                        # enforce auth on protected routes
```
Protected routes:
- `POST /contracts/{address}/prime`
- `POST /outcomes`

Public routes the frontend calls before login:
- `GET /auth/config` → returns `{privy_app_id, ...}` so the frontend boots
  Privy without hardcoding the app id.
- `GET /auth/me` → returns `{authenticated, user_id, wallets, email}` if a
  valid token is presented; `{authenticated: false}` otherwise.

### Frontend (React) snippet
```tsx
import { PrivyProvider, usePrivy } from "@privy-io/react-auth";

// Boot config from your backend so the app id never gets hard-coded.
const { privy_app_id } = await fetch("/auth/config").then(r => r.json());

export default function App() {
  return (
    <PrivyProvider
      appId={privy_app_id}
      config={{
        loginMethods: ["wallet", "email"],
        defaultChain: { id: 143, name: "Monad" },
        supportedChains: [{ id: 143 }, { id: 8453 }],
        embeddedWallets: { createOnLogin: "off" },
      }}
    >
      <Body />
    </PrivyProvider>
  );
}

function Body() {
  const { login, logout, ready, authenticated, getAccessToken, user } = usePrivy();
  if (!ready) return null;
  if (!authenticated) return <button onClick={login}>Connect wallet</button>;

  async function buyPrime(address: string) {
    const token = await getAccessToken();
    const res = await fetch(`/contracts/${address}/prime`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ payment_receipt: "" }),  // backend stamps user id
    });
    return res.json();
  }
  // ... rest of UI
}
```

## Tests

```bash
pytest -q
```

Tests use `aiosqlite` and `fakeredis` — no Postgres or Redis required.

## Operational notes

- The free deterministic scanner is the product. Fortytwo Prime is an optional
  augmentation; the entire system runs without it.
- Public RPCs are rate-limited; for production, set `MONAD_RPC_HTTP` to your
  own endpoint(s). The RPC client supports a comma-separated list and
  round-robins on failure.
- `scripts/bootstrap_chain.py` is restart-safe and idempotent — running the
  same range twice is a no-op.
