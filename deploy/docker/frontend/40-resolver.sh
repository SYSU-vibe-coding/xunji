#!/bin/sh
# Replace __DNS_RESOLVER__ in nginx config with the first nameserver from
# /etc/resolv.conf, so that nginx can re-resolve upstream DNS at request time.
# This protects against backend container restarts that change the IP.
set -eu

CONF=/etc/nginx/conf.d/default.conf
NS=$(awk '/^nameserver/ {print $2; exit}' /etc/resolv.conf)
if [ -z "${NS}" ]; then
  NS=127.0.0.11
fi
sed -i "s|__DNS_RESOLVER__|${NS}|g" "${CONF}"
echo "[entrypoint] nginx resolver set to ${NS}"
