FROM node:20-alpine AS builder
WORKDIR /app

COPY frontend/shared ./frontend/shared
COPY frontend/admin-web/package.json ./frontend/admin-web/package.json
COPY frontend/admin-web/pnpm-lock.yaml ./frontend/admin-web/pnpm-lock.yaml
COPY frontend/admin-web/tsconfig*.json ./frontend/admin-web/
COPY frontend/admin-web/vite.config.ts ./frontend/admin-web/
COPY frontend/admin-web/index.html ./frontend/admin-web/
WORKDIR /app/frontend/admin-web
RUN corepack enable && corepack prepare pnpm@9.15.9 --activate
RUN pnpm install --frozen-lockfile

COPY frontend/admin-web/src ./src
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN pnpm build

FROM nginx:1.27-alpine
COPY frontend/admin-web/nginx.conf /etc/nginx/conf.d/default.conf
COPY deploy/docker/frontend/40-resolver.sh /docker-entrypoint.d/40-resolver.sh
RUN chmod +x /docker-entrypoint.d/40-resolver.sh
COPY --from=builder /app/frontend/admin-web/dist /usr/share/nginx/html
EXPOSE 80
