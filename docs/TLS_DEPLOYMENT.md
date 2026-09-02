# TLS and Reverse-Proxy Deployment

Sentinel uses an out-of-band telemetry connection. A monitored customer server
does not need to accept inbound Sentinel traffic and customer application
requests do not traverse the Sentinel API.

## Production topology

```text
Remote host -> Sentinel Agent
                  |
                  | outbound HTTPS
                  v
             TLS reverse proxy
                  |
                  | private loopback/network
                  v
             Sentinel API :8000
```

The reference Compose deployment binds the backend to `127.0.0.1` rather than
publishing it on every host interface. Terminate TLS at an independently
managed reverse proxy (for example, nginx or Caddy) and proxy only Sentinel API
paths to `http://127.0.0.1:8000`. Keep the proxy's upstream private and apply a
firewall allowlist for agent egress sources where possible.

Example nginx shape (adapt paths, certificate locations, and access policy to
the deployment):

```nginx
server {
    listen 443 ssl http2;
    server_name sentinel.example.internal;
    ssl_certificate     /etc/letsencrypt/live/sentinel/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sentinel/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Request-ID $request_id;
        client_max_body_size 2m;
    }
}
```

The proxy is deployment infrastructure, not part of Sentinel. Do not proxy
customer application paths through this server.

## Agent TLS configuration

```powershell
sentinel-agent init `
  --server-url https://sentinel.example.internal `
  --interface Ethernet `
  --environment production `
  --tls-ca C:\ProgramData\Sentinel\ca\central-ca.pem
```

The agent uses the system trust store by default. `--tls-ca` is for an
explicitly trusted private CA bundle. `--tls-client-cert` and
`--tls-client-key` configure the transport interface for a future mTLS
deployment; this release does not issue or validate a client PKI.

Never use `curl -k`, `verify=False`, or an equivalent bypass in production.
Development-only insecure TLS is available only through the explicit
`--tls-insecure` setting and must not be copied into production configuration.

## Certificate behavior

The Python TLS library validates chain trust, hostname, and certificate expiry.
Invalid, expired, untrusted, or wrong-host certificates fail the connection.
This repository contains no private keys and no bundled development certificate.
An end-to-end HTTPS test requires a locally trusted test certificate or a real
staging CA; the automated Phase G suite validates the context and fail-closed
configuration without weakening certificate verification.
