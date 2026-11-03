FROM node:22-alpine AS builder

WORKDIR /app/mini-app/config

COPY mini-app/config/package.json mini-app/config/package-lock.json ./
RUN npm ci

COPY mini-app/ ../
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM nginx:alpine

RUN apk add --no-cache certbot gettext \
    && rm -f /etc/nginx/conf.d/default.conf

COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY nginx/conf.d/ /etc/nginx/source-conf.d/
COPY nginx/snippets/ /etc/nginx/snippets/
COPY nginx/docker-entrypoint.sh /usr/local/bin/dnd-nginx-entrypoint
COPY --from=builder /app/mini-app/dist /usr/share/nginx/html

RUN chmod 0755 /usr/local/bin/dnd-nginx-entrypoint \
    && mkdir -p /var/www/certbot

EXPOSE 80 443

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD wget -q --spider http://127.0.0.1/healthz || exit 1

ENTRYPOINT ["/usr/local/bin/dnd-nginx-entrypoint"]
