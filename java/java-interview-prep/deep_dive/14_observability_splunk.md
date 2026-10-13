# Observability: logs, metrics, traces, Splunk (SPL), SLOs and alerting

> **Runnable:** [`01_structured_logging_mdc_and_splunk_queries.java`](../examples/14_observability_splunk/01_structured_logging_mdc_and_splunk_queries.java) ·
> [`02_metrics_percentiles_slo_and_alerting.java`](../examples/14_observability_splunk/02_metrics_percentiles_slo_and_alerting.java)
> **Crib sheet:** [`topics/14-observability-splunk-grafana-prometheus.md`](../topics/14-observability-splunk-grafana-prometheus.md) · **Guide:** Q82–Q89

## What interviewers are actually probing

The requirement lists **Splunk** explicitly, so expect: write an SPL query for errors by service, find the slowest endpoint, trace a request across services,
investigate an error spike. Behind that they test whether you **log in a way that can be queried** (structured, correlation ids, no secrets) and whether you
connect **logs, metrics and traces** into one investigation story.

## Must-know points

- **Three pillars**: logs (events, why), metrics (numbers over time, alerting), traces (request path across services, where).
- Log **structured JSON**, one line per event, with `timestamp, level, service, env, version, correlationId/traceId, operation, duration_ms, outcome, errorCode`.
- A correlation id lives in the **MDC** (thread-local): propagate to async work, outbound HTTP headers and Kafka record headers.
- SPL is a **pipeline**: `search | stats | sort | table`. Narrow time and index first, then filter, then aggregate.
- Use **percentiles** (p95/p99), not averages. Page on **symptoms** (errors, latency, saturation) and **burn rate**, not on CPU alone.
- Metric label **cardinality** must be bounded: ids belong in logs/traces.

## Interview questions and full answers

### Q1. What is Splunk and how does data get into it?

A platform to ingest, index, search and visualise machine data. Typical path: application writes JSON to stdout/file → a **forwarder** (Universal Forwarder, or the Splunk OpenTelemetry/Fluent Bit/HEC logging driver on Kubernetes) ships it → **indexers** parse (`sourcetype`, timestamp extraction) and store in an **index** → **search heads** run SPL for dashboards, alerts and reports.
Choosing the right `index`, `sourcetype`, and timestamp parsing is what makes searches fast and correct.

### Q2. Write the SPL for the common questions.

```spl
# errors by service and exception, biggest first
index=app level=ERROR | stats count by service, exception | sort - count

# when did errors start? 5-minute buckets
index=app service="order-service" level=ERROR | timechart span=5m count

# slowest endpoints (duration_ms must be numeric)
index=app sourcetype=app:json | stats count avg(duration_ms) p95(duration_ms) p99(duration_ms) by endpoint | sort - p95(duration_ms)

# error rate per service per 5 minutes
index=app | eval err=if(level=="ERROR",1,0) | timechart span=5m sum(err) as errors count as total | eval rate=round(100*errors/total,2)

# trace one request across services
index=app correlationId="abc-123" | sort _time | table _time service level message traceId

# did a deploy introduce it?
index=app level=ERROR | stats count by version | sort - count
```

Example 14/01 sections 4–8 compute the same results in Java so you can see what each command does.

### Q3. How do you investigate a sudden spike of 5xx errors?

1. **Scope**: time window, which services/endpoints/pods/versions/regions. Compare with a baseline (`timechart` vs the same hour last week).
2. **Correlate**: traffic and latency changed too? deployment/config change? dependency (DB, Kafka lag, partner) degradations at the same moment? (metrics + change log)
3. **Group**: `stats count by exception, endpoint, version, host` to find the dominant signature.
4. **Trace** one failing request by correlation id to the first failing hop.
5. **Mitigate** (rollback, disable flag, scale, shed load) then confirm recovery in the metrics; **RCA** afterwards.
State that log counts alone don't establish cause — you need the corroborating metric/trace.

### Q4. What makes a good log line, and what must never be logged?

Good: structured fields, stable error codes, ids to join on, outcome and duration, one event per meaningful outcome, correct level (ERROR = needs a human; WARN = degraded/handled; INFO = business milestones; DEBUG sampled).
Never: passwords, tokens, secrets, full card/PII, entire payloads by default; and don't log-and-throw at every layer (the same stack trace five times). Mask at the logging framework level, and review what Splunk roles can see.

### Q5. What is the MDC and how do you propagate correlation ids?

Mapped Diagnostic Context: a thread-local map the logging framework adds to every line. A servlet filter reads `X-Correlation-Id` (or generates one), puts it in the MDC, and clears it in `finally`.
Propagation: outbound `RestClient/WebClient` interceptor adds the header; Kafka producer interceptor/`ProducerRecord` header; **async tasks** need a `TaskDecorator`/context-propagation because thread-locals don't cross threads (example 14/01 section 2). Prefer **W3C `traceparent`** via OpenTelemetry/Micrometer Tracing so traces and logs share the same ids.

### Q6. Logs vs metrics vs traces: when do you use each?

Metrics **detect** (cheap, aggregated, alertable); traces **locate** (which service/span is slow, with the dependency graph); logs **explain** (the exception, the payload id, the business context).
A good incident flow: alert on an SLO burn → dashboard narrows the service → trace shows the slow span → log line with the same trace id shows the exception.

### Q7. What do you monitor for a Spring Boot service? (RED + USE)

RED: request **R**ate, **E**rror ratio, **D**uration percentiles per endpoint (`http.server.requests`).
USE for resources: JVM heap/GC pauses (`jvm.memory.used`, `jvm.gc.pause`), threads (`tomcat.threads.busy`, `executor.queued`), DB pool (`hikaricp.connections.pending`, acquire time), Kafka consumer lag and rebalance rate, disk/CPU, circuit-breaker state, DLT depth.
Business KPIs (orders/minute) alongside technical ones.

### Q8. Why percentiles, and how do you aggregate them?

Averages hide tail latency (example 14/02: avg looks fine while 2% of requests take 3–4 s). p99 is what your worst-served users experience, and with fan-out it dominates end-to-end latency.
**Percentiles cannot be averaged across instances**; ship **histogram buckets** (Micrometer `publishPercentileHistogram`) and compute the quantile centrally (Prometheus `histogram_quantile`).

### Q9. Define SLI, SLO, error budget and burn-rate alerts.

SLI = measured indicator (fraction of requests < 500 ms and non-5xx). SLO = target over a window (99.9% / 30 days). **Error budget** = 1 − SLO (≈ 43 minutes of full outage per 30 days).
**Burn rate** = observed error ratio ÷ budget ratio; alert when burning fast over a short *and* long window (e.g. 14.4× over 1 h and 5 min → page; 6× over 6 h → page; 1× over days → ticket). This avoids both missed incidents and noisy pages. Budget exhausted → freeze risky changes.

### Q10. How does distributed tracing work?

Each request gets a **trace id**; each unit of work a **span** (id, parent id, timing, attributes). Context is propagated in headers (`traceparent`) and Kafka headers; instrumentation (OpenTelemetry Java agent or Micrometer Tracing) creates spans for HTTP, JDBC, Kafka.
Sampling (head-based, or tail-based in the collector) controls cost. Backends: Jaeger, Tempo, Zipkin, Splunk Observability Cloud, Datadog. Add business attributes (orderId) carefully.

### Q11. How do you alert without causing alert fatigue?

Alert on **user-visible symptoms** and SLO burn, include a runbook link and the dashboard, route by severity (page vs ticket), deduplicate/group, add `for:` durations to avoid flapping, review noisy alerts weekly, and make every page actionable. Capacity/saturation alerts are *warnings* with lead time.

### Q12. How would you instrument Kafka consumers in Splunk/Grafana?

Metrics: consumer-lag per partition (`records-lag-max`), processing time, records/s, error and DLT counts, rebalance count/duration. Logs: one line per processed batch/record id with `topic, partition, offset, key, outcome, duration_ms`, propagating the trace id from the record headers.
Alert on lag **growth rate** and DLT depth, not an absolute lag number only.

## A worked example

Run [`01_structured_logging_mdc_and_splunk_queries.java`](../examples/14_observability_splunk/01_structured_logging_mdc_and_splunk_queries.java).
The generated hour has a payment-provider incident in minutes 40–49: use section 4 (what), 5 (when), 6 (which endpoint, p95 2.7 s vs 78 ms), 8 (it's not the deploy: errors exist in both versions).
That four-step reading is the exact way to narrate an investigation in an interview.
Then [`02_metrics_percentiles_slo_and_alerting.java`](../examples/14_observability_splunk/02_metrics_percentiles_slo_and_alerting.java) for the budget and burn-rate table.

## Hands-on drills

1. Write the SPL for "top 10 users by error count in the last hour" and "requests per status code per endpoint".
2. Add a correlation-id servlet filter + `TaskDecorator` and prove the id survives an `@Async` call.
3. Use `rex` to extract a field from an unstructured log line and explain why JSON logging avoids it.
4. Configure Micrometer histogram buckets and write the PromQL for p95 per endpoint.
5. Define an SLO for a checkout API and derive the paging thresholds.

## The 60-second spoken answer

"I log structured JSON with a correlation or trace id, propagate it through HTTP and Kafka headers, and keep PII and secrets out.
In Splunk I narrow the time range and index, then `stats count by service, exception` to find the dominant error, `timechart` to see when it started,
`p95(duration_ms) by endpoint` for latency, and a correlation-id search to follow one request. Metrics detect, traces locate, logs explain; I alert on
SLO burn rate and symptoms rather than raw CPU, and I use percentiles because averages hide the tail."
