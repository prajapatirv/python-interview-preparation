# 08 — Scaling & Production Resilience

Pure stdlib — every file runs with `py <file>.py`, no dependencies.

## Crib sheet

- **Horizontal > vertical for the app tier.** Design stateless: externalize sessions to
  Redis/DB, files to object storage. Then you can add instances freely and do rolling,
  zero-downtime deploys. Keep vertical scaling for the database until you hit real limits, then
  add read replicas.
- **Retry with exponential backoff + jitter**: `delay = base * 2^attempt + random_jitter`. Jitter
  prevents every retrying client from hammering the recovering service at the exact same instant
  (a "retry storm"). Always cap max attempts and total time.
- **Circuit breaker states**: `CLOSED` (normal) → `OPEN` (failing fast, no calls reach the
  downstream) → `HALF-OPEN` (a trial call probes recovery) → back to `CLOSED` or `OPEN`. This
  protects a struggling downstream from being hammered by retries while it's already unhealthy.
- **Rate limiting**: a sliding-window counter per client key; return `429` with `Retry-After` when
  exceeded. Different from a circuit breaker — rate limiting protects *your* service from *too
  many callers*; a circuit breaker protects *a downstream* from *your* retries.
- **Health checks**: liveness ("is the process alive?") vs readiness ("can it serve traffic right
  now?", e.g. DB/cache reachable). Kubernetes restarts on failed liveness, but only *stops
  routing traffic* on failed readiness — a critical distinction.
- **Graceful shutdown**: catch `SIGTERM`, stop accepting new work, let in-flight requests finish,
  flush any buffered writes (a Kafka producer, a batched log), *then* exit. The container
  orchestrator's grace period must exceed however long this takes.

## Files

| File | Topic |
|---|---|
| `01_retry_backoff.py` | exponential backoff + jitter, capped attempts, only-retry-transient-errors |
| `02_circuit_breaker.py` | CLOSED → OPEN → HALF-OPEN → CLOSED state machine, built from scratch |
| `03_rate_limiter.py` | sliding-window rate limiter as a decorator, per-caller buckets |
| `04_health_checks_graceful_shutdown.py` | liveness vs readiness, `signal`-based graceful shutdown |

## Exercise

Compose `02_circuit_breaker.py`'s breaker with `01_retry_backoff.py`'s retry: wrap a call so it
retries transient failures with backoff *while the circuit is closed*, but skips straight to the
fallback with zero retries the instant the circuit opens. Explain in one sentence why retrying
into an already-open circuit would make an outage worse, not better.
