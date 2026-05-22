# Docker Assets

## Full local stack

Run from the repository root:

```bash
docker compose -f deploy/docker/docker-compose.yml up --build
```

Optional custom environment:

```bash
cp deploy/docker/.env.example deploy/docker/.env
docker compose --env-file deploy/docker/.env -f deploy/docker/docker-compose.yml up --build
```

Fedora Podman:

```bash
podman compose -f deploy/docker/docker-compose.yml up --build
```

If your Fedora installation uses the standalone plugin:

```bash
podman-compose -f deploy/docker/docker-compose.yml up --build
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

Default ports:

- User app: `http://localhost:18080`
- Admin web: `http://localhost:18081`
- Backend docs: `http://localhost:8080/docs`
- AI health: `http://localhost:5000/health`
- MySQL: `localhost:3306`
- MinIO console: `http://localhost:9001`

The MySQL container initializes from `backend/sql/schema.sql` and `backend/sql/seed-demo.sql` on first volume creation. To reset local data:

```bash
docker compose -f deploy/docker/docker-compose.yml down -v
```

## Frontend services

The user app and admin web can also be built by themselves. API calls still need a backend reachable from the browser or container network:

```bash
cd deploy/docker
docker compose -f docker-compose.frontend.yml up --build
```

By default the frontend-only compose builds API calls against `http://localhost:8080/api/v1`.

- User app: `http://localhost:18080`
- Admin web: `http://localhost:18081`

Override ports with `USER_WEB_PORT` and `ADMIN_WEB_PORT` when needed.
