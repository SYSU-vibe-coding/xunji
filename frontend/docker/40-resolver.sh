#!/bin/sh
# Replace __DNS_RESOLVER__ in nginx config with the first nameserver from
# /etc/resolv.conf, so nginx can re-resolve upstream DNS after restarts.
set -eu

CONF=/etc/nginx/conf.d/default.conf
NS=$(awk '/^nameserver/ {print $2; exit}' /etc/resolv.conf)
if [ -z "${NS}" ]; then
  NS=127.0.0.11
fi
BACKEND_UPSTREAM=${BACKEND_UPSTREAM:-http://backend:8080}
sed -i "s|__DNS_RESOLVER__|${NS}|g" "${CONF}"
sed -i "s|__BACKEND_UPSTREAM__|${BACKEND_UPSTREAM}|g" "${CONF}"
echo "[entrypoint] nginx resolver set to ${NS}; backend upstream configured"
