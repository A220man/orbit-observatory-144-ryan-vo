# Changelog

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to this project will be documented in this file.

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