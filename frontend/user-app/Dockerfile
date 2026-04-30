FROM node:20-alpine AS builder
WORKDIR /app

COPY frontend/shared ./frontend/shared
COPY frontend/user-app/package.json ./frontend/user-app/package.json
COPY frontend/user-app/pnpm-lock.yaml ./frontend/user-app/pnpm-lock.yaml
COPY frontend/user-app/tsconfig*.json ./frontend/user-app/
COPY frontend/user-app/vite.config.ts ./frontend/user-app/
COPY frontend/user-app/index.html ./frontend/user-app/
WORKDIR /app/frontend/user-app
RUN corepack enable && corepack prepare pnpm@9.15.9 --activate
RUN pnpm install --frozen-lockfile

COPY frontend/user-app/src ./src
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN pnpm build

FROM nginx:1.27-alpine
COPY frontend/user-app/nginx.conf /etc/nginx/conf.d/default.conf
COPY deploy/docker/frontend/40-resolver.sh /docker-entrypoint.d/40-resolver.sh
RUN chmod +x /docker-entrypoint.d/40-resolver.sh
COPY --from=builder /app/frontend/user-app/dist /usr/share/nginx/html
EXPOSE 80
