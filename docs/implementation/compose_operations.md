# Docker Compose Operations (Phase 01, FND-003)

The Compose stack at `docker-compose.yml` is the canonical local
runtime. It is hardened against the JDOS v1.2 requirements:

* Loopback bindings only.
* Health-gated startup ordering.
* Resource limits.
* Restart policies.
* Graceful shutdown.
* No automatic model downloads.

## Service Topology

| Service | Image | Port (loopback) | Profile | Healthcheck |
|---|---|---|---|---|
| `postgres` | `postgres:16-alpine` | 5432 | default | `pg_isready` |
| `redis` | `redis:7-alpine` | 6379 | default | `redis-cli ping` |
| `qdrant` | `qdrant/qdrant:v1.9.1` | 6333, 6334 | default | `GET /healthz` |
| `nats` | `nats:2.10-alpine` | 4222, 8222 | default | `GET /healthz` |
| `backend` | `jarvis-backend:dev` | 8000 | `app` | `GET /healthz` |

## Startup Ordering

The `backend` service uses `depends_on.condition: service_healthy`
so it does not start until every dependency reports healthy. The
stateful services (`postgres`, `redis`, `qdrant`, `nats`) start
in parallel; `backend` is gated on all four.

**Note:** Ollama runs natively on the host (not in Docker).
The backend communicates with it via `OLLAMA_BASE_URL`
(`http://127.0.0.1:11434` for local runs,
`http://host.docker.internal:11434` for Docker backend).

## Restart Policies

| Service | Policy | Rationale |
|---|---|---|
| `postgres`, `redis`, `qdrant`, `nats`, `backend` | `unless-stopped` | Local daemon should survive reboots. |

## Resource Limits

The `deploy.resources.limits` are sized for a developer laptop
running the full stack. Production deployments MUST be re-sized
through an ADR; the values below are starting points only.

| Service | CPU limit | Memory limit |
|---|---|---|
| `postgres` | 1.0 | 1024M |
| `redis` | 0.5 | 384M |
| `qdrant` | 1.0 | 1536M |
| `nats` | 0.75 | 512M |
| `backend` | 2.0 | 2G |

## Graceful Shutdown

`stop_grace_period` and (where applicable) `stop_signal` give each
service a defined window to drain in-flight work:

| Service | `stop_grace_period` | Drain behaviour |
|---|---|---|
| `postgres` | 30s | Smart shutdown, waits for backends. |
| `redis` | 20s | Append-Only File fsync then exit. |
| `qdrant` | 30s | Flushes in-memory segments. |
| `nats` | 15s | Drains subscriptions. |
| `backend` | 30s | Allows the FastAPI lifespan to close NATS/Redis/Qdrant. |

## Commands

```bash
# Start the foundation stack.
docker compose up -d

# Bring up an application service explicitly.
docker compose --profile app up -d backend

# Tail logs.
docker compose logs -f

# Status.
docker compose ps

# Stop without removing volumes.
docker compose stop

# Stop and remove volumes (destructive).
docker compose down -v
```

## Network

The default network is `jarvis-network` (bridge). Inter-container
DNS resolution is enabled (`com.docker.network.bridge.enable_icc=true`)
so backend, nats, postgres, redis, and qdrant can find
each other by service name. Masquerading is disabled to make
unexpected outbound traffic observable in firewall logs.

## Resource Quotas and the Operator

The Phase 01 stack runs on a developer laptop. The operator MUST
adjust the resource limits when the host is smaller (e.g. 16 GB
total memory) and MUST NOT run the full stack on a host with
less than 16 GB of RAM.

## Failure Mode Matrix

| Symptom | Likely cause | Mitigation |
|---|---|---|
| `backend` never becomes healthy | One dependency never reports healthy | `docker compose ps`; check `docker compose logs <svc>`. |
| Ollama 503 on `/api/tags` | Models not pre-pulled (native host) | Run the bootstrap script, or pull manually: `ollama pull nomic-embed-text`. |
| `qdrant` OOM | `memory: 1536M` too small | Increase `qdrant`'s `memory` limit and reload. |
| `postgres` slow start | `pg_isready` timing out | Increase `healthcheck.start_period`. |
| Disk usage growing | AOF / WAL retained too long | Tune `redis`'s `appendfsync` or `postgres`'s `wal_keep_size`. |

## CI Smoke

`.github/workflows/ci.yml` runs `docker-smoke` which:

1. Brings up the foundation stack.
2. Waits for every healthcheck to report healthy.
3. Runs `alembic upgrade head` against `postgres`.
4. Generates the SBOM and uploads it as an artifact.
5. Tears the stack down with `docker compose down -v`.
