# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

context-compression-core

## Roadmap

### skeleton — FastAPI/React skeleton with install instructions and tests

Status: done

Acceptance:
- Backend FastAPI app starts and serves /health
- Frontend React+Vite+TS builds and runs
- Docker Compose starts backend, frontend, Keycloak
- README has install/run/test steps
- Backend and frontend tests pass

Implementation: `backend/app/main.py`, `backend/app/api/health.py`, `backend/app/api/compression.py`, `backend/app/api/auth.py`, `backend/app/services/compression.py`, `backend/app/services/auth.py`, `backend/app/services/database.py`, `backend/app/models/__init__.py`, `backend/app/core/config.py`, `frontend/src/App.tsx`, `frontend/src/components/SessionDashboard.tsx`, `frontend/src/components/CompressionPanel.tsx`, `frontend/src/hooks/useAuth.tsx`

Tests: `backend/tests/test_main.py`, `frontend/src/__tests__/compression.test.tsx`, `frontend/src/__tests__/auth.test.tsx`

### context-compression-core — Core context compression engine with fold/unfold

Status: done

Acceptance:
- Compress tool folds message ranges into summaries
- Decompress tool restores folded content
- Search_context finds relevant folded content
- ACP cache/status tools work
- Deterministic offline core (no LLM required)

Implementation: `backend/app/services/compression.py`, `backend/app/api/compression.py`, `backend/app/api/sessions.py`, `backend/app/models/__init__.py`, `backend/tests/test_main.py`

Tests: `backend/tests/test_main.py::TestCompression`, `frontend/src/__tests__/compression.test.tsx`

### oidc-auth — OIDC authentication with Keycloak

Status: planned

Acceptance:
- Authorization-code flow with PKCE works
- Backend validates tokens (signature/issuer/audience)
- HttpOnly SameSite cookies with CSRF protection
- Role-based access (viewer/operator/admin)
- Logout works, no hardcoded bypass in production

### trae-interception — TRAE Code native compression interception

Status: planned

Acceptance:
- Detects TraeCode auto-compact trigger requests
- Rewrites/removes native compression system prompt
- Routes through ACP compress tool
- Configurable traeCompact flag

### graceful-degrade — Graceful degradation on sustained fold-coverage loss

Status: planned

Acceptance:
- Detects mass fold-coverage loss (latch ERROR)
- Resets dead fold state or short-circuits doomed compression
- Stops compress->timeout->retry loop
- Preserves summaries, refs, tool args, signed reasoning

### fork-inheritance — DSH fork adoption with snapshot retry

Status: planned

Acceptance:
- Treats 409 SNAPSHOT_UNAVAILABLE as transient
- Retries fork adoption on parent's next request
- Fallback: inherit compressed fold blocks from parent
- Logs degraded state clearly for debugging

### cache-seam-fix — Fix cache seams on responses wire

Status: planned

Acceptance:
- Stable acp_summary placement on round-2 resends
- systemInstruction includes withSummaryBudgetNote/withConversationIdNote
- Mid-history divergence eliminated for non-fold cases
- Configurable log retention for diagnostics

### compress-dryrun — Compress dryRun preview mode

Status: planned

Acceptance:
- dryRun boolean parameter on compress tool
- Returns validation errors, excluded protected refs, estimated savings
- Zero side effects (no ref allocation, no ledger writes)
- Idempotent repeated calls

