# Changelog

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## [Unreleased] - 2026-10-30

### Added
- Session management API endpoints (`/api/sessions`, `/api/sessions/{id}/messages`, `/api/sessions/{id}/folds`)
- Frontend CompressionPanel now fully functional with backend session/compression APIs
- Renamed database dependency `get_session` → `get_db_session` to avoid naming conflicts

### Fixed
- Parameter naming conflict in session endpoints (response model vs DB session dependency)
- All backend tests pass (12/12)
- All frontend tests pass (7/7)

### Changed
- `context-compression-core` feature marked complete in PLAN.md and feature-plan.json

## [1.0.0] - 2026-10-23

### Added
- FastAPI backend with modular structure (api, services, models, core)
- React + TypeScript + Vite frontend with dashboard and compression panel
- SQLite persistent storage with SQLAlchemy models (Session, Message, Fold, AuditLog, User)
- Core compression engine: fold, unfold, search, ACP status/cache
- Dry-run preview mode for compress tool
- OIDC authentication with Keycloak (authorization-code + PKCE)
- JWT token validation (signature, issuer, audience)
- HttpOnly SameSite cookies with CSRF protection
- Role-based access: viewer, operator, admin
- Dockerfiles for backend and frontend (non-root users)
- Docker Compose with Keycloak, persistent volumes, healthchecks
- Keycloak realm import with test users and roles
- README with install/run/test steps, architecture diagram, API reference
- MIT License with author metadata
- Backend tests (pytest with httpx)
- Frontend tests (vitest with React Testing Library)
- .github/workflows/ci.yml for CI/CD

### Security
- No hardcoded auth bypass in production
- LLM credentials server-side only
- Tokens never logged
- Demo mode explicitly labeled, refuses in production