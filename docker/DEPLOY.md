# Production deploy (single host: clearnet + onion)

This brings up the full stack on one VPS: the app + Redis behind **Caddy**
(clearnet, automatic Let's Encrypt TLS) and a **Tor** v3 onion service. Caddy
and Tor run as containers and reach the app over the internal Docker network;
the app port is never published to the host.

## Prerequisites

- Docker Engine + Compose plugin on the host.
- DNS: an `A` record for your clearnet domain pointing at the host's public IP
  (required before Caddy can issue a cert).
- Inbound `80` and `443` open (for clearnet + ACME). The onion service needs no
  inbound port; Tor reaches the network outbound.

## Configure

1. Create `.env` in the repo root (gitignored) from `.env.default`, with:
   - `ENVIRONMENT=production`
   - `SECRET_KEY=` a value >= 32 chars: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
   - `REDIS_PASSWORD=` a strong random value.
2. Create the Caddyfile from the template, substituting your domain:

   ```sh
   sed 's/__DOMAIN__/your.domain/' docker/Caddyfile.prod.example > docker/Caddyfile
   ```

## Launch

```sh
docker compose -f docker/docker-compose.prod.yaml up -d --build
```

## Get the onion address

```sh
docker compose -f docker/docker-compose.prod.yaml exec tor cat /var/lib/tor/vapour/hostname
```

The onion key lives in the `tor_data` volume — back it up to keep the address.

## Notes

- `HiddenServicePoWDefensesEnabled` (in `docker/torrc`) needs a Tor build with
  the pow module. If the packaged tor lacks it, tor will refuse to start; remove
  that line and rely on the in-app server-wide `/login` limiter.
- HSTS is set by Caddy (clearnet only), not the app, so it is never sent over
  the onion's http transport.
