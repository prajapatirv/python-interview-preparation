---
id: splunk-observability
title: Splunk & observability
order: 7
summary: Structured logging, correlation ids, SPL searches, dashboards, alerts, metrics and tracing.
crib: java/java-interview-prep/topics/14-observability-splunk-grafana-prometheus.md
docs: java/java-interview-prep/deep_dive/14_observability_splunk.md
examples: java/java-interview-prep/examples/14_observability_splunk
keywords: splunk, spl, log, logs, logging, correlation id, mdc, trace, tracing, opentelemetry, metrics, prometheus, grafana, dashboard, alert, alerting, observability, monitoring, micrometer, elk, kibana, slo, sli
---
Skill focus for Splunk & observability answers:
- Tell it as an incident: how you traced one failed request across 5 services (correlation id in MDC, propagated in HTTP and Kafka headers).
- Show short, realistic SPL where it helps (index=... | stats count by ... | timechart).
- Logs vs metrics vs traces and which answers which question; alert on SLOs and symptoms, not on every error.
- Cost and hygiene: log levels, PII masking, sampling, retention.
