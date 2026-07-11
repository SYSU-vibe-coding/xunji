# Docker Assets

## Full local stack

Run from the repository root:

```bash
cp deploy/docker/.env.example deploy/docker/.env
# Fill every blank required secret/password in deploy/docker/.env, then:
docker compose --env-file deploy/docker/.env -f deploy/docker/docker-compose.yml up --build
```

Compose requires non-empty JWT, administrator, database, MySQL root, and MinIO credentials.
Start from `.env.example`, fill every blank required password/token with a unique random value, and do not commit the resulting `.env`. The example explicitly enables `DEBUG`, one-time administrator bootstrap, and debug SMS for two exact demo numbers so the completed file is immediately usable for a local course demonstration. These settings are not production defaults and do not make arbitrary phone numbers eligible for debug codes.

Fedora Podman:

```bash
podman compose --env-file deploy/docker/.env -f deploy/docker/docker-compose.yml up --build
```

If your Fedora installation uses the standalone plugin:

```bash
podman-compose --env-file deploy/docker/.env -f deploy/docker/docker-compose.yml up --build
```

If `podman compose` reports that it is using Docker Compose as an external provider, make sure the Podman socket is enabled:

```bash
systemctl --user enable --now podman.socket
export DOCKER_HOST="unix://${XDG_RUNTIME_DIR}/podman/podman.sock"
podman compose -f deploy/docker/docker-compose.yml up --build
```

In restricted environments where `/run/user/$UID` is not writable, Podman can be pointed at temporary storage:

```bash
mkdir -p /tmp/xunji-podman-root /tmp/xunji-podman-runroot
export XDG_RUNTIME_DIR=/tmp/xunji-podman-runroot
podman --root /tmp/xunji-podman-root --runroot /tmp/xunji-podman-runroot info
```

If rootless Podman cannot start `aardvark-dns` because the user DBus session is unavailable, use the host-network compose file after building the four local app images:

```bash
podman build -f backend/Dockerfile -t xunji/backend:local .
podman build -f ai-service/Dockerfile -t xunji/ai-service:local .
podman build -f frontend/user-app/Dockerfile -t xunji/user-web:local .
podman build -f frontend/admin-web/Dockerfile -t xunji/admin-web:local .
podman compose -f deploy/docker/docker-compose.podman-host.yml up -d
```

Default local ports:

- User app: `http://localhost:18080`
- Admin web: `http://localhost:18081`
- Backend health: `http://localhost:8080/health`
- Backend docs: `http://localhost:8080/docs`
- AI health: `http://localhost:5000/health`
- MySQL: `127.0.0.1:3306`
- MinIO API: `http://127.0.0.1:9000`
- MinIO console: `http://localhost:9001`

MySQL and MinIO host ports bind to `127.0.0.1` by default. In a deployment where only the backend needs them, remove both host mappings with:

```bash
docker compose -f deploy/docker/docker-compose.yml -f deploy/docker/docker-compose.production.yml up -d
```

The backend runs `alembic upgrade head` before Uvicorn starts; `schema.sql` is not mounted into MySQL. The local demonstration example sets `BOOTSTRAP_ADMIN_ENABLED=true` only to create the configured administrator on its first startup. Set it back to `false` immediately after that account exists. Existing administrators are never reset by bootstrap, and the real compose file supplies no public default administrator/database/MinIO password.

Course SMS simulation is only for local whitelist demonstrations: it requires `DEBUG=true`, `SMS_DEBUG_ENABLED=true`, and controlled numbers in the comma-separated `SMS_DEMO_PHONES`. The example lists two replaceable demo numbers. A number outside that exact allowlist does not receive `debugCode`; without a real sender the API returns a clear unavailable error and stores no code. Wildcards are not supported. Disable both debug switches outside the local demonstration.

The compose file includes one shared local-development `AI_SERVICE_TOKEN` so a clean local stack starts without disabling service authentication. Set a unique random `AI_SERVICE_TOKEN` of at least 32 characters for any shared environment.

MinIO's `xunji` bucket is private. Backend startup creates the bucket when needed and deletes any existing anonymous bucket policy. `MINIO_PUBLIC_BASE_URL` is used only for browser preview signatures. AI calls receive a separate short-lived URL signed with `MINIO_ENDPOINT` (`minio:9000` in the default Docker network) and expiring after `MINIO_AI_URL_EXPIRE_MINUTES`.

The AI service accepts that private endpoint only because the exact host `minio` is in `AI_TRUSTED_PRIVATE_IMAGE_HOSTS`. Private IPs and single-label hosts not on this dedicated exact-match list remain blocked; `AI_ALLOWED_IMAGE_HOSTS` is only for optional public object-storage hosts and does not weaken private-network SSRF checks. Never add an anonymous `s3:GetObject` policy or a broad private-host wildcard.

For an existing deployment that was created from the historical handwritten `backend/sql/schema.sql` and has no `alembic_version`, do not blindly stamp it. Back up the database, compare every table, column, index, unique constraint, default, and nullability rule with the full Alembic history, and apply any missing structural changes first. Only after that review proves the live schema is exactly equivalent to the current migration head may an operator run the one-time `alembic stamp head`; subsequent changes use `alembic upgrade head` normally.

To reset local data:

```bash
docker compose -f deploy/docker/docker-compose.yml down -v
```

## Frontend services

The user app and admin web can also be built by themselves. API calls still need a backend reachable from the browser or container network:

```bash
cd deploy/docker
docker compose -f docker-compose.frontend.yml up --build
```

By default the frontend-only compose builds API calls against the absolute browser URL `http://localhost:8080/api/v1`. Override `VITE_API_BASE_URL` at build time for a backend on another origin and include both frontend origins in backend `CORS_ALLOWED_ORIGINS`. In the full-stack compose, `/api/v1` remains relative and is proxied by each frontend nginx container.

- User app: `http://localhost:18080`
- Admin web: `http://localhost:18081`

Override ports with `USER_WEB_PORT` and `ADMIN_WEB_PORT` when needed.
