# Telegram Mini App

Run locally from `mini-app/` with `npm --prefix config install`, copy `config/.env.example` to `.env.local`, set `VITE_API_BASE_URL`, then run `npm --prefix config run dev`. Production builds are created in `dist/` with `npm --prefix config run build`.

Deployment requires HTTPS hosting configured as a Telegram Web App URL. Configure the host to serve `index.html` for client-side routes. Set `VITE_API_BASE_URL` to the HTTPS backend API origin, backend `BOT_TOKEN` to the bot's token, and `MINI_APP_ALLOWED_ORIGINS` to the exact frontend origin. Do not inject backend secrets into `VITE_*` variables. Register the Mini App URL with BotFather after deployment.

The existing `POST /users/auth/external` endpoint accepts Telegram Mini App `initData`, verifies its HMAC and age, and returns an access token. The frontend keeps the token in memory and sends it as a bearer token for authenticated character requests. The endpoint continues to support trusted bot authentication using its server-side bot secret.
