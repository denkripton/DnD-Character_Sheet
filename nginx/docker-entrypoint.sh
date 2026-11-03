#!/bin/sh
set -eu

: "${MINI_APP_DOMAIN:?MINI_APP_DOMAIN is required}"
: "${API_DOMAIN:?API_DOMAIN is required}"
: "${ACME_EMAIL:?ACME_EMAIL is required}"

validate_domain() {
    case "$1" in
        ''|*[!A-Za-z0-9.-]*|.*|*.)
            printf 'Invalid domain value: %s\n' "$1" >&2
            exit 1
            ;;
    esac
}

validate_domain "$MINI_APP_DOMAIN"
validate_domain "$API_DOMAIN"
if [ "$MINI_APP_DOMAIN" = "$API_DOMAIN" ]; then
    printf 'MINI_APP_DOMAIN and API_DOMAIN must be different hostnames\n' >&2
    exit 1
fi

render_https_configuration() {
    envsubst '${MINI_APP_DOMAIN}' \
        < /etc/nginx/source-conf.d/frontend.conf.template \
        > /etc/nginx/conf.d/frontend.conf
    envsubst '${API_DOMAIN}' \
        < /etc/nginx/source-conf.d/backend.conf.template \
        > /etc/nginx/conf.d/backend.conf
}

certificate=/etc/letsencrypt/live/dnd-character-sheet/fullchain.pem
if [ -s "$certificate" ]; then
    render_https_configuration
fi

nginx -t
nginx -g 'daemon off;' &
nginx_pid=$!

stop_nginx() {
    kill -TERM "$nginx_pid" 2>/dev/null || true
    wait "$nginx_pid" 2>/dev/null || true
}
trap 'stop_nginx; exit 0' TERM INT

while kill -0 "$nginx_pid" 2>/dev/null; do
    if [ ! -s "$certificate" ]; then
        if certbot certonly \
            --non-interactive \
            --agree-tos \
            --email "$ACME_EMAIL" \
            --webroot \
            --webroot-path /var/www/certbot \
            --cert-name dnd-character-sheet \
            --domain "$MINI_APP_DOMAIN" \
            --domain "$API_DOMAIN"; then
            render_https_configuration
            if nginx -t; then
                nginx -s reload
            fi
        else
            printf 'Certificate issuance failed; retrying in one hour\n' >&2
        fi
        sleep 1h
    else
        certbot renew \
            --quiet \
            --webroot \
            --webroot-path /var/www/certbot \
            --deploy-hook 'nginx -t && nginx -s reload' || true
        sleep 12h
    fi
done

wait "$nginx_pid"
