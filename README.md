# MonadScope

**Deep analysis and real-time risk scoring for every smart contract on Monad.**

MonadScope is a full-stack contract intelligence platform built for [Monad](https://monad.xyz) (chain ID 143). It ingests blocks in near real time, automatically enriches newly deployed contracts, runs a deterministic findings + scoring engine, and surfaces the results through a polished React dashboard. An optional paid deep-analysis tier (Prime) backs verdicts with on-chain attestations via a Solidity contract.

---

## Repository layout

```
MonadScope/
├── monadscope/          # React + Vite frontend (landing page + app)
├── monad-intel/         # Python / FastAPI backend + pipeline workers
└── contracts/
    └── src/
        └── MonadScopePrime.sol   # On-chain payment & verdict attestation
```

---

## Features

### Landing page (`monadscope/`)

A marketing page with animated hero, features section, and a live-data dashboard preview. Built with React 19, Tailwind CSS v4, Framer Motion, and React Router.

### App shell & pages

| Route | Page | What it does |
|---|---|---|
| `/app` | **Contract Intelligence** | Search any Monad contract address to get its full intel card: name, kind, verification status, proxy flag, risk score, confidence, findings, Prime status, timestamps. Supports on-demand re-analysis. |
| `/app/library/recent` | **Recent Contracts** | Scrollable list of the latest contracts ingested from Monad mainnet, with risk tier and action badges. |
| `/app/library/high-risk` | **High-risk Contracts** | Contracts ranked by weighted-finding score — the ones to watch. |
| `/app/projects` | **Projects** | Look up a project group by ID to see all contracts clustered under the same deployer / protocol. |

---

### Backend pipeline (`monad-intel/`)

#### Block ingestion
- Connects to Monad via WebSocket (`newHeads` subscription — data is Voted/final, no reorg handling needed).
- Extracts transaction receipts from every block and identifies `contractAddress` fields to detect new deployments.

#### Enrichment workers
Each new contract shell goes through an enrichment queue:

| Step | What happens |
|---|---|
| **Verifier** | Checks Sourcify for verified source code; marks `source_verified`, fetches ABI. |
| **Classifier** | Labels contract kind: `ERC20`, `ERC721`, `ERC1155`, `proxy`, `multisig`, `unknown`, etc. |
| **Static features** | Extracts bytecode-level signals: `OWNER_CAN_MINT`, `BLACKLIST_FUNCTION`, `UPGRADEABLE_PROXY`, `LP_UNLOCKED`, etc. |
| **Dynamic features** | Queries on-chain state: holder count, liquidity, 1-day / 7-day transaction volume. |
| **Findings engine** | Combines static + dynamic features with the active ruleset to produce a list of `ContractFinding` records, each with a code, severity, weight, and evidence payload. |
| **Scoring engine** | Aggregates weighted findings into a `risk_score` (0–100), `confidence_score` (0–1), `risk_tier` (SAFE / CAUTION / HIGH_RISK / CRITICAL), and an `action` (ALLOW / WARN / ESCALATE / BLOCK). Hard-fail codes (e.g. `ADMIN_CAN_WITHDRAW_USER_FUNDS`, `PRIVILEGED_UNCAPPED_MINT`) pin the tier to CRITICAL regardless of score. |
| **Grouping** | Clusters contracts by deployer address and bytecode similarity into project groups. |

#### Findings ruleset (default weights)

| Code | Weight | What it detects |
|---|---|---|
| `OWNER_CAN_MINT` | 18 | Owner has uncapped mint access |
| `LP_UNLOCKED` | 15 | Liquidity pool tokens are not locked |
| `BLACKLIST_FUNCTION` | 14 | Contract can blacklist addresses |
| `TOP_HOLDER_CONCENTRATION_HIGH` | 14 | Top holders control a large share |
| `OWNER_CAN_CHANGE_FEES` | 13 | Fees can be modified by owner |
| `UPGRADEABLE_PROXY` | 12 | Contract logic can be swapped |
| `DEPLOYER_REUSED_SUSPICIOUS_BYTECODE` | 12 | Deployer has history of flagged contracts |
| `TRADING_CAN_PAUSE` | 10 | Owner can pause all transfers |
| `IMPLEMENTATION_UNVERIFIED` | 10 | Proxy implementation is not verified |
| `IMPLEMENTATION_CHANGED_RECENTLY` | 10 | Implementation address changed recently |
| `UNVERIFIED_CONTRACT` | 8 | Source code not verified on-chain |
| `OWNER_CHANGED_RECENTLY` | 8 | Ownership transferred recently |
| `MAX_WALLET_CONTROLS` | 6 | Max wallet size restrictions active |
| `MAX_TX_CONTROLS` | 5 | Per-transaction limits in place |

Hard-fail codes (auto-CRITICAL, weight 100): `ADMIN_CAN_WITHDRAW_USER_FUNDS`, `PRIVILEGED_UNCAPPED_MINT`, `BLACKLIST_PLUS_TRADING_GATE`, `HIDDEN_TRANSFER_RESTRICTIONS`, `PRIVILEGED_LIQUIDITY_EXTRACTION`.

#### Ruleset self-evolution
- Outcome tracking records user-reported labels (safe / rug / scam) per contract.
- Drift detection computes per-finding precision/recall over confirmed outcomes.
- Recalibration proposes new ruleset weight vectors as `status='proposed'` rows — they never touch production scoring automatically.
- Promoting a proposed ruleset to `active` requires an explicit admin `POST /admin/rulesets/{id}/promote`. The scoring engine is a pure function `(features, findings, ruleset) → verdict`; there is no live self-mutation path.

#### API routes (FastAPI)

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/contracts/{address}` | Full contract intel card |
| `POST` | `/contracts/{address}/analyze` | Trigger immediate re-analysis |
| `POST` | `/contracts/{address}/prime` | Commission Prime deep-analysis (auth required) |
| `GET` | `/library/recent` | Recently ingested contracts |
| `GET` | `/library/high-risk` | Top-risk contracts by weighted score |
| `GET` | `/projects/{id}` | Project group + linked contract IDs |
| `GET` | `/auth/config` | Privy app ID for frontend boot |
| `GET` | `/auth/me` | Authenticated user info |
| `POST` | `/outcomes` | Submit a user-reported outcome |
| `GET` | `/admin/rulesets` | List ruleset versions |
| `POST` | `/admin/rulesets/{id}/promote` | Promote a proposed ruleset to active |

#### Auth (Privy)
Users connect a wallet via [Privy](https://privy.io); the resulting JWT is verified backend-side against Privy's JWKS. Auth is required only for Prime purchase and outcome submission — the public case library and all contract lookups are unauthenticated.

---

### Smart contract (`contracts/src/MonadScopePrime.sol`)

`MonadScopePrime` is a Solidity contract (^0.8.24) deployed on Monad that serves two roles:

#### Pay-to-analyze
Users call `requestAnalysis(address target)` after approving `price` USDC. The contract pulls the payment and emits a `PrimePaid` event with a unique `jobId`. The backend picks up the event and queues a deep-analysis job.

#### On-chain verdict attestation
Once analysis is complete the backend attestor wallet calls `attestVerdict(target, jobId, riskScore, confidence, classification, rulesetVersion, findingsHash)`. This writes a tamper-evident `Verdict` struct on-chain (keyed by contract address) and emits `VerdictAttested`. Anyone can call `getVerdict(address)` or `hasVerdict(address)` to verify results without trusting the MonadScope backend.

#### Admin functions
- `setPrice(uint256)` — update analysis price (owner only)
- `setAttestor(address)` — rotate the attestor wallet (owner only)
- `transferOwnership(address)` — transfer contract ownership
- `withdraw(address, uint256)` — sweep collected USDC fees

The contract rejects native MON sends (`receive()` reverts) — it is USDC-only.

---

## Quick start

### Backend

```bash
cd monad-intel
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in: DATABASE_URL, REDIS_URL, MONAD_RPC_HTTP, MONAD_RPC_WS

# Seed a block range (optional, idempotent)
python scripts/bootstrap_chain.py --from-block 1000 --to-block 1200

# Live block listener
python scripts/run_listener.py

# Periodic rescan scheduler
python scripts/run_scheduler.py

# API server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd monadscope
npm install
npm run dev       # dev server at http://localhost:5173
npm run build     # production build -> dist/
```

---

## Environment variables (backend)

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | — | PostgreSQL connection string |
| `REDIS_URL` | — | Redis connection string |
| `MONAD_RPC_HTTP` | — | HTTP RPC endpoint(s), comma-separated for round-robin |
| `MONAD_RPC_WS` | — | WebSocket RPC endpoint |
| `MONAD_WS_SUBSCRIPTION` | `newHeads` | `newHeads` (Voted/final) or `monadNewHeads` (Proposed, ~1s faster) |
| `FORTYTWO_PRIME_ENABLED` | `false` | Enable Fortytwo Prime deep-analysis calls |
| `FORTYTWO_API_KEY` | — | Fortytwo bearer key (platform wallet only, never client-side) |
| `PRIME_PRICE_USD` | `6` | Per-contract deep-analysis price in USD |
| `PRIVY_APP_ID` | — | Privy application ID |
| `PRIVY_APP_SECRET` | — | Privy server secret (never sent to clients) |
| `PRIVY_REQUIRED` | `true` | Enforce Privy auth on protected routes |

---

## Tests

```bash
cd monad-intel
pytest -q
```

Uses `aiosqlite` and `fakeredis` — no Postgres or Redis required for the test suite.

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite, Tailwind CSS v4, Framer Motion, React Router v7 |
| Backend | Python 3.12, FastAPI, SQLAlchemy (async), asyncpg, aioredis |
| Blockchain | Monad (chain ID 143), WebSocket block subscription |
| Contract | Solidity ^0.8.24, USDC payment, on-chain attestation |
| Auth | Privy (wallet + email login, JWT verification) |
| Testing | pytest, aiosqlite, fakeredis |
