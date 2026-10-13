---
id: python-scaling
title: Scaling, caching & production stability
order: 5
summary: Caching, queues, capacity planning, zero-downtime changes, observability, AWS Lambda, large files.
docs: python/python-interview-prep/deep_dive/12_scaling_applications.md, python/python-interview-prep/deep_dive/17_caching.md, python/python-interview-prep/deep_dive/18_queue_architectures.md, python/python-interview-prep/deep_dive/19_production_stability_monitoring.md, python/python-interview-prep/deep_dive/27_zero_downtime_production_changes.md, python/python-interview-prep/deep_dive/28_observability_distributed_systems.md, python/python-interview-prep/deep_dive/29_capacity_scaling_tps.md, python/python-interview-prep/deep_dive/30_large_file_processing.md
folders: 07_caching_queues, 08_scaling_production_resilience, 09_aws_lambda_streaming, 13_system_design_scenarios
examples: python/python-interview-prep/13_system_design_scenarios
keywords: scale, scaling, cache, caching, redis, queue, celery, sqs, rate limit, circuit breaker, retry, resilience, monitoring, observability, metrics, alert, tps, capacity, zero downtime, canary, deploy, lambda, aws, s3, large file, 100gb, stream, memory, microservices, terraform, databricks, production
---
Skill focus for Scaling, caching & production stability answers:
- Do the arithmetic out loud: Little's Law, utilisation, the bottleneck table, SLO burn rate.
- Mitigate first, then fix; canary and expand/contract for zero-downtime changes.
- Observability: correlation ids, structured logs, RED/USE metrics, tracing.
