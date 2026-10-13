---
id: 14-observability
title: Observability - Splunk, Grafana, Prometheus (+ your Datadog & CloudWatch)
focus: Zero-experience tools; explain concepts via Datadog/CloudWatch you have used, plus SLOs and alerting
---
You have used Datadog and CloudWatch. Splunk (logs), Prometheus (metrics) and Grafana (dashboards) solve the same problems. Learn the vocabulary below and map: Datadog metrics = Prometheus + Grafana; Datadog/CloudWatch Logs = Splunk; Datadog APM = Tempo/Jaeger/OpenTelemetry.

### Q1 [basic] What are metrics, logs and traces?
Metrics: numbers over time (cheap, good for alerting). Logs: detailed events (good for "what happened"). Traces: one request's path through services with timings (good for "where is it slow"). Use a shared `traceId` to jump between the three.

### Q2 [basic] What is Prometheus and how does it collect data?
An open-source time-series database and alerting system that **pulls** (scrapes) `/metrics` over HTTP from targets at an interval. Targets are found by service discovery (Kubernetes). Data model: metric name + labels, queried with **PromQL**. Short-lived jobs push to a Pushgateway. Long-term storage via Thanos/Mimir/Cortex.

### Q3 [intermediate] Prometheus metric types?
Counter (only goes up: requests_total), Gauge (up/down: queue size), Histogram (bucketed observations: latency; aggregable across instances), Summary (client-side quantiles; not aggregable). Prefer histograms for latency SLOs.

### Q4 [intermediate] Write the PromQL you use most.
```promql
# requests per second per service
sum by (service) (rate(http_server_requests_seconds_count[5m]))
# error ratio
sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m]))
  / sum(rate(http_server_requests_seconds_count[5m]))
# p95 latency from a histogram
histogram_quantile(0.95, sum by (le) (rate(http_server_requests_seconds_bucket[5m])))
```
Use `rate()` on counters, never graph a raw counter.

### Q5 [intermediate] How do you expose Prometheus metrics from Spring Boot?
Add Actuator + `micrometer-registry-prometheus`; expose `/actuator/prometheus`. Micrometer provides JVM, HTTP, datasource (Hikari), Kafka and custom metrics (`Counter`, `Timer`, `Gauge`). Tag with low-cardinality labels only (route template, status) - **never** userId/orderId/raw URL.

### Q6 [intermediate] What is Grafana and what do you build in it?
A visualisation and alerting tool that queries many data sources (Prometheus, Loki, Elasticsearch/OpenSearch, CloudWatch, Datadog, SQL, Tempo). You build dashboards (panels, variables for env/service), alert rules and annotations (deploy markers). Dashboards-as-code (JSON/Terraform/Grafonnet) keep them reviewable.

### Q7 [intermediate] Which dashboards do you build first for a service?
Golden signals / RED: **Rate**, **Errors**, **Duration** per endpoint; **saturation**: CPU, memory, GC pause, thread pool and connection pool usage, queue/consumer lag. Plus dependencies (DB, downstream latency), deploy markers, and JVM heap after GC.

### Q8 [basic] What is Splunk and what is SPL?
A platform to ingest, index, search and analyse machine data (logs, events, metrics). Forwarders ship logs to indexers; search heads run queries in **SPL** (Search Processing Language). Used heavily for security and operations in large enterprises.

### Q9 [intermediate] Write a few Splunk SPL examples.
```
index=prod sourcetype=app service=orders level=ERROR earliest=-15m
| stats count by exception, host
| sort - count

index=prod service=orders | timechart span=1m avg(duration_ms) p95(duration_ms)

index=prod traceId="abc123" | sort _time
```
Mapping: `stats` ~ SQL `GROUP BY`; pipes pass results to the next command. Also `rex` (regex extraction), `eval`, `top`, `transaction`, `dedup`.

### Q10 [intermediate] How do you design logging so it works in Splunk/ELK/Datadog?
Structured JSON logs (one event per line) with `timestamp`, `level`, `service`, `env`, `traceId`, `spanId`, `userId` (hashed if sensitive), `event`, `durationMs`; log to stdout in containers; consistent levels; no secrets/PII; sample noisy logs; set retention by value. Use MDC for correlation ids.

### Q11 [intermediate] What is OpenTelemetry and why does it matter?
A vendor-neutral standard (API/SDK/Collector) for traces, metrics and logs. Instrument once (Java agent or Micrometer tracing), send via the **OTel Collector** to Datadog, Grafana Tempo/Prometheus, Splunk or X-Ray without changing code. Propagates `traceparent` over HTTP and Kafka headers.

### Q12 [intermediate] What is an SLI, SLO, SLA and error budget?
SLI = a measured indicator (percent of requests < 300 ms and non-5xx). SLO = target (99.9% over 30 days). SLA = contract with penalties. Error budget = `1 - SLO` (43 minutes per 30 days at 99.9%); spend it on releases, freeze risky changes when it is burned.

### Q13 [advanced] How do you write good alerts and avoid alert fatigue?
Alert on **symptoms users feel** (error rate, latency SLO burn) rather than every cause (CPU 80%). Use multi-window burn-rate alerts (fast: 5m+1h; slow: 6h+3d). Every alert must be actionable, have an owner and a runbook link, severity levels (page vs ticket), and be reviewed after incidents; delete noisy ones.

### Q14 [advanced] Cardinality - what is it and why can it take Prometheus down?
Each unique label combination is a separate time series. Labelling by `userId` or full URL creates millions of series -> memory blow-up and slow queries. Use route templates and bounded enums; put per-entity detail in logs/traces.

### Q15 [intermediate] How would you monitor a Kafka consumer service?
Metrics: consumer lag, records/sec, processing duration histogram, error and DLT counts, rebalances; JVM/pool metrics; logs with topic/partition/offset on failure; a lag alert that fires when lag keeps increasing for N minutes; trace context carried in message headers.

### Q16 [intermediate] Datadog / CloudWatch you've used: how do they map?
Datadog agent/APM ~ OTel + Prometheus + Tempo; Datadog dashboards/monitors ~ Grafana dashboards/alert rules; CloudWatch Logs Insights ~ Splunk SPL/Loki LogQL; CloudWatch alarms ~ Prometheus Alertmanager. Be ready to describe a real incident you solved with them.

### Q17 [advanced] What is Alertmanager?
Receives alerts from Prometheus, then deduplicates, groups, silences, inhibits and routes them to Slack, PagerDuty or email by label. Configuration controls who is paged and avoids alert storms.

### Q18 [design] Design the observability platform for a 30-service Kubernetes estate.
Micrometer/OTel in every service -> OTel Collector DaemonSet -> metrics to Prometheus (long-term in Mimir/Thanos), logs to Loki/Splunk/OpenSearch, traces to Tempo/Jaeger -> Grafana as the single pane with data-source links by `traceId` -> Alertmanager to PagerDuty/Slack -> SLO dashboards per team -> cost controls (sampling, retention tiers, label limits) -> standard library/starter that adds all of it to a new service.

### Q19 [design] A latency spike is reported at 2 a.m. - walk through the investigation using these tools.
Check the SLO dashboard (which service/endpoint, since when) -> compare with deploy markers -> look at traces for the slow spans (DB vs downstream vs CPU) -> look at saturation: pools, GC, threads, lag -> search logs by `traceId` for errors/timeouts -> mitigate first (rollback, scale, disable feature, shed load) -> then root cause and write the RCA.

### Q20 [intermediate] Honest answer: "You haven't used Splunk/Grafana/Prometheus?"
"Not hands-on. My production monitoring has been Datadog and CloudWatch - dashboards, monitors, log search and APM traces. Prometheus/Grafana/Splunk use the same ideas - metrics with labels and PromQL, SPL for logs - so the difference is syntax and operating the stack. I've set up Micrometer metrics and structured logging, and I'd pick up PromQL/SPL quickly."

### Q21 [design] Design an alerting strategy that pages on user impact and avoids alert fatigue.
Define SLIs and SLOs (availability, latency), alert on **error-budget burn rate** (multi-window, for example 5 min and 1 h) rather than on raw CPU or single errors, route by severity (page vs ticket vs dashboard), and attach a runbook link to every alert. Review alert quality monthly: delete alerts nobody acted on. Failure modes: alerting on causes not symptoms, missing 'no data' alerts, and flapping thresholds without a `for:` duration.
