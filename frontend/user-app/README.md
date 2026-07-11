# User App

Vue 3 + Vite + Pinia mobile-first web client. Opened directly in mobile or desktop browsers, no mini-program packaging.

## Service

- Dev server: `pnpm dev` on port `5173`
- Docker service: `xunji-user-web`, exposed by the frontend compose example on `18080`

API requests use build-time `VITE_API_BASE_URL` when set, including absolute URLs such as `http://localhost:8080/api/v1`; otherwise they use `/api/v1` through the dev/nginx proxy. Cross-origin absolute URLs must be present in backend CORS configuration.

## First pages

- login
- home feed
- publish lost item
- publish found item
- match list
- notification center
- profile
