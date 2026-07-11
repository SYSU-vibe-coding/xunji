# Admin Web

## Service

- Dev server: `pnpm dev` on port `5174`
- Docker service: `xunji-admin-web`, exposed by the frontend compose example on `18081`

API requests use build-time `VITE_API_BASE_URL` when set, including absolute URLs such as `http://localhost:8080/api/v1`; otherwise they use `/api/v1` through the dev/nginx proxy. Cross-origin absolute URLs must be present in backend CORS configuration.

## Scope

- identity approval
- content moderation
- report handling
- dashboard
- announcement management
