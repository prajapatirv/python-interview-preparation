---
id: foundations-splunk-observability
title: Splunk & observability: from the basics (drafted)
stack: java
skill: splunk-observability
---
Drafted concepts-first answers for questions whose stored answer was too short. Each starts with the concepts in plain words, then a real scenario, then the answer. Review before relying on them.

Levels: **fresher** (0-2 yrs) · **mid** (3-6) · **senior** (6-10) · **architect** (10+).

### Q1 [fresher] What are metrics, logs and traces?
tags: observability, splunk, metrics, logs, traces, correlation-id, basics

**Start here: the concepts**
- **Observability:** how well you can understand what a running system is doing from the outside, using the data it emits. It exists because in production you cannot attach a debugger.
- **Metric:** a number sampled over time, such as requests per second, error rate or CPU %. It is small and cheap to store, so it suits dashboards and alerts. It tells you *that* something is wrong, not *why*.
- **Log:** a text record of one event ("payment declined for order 8841"). It is detailed, so it answers "what happened?". It is also bulky and costly at high volume.
- **Trace:** the recorded journey of one request through several services. It is made of **spans**, which are timed steps such as "call to the payment service took 1.8 s". It answers "where is it slow or failing?".
- **traceId / correlation id:** a unique ID created when a request enters the system and passed to every service it touches. It is sent in HTTP headers or Kafka message headers. Each service puts it in every log line, usually via the **MDC** (a per-thread map that the logging library adds to each line). It lets you gather all the evidence for one request.
- **SPL:** Splunk's search language. It is used to search and count logs.
- **SLO:** Service Level Objective, a target such as "99.9% of checkouts succeed". Alerts based on SLOs track user pain.

**The live scenario**
Checkout handles about 500 requests per second. At 10:02 an alert fires because the checkout error rate went from 0.1% to 6% (a **metric**). That says something is wrong but not where. A **trace** of a failing request shows 5 services, and the call to the inventory service is taking 8 s and timing out. The inventory **logs**, searched by that traceId, show "connection pool exhausted". The team fixes the pool size and the error rate returns to normal within minutes. Each signal answered a different question.

**What the interviewer is really checking**
Whether you know that the three signals answer different questions and work together, and whether you can say when you would reach for each one.

**How I answer it**
1. **Define each signal by the question it answers.** Metrics: "is something wrong?" Traces: "where?" Logs: "why, exactly?" This shows you understand their purpose rather than just reciting definitions.
2. **Start from metrics.** They are numbers, so storing and graphing them is cheap, and a rule like "error rate above 2% for 5 minutes" is easy to evaluate. Alert on symptoms users feel (errors, latency) rather than on every single error.
3. **Use traces to narrow down.** A trace shows the path and the time spent in each service, so you find the slow or failing hop without opening five services' logs.
4. **Use logs for the detail.** Once you know the service, the log line has the actual exception and the values involved.
5. **Link them with the shared ID.** Every service logs the traceId, so one search gathers one request's story across services:
```
index=prod traceId=abc123 | sort _time | table _time service level message
```
6. **Correct a common simplification:** logs and traces share the traceId directly. Metrics are aggregates over many requests, so they do not carry one request's ID. You usually link a metric spike to traces and logs by service name and time window.

**Trade-offs and what can go wrong**
- Metrics are cheap only if labels stay low-cardinality. A label like `userId` creates millions of separate series and can overwhelm the metrics store.
- Logs are costly. Too much DEBUG logging inflates storage and search cost, and logs may leak personal data (PII), so mask it.
- Tracing every request can be expensive, so many teams **sample** (keep a fraction).
- If a service forgets to pass the ID on, the trace breaks at that hop.
- Alerting on every error causes alert fatigue, and people start ignoring alerts.

**How I'd monitor it**
- Check that each request produces a traceId in the logs of every service. A Splunk search like `index=prod | stats count by service | where isnull(traceId)` style checks (events missing the ID) show gaps.
- Watch error rate and latency percentiles (such as p95) on a dashboard.
- Alert on SLO burn, such as a high error rate for several minutes.
- Track daily log volume per service and the retention period to control cost.

**Follow-ups to expect**
- *Which one would you check first in an incident?* -> Metrics or the alert, to confirm impact and time. Then traces to find the hop, then logs for the cause.
- *Why not just use logs for everything?* -> Counting and alerting over huge log volumes is slow and expensive, and logs don't show timing across services as clearly.
- *How does the traceId travel through Kafka?* -> The producer puts it in a message header, and the consumer reads it and sets it in the MDC before logging.

**60-second answer**
Metrics, logs and traces are the three kinds of data that let us understand a running system. Metrics are numbers over time, like error rate or latency. They are cheap, so they are good for dashboards and alerts, and they tell me something is wrong. Traces follow one request across services with timings, so they show where it is slow or failing. Logs are detailed event records, so they tell me exactly what happened and why. I connect logs and traces with a shared traceId that every service passes along and writes in its logs. In an incident I start from the metric alert, use the trace to find the slow service, then search that traceId in the logs for the root cause.

### Q2 [fresher] What is Prometheus and how does it collect data?
tags: prometheus, metrics, promql, monitoring, observability, scraping, basics

**Start here: the concepts**
- **Metric:** a number that describes system behaviour and changes over time, such as requests served, memory used or queue length. Metrics are cheap to store and good for spotting trends.
- **Time-series database:** a database built to store values together with the time they were recorded, so you can ask "what was this number over the last hour?". Prometheus is one.
- **Target:** any application or server that Prometheus watches. A Spring Boot service is a target.
- **`/metrics` endpoint:** a web page your application serves that lists its current metric values as plain text. In Spring Boot, Micrometer with Actuator exposes it at `/actuator/prometheus`.
- **Scraping (pull model):** Prometheus calls each target's `/metrics` URL over HTTP every few seconds (the scrape interval, often 15-30s) and stores what it reads. The targets do not send anything. Pulling means Prometheus notices at once when a target is down, because the scrape fails.
- **Service discovery:** in Kubernetes, pods start, stop and change IP addresses constantly. Prometheus asks the Kubernetes API for the current list of pods instead of using a hand-written list.
- **Labels:** key-value tags on a metric, such as `status="500"` or `pod="cart-7"`. The metric name plus its labels identifies one time series.
- **PromQL:** Prometheus's query language, used for dashboards and alert rules.
- **Pushgateway:** a small holding service for short-lived batch jobs. They can finish before Prometheus scrapes them, so they push their result to the gateway, and Prometheus scrapes the gateway.
- **Long-term storage (Thanos, Mimir, Cortex):** Prometheus keeps data on local disk for a limited time. These systems keep it for months or years and can combine several Prometheus servers.

**The live scenario**
Checkout runs 12 pods and handles about 800 requests/second. At 14:05 customers report slowness. Prometheus has been scraping every 15 seconds, so the dashboard shows p95 latency (the time 95% of requests beat) jumping from 300 ms to 2 s. Splitting by the `pod` label shows only one pod is affected, and its 5xx rate is climbing. Metrics told the team *what* and *where* within a minute. They then searched Splunk logs for that pod to find *why*, which turned out to be a connection pool exhausted by a slow database.

**What the interviewer is really checking**
Whether you know Prometheus is pull-based, understand metrics with labels, and know where it fits next to logs (Splunk) and traces.

**How I answer it**
1. **Define it:** Prometheus is an open-source time-series database and monitoring system. It stores numbers over time, not log text, so it answers "how much and how fast?".
2. **Explain collection:** apps expose `/metrics`, and Prometheus pulls from it at an interval. Pull keeps the apps simple and makes a dead target obvious.
3. **Explain target discovery:** in Kubernetes, service discovery finds pods automatically, so scaling up or down needs no config edits.
4. **Explain the data model:** metric name plus labels, for example:
   ```
   rate(http_server_requests_seconds_count{status="500"}[5m])
   ```
   This PromQL gives the per-second rate of 500 errors over 5 minutes.
5. **Mention alerting correctly:** Prometheus evaluates alert rules, and a separate component, Alertmanager, groups and sends the notifications.
6. **Cover the edge cases:** batch jobs use the Pushgateway, and long retention uses Thanos, Mimir or Cortex.

**Trade-offs and what can go wrong**
- **High cardinality:** putting values like user id or request id in labels creates millions of series and can exhaust memory. Labels should have few distinct values.
- **Short-lived jobs:** these are missed by scraping unless they use the Pushgateway. Overusing the Pushgateway for normal services is a mistake, because it hides whether the service is actually alive.
- **Local storage:** a single Prometheus is limited by disk and retention, so use remote storage for long history.
- **Metrics show symptoms, not causes:** you still need logs and traces to find the root cause.
- **Scrape interval:** too long and you miss short spikes. Too short and you add load and storage cost.

**How I'd monitor it**
- Check the Targets page, or the `up` metric, which is 1 when a scrape succeeds and 0 when it fails. Alert on `up == 0`.
- Watch Prometheus's own health: scrape duration, number of time series, disk usage and rule evaluation failures.
- Alert on user-facing symptoms (error rate, latency) rather than every internal blip.
- Link dashboards to Splunk searches by service and time so you can go from a metric spike to the matching logs.

**Follow-ups to expect**
- *Why pull instead of push?* -> Prometheus controls the load and the interval, and a failed scrape shows a target is down. The downside is that short-lived jobs need the Pushgateway.
- *Prometheus vs Splunk?* -> Prometheus stores cheap numeric metrics for trends and alerts. Splunk stores detailed log events for investigating individual requests.
- *What is the danger of high-cardinality labels?* -> Each unique label combination creates a new series, so unbounded values like user ids blow up memory and slow queries.

**60-second answer**
Prometheus is an open-source time-series database for metrics, which are numbers like request counts and latency tracked over time. It works on a pull model: each application exposes a `/metrics` page, and Prometheus scrapes it over HTTP every 15 seconds or so. In Kubernetes it finds pods through service discovery, so new pods are picked up automatically. Each metric has a name and labels, and I query it with PromQL, for example the rate of 500 errors per pod. Prometheus evaluates alert rules, and Alertmanager sends the notifications. Short batch jobs push to a Pushgateway, and for long-term storage I would add Thanos, Mimir or Cortex. Metrics tell me what is wrong and where, and then I use logs and traces to find the cause.

### Q3 [mid] Prometheus metric types?
tags: prometheus, metrics, histogram, counter, gauge, observability, basics

**Start here: the concepts**
- **Metric:** a number measured repeatedly over time, such as requests served or queue length. Metrics are cheap to store and good for graphs and alerts. They tell you *that* something is wrong, not *which request* failed (that is what logs and traces are for).
- **Prometheus:** a monitoring system that regularly "scrapes" (reads) a `/metrics` page from each app instance and stores the values as time series.
- **Counter:** a number that only increases, such as `http_requests_total`. It resets to zero when the process restarts. You almost never graph the raw value. You graph its rate of change with `rate()`, which also handles the resets.
- **Gauge:** a number that can go up and down, such as queue size, memory in use or active connections. It is a snapshot of "right now".
- **Histogram:** instead of storing every measurement, it counts how many observations fell into predefined ranges ("buckets"), for example "under 100 ms", "under 500 ms", "under 1 s". Buckets are cumulative, and each bucket is a counter. Because they are plain counters, you can add them across instances.
- **Summary:** the app itself calculates quantiles (such as the 99th percentile) and exposes the finished numbers. Quantiles from different instances cannot be correctly combined, so summaries are not aggregable.
- **Percentile / quantile:** p99 = 1.2 s means 99% of requests were faster than 1.2 s. It shows the slow tail that an average hides.
- **SLO (service level objective):** a target such as "99% of requests under 500 ms". It is measured with latency percentiles or bucket counts.

**The live scenario**
A checkout service runs on 12 pods. The team exposed latency as a Summary and the dashboard averaged each pod's p99, showing about 180 ms. Meanwhile customers complained about timeouts. One pod had a p99 of 4 s because of a bad connection pool, and averaging with 11 healthy pods hid it. After switching to a histogram, the combined p99 across all pods showed about 1.2 s, and the SLO breach was obvious. (Numbers are illustrative.)

**What the interviewer is really checking**
Do you know when each type fits, and do you understand *why* histograms beat summaries for latency in a multi-instance system (aggregation)?

**How I answer it**
1. **Counter for things that only accumulate** (requests, errors, bytes). The reason is that a total survives missed scrapes, and `rate()` turns it into "per second" and copes with restarts.
2. **Gauge for current levels** (queue depth, heap used, in-flight requests). The reason is that the value is meaningful on its own and does not need a rate.
3. **Histogram for latency and sizes.** Each bucket is a counter, so you can sum buckets across all pods and then compute a percentile on the server:
   `histogram_quantile(0.99, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))`
4. **Summary only when you need exact quantiles from one instance** and will never combine instances. The reason is that quantiles computed on the client are fixed at startup and cannot be averaged or summed meaningfully.
5. **Choose buckets around your SLO.** If the target is 500 ms, make sure a bucket boundary sits at 0.5 s. Percentiles are only estimates, interpolated inside a bucket.

**Trade-offs and what can go wrong**
- Histograms cost more storage: one time series per bucket, per label combination. Summaries are cheaper per series but cannot be aggregated.
- Poorly placed buckets give inaccurate percentiles.
- High-cardinality labels (user id, full URL) multiply series and can overload Prometheus. Use route templates, not raw paths.
- Graphing a raw counter, or taking `rate()` of a gauge, gives misleading results.
- Averaging percentiles across instances is a common and serious mistake.

**How I'd monitor it**
- Alert on SLO symptoms, such as p99 above 500 ms for 10 minutes or an error ratio computed from counters, rather than on every error.
- Watch Prometheus's own series count and scrape duration to catch cardinality blowups.
- Use metrics to spot the problem, then pivot to Splunk with the time window and correlation id to find the failing requests, for example `index=app service=checkout level=ERROR | timechart count by pod`.

**Follow-ups to expect**
- *Why can't you average p99 across pods?* -> A percentile depends on the full distribution, so averaging p99 values gives a number that corresponds to no real set of requests. Histogram buckets can be summed first.
- *Why use `rate()` on a counter?* -> It converts the ever-growing total into a per-second value and handles counter resets after restarts.
- *Metrics vs logs vs traces?* -> Metrics show how much and how fast, logs show what happened to one request, and traces show where time went across services.

**60-second answer**
Prometheus has four metric types. A counter only goes up, such as requests_total, and I view it through rate() because it resets on restart. A gauge goes up and down, like queue size or memory. A histogram counts observations in buckets, which suits latency, and because buckets are plain counters I can sum them across all instances and compute a percentile with histogram_quantile. A summary calculates quantiles inside the app, which is accurate for one instance but cannot be aggregated across instances. So for latency SLOs I prefer histograms, with buckets placed around my target, and I keep labels low-cardinality to control cost.

### Q4 [mid] Write the PromQL you use most.
tags: promql, prometheus, metrics, micrometer, rate, histogram, observability, basics

**Start here: the concepts**
- **Metric:** a number sampled over time, such as "total requests so far". Metrics are cheap to store and good for alerts and trends. Logs and traces tell you *which* request failed; metrics tell you *that* something is wrong.
- **Prometheus and PromQL:** Prometheus scrapes (polls) services every few seconds and stores the numbers. PromQL is its query language.
- **Counter:** a number that only goes up, and resets to 0 on restart. `http_server_requests_seconds_count` is one. The raw value ("4,000,000 requests since boot") says little about the present.
- **`rate(x[5m])`:** the per-second increase of a counter over the last 5 minutes. It also handles restart resets.
- **Label:** a key/value tag on a series, such as `status="500"`. `sum by (service)` adds series together and keeps one line per label value.
- **Histogram:** latency counted into buckets ("≤ 0.1s", "≤ 0.5s"...). The `le` label means "less than or equal". `histogram_quantile(0.95, ...)` estimates the value 95% of requests were faster than (p95).
- **Micrometer:** the Spring Boot metrics library that creates these metric names.

**The live scenario**
A checkout API handles about 800 requests/s. Users say it is "slow sometimes". The raw counter graph only climbs and shows nothing. Plotting `rate()` shows traffic is normal. The error ratio is 4% (illustrative), and p95 has jumped from 300 ms to 2.5 s. The average hid this. We then take one failing request's correlation id to Splunk to find the cause.

**What the interviewer is really checking**
Whether you know the three golden signals (traffic, errors, latency) and the right PromQL for each. Specifically: `rate()` on counters, summing before dividing, and `histogram_quantile` on buckets.

**How I answer it**
1. Traffic per service:
2. Error ratio, errors divided by all requests:
3. p95 latency:
```promql
sum by (service) (rate(http_server_requests_seconds_count[5m]))
sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m])) / sum(rate(http_server_requests_seconds_count[5m]))
histogram_quantile(0.95, sum by (le) (rate(http_server_requests_seconds_bucket[5m])))
```
4. **Use `rate()` on counters, and don't graph the raw value.** A raw counter only grows, so it hides the current speed. `rate()` gives requests per second now. The raw value is only useful for debugging.
5. **Error ratio:** `status=~"5.."` is a regex for any 5xx code. Sum the numerator and denominator separately, then divide. This gives a true ratio, not an average of averages.
6. **p95:** `rate()` on `_bucket` gives bucket speeds. `sum by (le)` merges instances and **must keep `le`**, or the quantile cannot be computed. The result is an estimate, as accurate as the bucket boundaries allow.
7. **Corrections to the stored answer:** the `service` label is not automatic. It comes from scrape config or Micrometer common tags (often `application`). `_bucket` series exist only if histograms are enabled, e.g. `management.metrics.distribution.percentiles-histogram.http.server.requests=true`.

**Trade-offs and what can go wrong**
- The error-ratio query has no `by`, so it is global. Use `sum by (service)` on both sides for per-service ratios, and add `service` to the p95 grouping too.
- If there are no 5xx series, the numerator is empty and the result shows "no data", not 0. Handle it with `or vector(0)` in alerts.
- Keep the `rate` window at least about 4× the scrape interval. Shorter windows are noisy and longer ones react slowly.
- Never average percentiles across services. Aggregate buckets first.
- High-cardinality labels (user id, full URL) make Prometheus memory explode.

**How I'd monitor it**
Alert on symptoms, i.e. SLOs: error ratio above 1% for 10 minutes, or p95 above target. Don't alert on every error. Put the three queries on a dashboard, then jump to Splunk (`index=app correlationId=...`) to explain a spike. Watch the Prometheus series count and scrape failures too.

**Follow-ups to expect**
- *Why not `avg` latency?* -> It hides the slow tail. A few 5-second calls barely move the average but hurt real users.
- *`rate` vs `increase`?* -> `increase` is the total over the window. `rate` is that total divided by the seconds in the window.
- *Metrics vs logs vs traces?* -> Metrics say something is wrong, traces show where time went, and logs explain why.

**60-second answer**
"The three queries I use most are traffic, error ratio and p95 latency. Traffic is `sum by (service) (rate(http_server_requests_seconds_count[5m]))`. I always use `rate()` on counters because a raw counter only grows and says nothing about now. The error ratio is the rate of 5xx requests divided by the rate of all requests. For latency I use `histogram_quantile(0.95, ...)` over the `_bucket` series, summed by `le`. Buckets exist only if histograms are enabled, and I group by service for per-service views. I alert on these as SLO symptoms, then use the correlation id in Splunk to find the cause."

### Q5 [mid] How do you expose Prometheus metrics from Spring Boot?
tags: prometheus, micrometer, spring-boot, actuator, metrics, cardinality, basics

**Start here: the concepts**
- **Metric**: a number measured over time, such as requests per second or the 99th-percentile latency. It is cheap to store and good for answering "is something wrong, and how bad?". Logs explain why, and traces show where in a call chain.
- **Prometheus**: a time-series database that *pulls* (scrapes) a plain-text page from each service every ~15-30 seconds and stores the numbers. Your app does not push anything.
- **Spring Boot Actuator**: a Spring Boot module that adds operational HTTP endpoints (health, info, metrics) to your app.
- **Micrometer**: the metrics facade inside Spring Boot. You write metrics once against its API, and a "registry" library translates them into a backend's format. `micrometer-registry-prometheus` is the Prometheus translator.
- **Counter, Timer, Gauge**: a Counter only goes up (orders placed). A Timer records how long something took and how often. A Gauge is a value that moves up and down (queue size).
- **Tag (label)**: a key-value pair on a metric, such as `status=500`. Each distinct combination of tag values creates a separate time series in Prometheus.
- **Cardinality**: the number of distinct tag combinations. High cardinality means millions of series, which exhausts Prometheus memory and storage.

**The live scenario**
A checkout service handles about 800 requests/second. A developer adds a custom counter `orders_total` tagged with `orderId`, so there is a new series for every order. Within a day the 3M new orders create 3M series. Prometheus memory climbs, queries time out, and the on-call dashboards go blank during peak traffic. The fix is to remove `orderId` and tag by `status` and `paymentType` only, which is about 10 series. The order id belongs in the logs, where Splunk can search it.

**What the interviewer is really checking**
Whether you know the wiring (dependency, endpoint exposure, scraping) and, more importantly, whether you understand label cardinality, the most common way metrics break production.

**How I answer it**
1. **Add `spring-boot-starter-actuator` and `micrometer-registry-prometheus`.** Actuator provides the endpoint and Micrometer supplies the Prometheus format.
2. **Expose the endpoint explicitly.** Over HTTP, Actuator exposes only `health` by default, so `/actuator/prometheus` returns 404 until you enable it:
   ```properties
   management.endpoints.web.exposure.include=health,prometheus
   management.server.port=9090
   ```
   A separate management port keeps metrics off the public API, and you can firewall it.
3. **Point Prometheus at `/actuator/prometheus`** as a scrape target. Prometheus pulls the text page, so the service needs no knowledge of Prometheus.
4. **Rely on the built-in metrics first.** Boot auto-registers JVM (heap, GC, threads), HTTP server requests (`http_server_requests_seconds`), HikariCP datasource pool, and Kafka client metrics when Spring Kafka is used. These give most of the value for free.
5. **Add custom metrics for business meaning.** Use `Counter` for events, `Timer` for durations and `Gauge` for current levels, injected through `MeterRegistry`.
6. **Keep tags low-cardinality.** Use bounded values such as the route *template* (`/orders/{id}`), method and status. Never use userId, orderId or the raw URL, because each unique value creates a new series.

**Trade-offs and what can go wrong**
- Forgetting step 2 is the classic "endpoint 404" mistake.
- An open metrics endpoint leaks internals, so secure it or isolate it on a management port.
- Timers give averages and counts by default. For percentiles across many instances, enable histograms (`management.metrics.distribution.percentiles-histogram.http.server.requests=true`), which costs more series.
- Because Prometheus scrapes periodically, very short spikes between scrapes can be missed.
- Metrics tell you *that* something is slow, not *why*. You still need logs and traces.

**How I'd monitor it**
- In Prometheus, check the `up` metric for each target. `up == 0` means scraping is broken.
- Watch `prometheus_tsdb_head_series` and the top metrics by series count to catch cardinality growth early.
- Alert on symptoms: the 5xx ratio from `http_server_requests_seconds_count`, p99 latency, and Hikari pending connections.
- When an alert fires, jump to Splunk with the same time window, for example `index=app service=checkout level=ERROR | timechart count`, and follow a correlation id.

**Follow-ups to expect**
- *Why is the route template safe but the raw URL not?* -> `/orders/{id}` is one value, while `/orders/123`, `/orders/124` and so on are unbounded. Spring MVC records the template in the `uri` tag by default.
- *Pull or push?* -> Prometheus pulls, so it detects dead targets, and the app stays simple. Short-lived batch jobs may need a Pushgateway.
- *Metrics vs logs vs traces?* -> Metrics show that and how much, logs show what happened to one request, traces show where time went across services.

**60-second answer**
I add the Actuator starter and `micrometer-registry-prometheus`, then expose the `prometheus` endpoint, because Actuator only exposes health over HTTP by default. Prometheus scrapes `/actuator/prometheus` on a schedule, ideally on a separate, protected management port. Micrometer gives me JVM, HTTP, Hikari and Kafka metrics out of the box, and I add Counters, Timers and Gauges for business events. The key rule is low-cardinality tags: route template, method and status are fine, but userId, orderId or raw URLs create a new time series per value and can overwhelm Prometheus. I alert on symptoms such as error ratio and p99 latency, and use logs with correlation ids in Splunk to find the cause.

### Q6 [mid] What is Grafana and what do you build in it?
tags: grafana, observability, dashboards, alerting, prometheus, metrics, basics

**Start here: the concepts**
- **Observability:** being able to tell what a running system is doing from the data it emits. That data comes in three kinds: logs, metrics and traces.
- **Metric:** a number sampled over time, such as requests per second or p95 latency. It is cheap to store and good for "is something wrong, and how badly?"
- **Log:** a text or JSON record of one event. It is good for "what exactly happened to this request?"
- **Trace:** the path of one request across services, with the time spent in each. It is good for "where was it slow?"
- **Data source:** a system that stores that data (Prometheus for metrics, Loki or Elasticsearch/OpenSearch for logs, Tempo for traces, CloudWatch, Datadog, SQL databases). Some, like Datadog, are added through plugins.
- **Grafana:** a web tool that stores almost none of this data itself. It connects to data sources, runs queries and draws the results. Its value is one screen over many systems.
- **Dashboard and panel:** a dashboard is a page of panels. Each panel is one query drawn as a graph, table or single number.
- **Variable:** a dropdown (environment, service, pod) that changes every query on the page, so one dashboard serves many services.
- **Alert rule:** a query plus a condition ("error rate above 2% for 5 minutes") that sends a notification when true.
- **Annotation:** a vertical marker on graphs, such as "deploy v1.42 at 14:03".
- **Dashboards-as-code:** dashboards kept as JSON, Terraform or Grafonnet (a Jsonnet library) in Git, so changes go through review.

**The live scenario**
An order service handles about 800 requests/s. At 14:03 a deploy goes out, and by 14:08 customers report slow checkout. On a Grafana dashboard, the p95 latency panel shows a jump from 300 ms to 2.4 s, and the deploy annotation sits exactly at the start of the jump. A `service` variable shows that only `payment-adapter` is affected. The team rolls back in 4 minutes. Without the dashboard, they would have searched logs service by service for 30 minutes.

**What the interviewer is really checking**
Do you understand that Grafana is a visualisation and alerting layer over other data stores, and do you know what a useful dashboard contains (symptoms, not just charts)? A mid-level candidate should also mention maintainability: variables and dashboards-as-code.

**How I answer it**
1. **Define it as a query-and-display layer.** Grafana does not collect data. Prometheus, Loki and the others do. This explains why one dashboard can mix metrics, logs and traces.
2. **Build dashboards around the golden signals:** traffic, errors, latency and saturation (CPU, memory, Kafka consumer lag). These answer "are users hurt?" before "which server is sick?"
3. **Add variables** for environment, service and instance. One templated dashboard replaces ten copies that drift apart.
4. **Add annotations** for deploys and config changes. Most incidents follow a change, so seeing the marker beside the spike speeds up diagnosis.
5. **Create alert rules on symptoms and SLOs,** for example "p95 latency over 1 s for 5 minutes", not on every single error. Alerts that fire constantly get ignored.
6. **Keep dashboards in Git** (JSON, Terraform provider or Grafonnet). Changes are reviewed, versioned and restorable, and a lost Grafana instance can be rebuilt.
7. **Link the signals.** From a latency spike, jump to logs filtered by the same time range and correlation id, then to the trace.

**Trade-offs and what can go wrong**
- Too many panels: nobody can read the page during an incident. Put the key symptoms at the top.
- Heavy queries over long ranges slow the dashboard and load the data source.
- High-cardinality labels (user id as a metric label) can overload Prometheus.
- Alerts on causes (CPU 80%) create noise. Alert on user-visible symptoms.
- Click-edited dashboards drift and are lost. Provision them from code.
- Grafana is not a log store, so retention, cost and PII masking belong to the underlying data source.

**How I'd monitor it**
- Watch dashboard query latency and data source error rates.
- Track alert quality: how many alerts fired, how many were actionable, and time to acknowledge.
- Review stale dashboards and unused alert rules each quarter.
- Confirm alert delivery with a test notification to the on-call channel.

**Follow-ups to expect**
- *Grafana vs Splunk?* -> Splunk stores and searches logs with SPL. Grafana mainly visualises data from many sources. Splunk can be used as one of those sources, depending on plugin or edition.
- *Logs vs metrics vs traces, which do you open first?* -> Metrics to detect and scope the problem, traces to locate the slow hop, logs to see the exact error.
- *How do you avoid alert fatigue?* -> Alert on SLO or symptom thresholds with a "for" duration, route by severity, and delete alerts that nobody acts on.

**60-second answer**
Grafana is a visualisation and alerting tool that sits on top of data sources such as Prometheus, Loki, Elasticsearch, CloudWatch and Tempo. It does not store the data. It queries it and draws it. I build dashboards with panels for traffic, errors, latency and saturation, and use variables for environment and service so one dashboard serves many services. I add deploy annotations so I can see whether a spike follows a release. I set up alert rules on symptoms, like p95 latency over a threshold for five minutes, rather than on every error. I keep everything as code in Git, using JSON, Terraform or Grafonnet, so changes are reviewed and recoverable.

### Q7 [mid] Which dashboards do you build first for a service?
tags: splunk, observability, dashboards, red-method, golden-signals, saturation, jvm, basics

**Start here: the concepts**
- **Dashboard**: one screen of charts that answers "is this service healthy right now, and if not, where is it hurting?" It exists so you do not search logs by hand during an incident.
- **RED method**: three numbers per endpoint. **Rate** is requests per second, **Errors** is the share (or count) of failed requests, and **Duration** is how long requests take. It describes what users experience.
- **Golden signals**: Google's SRE list of latency, traffic, errors and saturation. RED is basically the first three, so the stored answer's "golden signals / RED" is two related ideas, not one. Saturation is the extra one.
- **Saturation**: how full a limited resource is: CPU, memory, a thread pool, a connection pool, a queue. Near 100% means requests start waiting.
- **Percentiles (p50/p95/p99)**: p99 = 99% of requests were faster than this. Averages hide slow tail requests, so use percentiles for Duration.
- **GC pause and heap after GC**: the JVM periodically stops to free memory (garbage collection). "Heap after GC" is the memory still in use after cleanup. If it keeps climbing, you likely have a leak.
- **Thread pool / connection pool**: fixed sets of workers or database connections. When all are busy, new requests queue up.
- **Consumer lag**: for Kafka, how many messages the consumer is behind the latest message. Growing lag means consumers cannot keep up.
- **Deploy marker**: a vertical line on a chart showing when a release happened, so you can see "it broke right after v2.4".

**The live scenario**
Payments API: about 400 requests/sec, normally p99 of 300 ms. At 14:05 users report timeouts. The old dashboard showed only average latency (120 ms, looks fine) and CPU (40%). A new dashboard shows p99 at 4 s on `/pay` only, a deploy marker at 14:02, DB connection pool at 100% in use, and downstream bank-API latency doubled. In five minutes the team sees that the new release added a slow query holding connections. They roll back.

**What the interviewer is really checking**
Whether you know the difference between user-facing symptoms (RED) and resource causes (saturation, dependencies), and whether you can name the first charts you would open during an incident.

**How I answer it**
1. **Start with RED per endpoint.** Rate, error %, and p50/p95/p99 duration. Reason: these show user pain first, and per-endpoint splitting shows which API is the problem.
2. **Add saturation next.** CPU, memory, GC pause, thread pool use, connection pool use, and queue/consumer lag. Reason: these explain *why* latency rose, and they often warn before users feel it.
3. **Add JVM health.** Heap after GC, GC pause time. Reason: a rising post-GC floor means a leak, and long pauses show up as latency spikes.
4. **Add dependencies.** DB query time, downstream call latency and errors. Reason: many "our service is slow" incidents are really someone else's slowness.
5. **Overlay deploy markers.** Reason: the most common cause of a sudden change is a release or config change.
6. **Layout: symptoms on top, causes below.** Reason: whoever is on call reads top to bottom and narrows down.

Example SPL for the error-rate panel:
```
index=app service=payments | timechart span=1m count as total, count(eval(status>=500)) as errors
```

**Trade-offs and what can go wrong**
- Averages hide tail latency. Use percentiles.
- Too many charts mean nobody reads them. Keep the first dashboard to about 10 panels.
- Searching raw logs for every refresh is slow and costly in Splunk. Use summary or metrics indexes for high-volume panels.
- Dashboards show what already happened. Alerts should fire on symptoms (error rate, p99 against the SLO), not on every error.
- Never put PII in the log fields that feed dashboards.

**How I'd monitor it**
Check that each panel has an owner and an alert behind it. Alert on p99 above the SLO, error rate above a threshold, pool usage above ~80%, and sustained consumer lag growth. Review the dashboard after each incident: did it show the cause fast? If not, add the missing panel.

**Follow-ups to expect**
- *Why percentiles instead of averages?* -> The average hides the slowest users. One request at 10 s barely moves it, but p99 shows it.
- *Logs, metrics or traces: which for the dashboard?* -> Metrics for trends and alerts, logs for details of one failure, traces for where time went across services.
- *How do you find the cause once the dashboard shows a problem?* -> Take a failing correlation id and search it in Splunk across all services.

**60-second answer**
I build RED first: request rate, error percentage and p50/p95/p99 duration per endpoint, because that is what users feel. Next comes saturation: CPU, memory, GC pause, thread and connection pool usage, and Kafka consumer lag, since those usually explain the slowness. I add JVM heap after GC to spot leaks, and dependency panels for DB and downstream latency. I overlay deploy markers because many incidents start with a release. Symptoms go at the top and causes below, and alerts fire on the SLO rather than on every error. I keep it small so on-call can read it in seconds.

### Q8 [fresher] What is Splunk and what is SPL?
tags: splunk, spl, logging, observability, forwarder, indexer, basics

**Start here: the concepts**
- **Machine data:** Text and numbers that software produces on its own, such as log lines, events, and metrics (measurements like CPU use or requests per second). It is the main record of what a system actually did.
- **Log:** A line an application writes when something happens, for example "payment 123 failed". With 40 servers you cannot open each file by hand, so you need one central place to search them all.
- **Splunk:** A platform that collects machine data from many servers, stores it so it can be searched quickly, and lets you query, chart, and alert on it.
- **Ingest and index:** *Ingest* means pulling data in. *Index* means storing it in a searchable structure, like the index at the back of a book. In Splunk, "an index" is also the name of a named data store, such as `index=prod_app`.
- **Forwarder:** A small agent on each application server that reads log files and sends them to Splunk.
- **Indexer:** The Splunk server that receives data, parses it, and stores it.
- **Search head:** The part you use in the browser. It sends your query to the indexers and shows the results.
- **SPL (Search Processing Language):** Splunk's query language. You write a search, then chain steps with the pipe `|`, like a Unix shell. Each step takes the previous step's results and filters, counts, or reshapes them.

**The live scenario**
It is 10:05 on a Monday. Customers say checkout is failing. The checkout service runs on 30 servers, and together they write about 20 million log lines an hour. Nobody can log into 30 machines and grep files. Because forwarders ship every log to Splunk, an engineer opens the search head and, within a minute, sees that errors jumped from about 20 per minute to about 900 per minute, starting at 10:01, all from one service. Without central logs, finding that could take an hour.

**What the interviewer is really checking**
Whether you understand why central log search exists and can name the pieces (forwarder, indexer, search head) in order. Also whether you know SPL is a pipeline of steps, not SQL.

**How I answer it**
1. **Define Splunk by its job.** It ingests, indexes, searches, and analyses machine data (logs, events, metrics). The reason is that logs scattered over many servers are useless in an incident.
2. **Walk the data path.** Forwarders on the app servers ship data to indexers, which parse and store it. A search head sends your queries to the indexers and shows results. Splitting the roles lets each part scale on its own: add indexers for more data, add search heads for more users.
3. **Define SPL.** You start with a search (which index, which words), then pipe the results through commands. Each pipe does one small job, so complex questions are built from simple steps.
4. **Show one tiny example.** It counts errors per service in the last 15 minutes:
```
index=prod_app level=ERROR earliest=-15m | stats count by service | sort -count
```
5. **Say where it is used.** Large enterprises use it heavily for operations (finding and fixing production problems) and security (spotting suspicious activity), because both start with "what happened, and when?"

**Trade-offs and what can go wrong**
- Splunk is usually licensed by the amount of data ingested per day, so logging everything at DEBUG gets expensive. Choose log levels deliberately.
- Logs can contain personal data such as card numbers or emails. Mask it before it is written, because it is hard to remove once indexed.
- Unstructured logs are hard to search. Structured logs (key=value or JSON) with a correlation id make searches far easier.
- Splunk answers "what happened?" well, but metrics and traces are often better for "how is it trending?" and "where is the time spent?".

**How I'd monitor it**
- Watch daily ingest volume per index against the licence.
- Check forwarder health: a silent server may mean a broken forwarder, not a quiet app. A search like `| tstats count where index=* by host` shows which hosts are still sending.
- Alert on symptoms such as error rate or latency, not on every single error.

**Follow-ups to expect**
- *Is SPL the same as SQL?* -> No. SQL queries tables. SPL starts with a time-ordered stream of events and pipes it through commands like `stats` and `timechart`.
- *What is a correlation id and why does Splunk need it?* -> A unique id put on every log line of one request, so you can search it and see that request across all services.
- *Logs vs metrics vs traces?* -> Logs say what happened, metrics show numbers over time, traces show the path and time of one request across services.

**60-second answer**
Splunk is a platform that collects machine data like logs, events, and metrics from many servers into one place, indexes it, and lets you search and analyse it. Small agents called forwarders run on the application servers and ship data to indexers, which store it. A search head is where you run queries and build dashboards. Queries are written in SPL, the Search Processing Language, which chains commands with pipes, for example searching errors and then counting them by service. Large companies use it for operations and security, because in an incident you need to see what happened across many machines quickly. I would also mention keeping logs structured, masking personal data, and controlling log volume, since cost depends on how much you ingest.

### Q9 [mid] Write a few Splunk SPL examples.
tags: splunk, spl, observability, structured-logging, correlation-id, search, basics

**Start here: the concepts**
- **Splunk**: a tool that collects logs from all your servers into one place so you can search them. Without it you would SSH into many machines and grep files.
- **SPL (Search Processing Language)**: Splunk's query language. You write a search, then chain commands with `|` (pipe). Each command takes the previous result and changes it, like Unix pipes.
- **index**: a named storage bucket for events, for example `prod`. Naming it narrows the search and makes it faster.
- **sourcetype**: a label saying what format the log has, for example `app`. Splunk uses it to find the fields.
- **Field**: a named value in a log event, such as `service`, `level` or `duration_ms`. Structured (JSON or key=value) logs make fields easy to search.
- **`stats`**: groups events and calculates numbers. `stats count by exception, host` is like SQL `SELECT exception, host, COUNT(*) ... GROUP BY exception, host`.
- **`timechart`**: like `stats`, but grouped by time buckets, so it is ready to draw as a graph.
- **p95 (95th percentile)**: 95% of requests were faster than this value. It shows slow-user pain that an average hides. In Splunk, `perc95()` is the standard name.
- **traceId / correlation id**: one id stamped on every log line of one request across all services. Searching it shows that request's whole journey.
- **Helper commands**: `rex` extracts a field with a regex, `eval` computes a new field, `top` lists the most common values, `dedup` removes duplicates, and `transaction` glues related events into one group.

**The live scenario**
At 10:02 the orders API starts returning errors to about 3% of 2,000 requests per minute. The on-call engineer doesn't know which service is at fault. In 3 searches they find the cause. First they list the top exceptions in the last 15 minutes. Then they chart latency per minute and see the p95 jump from 300 ms to 4 s at 10:01. Finally they take one failed request's traceId and read its path. The path stalls at the payment call. The fix takes minutes instead of an hour of grepping.

**What the interviewer is really checking**
Whether you can write practical searches, not just recite commands. They also want to see that you know `stats` vs `timechart`, that you use a time range and filters, and that you can follow one request with an id.

**How I answer it**
1. **Count errors by cause.** Filter early by index, service, level and time, then group. Narrow filters make the search fast and cheap.
2. **Chart latency over time.** Use `timechart` with both average and p95. The average can look fine while p95 shows the real pain.
3. **Trace one request.** Search the id and sort oldest first, because Splunk shows newest first by default. This only works if every service logs the same id.

```
index=prod sourcetype=app service=orders level=ERROR earliest=-15m | stats count by exception, host | sort - count
index=prod service=orders | timechart span=1m avg(duration_ms) perc95(duration_ms)
index=prod traceId="abc123" | sort 0 _time
```

4. **Explain the pipes.** Each `|` passes its result to the next command. `sort - count` puts the biggest counts first. `sort 0` removes sort's default limit of 10,000 results, so none are dropped.
5. **Name the helpers.** Use `rex` for fields buried in text, `eval` for derived values, `top` for quick rankings, and `dedup` to remove repeats. Use `transaction` sparingly.

**Trade-offs and what can go wrong**
- A search with no time range or index scans too much data. It is slow and expensive.
- `transaction` is memory-heavy. Prefer `stats` with `by traceId` when you can.
- `rex` on unstructured text is fragile. Log in JSON so fields exist already.
- Searching a traceId only works if the id is propagated in HTTP and Kafka headers and put into the logging context (MDC).
- Never log PII (personal data) in the logs you search.

**How I'd monitor it**
Turn the good searches into saved dashboards. Alert on symptoms, such as error rate or p95 latency above the SLO for 5 minutes, not on every single error. Track search runtime and daily ingest volume to control cost.

**Follow-ups to expect**
- *stats vs timechart?* -> `stats` groups by any field. `timechart` always groups by time and is made for graphs.
- *Why not use `transaction` for everything?* -> It is slow and memory-heavy. `stats` by id is usually cheaper.
- *How do you alert without noise?* -> Alert on SLO breaches, such as error rate over a threshold for several minutes, not on single errors.

**60-second answer**
SPL chains commands with pipes, starting from an index and filters. For errors, I search `service=orders level=ERROR` for the last 15 minutes, then `stats count by exception, host` and sort by count. For latency, I use `timechart span=1m` with average and p95, because the average hides slow requests. To follow one failed request, I search its traceId and sort by time. That only works if every service logs the same correlation id. I also use `rex`, `eval`, `top` and `dedup`, and I avoid `transaction` on big data because it is expensive. I always set a time range and index so searches stay fast and cheap.

### Q10 [mid] How do you design logging so it works in Splunk/ELK/Datadog?
tags: logging, structured-logging, splunk, elk, datadog, mdc, observability, basics

**Start here: the concepts**
- **Log event:** one record saying "this happened, at this time, in this service". Logs are what you search when something breaks.
- **Structured logging:** each event is written as key-value fields (usually JSON), not a sentence. Splunk, ELK and Datadog can then filter and count by field, so you don't parse free text with fragile regex.
- **One event per line:** a JSON object on a single line. Log shippers read line by line, so a multi-line stack trace would otherwise be split into separate events. Put the stack trace inside a field.
- **Stdout in containers:** the app prints to standard output. The platform's agent (Splunk forwarder, Fluent Bit, Datadog agent) collects it. Containers are short-lived, so log files inside them vanish.
- **Correlation id / traceId / spanId:** a traceId is one id shared by every log line of one request across all services. A spanId marks one step within that request. They let you follow a single request through many services.
- **MDC (Mapped Diagnostic Context):** a per-thread key-value map in SLF4J/Logback/Log4j. Put `traceId` in once, and the logging layout adds it to every line that thread writes.
- **PII:** personally identifiable information (email, phone, card number). It must not sit in searchable logs.
- **Sampling and retention:** sampling keeps only a fraction of very noisy events. Retention is how long logs are kept before deletion.

**The live scenario**
A payment API handles about 2,000 requests per second across 5 services. A customer says "my payment failed at 10:42". Logs are plain text, each service uses its own format, and there is no shared id. Three engineers grep for 40 minutes. In the same week the Splunk bill jumps because DEBUG logs were left on in production, and a security review finds full email addresses in logs. After the redesign, one search on a `traceId` shows the whole journey in seconds, and cost and PII risk both drop.

**What the interviewer is really checking**
Whether you treat logs as searchable data, not text: consistent fields, correlation across services, and discipline about cost and sensitive data.

**How I answer it**
1. **Write JSON, one event per line, to stdout.** Machines can parse it reliably, and the platform agent ships it with no file handling in the app.
2. **Agree one field set across all services.** Use `timestamp` (ISO-8601, UTC), `level`, `service`, `env`, `traceId`, `spanId`, `userId`, `event` (a stable name like `payment.declined`) and `durationMs` (a number, so you can average it). Shared names make one query work everywhere.
```json
{"timestamp":"2025-01-10T10:42:03Z","level":"ERROR","service":"payment","env":"prod","traceId":"a1b2","spanId":"c3","userId":"u_9f2e","event":"payment.declined","durationMs":412}
```
3. **Put the traceId in MDC at the entry point** (a servlet filter or Kafka consumer interceptor). Read it from the incoming header, or create it if missing. Every log line then carries it without developers remembering. Copy it to async threads, and pass it on in outgoing HTTP and Kafka headers, because MDC is per-thread and does not cross threads or services by itself.
4. **Use levels consistently.** ERROR means someone must act, WARN is odd but handled, INFO is business milestones, DEBUG is off in production by default. Otherwise level filters and alerts are meaningless.
5. **Keep secrets and PII out.** Never log passwords, tokens or card numbers. If you need a user identifier, use a keyed hash (HMAC) or an internal id. A plain hash of a small id space can be reversed by brute force.
6. **Sample noisy logs, never errors.** Keep, say, 1 in 100 health-check or success-path debug lines, and keep every error.
7. **Set retention by value.** Keep security and audit logs long, and ordinary application logs short (illustratively 7 to 30 days). Storage and indexing are what you pay for.

**Trade-offs and what can go wrong**
- More fields and more logging means more cost. Log events that answer questions, not every method call.
- Field names drifting between teams (`userId` vs `user_id`) break shared dashboards.
- A lost MDC in thread pools or reactive code leaves lines with no traceId.
- Free-text values inside fields (full request bodies) bring back PII and cost.
- Sampling can hide the one rare event you needed, so sample only low-value events.

**How I'd monitor it**
- Follow a failed request: `index=prod traceId=a1b2 | sort _time`.
- Check hygiene: `index=prod | stats count by service, level` to spot a service flooding DEBUG, and `index=prod NOT traceId=* | stats count by service` to find lines missing a traceId.
- Track daily ingest volume per service and alert when it jumps.
- Run a scheduled search for email or card patterns to catch PII leaks.

**Follow-ups to expect**
- *Logs vs metrics vs traces?* -> Metrics tell you something is wrong (error rate, latency), traces show where in the call chain, and logs explain why.
- *How does the traceId cross Kafka?* -> The producer writes it as a record header, and the consumer reads it and puts it into MDC before processing.
- *Why not log everything and filter later?* -> You pay for ingest and storage, noise hides signal, and more data means more PII risk.

**60-second answer**
I write structured JSON logs, one event per line, to stdout so the platform agent can ship them to Splunk, ELK or Datadog. Every service uses the same fields: timestamp, level, service, env, traceId, spanId, a hashed userId, an event name and durationMs. I set the traceId in MDC at the entry point and pass it in HTTP and Kafka headers, so one search follows a request across services. I keep log levels consistent and never log secrets or PII, and I use a keyed hash for user ids. I sample noisy low-value logs but keep all errors, and I set retention by how valuable the logs are. Then I monitor ingest volume and missing traceIds to keep it healthy and affordable.

### Q11 [mid] What is OpenTelemetry and why does it matter?
tags: opentelemetry, otel, tracing, observability, collector, splunk, basics

**Start here: the concepts**
- **Observability:** the ability to understand what a running system is doing from the data it emits. It exists because in microservices you cannot attach a debugger to production.
- **Signals:** the three kinds of data. **Logs** are timestamped event lines ("what happened?"). **Metrics** are numbers over time, such as requests per second or error rate ("is something wrong, and how much?"). **Traces** follow one request across services ("where did the time go?").
- **Span and trace:** a span is one timed step, such as one HTTP call or one DB query. A trace is the tree of spans for a single request, all sharing one **trace id**.
- **Context propagation:** passing the trace id from service to service so spans can be joined. Without it, each service only sees its own fragment.
- **`traceparent`:** the header defined by the W3C Trace Context standard. It carries the trace id and the parent span id. It travels as an HTTP header and as a Kafka record header.
- **OpenTelemetry (OTel):** an open, vendor-neutral project (CNCF) that defines how to create and export logs, metrics and traces. It exists so you are not locked into one vendor's agent or library. It has three parts:
  - **API:** what your code calls to create spans and metrics.
  - **SDK:** the implementation that samples, batches and exports the data.
  - **Collector:** a separate process that receives, processes and forwards telemetry to backends.
- **OTLP:** OTel's own wire protocol for sending telemetry.
- **Backend:** the tool that stores and displays the data (Datadog, Grafana Tempo for traces, Prometheus for metrics, Splunk, AWS X-Ray).

**The live scenario**
An order flow crosses 5 services plus a Kafka hop. Illustratively, checkout p99 jumps from 400 ms to 3 s. The company has three agents from three vendors, and each team's data has a different id format, so nobody can join them. Finding the slow step takes hours. After moving to OTel, every service emits spans with the same trace id. One trace shows 2.4 s waiting in the inventory service's DB call. Later the company changes backend, and only the Collector's exporter config changes.

**What the interviewer is really checking**
Whether you understand OTel as a standard that decouples instrumentation from backend, and whether you know how trace context travels across HTTP and Kafka. Mid-level candidates should also know the Collector's role.

**How I answer it**
1. **Define it as a standard, not a product.** It is an API, SDK and Collector for traces, metrics and logs. The reason is that it stores nothing and shows nothing, because backends do that.
2. **Instrument once.** Use the OTel Java agent (no code changes, it hooks common libraries), or Micrometer Tracing in Spring Boot (a facade that can bridge to OTel). Either way, the app code is not tied to a vendor.
   ```
   java -javaagent:opentelemetry-javaagent.jar -Dotel.service.name=orders \
        -Dotel.exporter.otlp.endpoint=http://collector:4317 -jar app.jar
   ```
3. **Send telemetry to the Collector.** It can batch, drop or mask fields, and fan out to several backends. Switching from Datadog to Grafana Tempo/Prometheus, Splunk or X-Ray then means changing Collector config, not application code. (Exporting straight from the SDK also works, but you lose central control.)
4. **Propagate context.** `traceparent` is injected into outgoing HTTP calls and Kafka record headers and read by the receiver, so a consumer's span joins the producer's trace.
5. **Link logs to traces.** Put the trace id in each log line (via MDC), so you can jump from a trace to the matching Splunk logs.

**Trade-offs and what can go wrong**
- Tracing every request is expensive, so you need sampling. Head sampling decides at the start and is cheap but may miss rare slow requests. Tail sampling in the Collector keeps slow or failed traces but needs more memory.
- Broken propagation (a custom HTTP client, an async thread pool or a non-instrumented messaging library) splits one trace into many.
- The Collector is another component to run, scale and secure.
- Telemetry can leak PII, such as URLs and query parameters in span attributes. Mask them.
- "No code change" means no change to business code, not zero configuration. Maturity also differs by signal and language, so check the Java status of logs before relying on them.

**How I'd monitor it**
- Check the Collector's own metrics: spans received, dropped and exporter failures, queue size, memory.
- Check the share of traces that span all expected services (an orphan-span ratio).
- Search Splunk for log lines missing a trace id, for example `index=app NOT trace_id=* | stats count by service`.
- Alert on symptoms, such as p99 latency and error rate against the SLO, not on every exception.
- Watch telemetry volume and cost per service.

**Follow-ups to expect**
- *Do I still need the Collector?* -> No, the SDK can export directly to a backend, but the Collector centralises sampling, masking, retries and multi-backend routing.
- *How does a trace cross Kafka?* -> The producer instrumentation writes `traceparent` into record headers, and the consumer instrumentation reads it and continues the trace.
- *OTel vs Micrometer?* -> Micrometer is the Spring-friendly metrics and tracing facade. It can use OTel underneath, so they complement each other.

**60-second answer**
OpenTelemetry is a vendor-neutral standard for producing traces, metrics and logs. It has an API and SDK for instrumenting code and a Collector for processing and forwarding the data. In Java I instrument once, with the OTel agent or Micrometer Tracing, and send data to the Collector. The Collector then routes it to Datadog, Grafana Tempo and Prometheus, Splunk or X-Ray, so changing backend is a config change, not a code change. It propagates a `traceparent` header over HTTP and Kafka headers, so one trace follows a request across all services. That is what lets me find the slow step in minutes. I watch for sampling, broken propagation and PII in attributes.

### Q12 [mid] What is an SLI, SLO, SLA and error budget?
tags: sli, slo, sla, error-budget, reliability, observability, splunk, basics

**Start here: the concepts**
- **SLI (Service Level Indicator):** a number you measure that shows whether users are having a good experience. Example: the percentage of requests that finish in under 300 ms and do not return a 5xx error. It exists so "is the service good?" has a measurable answer instead of an opinion.
- **SLO (Service Level Objective):** the target you set for an SLI over a time window. Example: 99.9% of requests are good over 30 days. It is an internal goal that tells the team how reliable "reliable enough" is.
- **SLA (Service Level Agreement):** a contract with a customer that says what happens (refunds, credits, penalties) if you miss a promise. It is a business and legal document, not an engineering target. The SLA is usually looser than the SLO, so you get a warning before you owe money.
- **Error budget:** the amount of failure the SLO allows, which is `1 - SLO`. At 99.9% over 30 days (43,200 minutes) that is 0.1%, about 43 minutes of full downtime, or the equivalent number of bad requests. It exists so that reliability and feature speed can be traded off with numbers instead of arguments.

**The live scenario**
A checkout service handles about 1,000 requests per minute, roughly 43 million per 30 days. The SLO is 99.9% good requests, so the budget is about 43,000 bad requests. A release on day 10 had a bug, and for 60 minutes about 30% of requests failed. That is about 18,000 bad requests, so 40% of the monthly budget was gone in one hour. A later slow database incident burned more. By day 20, 85% of the budget was spent. The team froze risky feature releases and worked on reliability until the window recovered. Nobody had to argue about it, because the number decided.

**What the interviewer is really checking**
Whether you know that the four terms are different things at different layers (measure, goal, contract, allowance). Also whether you can use them to make decisions, not just recite definitions.

**How I answer it**
1. **Pick the SLI from the user's view.** Measure what users feel: availability (non-5xx) and latency (under 300 ms). Do not use CPU or memory, because users do not experience those directly.
2. **Set the SLO below 100%.** 100% is impossible and very expensive. A realistic target such as 99.9% lets the team still ship changes.
3. **Compute the error budget.** `1 - SLO` over the window. At 99.9% over 30 days that is about 43 minutes. This turns reliability into a spendable amount.
4. **Spend the budget on change.** Releases, experiments and migrations all carry some risk, and the budget pays for it.
5. **Freeze when it is burned.** If the budget is nearly gone, pause risky changes and fix reliability first. The rule is agreed in advance, so it is fair and not political.
6. **Keep the SLA looser than the SLO.** For example, the SLO is 99.9% and the SLA promises 99.5%. You then react internally before you owe penalties.

A simple SLI search in Splunk:
```
index=prod app=checkout | eval good=if(status<500 AND duration_ms<300,1,0) | stats sum(good) as good count as total | eval sli=round(100*good/total,3)
```

**Trade-offs and what can go wrong**
- An SLO that is too strict slows delivery and costs a lot. One that is too loose hides real pain.
- A bad SLI, such as server CPU, can look green while users suffer.
- Counting health-check or bot traffic distorts the percentage.
- An SLA written with no matching SLO means you find out about a breach from the customer.
- If nobody enforces the freeze, the error budget is just decoration.

**How I'd monitor it**
- Track the SLI as a metric (request count, error count, latency histogram). Logs in Splunk work as well, but metrics are cheaper and faster for this.
- Show the remaining error budget and the 30-day trend on a dashboard.
- Alert on burn rate: for example, page if the budget is being spent 10x faster than planned for the last hour. Do not page on every single error.
- Review the budget in release planning.

**Follow-ups to expect**
- *Why not alert on every error?* -> A few errors are expected and affordable. Alert when the burn rate threatens the SLO, which is a symptom users feel.
- *What is the difference between SLO and SLA?* -> The SLO is an internal target. The SLA is an external contract with penalties, and it is usually looser.
- *What is a burn rate?* -> How fast you consume the budget compared with an even spend. A burn rate of 1 uses exactly the whole budget by the end of the window.

**60-second answer**
An SLI is a measurement of user experience, like the percentage of requests that are under 300 ms and not 5xx. An SLO is the target for that SLI, for example 99.9% over 30 days. An SLA is the customer contract with penalties, and it should be looser than the SLO so I get warned first. The error budget is `1 - SLO`, which at 99.9% is about 43 minutes per 30 days. I spend that budget on releases and changes, and if it is nearly burned I freeze risky changes and fix reliability. I alert on how fast the budget is burning, not on every single error.

### Q13 [senior] How do you write good alerts and avoid alert fatigue?
tags: splunk, alerting, slo, burn-rate, observability, on-call, basics

**Start here: the concepts**
- **Alert**: an automatic message, such as a page, SMS or ticket, sent when a condition is true. It exists so humans look at the system only when needed.
- **Alert fatigue**: when on-call people get so many alerts, mostly useless, that they start ignoring them, including the real ones.
- **Symptom vs cause**: a symptom is what users feel (checkout fails, pages are slow). A cause is an internal condition that might lead to one (CPU at 80%, a pod restart). Causes often cause no user harm, so alerting on them produces noise.
- **SLI**: a measured number describing service health, for example "the share of requests that succeed".
- **SLO**: the target for an SLI, for example "99.9% of requests succeed over 30 days".
- **Error budget**: the failure the SLO allows. With 99.9%, 0.1% of requests may fail.
- **Burn rate**: how fast you spend the budget. Burn rate 1 uses exactly the whole budget in 30 days. Burn rate 14.4 uses 2% of it in one hour.
- **Multi-window alert**: the alert fires only if a long window (shows it is real) and a short window (shows it is still happening) both exceed the threshold. This avoids paging for old, already-finished problems.
- **Page vs ticket**: a page wakes someone now. A ticket is handled in working hours.
- **Runbook**: a short document saying what the alert means, how to check it and how to fix it.

**The live scenario**
A checkout team had 120 alerts a week, about 90% of them noise (CPU spikes, single pod restarts, one-off 500s). On-call people muted the channel. One night payment errors hit 5% for 40 minutes. The page was buried under CPU alerts and customers complained first. The team rebuilt alerting around the checkout SLO (99.9% success). They went down to 6 alerts, each with an owner and a runbook. The next payment-provider slowdown paged within 5 minutes, and the runbook told the responder to switch to the backup provider.

**What the interviewer is really checking**
Whether you treat alerting as a design problem tied to user impact (SLOs, severity, ownership, continuous cleanup) rather than "add an alert for every error".

**How I answer it**
1. **Alert on symptoms users feel.** Use error rate and latency against the SLO. Reason: if users are hurt, someone must act. If CPU is at 80% and users are fine, nobody needs waking. Keep cause metrics on dashboards for diagnosis.
2. **Use burn-rate alerts with two windows.** A fixed threshold like "errors > 1%" is either too noisy or too slow. Burn rate asks how fast the budget is vanishing. The Google SRE Workbook suggests:
   - **Page:** burn rate 14.4 over 1h and 5m (fast, severe outage).
   - **Page:** burn rate 6 over 6h and 30m (slower but serious burn).
   - **Ticket:** burn rate 1 over 3d and 6h (a slow leak).

   The short window makes the alert clear quickly once the problem stops.
3. **Make every alert actionable.** Ask: "what would the responder do right now?" If the answer is "nothing", delete it or turn it into a dashboard panel. This is the main defence against fatigue.
4. **Give every alert an owner and a runbook link.** An alert nobody owns decays. The runbook cuts diagnosis time at 3 a.m.
5. **Set severity.** Page only for user-visible, urgent harm. Everything else becomes a ticket or a daily digest.
6. **Review after incidents and monthly.** Ask whether the alert fired, whether it was useful, and what was noisy. Delete or tune the noisy ones. Alerts need maintenance like code.

Illustrative Splunk base search for the error-rate symptom:
```
index=prod service=checkout | timechart span=5m count(eval(status>=500)) as errors, count as total | eval err_pct=round(errors*100/total,2)
```

**Trade-offs and what can go wrong**
- Burn-rate alerts are harder to explain than "errors > 1%", so teams need to learn them.
- Pure symptom alerting can fire late for slow-building causes such as a disk filling. Keep a few cause alerts, as tickets, for things with a hard deadline.
- Low-traffic services give unstable error rates. Use minimum request counts.
- Too many "just in case" alerts bring fatigue back. Too few leave blind spots.
- An alert with no tested runbook just moves the confusion to 3 a.m.

**How I'd monitor it**
Track alerting itself as a system: pages per on-call shift, the share of pages that needed action (the target is high), time to acknowledge, and the number of incidents found by customers rather than alerts. Also check how many alerts have an owner and runbook. In Splunk, search the alert history, for example `index=_audit action=alert_fired | stats count by ss_name`, to find the noisiest alerts. Check the SLO dashboard for remaining error budget.

**Follow-ups to expect**
- *Why not alert on CPU at all?* -> CPU is a cause, not user pain. Keep it on dashboards, and alert only if it reliably predicts an outage, as a ticket.
- *Why two windows?* -> The long window avoids pages for blips. The short window makes the alert reset quickly after recovery.
- *How do you handle a flapping alert?* -> Lengthen the window or add a minimum-volume condition. If it still has no action, delete it.

**60-second answer**
I alert on symptoms users feel, such as error rate and latency against an SLO, not on causes like CPU 80%. I use burn-rate alerts with two windows: a fast one that pages for severe burn, such as 1 hour with a 5-minute confirmation, and slower ones for gradual burn, ending in a ticket. Every alert must be actionable, have an owner and a runbook link, and carry a severity, so only urgent user harm pages a human. I keep cause metrics on dashboards for diagnosis. After every incident and in a monthly review, I check which alerts helped and delete or tune the noisy ones. I also measure alerting itself, such as pages per shift and the share that needed action.

### Q14 [senior] Cardinality - what is it and why can it take Prometheus down?
tags: prometheus, cardinality, metrics, labels, observability, micrometer, splunk, basics

**Start here: the concepts**
- **Metric**: a number measured over time, such as "HTTP requests handled". It is cheap to store and good for answering "how much, how fast, how often?".
- **Prometheus**: a system that pulls (scrapes) metrics from your services every few seconds and stores them in its own time-series database.
- **Label**: a key=value tag on a metric, such as `method="GET"` or `status="200"`. Labels let you slice one metric by dimension.
- **Time series**: one metric name plus one exact set of label values, stored as a list of (timestamp, value) points. `http_requests{route="/orders/{id}",status="200"}` is one series. Change any label value and you get a different series.
- **Cardinality**: the number of distinct series a metric produces. It is the product of the distinct values of each label. For example, 5 methods × 20 routes × 6 status codes × 50 pods = 30,000 series.
- **Why Prometheus keeps them in memory**: it holds every recently active series in RAM so that writes and queries are fast. The cost is therefore paid per series, not per request.

**The live scenario**
A team adds a `uri` label to a request-latency histogram, using the raw path (`/orders/918273`) instead of the template. Traffic is 2,000 requests/s across 20 pods. Within a day there are about 3 million distinct order URLs. A histogram also creates roughly a dozen series per label combination (one per bucket, plus sum and count). That is tens of millions of series. Prometheus memory climbs from a few GB until the process is killed for running out of memory (OOM). Dashboards time out, and during the restart there is a monitoring blind spot just when the team needs it.

**What the interviewer is really checking**
Whether you know that metric cost scales with the number of distinct label combinations, not with traffic. They also want to see that you know where per-entity detail belongs (logs and traces).

**How I answer it**
1. **Define it by multiplication.** Cardinality is the product of each label's distinct values. One unbounded label (user id, order id, full URL, session id, trace id) multiplies everything else by millions.
2. **Explain the mechanism.** Every new combination creates a new series that Prometheus keeps in memory, indexes, and has to scan during queries. That is the memory blow-up and the slow queries.
3. **Watch for hidden multipliers.** Histograms add a series per bucket. Many pods, and pods that restart with new names, add more. Series that appear and disappear constantly (churn) are also costly.
4. **Use bounded label values.** Use route templates (`/orders/{id}`), not raw paths. Use small fixed sets such as method, status class (2xx/4xx/5xx), and outcome. Spring Boot's Micrometer HTTP metrics use the route template for the `uri` tag by default, so don't overwrite it with the raw path.
5. **Put per-entity questions elsewhere.** "What happened to user 42?" goes to structured logs in Splunk, searched by correlation id, or to traces. Those systems are built for high-cardinality data. Metrics are for aggregates.
6. **Add guardrails.** Set `sample_limit` in the scrape config so a bad deploy fails its scrape instead of killing the server. Use relabeling to drop dangerous labels.

```yaml
scrape_configs:
  - job_name: orders
    sample_limit: 50000   # scrape is rejected if a target exceeds this
```

**Trade-offs and what can go wrong**
- Fewer labels mean less detail. You cannot slice a metric by customer, so you must decide up front which dimensions matter.
- Dropping a label after the fact does not remove the old series immediately. They stay until they age out.
- The `sample_limit` guardrail protects the server but loses that target's metrics entirely, so alert on it.
- Common mistakes: logging-style labels such as error message text or exception strings, labels built from request parameters, and unbounded "unmatched route" values from bots scanning random URLs.

**How I'd monitor it**
- Alert on `prometheus_tsdb_head_series` (active series) growing abnormally, and on Prometheus memory use.
- Watch `scrape_samples_scraped` per target to find the service that suddenly explodes.
- Use the Prometheus UI's TSDB Status page to list the metrics and labels with the most series.
- Review new metrics and labels in code review, asking "is every label bounded?"

**Follow-ups to expect**
- *How do you find which metric is the culprit?* -> Check the TSDB Status page for top series counts by metric and by label, then compare `scrape_samples_scraped` per target.
- *Why not just give Prometheus more RAM?* -> Series grow with data values, not traffic, so unbounded labels will eventually outgrow any machine. Queries also get slower, so the real fix is bounding labels.
- *Where do I look up one user's failed request?* -> In Splunk, search by correlation id or user id in structured logs, or open the trace. Do not use a metric label.

**60-second answer**
Cardinality is the number of distinct time series a metric creates. A series is a metric name plus one exact set of label values, so the total is the product of the distinct values of every label. Prometheus keeps active series in memory, so a label like user id or full URL can create millions of series. That means a memory blow-up, slow queries, and sometimes an OOM crash. I keep labels bounded: route templates instead of raw paths, and small fixed sets like method and status class. I put per-user or per-request detail in logs and traces, for example Splunk searches by correlation id. I also add guardrails like `sample_limit` and alert on active series growth.

### Q15 [mid] How would you monitor a Kafka consumer service?
tags: kafka, consumer-lag, monitoring, observability, splunk, micrometer, dead-letter-topic, basics

**Start here: the concepts**
- **Consumer service:** An app that reads messages from a Kafka topic and does work with each one, such as saving an order or sending an email.
- **Partition and offset:** A topic is split into partitions. Each message in a partition has a sequential number called its offset. The consumer tracks "I have read up to offset N".
- **Consumer lag:** Lag is the latest offset in a partition minus the offset the consumer group has committed. It is how many messages are waiting. Lag shows whether the consumer keeps up with the producers.
- **Throughput (records/sec):** How many messages the consumer processes per second. Compare it with the incoming rate.
- **Histogram:** A metric that records how long each message took, so you can read p50, p95 and p99. An average hides slow outliers.
- **Dead-letter topic (DLT):** A side topic where messages that keep failing are parked, so one bad message doesn't block the partition. A rising DLT count means messages are being set aside.
- **Rebalance:** Kafka reassigns partitions among the consumers in a group when one joins, leaves or looks dead. Consumption pauses during a rebalance, so frequent rebalances hurt.
- **JVM/pool metrics:** Heap, GC pauses, threads, and DB or HTTP connection pool usage. They explain why a consumer is slow.
- **Trace context in headers:** A correlation or trace id is copied into the Kafka message headers, so one request can be followed across services.

**The live scenario**
An order service publishes about 2,000 messages/sec. At 14:00 a downstream database slows down. Our consumer's processing time rises from 20 ms to 400 ms, so it handles only about 500 msgs/sec. Lag grows by roughly 1,500 per second. No errors appear, so an error-rate alert stays silent. Customers see "order not confirmed" for 20 minutes. A lag alert plus a latency histogram would have caught it within 5 minutes.

**What the interviewer is really checking**
Whether you know the difference between "the app is up" and "the app is keeping up". They also want to see that you can combine metrics, logs and traces, and alert on symptoms rather than noise.

**How I answer it**
1. **Track consumer lag per partition and group.** It is the most direct sign of falling behind. Per-partition lag also exposes one stuck partition that a total would hide.
2. **Track records/sec and a processing-duration histogram.** If throughput drops while the incoming rate stays the same, lag will grow. The histogram shows whether slowness comes from our code or a dependency.
3. **Count errors, retries and DLT messages.** Failures can be silent. A rising DLT count means data is being diverted and someone must replay or fix it.
4. **Watch rebalances.** Frequent rebalances usually mean consumers are slow to poll (for example, they exceed `max.poll.interval.ms`) or are crashing and restarting.
5. **Watch JVM and pool metrics.** GC pauses, exhausted threads or a full DB pool explain slow processing.
6. **Log context on failure.** Log topic, partition, offset and correlation id as structured fields, so you can find and replay the exact message:
   `index=app service=orders-consumer level=ERROR | stats count by topic, partition`
7. **Propagate trace context in message headers.** Put the correlation id into the headers on produce, and into the MDC (the logger's per-thread context) on consume. One id then links the HTTP call, the Kafka message and the consumer log lines.
8. **Alert on lag that keeps increasing for N minutes** (for example 5). One brief spike during a deploy is normal. Sustained growth is not.

**Trade-offs and what can go wrong**
- Alerting on a fixed lag number gives false alarms at peak and misses problems at night, so prefer a trend or lag in time ("N minutes behind").
- Lag can be zero while a consumer is dead if it never committed offsets. Also alert when throughput is zero while messages arrive.
- Per-partition and per-message labels can create too many metric series, which is costly. Keep ids in logs, not metric labels.
- Don't log message payloads with personal data. Mask them, and use sensible log levels and retention.
- Alerting on every error makes people ignore the alerts.

**How I'd monitor it**
Use Micrometer or the Kafka client metrics, exported to a dashboard with lag, throughput, p95/p99 latency, errors, DLT and rebalance panels. Add a Splunk alert on a stuck or growing lag. Use `| timechart count by partition` on failure logs to find hot partitions. Use traces to follow one slow message through the services.

**Follow-ups to expect**
- *Lag is growing. What do you do?* -> Check whether the cause is slow processing (dependency, GC), a stuck partition, or a traffic spike. Then fix the cause, or add consumers up to the partition count.
- *Why not alert on every error?* -> It causes noise. Alert on symptoms tied to the SLO, like sustained lag or a DLT growth rate.
- *How do you trace one message across services?* -> Put the correlation id in the headers and the MDC, then search by it in Splunk.

**60-second answer**
I monitor a Kafka consumer on four fronts. First is consumer lag per partition, which shows whether we keep up. Second is throughput and a processing-time histogram, which shows how fast we are. Third is error, retry and dead-letter counts plus rebalances, which show whether messages are failing or consumers are unstable. Fourth is JVM and connection-pool health. On failures I log topic, partition, offset and correlation id as structured fields. I also pass the trace context in message headers, so I can follow one message across services in Splunk. I alert when lag keeps rising for several minutes, and when throughput is zero while messages arrive. I don't alert on every single error.

### Q16 [mid] Datadog / CloudWatch you've used: how do they map?
tags: observability, datadog, cloudwatch, splunk, prometheus, opentelemetry, basics

**Start here: the concepts**
- **Observability:** being able to understand what a running system is doing from the data it emits. It rests on three signals: logs, metrics and traces.
- **Logs:** timestamped text or JSON lines describing events. They answer "what exactly happened to this request?"
- **Metrics:** numbers sampled over time, such as requests per second or p99 latency. They are cheap and answer "is something wrong, and since when?"
- **Traces:** the path of one request across services, split into timed steps called spans. They answer "where was the time spent?"
- **Datadog:** a paid SaaS product that bundles all three signals. Its agent runs on each host, and its APM (application performance monitoring) collects traces.
- **CloudWatch:** AWS's built-in monitoring. It covers Logs, Logs Insights (a query language over logs), metrics and alarms.
- **OpenTelemetry (OTel):** a vendor-neutral standard and set of libraries for producing traces, metrics and logs. It is the open-source equivalent of the Datadog agent and APM libraries.
- **Prometheus:** an open-source metrics store that scrapes numbers from your services. **Tempo** stores traces. **Grafana** draws dashboards. **Loki** stores logs and is queried with **LogQL**.
- **Alertmanager:** the Prometheus component that groups, silences and routes alerts to Slack or PagerDuty. Prometheus alert rules decide when something is firing.
- **Splunk SPL:** Splunk's search language for logs.

**The live scenario**
Your team moves a payments service from an AWS-only setup (CloudWatch) to a company-standard stack of Splunk plus Grafana and Prometheus. At 10:05 checkout p99 latency rises from 300 ms to 4 s, and about 3% of 2,000 requests per minute fail. Your old habits (a Datadog monitor, a Logs Insights query) still apply, but you now need the new tool names. The skill that matters is knowing which signal to open first, whatever the product is called.

**What the interviewer is really checking**
That you understand the concepts (metrics, logs, traces, alerts) and not just product names. They also want to see that you can move between tools and have used them on a real incident.

**How I answer it**
1. **Map by job, not by brand.** Datadog agent and APM correspond to OTel instrumentation plus Prometheus (metrics) plus Tempo (traces). Datadog's single product becomes several parts you assemble. Reason: the interviewer wants to hear that you know what each part does.
2. **Dashboards and monitors.** Datadog dashboards map to Grafana dashboards. Datadog monitors map to Grafana or Prometheus alert rules. Reason: both pairs do the same job, which is to visualise a signal and to fire when it crosses a threshold.
3. **Logs.** CloudWatch Logs Insights maps to Splunk SPL or Loki LogQL. Datadog Log Management is also in this group. Same question, different syntax:
```
Logs Insights: filter @message like /ERROR/ | stats count() by bin(5m)
SPL:           index=app level=ERROR | timechart span=5m count
LogQL:         sum(count_over_time({app="payments"} |= "ERROR" [5m]))
```
4. **Alarms.** CloudWatch alarms map to Prometheus alert rules plus Alertmanager. One alarm does both the checking and the notifying. In Prometheus those jobs are split between the rule and Alertmanager.
5. **Tell a real incident.** Start from a symptom alert (p99 latency or error rate). Look at the metric to see when it started. Follow a trace to find the slow service. Then search logs by correlation id for the cause. Reason: it proves you used the signals in order.

**Trade-offs and what can go wrong**
- The mapping is approximate, not one-to-one. Say "roughly equivalent" and avoid claiming exact feature parity.
- Datadog is easy to adopt but expensive at volume. The open-source stack is cheaper per unit but you run and patch it yourself.
- Alerting on every error, instead of on symptoms or SLOs, causes alert fatigue in any tool.
- High-cardinality labels (for example a user id on a metric) can overload Prometheus or inflate a Datadog bill.
- Do not claim experience you lack. Describe the incident you actually handled.

**How I'd monitor it**
- Alert on symptoms: error rate, p99 latency and saturation against SLO targets.
- Keep a trace id or correlation id in every log line so the three signals link up.
- Track the observability stack itself: ingestion lag, dropped spans and log volume per service.
- Review monthly cost per signal and apply log-level, sampling and retention rules.

**Follow-ups to expect**
- *Logs vs metrics vs traces: which first?* -> Metrics tell you something is wrong, traces locate where, logs explain why.
- *Why split alert rules from Alertmanager?* -> Rules detect problems. Alertmanager deduplicates, groups and routes them so one outage sends one page, not fifty.
- *How do you control observability cost?* -> Use sensible log levels, sample traces, mask PII (personal data), set retention by value, and avoid high-cardinality labels.

**60-second answer**
"I think of these tools by the job they do. Datadog's agent and APM map to OpenTelemetry for instrumentation, Prometheus for metrics and Tempo for traces. Datadog dashboards and monitors map to Grafana dashboards and alert rules. CloudWatch Logs Insights maps to Splunk SPL or Loki LogQL. CloudWatch alarms map to Prometheus alert rules plus Alertmanager, which routes the alerts. The mapping is approximate, but the workflow is the same. An alert on p99 latency fires, I check the metric for when it began, follow a trace to the slow service, then search logs by correlation id for the cause. I can walk you through a real incident I solved that way."

### Q17 [senior] What is Alertmanager?
tags: alertmanager, prometheus, alerting, observability, on-call, slo, basics

**Start here: the concepts**
- **Prometheus**: a monitoring system that collects numeric measurements (metrics) such as error rate or latency, and stores them over time.
- **Alert rule**: a condition written in Prometheus, for example "5xx error rate above 5% for 10 minutes". Prometheus evaluates it. When it is true, Prometheus sends an alert to Alertmanager. Prometheus decides *when* something is wrong. It does not decide *who is told*.
- **Alertmanager**: a separate service that receives alerts and decides what to do with them. It exists so that one problem does not become a flood of messages that people learn to ignore.
- **Label**: a key-value tag on an alert, such as `severity=critical` or `team=payments`. Alertmanager uses labels to make decisions.
- **Deduplication**: if the same alert arrives repeatedly (Prometheus re-sends it while it stays firing), Alertmanager treats it as one alert and notifies once, then at a controlled repeat interval.
- **Grouping**: bundling related alerts, such as 40 pods of one service failing, into a single notification.
- **Inhibition**: suppressing a less important alert when a more important one explains it. Example: if "database down" is firing, mute "API slow".
- **Silence**: a temporary, manual mute for matching alerts, for example during planned maintenance.
- **Routing**: a tree of rules that matches labels and sends the alert to a **receiver**: Slack, PagerDuty, email, or a webhook.

**The live scenario**
A payments platform runs 40 pods. At 02:10 the database fails over. Within one minute, 40 pods each raise "high error rate", "timeouts" and "health check failing". With no Alertmanager logic, that is about 120 pages to one on-call engineer in 60 seconds. They cannot tell what is the cause and what is a side effect. With Alertmanager, the alerts are grouped by service, the symptom alerts are inhibited by "database failover", and the engineer gets 1 page. The same alert goes to the payments team's PagerDuty, and a lower-severity copy goes to Slack.

**What the interviewer is really checking**
Whether you understand that alerting is split in two (Prometheus detects, Alertmanager notifies) and whether you design notifications to protect human attention instead of just forwarding every error.

**How I answer it**
1. **Define the split.** Prometheus evaluates rules and fires alerts. Alertmanager only handles notification. This keeps detection logic and "who gets woken up" separate, so you can change one without touching the other.
2. **Deduplicate.** Prometheus keeps re-sending a firing alert. Alertmanager collapses those into one, so you are not re-paged every few seconds.
3. **Group.** Pick labels to group by, such as `alertname` and `service`. One incident then produces one message listing all the affected pods, which is easier to read and act on.
4. **Inhibit.** Define that a root-cause alert hides its known symptoms. This is the main defence against an alert storm, because it removes noise that carries no new information.
5. **Silence.** Use silences for planned work or known issues. They expire automatically, so they cannot stay muted forever by accident.
6. **Route by label.** Critical alerts for team payments go to PagerDuty. Warnings go to Slack. Everything else can go to email.

```yaml
route:
  group_by: [alertname, service]
  receiver: slack-default
  routes:
    - match: {severity: critical}
      receiver: pagerduty-payments
```

**Trade-offs and what can go wrong**
- Grouping too broadly hides distinct problems. Grouping too narrowly brings the storm back.
- Over-eager inhibition can hide a real second failure.
- A silence with a wrong matcher, or one that is too long, can mute a real outage.
- Alertmanager is a single point of failure unless you run several instances in a cluster (they share state to avoid duplicate notifications). Send Prometheus alerts to all of them.
- Alerting on every error instead of symptoms or SLO burn leads to alert fatigue, whatever the routing looks like.

**How I'd monitor it**
- Watch Alertmanager's own metrics: notifications sent and failed per receiver, and the number of active alerts and silences.
- Run a "dead man's switch": an alert that always fires and goes to an external service. If it goes quiet, the alert pipeline is broken.
- Review pages per on-call shift and how many were actionable.
- Compare with Splunk: use it for log-based alerts and for investigating after the page. Prometheus and Alertmanager answer "is it broken now?", and logs and traces answer "why?".

**Follow-ups to expect**
- *Difference between grouping and inhibition?* -> Grouping merges similar alerts into one message. Inhibition suppresses an alert because a more important one already explains it.
- *Does Alertmanager evaluate alert conditions?* -> No. Prometheus evaluates the rules. Alertmanager only receives alerts and handles notification.
- *How do you make it highly available?* -> Run multiple Alertmanager instances in a cluster, and configure Prometheus to send to every one. They coordinate to avoid sending duplicate notifications.

**60-second answer**
Alertmanager is the notification manager for Prometheus. Prometheus evaluates the alert rules and fires alerts. Alertmanager receives them and deduplicates repeats, groups related alerts into one message, and inhibits symptom alerts when a root-cause alert is firing. It also supports silences for planned maintenance. It then routes alerts by label to receivers such as Slack, PagerDuty or email, so the right team is paged. The goal is to avoid alert storms and alert fatigue. In production I run it as a cluster and use a dead man's switch to confirm the pipeline works. I also alert on symptoms and SLOs rather than on every error.

### Q18 [architect] A latency spike is reported at 2 a.m. - walk through the investigation using these tools.
tags: splunk, observability, incident-response, slo, distributed-tracing, correlation-id, latency, basics

**Start here: the concepts**
- **Latency spike:** requests take much longer than normal. It is usually measured as p95/p99 (the time within which 95% or 99% of requests finish), because averages hide slow outliers.
- **SLO (Service Level Objective):** a target such as "99% of checkout calls finish under 500 ms". It tells you whether users are actually hurt, so you alert on it rather than on every error.
- **Deploy marker:** a vertical line on a dashboard showing when a release or config change went out. It shows quickly whether the problem started at the same moment.
- **Trace and span:** a trace is the path of one request through all services. Each step (an HTTP call, a DB query) is a span with its own duration. The longest span shows where time went.
- **Saturation:** how full a resource is. Examples are connection pool usage, thread pool queues, garbage collection (GC) pauses, and Kafka consumer lag (how far consumers are behind the newest messages). A full resource makes requests wait.
- **Correlation id / traceId:** a unique id put in the logging context (MDC) and passed in HTTP and Kafka headers, so one search in Splunk returns that request's logs from every service.
- **Mitigation vs root cause:** mitigation stops user pain now. Root cause is the real reason, found afterwards.
- **RCA (root cause analysis):** a written post-incident report covering the timeline, cause, and fixes.

**The live scenario**
At 2:03 a.m. an alert fires: checkout p99 has gone from 400 ms to 6 s, and 8% of requests time out. Traffic is a normal ~300 req/s. The on-call engineer sees the problem began at 1:50, right after an automated config deploy. Traces show the payment-service span taking 5 s. Its DB connection pool is at 100% and threads are queuing. A rollback at 2:15 restores latency. The RCA finds a new query with no index.

**What the interviewer is really checking**
Whether you work from symptom to cause in a disciplined order, know which tool answers which question (metrics, traces, logs), and put restoring service ahead of curiosity.

**How I answer it**
1. **Confirm the impact on the SLO dashboard.** Find which service and endpoint are affected and since when. Reason: this separates a real user-facing problem from noise and tells you where to look.
2. **Compare with deploy markers.** Check releases, config changes, and scheduled jobs around the start time. Reason: most incidents follow a change, and a match gives you a fast mitigation (rollback).
3. **Open traces of slow requests and find the slow span.** Is it a DB call, a downstream service, or a span with no children? The last case points to time inside the process (CPU, GC, lock waits). Reason: this narrows the search to one component. Traces are usually sampled, so make sure you are looking at slow ones.
4. **Check saturation of that component.** Look at pool usage, thread queues, GC pauses, CPU, and Kafka lag. Reason: a latency spike is often requests waiting for a scarce resource, not slow code.
5. **Search logs by traceId for errors and timeouts.** Reason: logs give the exact error that metrics and traces only hint at.
```
index=prod traceId=abc123 | sort _time | table _time service level message
```
6. **Mitigate as soon as you have a credible lead; do not wait for full proof.** Options are rollback, scale out, disable a feature flag, or shed load (reject low-priority traffic). Reason: users are suffering, and a rollback is cheap and reversible.
7. **Then find the root cause and write the RCA.** Include a timeline, the cause, and follow-up actions such as new alerts, tests, or indexes. Reason: this stops the same incident coming back.

**Trade-offs and what can go wrong**
- Rolling back can destroy evidence, so capture thread dumps, heap stats, and trace samples first if it is safe.
- Scaling out can make a saturated database worse by adding more connections.
- Sampled traces may miss the slowest requests, and without a correlation id in every service you cannot follow one request.
- Alerting on every error wakes people for nothing. Alert on SLO burn instead.
- Mask PII in logs, and keep log levels and retention under control to limit cost.

**How I'd monitor it**
- Metrics: p95/p99 latency, error rate, and saturation (pool usage, queue depth, GC time, consumer lag).
- Traces: span durations per dependency.
- Splunk: `index=prod level=ERROR | timechart count by service` to see when and where errors began.
- Alerts: SLO burn-rate alerts on symptoms, with deploy markers shown on dashboards.

**Follow-ups to expect**
- *Why mitigate before finding the root cause?* -> Every minute costs users and revenue, and a rollback is safe and reversible. Diagnose afterwards using the preserved evidence.
- *Logs, metrics, or traces: which first?* -> Metrics tell you that something is wrong and how big it is. Traces tell you where. Logs tell you why.
- *How do you follow one request through Kafka?* -> Put the traceId in the message headers and restore it into the MDC in the consumer, so the same Splunk search works across the async hop.

**60-second answer**
First I check the SLO dashboard to see which service and endpoint are slow and when it started. Then I compare that time with deploy markers, because most incidents follow a change. Next I open traces of slow requests to see which span is slow: the database, a downstream call, or time inside the process. I check saturation there, such as connection pools, threads, GC, and Kafka lag. Then I search Splunk by traceId for the exact errors or timeouts. As soon as I have a credible lead I mitigate by rolling back, scaling, disabling a feature, or shedding load. Afterwards I find the root cause and write an RCA with follow-up actions.

### Q19 [mid] Honest answer: "You haven't used Splunk/Grafana/Prometheus?"
tags: splunk, observability, prometheus, grafana, datadog, micrometer, structured-logging, basics

**Start here: the concepts**
- **Observability:** being able to understand what a running system is doing from the data it emits (logs, metrics, traces). It exists because you can't attach a debugger to production.
- **Log:** a text record of one event ("payment 123 failed"). It is detailed but expensive to store and search at scale.
- **Structured logging:** writing logs as key-value fields (usually JSON) instead of free text, so a tool can filter on `orderId` or `level` instead of guessing with text patterns.
- **Metric:** a number sampled over time, such as requests per second or error count. It is cheap and good for trends and alerts, but it doesn't tell you which request failed.
- **Label (tag):** a key-value pair attached to a metric, such as `status=500` or `service=orders`, so you can slice one metric many ways.
- **Trace / APM:** the path of one request across services, shown as timed steps. APM (application performance monitoring) tools collect these.
- **Micrometer:** the Java metrics library used by Spring Boot. It records metrics once and can send them to Prometheus, Datadog, CloudWatch and others.
- **Prometheus:** a metrics database that periodically *pulls* (scrapes) metrics from your apps. Its query language is **PromQL**.
- **Grafana:** a dashboard tool that draws charts from data sources such as Prometheus. It is not a database itself.
- **Splunk:** a platform for searching logs, using the query language **SPL** (Search Processing Language).
- **Datadog / CloudWatch:** hosted monitoring products, where Datadog is third-party and CloudWatch is AWS's own. Both cover dashboards, monitors (alerts), log search and metrics, and Datadog also offers APM.

**The live scenario**
Checkout errors jump from 0.1% to 4% at 2 pm. In Datadog, a monitor on the error rate fires. I open the dashboard and see that only the payment service is affected. I search its logs for the failing time window and find timeouts to a downstream bank API. An APM trace confirms the calls take 8 seconds instead of 300 ms. The team fixes it with a timeout and circuit breaker. If this team used Splunk and Grafana instead, I'd do the same steps with different syntax.

**What the interviewer is really checking**
Whether you're honest about your gaps, whether you understand observability concepts rather than just tool buttons, and whether you can learn a new stack fast.

**How I answer it**
1. **Say plainly that I haven't used them hands-on.** Bluffing gets exposed in one follow-up, and honesty builds trust.
2. **Name what I have used:** Datadog and CloudWatch for dashboards, monitors, log search and APM traces. This shows real production experience.
3. **Show the ideas map across tools.** Metrics with labels in Datadog are the same idea as Prometheus metrics with labels. Searching logs in Datadog is the same job as SPL in Splunk. For example:
   ```
   PromQL: rate(http_server_requests_seconds_count{status="500"}[5m])
   SPL:    index=orders level=ERROR | timechart span=5m count by service
   ```
4. **Be specific about what's actually different:** the query syntax, and *operating* the stack. With Prometheus and Grafana you run, scale and store the data yourself, and Prometheus pulls from apps. With Datadog the vendor runs the backend.
5. **Point to transferable work:** I've set up Micrometer metrics and structured logging. That is the application side, which is the same regardless of backend.
6. **Say I'd pick up PromQL and SPL quickly,** and back it with how I'd start: read the team's existing dashboards and queries.

**Trade-offs and what can go wrong**
- Don't claim "it's all the same." Operating Prometheus (retention, storage, high-cardinality labels) and Splunk (indexing, licence cost per data volume) are real skills I'd still need to learn.
- Don't dismiss the gap either. Query languages do take practice, especially PromQL functions like `rate`.
- Avoid overselling "quickly." Offer a concrete plan instead.

**How I'd monitor it**
This is about how I'd prove I've closed the gap:
- Run a small local Prometheus and Grafana against a Spring Boot app using Micrometer.
- Recreate one of my Datadog monitors as a PromQL alert, for example error rate above a threshold.
- Ingest the app's JSON logs into Splunk (the free trial) and write the SPL for "errors per service per 5 minutes."

**Follow-ups to expect**
- *How would you alert on errors in Prometheus?* -> Alert on a symptom such as the error ratio over 5 minutes, not on each error, and route it through Alertmanager.
- *Why not just use logs for everything?* -> Logs are costly to search at scale. Metrics are cheap for trends and alerts, logs explain individual failures, and traces show where time goes across services.
- *What's a high-cardinality label problem?* -> Putting values like user IDs in labels creates millions of time series, which can overload Prometheus. Keep labels to small sets of values.

**60-second answer**
"I haven't used Splunk, Grafana or Prometheus hands-on. In production I've used Datadog and CloudWatch for dashboards, monitors, log search and APM traces. The concepts carry over: metrics with labels are queried with PromQL, and logs are searched with SPL in Splunk. What differs is the syntax and the work of running the stack yourself. I've set up Micrometer metrics and structured logging in Spring Boot, so the application side is familiar. I'd start by reading the team's existing queries, and I'd practise by rebuilding one of my Datadog monitors in PromQL."

### Q20 [mid] What is Splunk?
tags: splunk, observability, logging, spl, dashboards, alerting, basics

**Start here: the concepts**
- **Machine-generated data:** text or records that software produces by itself, such as application logs, server and network logs, and security events. Nobody types it. It exists because it is the only record of what a running system did.
- **Log event:** one line or record describing one thing that happened, with a timestamp, for example "payment failed for order 123".
- **Ingest:** getting that data into Splunk. A forwarder (a small agent on each server) or an HTTP endpoint sends the events in. Splunk stores them in an **index**, which is a searchable store, so you don't have to log into 40 servers and grep files.
- **SPL (Search Processing Language):** Splunk's query language. You write a search, then pipe (`|`) the results through commands such as filter, count or chart, like a Unix pipeline.
- **Field extraction:** turning raw text into named fields such as `status=500` or `service=payment`, so you can filter and group by them. This mostly happens when you search. It is far easier if the app logs structured data (key=value or JSON).
- **Dashboard:** saved searches shown as charts and tables on one screen.
- **Alert:** a saved search that runs on a schedule or in real time and notifies someone when a condition is met.
- **Correlation id:** a unique id attached to a request and logged by every service it touches. It lets you follow one request across services.

**The live scenario**
At 10:02, checkout started failing for about 3% of 2,000 requests per minute. Support had a few complaints, but no single server looked broken. An on-call engineer searched Splunk for `status=500` in the last 30 minutes and found the errors. She picked one failed request's correlation id and searched for it across all indexes. That showed the request passing through the gateway, order, inventory and payment services, and failing in payment with a timeout calling a bank API. Grouping errors by `service` and charting them over time showed the spike began exactly at a deployment. Diagnosis took 10 minutes instead of an hour of manual log hunting.

**What the interviewer is really checking**
Whether you understand Splunk as a tool for answering real questions in production (search, aggregate, visualize, alert), not just a definition. At mid level, they also want to see that you know logs need structure and correlation ids to be useful.

**How I answer it**
1. **Define it simply.** Splunk ingests machine data, indexes it and lets you search and analyze it in one place. The reason is that logs scattered across many servers are impossible to use during an incident.
2. **Describe the workflow.** Pick a time range first, because it limits the data scanned and keeps searches fast. Then filter events, extract or use fields, aggregate and visualize.
3. **Show a tiny search:**
```
index=prod service=payment level=ERROR earliest=-30m
| timechart span=1m count by error_type
```
This filters to payment errors in the last 30 minutes and charts them per minute by type, which shows when and what started failing.
4. **Mention dashboards.** They turn repeated searches (error rate, latency, volume) into a shared view for the team.
5. **Mention alerts.** Alert on symptoms users feel, such as error rate above a threshold for 5 minutes, not on every single error. Otherwise people get noise and start ignoring pages.
6. **Place it among the pillars.** Logs tell you what happened in detail. Metrics tell you how much and how fast. Traces show where time was spent across services. Splunk is best known for logs, and Splunk's observability products also cover metrics and traces.

**Trade-offs and what can go wrong**
- Unstructured logs make field extraction fragile and searches slow and hard to write.
- Without a correlation id, you can't follow one request across services.
- Debug-level logging everywhere raises ingest cost, because Splunk licensing is commonly tied to data volume.
- Logging passwords, card numbers or personal data creates a compliance risk. Mask it before it is logged.
- Alerting on every error causes alert fatigue.
- Retention too short means you can't investigate old incidents. Too long costs money.

**How I'd monitor it**
- Daily ingest volume per index and per source, to catch log spikes before they hit license or cost limits.
- Dashboards for error rate, latency and request count per service.
- Alerts on error-rate and latency thresholds that match your SLOs.
- Checks that forwarders are still sending data, so silence isn't mistaken for health.
- Periodic review of noisy or unused alerts and searches.

**Follow-ups to expect**
- *How do you trace one request across services?* -> Generate a correlation id at the edge, put it in the logging context (MDC in Java), pass it in HTTP and Kafka headers, and search by it in Splunk.
- *Logs vs metrics vs traces?* -> Logs give detail about events, metrics give cheap aggregated trends for alerting, and traces show the path and timing of one request.
- *How do you control Splunk cost?* -> Use sensible log levels, avoid noisy debug logs, mask or drop sensitive and useless fields, and set retention per index.

**60-second answer**
Splunk is a platform that collects machine-generated data like application logs, infrastructure logs and security events, indexes it, and lets teams search and analyze it in one place. You use SPL, its query language, to pick a time range, filter events, extract fields, aggregate and chart the results. Teams then save useful searches as dashboards and set alerts that fire on real conditions, such as a sustained rise in error rate. In an incident I would search for the failing requests, take one correlation id and follow it across every service to find where it broke. It works best when logs are structured and carry correlation ids, when sensitive data is masked, and when log volume is controlled to keep costs down.

### Q21 [mid] What is the difference between logs, metrics, and traces?
tags: logs, metrics, traces, observability, splunk, correlation-id, mdc, basics

**Start here: the concepts**
- **Observability:** how well you can understand what a running system is doing from the outside, using the data it emits. It exists because in production you cannot attach a debugger.
- **Log:** a timestamped record of one event, such as "payment declined for order 42, reason: timeout". It is the most detailed signal and answers "what exactly happened?"
- **Metric:** a number measured over time, such as requests per second, error rate or p99 latency (the time within which 99% of requests finish). Metrics are small and cheap to store, so they suit dashboards and alerts. They answer "is something wrong, and since when?" but not "why?"
- **Trace:** the record of one request's journey across services. It is made of **spans**, each span being one timed step (for example "call payment-service"). A trace answers "where did the time go or where did it fail?"
- **Trace ID / correlation ID:** a unique ID created at the entry point and passed to every service, in HTTP headers and Kafka message headers. Each service writes it into its logs, for example via the logging **MDC** (a per-thread map that the logger prints on every line). This is what lets you connect logs and traces for one request.

**The live scenario**
Checkout handles about 2,000 requests a minute. At 14:05 p99 latency jumps from 300 ms to 4 s, and the error-rate alert fires within two minutes. That is the **metric** doing its job: it says something is wrong, but not where. The team opens a **trace** of a slow request and sees 3.5 s of the 4 s is spent in payment-service calling the database. They copy that trace ID into Splunk and read the **logs** for that one request. The logs show "connection pool exhausted, waiting" and retries. The cause turns out to be a pool size too small after a traffic spike. Each signal answered a different question.

**What the interviewer is really checking**
Whether you know that the three signals answer different questions, how you use them in order during an incident, and that correlation IDs are what tie them together.

**How I answer it**
1. **Define each signal in one line.** Logs are event details, metrics are numbers over time, traces are a request's path. Clear definitions show you understand the basics.
2. **Say which question each answers.** Metrics tell you whether something is wrong, traces tell you where, and logs tell you why. This turns definitions into a debugging method.
3. **Describe the incident order.** Detect with a metric alert, locate with a trace, then inspect with logs. Going in this order avoids grepping millions of log lines blindly.
4. **Explain the glue.** The entry service generates the ID, every service forwards it in HTTP and Kafka headers, and the logger prints it from the MDC. Then one search finds everything for that request:
```
index=prod trace_id="abc123" | sort _time | table _time service level message
```
5. **Alert on symptoms.** Alert on user-facing signals such as error rate or latency against an SLO (a target like "99% of requests under 500 ms"), not on every single error log. Otherwise people get alert fatigue and ignore the pager.

**Trade-offs and what can go wrong**
- **Logs:** they are the most expensive to store and search at volume. Control cost with log levels, retention limits, and masking of personal data (PII) such as card or email values.
- **Metrics:** they are cheap, but labels with huge numbers of distinct values (such as user ID) make them costly and slow. They also lose per-request detail.
- **Traces:** they are often **sampled** (only a fraction is kept) to save cost, so the exact request you want may be missing.
- **Missing propagation:** if one service or Kafka hop drops the ID, the trace and log trail breaks there. This is the most common real-world failure.

**How I'd monitor it**
- Alert on SLO symptoms: error rate, p99 latency, and Kafka consumer lag.
- Check that the ID is present, for example with `index=prod NOT trace_id=* | stats count by service` to find services that log without it.
- Watch daily log volume per service, trace sampling rate, and how many logs are masked.

**Follow-ups to expect**
- *Which signal do you check first in an incident?* -> The metric or dashboard, because it tells you something is wrong and how big it is. Then a trace to locate it, then logs to explain it.
- *How does the ID cross a Kafka hop?* -> The producer puts it in a message header, and the consumer reads it and puts it back into the MDC before processing.
- *Why not just log everything?* -> It costs money, slows searches, risks leaking PII, and buries the useful lines in noise.

**60-second answer**
Logs are detailed records of individual events, metrics are numbers measured over time, and traces show one request's path across services. I use them in order during an incident. A metric alert tells me something is wrong, such as p99 latency or error rate breaching an SLO. A trace shows me which service or call is slow or failing. Then I search the logs by trace ID to see the exact details of why. That works because a correlation ID is created at the entry point, passed in HTTP and Kafka headers, and written into every log line through the MDC. I alert on symptoms, not every error, and I keep costs and risk down with log levels, PII masking, sampling and retention limits.
