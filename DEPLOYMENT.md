# NGINX edge proxy and TLS

The `nginx` Compose service is the only public application entry point. It serves the built Mini App on its frontend domain and proxies the API domain to `backend:8000`. PostgreSQL, Redis, RabbitMQ, and FastAPI do not publish host ports in production.

The service-owned `nginx/Dockerfile` builds the Mini App with `npm ci` and Vite, then copies its static assets into the NGINX image. `nginx/` also contains `nginx.conf`, two `conf.d/*.conf.template` virtual hosts, shared snippets, and the certificate lifecycle script. The lifecycle script is required to start without a certificate, issue the first certificate, and run periodic renewal; the Certbot deploy hook validates and reloads NGINX directly. The backend and bot Dockerfiles live at `backend/docker/Dockerfile` and `bot/docker/Dockerfile`.

## Required environment

Set these values in the repository root `.env` file:

```dotenv
MINI_APP_DOMAIN=mini-app.example.com
API_DOMAIN=api.example.com
ACME_EMAIL=ops@example.com
MINI_APP_URL=https://mini-app.example.com
```

The domains must be different public hostnames and must resolve to the deployment host. `ACME_EMAIL` is the valid contact address supplied to Let's Encrypt. Backend CORS is restricted to `https://${MINI_APP_DOMAIN}`. The NGINX image builds the frontend with `VITE_API_BASE_URL=https://${API_DOMAIN}`; that value is public and must not contain credentials or secrets.

## First deployment

1. Copy `.env.example` to `.env`, set the hostnames and a valid `ACME_EMAIL`, and replace all example secrets with strong values.
2. Create DNS `A` records for both domains to the host's public IPv4 address. Create `AAAA` records only when inbound IPv6 is correctly configured.
3. Allow inbound TCP 80 and 443 through the host firewall and cloud firewall. HTTP-01 certificate validation requires port 80 to be publicly reachable.
4. Start the stack:

   ```sh
   docker compose config
   docker compose build
   docker compose up -d
   docker compose ps
   docker compose logs -f nginx
   ```

At startup, NGINX serves HTTP on port 80. Until a certificate exists, ordinary requests receive `503` rather than being sent over cleartext; HTTP-01 challenges are served from `/var/www/certbot`. Certbot requests one publicly trusted certificate with both hostnames. On issuance success, the entrypoint renders the two domain-specific templates with `envsubst`, enables the TLS virtual hosts and HTTP redirects, validates the generated configuration, and reloads NGINX. On subsequent starts it renders the same templates from the persisted certificate before starting NGINX.

If Let's Encrypt issuance fails, NGINX remains running in HTTP bootstrap mode and retries after one hour. Check DNS, firewall reachability, `ACME_EMAIL`, and `docker compose logs nginx`. Do not repeatedly restart the service to retry issuance; correct the cause and allow the scheduled retry or restart it once.

## Renewal

The NGINX container runs `certbot renew` every 12 hours against the persisted `nginx_certs` volume. Certbot renews only when due and runs the deploy hook after a successful renewal. The hook executes `nginx -t` followed by `nginx -s reload`, so the renewed certificate is loaded without a Docker socket or container restart. ACME challenge files use the persisted `acme_webroot` volume. Both volumes must be retained during upgrades and backups; protect backups of `nginx_certs` because it contains private keys.

Monitor renewal and proxy logs with:

```sh
docker compose logs --since=24h nginx
docker compose exec nginx certbot certificates
```

The NGINX health check requests `http://127.0.0.1/healthz` from the running server, including before TLS issuance. Configuration is checked with `nginx -t` before startup and every reload. Client-side routes such as `/characters` fall back to the bundled `index.html`.

## Development

With a repository-root `.env` containing the backend, database, RabbitMQ, bot, and AI credentials (copy `.env.example` and replace the placeholders if needed), start local development from the repository root:

```sh
docker compose -f compose.yml -f compose.dev.yml up --build -d
```

The override disables production NGINX and ACME. Vite is available at `http://localhost:5173`, FastAPI at `http://localhost:8000`, and Swagger UI at `http://localhost:8000/docs`. The frontend's `VITE_API_BASE_URL` points to the browser-accessible API URL, while backend and bot connections to PostgreSQL, Redis, and RabbitMQ use Compose service names. CORS allows the local Vite origin. `MINI_APP_DOMAIN`, `API_DOMAIN`, and `ACME_EMAIL` are only used by the disabled production NGINX service, so they need no localhost values in development.

The bot's development `MINI_APP_URL` is `http://localhost:5173`. Telegram does not accept HTTP Web App buttons, even for localhost; the bot retains its command menu and can display the local URL instead. The browser frontend requires genuine Telegram `initData` for sign-in, so opening the HTTP page directly shows a sign-in prompt. Testing the authenticated Telegram Mini App flow requires a publicly reachable HTTPS origin; local development does not bypass authentication.
