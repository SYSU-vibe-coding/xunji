FROM node:20-alpine AS builder
WORKDIR /app

COPY shared ./shared
COPY admin-web/package.json ./admin-web/package.json
COPY admin-web/pnpm-lock.yaml ./admin-web/pnpm-lock.yaml
COPY admin-web/tsconfig*.json ./admin-web/
COPY admin-web/vite.config.ts ./admin-web/
COPY admin-web/index.html ./admin-web/
WORKDIR /app/admin-web
RUN npm install -g pnpm@9.15.9 --registry=https://registry.npmmirror.com
RUN pnpm config set registry https://registry.npmmirror.com && pnpm install --frozen-lockfile

COPY admin-web/src ./src
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN pnpm build

FROM nginx:1.27-alpine
ENV BACKEND_UPSTREAM=http://backend:8080
COPY admin-web/nginx.conf /etc/nginx/conf.d/default.conf
COPY docker/40-resolver.sh /docker-entrypoint.d/40-resolver.sh
RUN chmod +x /docker-entrypoint.d/40-resolver.sh
COPY --from=builder /app/admin-web/dist /usr/share/nginx/html
EXPOSE 80
