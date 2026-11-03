# Telegram Mini App

Run locally from the repository root with `cp mini-app/config/.env.example mini-app/.env.local`, set `VITE_API_BASE_URL`, then run `npm --prefix mini-app/config ci` and `npm --prefix mini-app/config run dev`. Production builds are created in `mini-app/dist/` with `npm --prefix mini-app/config run build`.

Production Docker deployment is documented in [`../DEPLOYMENT.md`](../DEPLOYMENT.md). The multi-stage `nginx/Dockerfile` builds the Mini App and serves it alongside an HTTPS reverse proxy for FastAPI. Set `VITE_API_BASE_URL` to the HTTPS API domain at image build time, backend `BOT_TOKEN` to the bot's token, and `MINI_APP_ALLOWED_ORIGINS` to the exact frontend origin. Do not inject backend secrets into `VITE_*` variables. Register the Mini App URL with BotFather after deployment.

The existing `POST /users/auth/external` endpoint accepts Telegram Mini App `initData`, verifies its HMAC and age, and returns an access token. The frontend keeps the token in memory and sends it as a bearer token for authenticated character requests. The endpoint continues to support trusted bot authentication using its server-side bot secret.
