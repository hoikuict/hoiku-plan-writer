# Public demo deployment

This repository supports a public demo mode for Dockge deployments.

## What public demo mode does

- Creates a fresh SQLite database per browser session.
- Starts each session from the same seeded demo data.
- Resets the demo data when you clear the session or start a new browser session.
- Cleans up expired session databases after the configured TTL.
- Rejects oversized write requests.
- Rejects sessions that exceed the total write budget.

## Recommended environment values

- `PUBLIC_DEMO_MODE=1`
- `DEMO_SESSION_TTL_MINUTES=120`
- `DEMO_SESSION_INPUT_LIMIT_BYTES=65536`
- `DEMO_MAX_REQUEST_BODY_BYTES=16384`
- `DEMO_SECURE_COOKIES=1`

## Dockge

1. Create or switch to the public demo branch.
2. In Dockge, create a stack from this repository or paste in `compose.yaml`.
3. Copy `.env.example` values into the stack environment editor.
4. Set `CLOUDFLARE_TUNNEL_TOKEN` if you want the stack to publish itself through Cloudflare Tunnel.
5. Start the stack and confirm the app responds on the host port configured by `HOST_PORT`.

## Cloudflare

If you already run `cloudflared` elsewhere, you can remove the bundled `cloudflared` service and point your existing tunnel at `http://app:8000` on the same Docker network or at the host port you exposed from Dockge.

The `app` container always listens on port `8000` internally. Only the host-side published port should vary. For example:

- `HOST_PORT=8010`
- Cloudflare Service URL: `http://app:8000`

If you use the bundled `cloudflared` service:

1. Create a Cloudflare Tunnel in the dashboard.
2. Add a public hostname for your chosen domain.
3. Point that hostname to `http://app:8000`.
4. Copy the tunnel token into `CLOUDFLARE_TUNNEL_TOKEN`.
5. Redeploy the stack.

## Ollama

If the same TrueNAS environment already has Ollama available on the Docker network, you can enable annual LLM preview with these environment values.

- `HOIKU_PLAN_AI_PROVIDER=ollama`
- `HOIKU_PLAN_AI_ENABLE_ANNUAL_PREVIEW=1`
- `HOIKU_PLAN_AI_MODEL=qwen2.5:0.5b`
- `HOIKU_PLAN_AI_BASE_URL=http://ollama:11434`

If the public demo must stay stable, keep AI preview disabled until you confirm the Ollama endpoint and response time in the deployment network.

## Notes

- Public demo mode keeps runtime session data under `./runtime`, which is ignored by git.
- No persistent volume is configured on purpose, so demo sessions disappear on redeploy or container recreation.
