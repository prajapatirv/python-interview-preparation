"""
"How does observability work in a distributed system, and what are its key components?"

Monitoring tells you THAT something is wrong. Observability lets you ask WHY, including questions
you did not think of in advance. That distinction is the first thing to say.

The components, and what each one is actually for:

  METRICS  -- cheap, aggregated numbers over time. Answer "is it broken, and how badly?"
              Fixed cost per series; you cannot put a user id in a label.
  LOGS     -- one structured event per interesting thing. Answer "what exactly happened to THIS
              request?" Expensive at volume; sample the boring ones, never the errors.
  TRACES   -- one causally-linked tree of spans per request across services. Answer "WHERE did
              the 2 seconds go?" The only pillar that shows you the call graph.
  + the glue: a CORRELATION / TRACE ID propagated through every hop, so all three join up.
  + the contract: SLI -> SLO -> ERROR BUDGET, which turns "it feels slow" into a decision.

This file implements a miniature version of all of it -- a correlation-ID context, a structured
JSON logger, a metrics registry with counters/gauges/histograms and real percentiles, a tracer
with parent/child spans, RED and USE dashboards, SLO burn-rate alerting, and log sampling --
then runs a simulated distributed request flow through it and shows the three views of the SAME
slow request.

Pure stdlib. Run me: python 02_observability_pillars.py
"""
import json
import random
import time
import uuid
from bisect import insort
from collections import defaultdict
from contextlib import contextmanager
from contextvars import ContextVar


def section(title):
    print(f"\n{'=' * 76}\n{title}\n{'=' * 76}")


# ================================================================ the glue: correlation context
# ContextVar is the right tool: it is isolated per asyncio task AND per thread, so a correlation
# id set at the edge of a request cannot leak into a concurrent one. A module-level global would.
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")
current_span: ContextVar["Span | None"] = ContextVar("current_span", default=None)


@contextmanager
def request_context(cid=None):
    """Set at the ingress edge: a middleware reads the incoming `X-Correlation-ID` header, or
    mints one if absent, and every log line / span / outbound call carries it from then on.

    The rule that makes an incident debuggable: ACCEPT an inbound correlation id, don't overwrite
    it. That is what lets you follow one customer's request across six services and two queues.
    """
    token = correlation_id.set(cid or f"req-{uuid.uuid4().hex[:12]}")
    try:
        yield correlation_id.get()
    finally:
        correlation_id.reset(token)


# ================================================================ pillar 1: metrics
class MetricsRegistry:
    """A tiny Prometheus-shaped registry. The four metric types and when each is right:

      COUNTER   -- monotonically increasing total (requests, errors, messages consumed).
                   You never read a counter directly; you read its RATE: rate(x[5m]).
      GAUGE     -- a value that goes up and down (queue depth, in-flight requests, pool size).
      HISTOGRAM -- bucketed observations, so percentiles can be computed server-side.
                   THIS is what latency goes in. Never a gauge, never an average.
      SUMMARY   -- client-computed quantiles; cheaper, but cannot be aggregated across instances.

    The cardinality rule that keeps you employed: labels must be LOW CARDINALITY. endpoint,
    status_code, region -- fine. user_id, order_id, correlation_id -- never: every distinct value
    creates a new time series, and a million users means a million series and an OOM'd Prometheus.
    High-cardinality fields belong in LOGS and TRACES, which is exactly why you need all three.
    """

    def __init__(self):
        self.counters = defaultdict(float)
        self.gauges = {}
        self.histograms = defaultdict(list)

    @staticmethod
    def _key(name, labels):
        if not labels:
            return name
        return name + "{" + ",".join(f'{k}="{v}"' for k, v in sorted(labels.items())) + "}"

    def inc(self, name, value=1, **labels):
        self.counters[self._key(name, labels)] += value

    def gauge(self, name, value, **labels):
        self.gauges[self._key(name, labels)] = value

    def observe(self, name, seconds, **labels):
        insort(self.histograms[self._key(name, labels)], seconds)

    def percentile(self, name, p, **labels):
        values = self.histograms.get(self._key(name, labels), [])
        if not values:
            return None
        # nearest-rank; a real histogram interpolates within buckets, which is why reported
        # percentiles are approximate -- say so if asked.
        index = min(int(round(p / 100 * len(values) + 0.5)) - 1, len(values) - 1)
        return values[max(index, 0)]

    def summary(self, name, **labels):
        values = self.histograms.get(self._key(name, labels), [])
        if not values:
            return {}
        return {
            "count": len(values),
            "avg_ms": round(1000 * sum(values) / len(values), 1),
            "p50_ms": round(1000 * self.percentile(name, 50, **labels), 1),
            "p95_ms": round(1000 * self.percentile(name, 95, **labels), 1),
            "p99_ms": round(1000 * self.percentile(name, 99, **labels), 1),
            "max_ms": round(1000 * values[-1], 1),
        }


METRICS = MetricsRegistry()


# ================================================================ pillar 2: structured logs
class StructuredLogger:
    """One JSON object per event. Not a sentence -- a QUERYABLE RECORD.

      BAD : log.info(f"Order {oid} failed for user {uid} after {ms}ms")
            -> to find slow orders you now need a regex, and it breaks the day someone
               rephrases the message.
      GOOD: log.info("order.failed", order_id=oid, user_id=uid, duration_ms=ms)
            -> `duration_ms > 1000 AND event = "order.failed"` is a query, in any log backend.

    Always included, automatically: timestamp, level, service, correlation_id, trace/span id.
    Never included: passwords, tokens, card numbers, full request bodies with PII.
    """

    def __init__(self, service, sample_rate=1.0, sink=None):
        self.service, self.sample_rate = service, sample_rate
        self.sink = sink if sink is not None else []
        self.dropped = 0

    def _emit(self, level, event, **fields):
        # SAMPLING: drop a fraction of routine INFO lines to control cost -- but NEVER sample
        # out warnings or errors, and never sample a request that is already erroring.
        if level == "INFO" and self.sample_rate < 1.0 and random.random() > self.sample_rate:
            self.dropped += 1
            return
        span = current_span.get()
        record = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "level": level,
            "service": self.service,
            "event": event,
            "correlation_id": correlation_id.get(),
        }
        if span is not None:
            record |= {"trace_id": span.trace_id, "span_id": span.span_id}
        record |= fields
        self.sink.append(record)

    def info(self, event, **f):
        self._emit("INFO", event, **f)

    def warning(self, event, **f):
        self._emit("WARN", event, **f)

    def error(self, event, **f):
        self._emit("ERROR", event, **f)


# ================================================================ pillar 3: traces
class Span:
    """One unit of work. A trace is the TREE of spans sharing a trace_id, linked by parent_span_id.

    The propagation that makes it work across a network: the W3C `traceparent` header,
        00-<32-hex trace id>-<16-hex span id>-01
    injected on every outbound HTTP call and into every Kafka message header. Drop it on one hop
    and the trace breaks into two unconnected halves -- which is the #1 reason traces look wrong.
    """

    def __init__(self, name, trace_id, parent_span_id=None):
        self.name, self.trace_id = name, trace_id
        self.span_id = uuid.uuid4().hex[:8]
        self.parent_span_id = parent_span_id
        self.start = time.perf_counter()
        self.duration = None
        self.simulated = None     # set by simulate() so the demo can show realistic latencies
        self.attributes = {}
        self.status = "OK"

    def simulate(self, seconds):
        """Report this span as having taken `seconds`, instead of its (tiny) real wall time.
        Demo-only scaffolding: it lets a 'slow query' show up as 850ms without the file taking
        850ms to run. Real tracers always use the wall clock."""
        self.simulated = seconds

    def set(self, **attrs):
        """Span attributes are where HIGH-CARDINALITY data belongs: order_id, user_id, the SQL
        statement, the cache key. Exactly what you must keep OUT of metric labels."""
        self.attributes |= attrs

    def traceparent(self):
        return f"00-{self.trace_id}-{self.span_id}-01"


class Tracer:
    def __init__(self):
        self.finished = []

    @contextmanager
    def span(self, name, **attrs):
        parent = current_span.get()
        trace_id = parent.trace_id if parent else uuid.uuid4().hex
        span = Span(name, trace_id, parent.span_id if parent else None)
        span.set(**attrs)
        token = current_span.set(span)
        try:
            yield span
        except Exception as e:
            span.status = f"ERROR: {type(e).__name__}"
            raise
        finally:
            span.duration = (span.simulated if span.simulated is not None
                             else time.perf_counter() - span.start)
            current_span.reset(token)
            self.finished.append(span)

    def render(self, trace_id):
        """Prints the waterfall -- the view that answers 'where did the time go?' in one glance."""
        spans = [s for s in self.finished if s.trace_id == trace_id]
        if not spans:
            return
        root = next(s for s in spans if s.parent_span_id is None)
        total = root.duration
        by_parent = defaultdict(list)
        for s in spans:
            by_parent[s.parent_span_id].append(s)

        def walk(span, depth=0):
            ms = span.duration * 1000
            share = span.duration / total if total else 0
            bar = "#" * max(1, int(share * 40))
            flag = "" if span.status == "OK" else f"  <-- {span.status}"
            print(f"    {'  ' * depth}{span.name:26s} {ms:7.1f}ms {share:5.1%} {bar}{flag}")
            for attr, value in span.attributes.items():
                print(f"    {'  ' * depth}  . {attr}={value}")
            for child in sorted(by_parent[span.span_id], key=lambda s: s.start):
                walk(child, depth + 1)

        walk(root)


TRACER = Tracer()


# ================================================================ SLI / SLO / error budget
class SLO:
    """The contract that turns observability into decisions.

      SLI -- the measurement:   "fraction of requests served in <300ms with a 2xx/3xx/4xx status"
      SLO -- the target:        "99.9% over a rolling 28 days"
      ERROR BUDGET -- 100% - SLO = 0.1% = ~40 minutes of failure per 28 days.

    Why the budget matters more than the number: it is a SHARED CURRENCY between product and
    engineering. Budget left over -> ship faster, take risks. Budget spent -> deploys freeze and
    the next sprint is reliability work. No arguing about whether it "feels" reliable.

    And alert on BURN RATE, not on the raw SLI: a 14.4x burn over 1 hour means you will exhaust a
    28-day budget in ~2 days -> page someone. A 1.5x burn over 6 hours -> a ticket, not a page.
    (Those multipliers are the standard Google SRE multi-window burn-rate alerts.)
    """

    def __init__(self, name, target=0.999, window_minutes=28 * 24 * 60):
        self.name, self.target, self.window_minutes = name, target, window_minutes
        self.good = self.total = 0

    def record(self, is_good):
        self.total += 1
        self.good += 1 if is_good else 0

    @property
    def sli(self):
        return self.good / self.total if self.total else 1.0

    @property
    def budget_consumed(self):
        allowed_bad = (1 - self.target) * self.total
        actual_bad = self.total - self.good
        return actual_bad / allowed_bad if allowed_bad else 0.0

    def burn_rate(self):
        """How many times faster than 'allowed' we are burning budget right now."""
        error_rate = 1 - self.sli
        allowed = 1 - self.target
        return error_rate / allowed if allowed else 0.0

    def alert(self):
        br = self.burn_rate()
        if br >= 14.4:
            return "PAGE", f"burn rate {br:.1f}x -- 28-day budget gone in ~2 days"
        if br >= 6:
            return "PAGE", f"burn rate {br:.1f}x -- budget gone in ~5 days"
        if br >= 1:
            return "TICKET", f"burn rate {br:.1f}x -- budget will be exhausted this window"
        return "OK", f"burn rate {br:.1f}x -- comfortably inside budget"


# ================================================================ the simulated distributed flow
LOG = StructuredLogger("orders-api")


def fake_work(lo_ms, hi_ms, rng):
    """Returns the SIMULATED duration in seconds, sleeping only a fraction of it so the file runs
    fast. Every span/metric below is recorded with the simulated value."""
    delay = rng.uniform(lo_ms, hi_ms) / 1000
    time.sleep(min(delay, 0.0005))
    return delay


def db_query(statement, rng, slow=False):
    with TRACER.span("postgres.query", **{"db.statement": statement}) as span:
        d = fake_work(400, 900, rng) if slow else fake_work(4, 14, rng)
        span.simulate(d)
        span.set(**{"db.rows": rng.randint(1, 20)})
        METRICS.observe("db_query_duration_seconds", d, operation="select")
        METRICS.inc("db_queries_total", operation="select")
        if slow:
            LOG.warning("db.slow_query", statement=statement, duration_ms=round(d * 1000, 1),
                        threshold_ms=100)
        return d


def cache_get(key, rng, hit=True):
    with TRACER.span("redis.get", **{"cache.key": key}) as span:
        d = fake_work(1, 3, rng)
        span.simulate(d)
        span.set(**{"cache.hit": hit})
        METRICS.inc("cache_requests_total", result="hit" if hit else "miss")
        return d


def call_inventory_service(rng, fail=False):
    with TRACER.span("http.client inventory-service") as span:
        span.set(**{"http.method": "GET", "http.url": "/inventory/reserve",
                    "traceparent": span.traceparent()})       # <-- the header that links services
        d = fake_work(20, 60, rng)
        span.simulate(d)
        METRICS.observe("http_client_duration_seconds", d, peer="inventory")
        if fail:
            METRICS.inc("http_client_errors_total", peer="inventory", code="503")
            LOG.error("downstream.failed", peer="inventory-service", status=503,
                      retryable=True)
            raise TimeoutError("inventory-service 503")
        return d


def handle_order(order_id, rng, slow_db=False, downstream_fails=False, inbound_cid=None):
    """One request through the whole stack, instrumented once. Note that the business code is
    almost unchanged -- the metric, the log and the span are 3 lines each, and the correlation id
    is set once at the edge. That cheapness is why you can afford to instrument everything."""
    spent = 0.0        # the simulated time budget, accumulated from each downstream call
    with request_context(inbound_cid) as cid:
        with TRACER.span("POST /orders", **{"http.route": "/orders", "order.id": order_id}) as root:
            LOG.info("request.started", route="/orders", order_id=order_id)
            METRICS.inc("http_requests_total", route="/orders", method="POST")
            METRICS.gauge("http_requests_in_flight", 1, route="/orders")
            status = 200
            try:
                spent += cache_get(f"customer:{order_id}", rng, hit=not slow_db)
                spent += db_query("SELECT * FROM orders WHERE id = $1", rng, slow=slow_db)
                spent += call_inventory_service(rng, fail=downstream_fails)
                spent += db_query("INSERT INTO order_events ...", rng)
                LOG.info("order.created", order_id=order_id)
            except TimeoutError:
                status = 503
                root.status = "ERROR: TimeoutError"
            finally:
                elapsed = spent + 0.002          # + a little application overhead
                root.simulate(elapsed)
                METRICS.observe("http_request_duration_seconds", elapsed,
                                route="/orders", method="POST")
                METRICS.inc("http_requests_total", route="/orders", method="POST",
                            status=str(status))
                METRICS.gauge("http_requests_in_flight", 0, route="/orders")
                LOG.info("request.completed", status=status,
                         duration_ms=round(elapsed * 1000, 1))
            return status, cid, root.trace_id, elapsed


# ================================================================ dashboards
def red_dashboard(metrics):
    """RED -- for request-driven SERVICES. The three numbers that belong on every service
    dashboard, in this order:
        RATE     -- requests per second
        ERRORS   -- failed requests per second (and as a % of rate)
        DURATION -- the latency DISTRIBUTION: p50, p95, p99. Never the average.
    If you only get three graphs per service, these are the three."""
    total = sum(v for k, v in metrics.counters.items()
                if k.startswith("http_requests_total") and "status=" in k)
    errors = sum(v for k, v in metrics.counters.items()
                 if k.startswith("http_requests_total") and 'status="5' in k)
    lat = metrics.summary("http_request_duration_seconds", route="/orders", method="POST")
    return {"requests": int(total), "errors": int(errors),
            "error_rate": f"{(errors / total if total else 0):.1%}", **lat}


USE_NOTE = """\
  USE -- for RESOURCES (CPU, memory, disk, connection pools, thread pools, queues):
      UTILIZATION -- % of time the resource was busy
      SATURATION  -- how much work is QUEUED waiting for it   <- the leading indicator
      ERRORS      -- error events for that resource
  Saturation is the one people forget, and it is the one that predicts the outage: a connection
  pool at 100% utilization with 0 queued is fine; at 100% with 50 waiting you are already failing,
  the latency graph just hasn't caught up yet.

  The four golden signals (Google SRE) are the same idea, phrased for services:
      latency, traffic, errors, saturation."""


if __name__ == "__main__":
    rng = random.Random(42)

    section("the three pillars, on ONE request -- metrics, logs, traces")
    status, cid, trace_id, elapsed = handle_order("ORD-1001", rng)
    print(f"    request completed: status={status} in {elapsed * 1000:.1f}ms")
    print(f"    correlation_id={cid}")
    print(f"    trace_id={trace_id}")

    print("\n    LOGS (structured, each carrying the correlation and trace ids):")
    for record in LOG.sink:
        print(f"      {json.dumps(record)}")

    print("\n    TRACE (the waterfall -- this is the only view that shows WHERE the time went):")
    TRACER.render(trace_id)

    print("\n    METRICS (aggregated, low cardinality, no ids anywhere):")
    for key, value in sorted(METRICS.counters.items()):
        print(f"      {key} = {value:g}")

    section("a SLOW request: the three pillars answer three different questions")
    LOG.sink.clear()
    status, cid, trace_id, elapsed = handle_order("ORD-1002", rng, slow_db=True)
    print(f"    METRICS say THAT it is slow : p99 = "
          f"{METRICS.summary('http_request_duration_seconds', route='/orders', method='POST')['p99_ms']}ms")
    print(f"    LOGS say WHICH request      : correlation_id={cid}, and the slow-query warning:")
    for record in LOG.sink:
        if record["level"] == "WARN":
            print(f"      {json.dumps(record)}")
    print("    TRACES say WHERE the time went:")
    TRACER.render(trace_id)
    print("    that is the whole argument for all three: no single pillar answers all three")
    print("    questions, and an incident needs all three answers in under five minutes.")

    section("a FAILING downstream call, and how the trace shows the blame")
    LOG.sink.clear()
    status, cid, trace_id, elapsed = handle_order("ORD-1003", rng, downstream_fails=True)
    print(f"    status={status}")
    TRACER.render(trace_id)
    for record in LOG.sink:
        if record["level"] == "ERROR":
            print(f"      {json.dumps(record)}")

    section("correlation id propagation across services")
    inbound = "req-from-mobile-app-1"
    _, cid, trace_id, _ = handle_order("ORD-1004", rng, inbound_cid=inbound)
    print(f"    inbound header X-Correlation-ID: {inbound}")
    print(f"    adopted, not overwritten       : {cid}")
    print("    every downstream span carries a `traceparent` built from the SAME trace id:")
    for span in TRACER.finished:
        if span.trace_id == trace_id and "traceparent" in span.attributes:
            print(f"      {span.name}: {span.attributes['traceparent']}")
    print("    drop that header on ONE hop and the trace splits in two -- the single most common")
    print("    reason a distributed trace looks broken.")

    section("RED and USE: what belongs on a dashboard")
    for _ in range(40):                           # some traffic to make percentiles meaningful
        handle_order(f"ORD-{rng.randint(2000, 9000)}", rng,
                     slow_db=rng.random() < 0.08, downstream_fails=rng.random() < 0.05)
    print("    RED (services):")
    for key, value in red_dashboard(METRICS).items():
        print(f"      {key:12s} {value}")
    print()
    print(USE_NOTE)

    section("SLI / SLO / error budget, and burn-rate alerting")
    for target, label in [(0.999, "three nines")]:
        print(f"    SLO: 99.9% of /orders requests succeed in <300ms over 28 days ({label})")
        print(f"    error budget: {(1 - target) * 100:.2f}% = "
              f"{(1 - target) * 28 * 24 * 60:.0f} minutes of failure per 28 days")

    for scenario, error_rate in [("healthy", 0.0002), ("degraded", 0.006), ("incident", 0.08)]:
        slo = SLO("orders-availability", target=0.999)
        for i in range(5000):
            slo.record(rng.random() > error_rate)
        severity, message = slo.alert()
        print(f"\n    {scenario:9s} observed error rate {1 - slo.sli:.3%}")
        print(f"      SLI={slo.sli:.4%}  budget consumed={slo.budget_consumed:.0%}")
        print(f"      -> {severity}: {message}")
    print("\n    note what you do NOT alert on: CPU, memory, a single slow query, disk at 70%.")
    print("    those are CAUSES. You alert on SYMPTOMS the user feels (error rate, latency,")
    print("    queue age) and you DEBUG with the causes. Cause-based alerts are how teams end up")
    print("    with 200 alerts nobody reads.")

    section("log sampling: keeping cost sane without going blind")
    sampled = StructuredLogger("high-volume-api", sample_rate=0.1)
    for i in range(1000):
        sampled.info("request.completed", status=200)
    for i in range(5):
        sampled.error("request.failed", status=500)         # errors are NEVER sampled out
    kept_info = sum(1 for r in sampled.sink if r["level"] == "INFO")
    kept_err = sum(1 for r in sampled.sink if r["level"] == "ERROR")
    print(f"    1000 INFO lines at sample_rate=0.1 -> {kept_info} kept, {sampled.dropped} dropped")
    print(f"    5 ERROR lines                      -> {kept_err} kept (always)")
    print("    better still: TAIL-BASED sampling -- buffer the trace, then keep 100% of traces")
    print("    that errored or exceeded a latency threshold, and 1% of the boring ones.")

    section("the 60-second spoken answer")
    print("""  "Observability is the ability to answer questions about a system you didn't
  anticipate, from its external outputs. It stands on three pillars plus the glue that joins them.

  METRICS are cheap aggregated numbers -- counters, gauges and histograms -- and they tell me
  THAT something is wrong: error rate, p99 latency, queue depth. Latency always goes in a
  histogram, never an average, and labels stay low-cardinality because every label value is a new
  time series.

  LOGS are one structured JSON event per interesting thing, and they tell me WHAT happened to a
  specific request. High-cardinality fields -- order id, user id, cache key -- live here, not in
  metric labels. I sample routine INFO lines to control cost but never sample errors.

  TRACES are a tree of spans per request across services, and they tell me WHERE the time went.
  They're propagated with the W3C traceparent header on every HTTP call and in every Kafka message
  header; miss one hop and the trace splits.

  The glue is a correlation id generated at the edge -- or adopted from the inbound header -- held
  in a ContextVar so it's safe across threads and async tasks, and stamped on every log line and
  span. That's what lets me pivot from a metric spike to the exact requests to the exact slow span
  in under five minutes.

  On top of that sits the contract: an SLI I measure, an SLO I promise, and an error budget =
  1 minus the SLO. I alert on burn rate against that budget -- 14.4x over an hour pages someone,
  1.5x over six hours opens a ticket -- and I alert on SYMPTOMS the user feels, never on causes
  like CPU. Dashboards follow RED for services and USE for resources, and saturation is the signal
  I watch hardest because it's the one that predicts the outage rather than reporting it.\"""")

# EXPERIMENT 1: add `order_id=order_id` as a METRIC label in handle_order, run the 40-request loop,
# and count the distinct series in METRICS.counters. That growth is a cardinality explosion -- the
# same mistake takes down real Prometheus instances.
# EXPERIMENT 2: remove the `traceparent` attribute from call_inventory_service and explain what the
# downstream service's trace would look like to an on-call engineer.
# EXPERIMENT 3: set sample_rate=0.001 on LOG and re-run the slow-request scenario. You now have a
# p99 spike in metrics and no log line explaining it. That is the cost/blindness trade-off, live.
# EXPERIMENT 4: change SLO target to 0.99 and re-run the three scenarios. The "degraded" case stops
# paging. Decide which target you'd actually promise for a checkout API, and what it costs you.

# EXERCISE: add a fourth pillar -- CONTINUOUS PROFILING -- as a `profile_span` that records
# simulated CPU samples per span, then answer: given a p99 regression with NO change in any
# downstream span duration, which pillar identifies the cause? (Hint: none of the three above.)
