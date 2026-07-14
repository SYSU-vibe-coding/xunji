FROM node:20-alpine AS builder
WORKDIR /app

COPY shared ./shared
COPY user-app/package.json ./user-app/package.json
COPY user-app/pnpm-lock.yaml ./user-app/pnpm-lock.yaml
COPY user-app/tsconfig*.json ./user-app/
COPY user-app/vite.config.ts ./user-app/
COPY user-app/index.html ./user-app/
WORKDIR /app/user-app
RUN npm install -g pnpm@9.15.9 --registry=https://registry.npmmirror.com
RUN pnpm config set registry https://registry.npmmirror.com && pnpm install --frozen-lockfile

COPY user-app/src ./src
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN pnpm build

FROM nginx:1.27-alpine
ENV BACKEND_UPSTREAM=http://backend:8080
COPY user-app/nginx.conf /etc/nginx/conf.d/default.conf
COPY docker/40-resolver.sh /docker-entrypoint.d/40-resolver.sh
RUN chmod +x /docker-entrypoint.d/40-resolver.sh
COPY --from=builder /app/user-app/dist /usr/share/nginx/html
EXPOSE 80
