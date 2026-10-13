---
id: python-kafka
title: Kafka from Python
order: 4
summary: confluent-kafka config, delivery semantics, retries/DLQ, schema management, sinks.
docs: python/python-interview-prep/deep_dive/13_kafka_core.md, python/python-interview-prep/deep_dive/14_kafka_pipelines_delivery_semantics.md, python/python-interview-prep/deep_dive/15_kafka_failure_handling.md, python/python-interview-prep/deep_dive/16_kafka_schema_management.md, python/python-interview-prep/deep_dive/31_kafka_python_integration.md
folders: 06_kafka
examples: python/python-interview-prep/06_kafka
keywords: kafka, topic, partition, consumer, producer, offset, rebalance, lag, dlq, dead letter, schema registry, avro, confluent, exactly-once, idempotent
---
Skill focus for Kafka from Python answers:
- Same Kafka fundamentals as Java (partitions, groups, offsets, rebalancing, lag) - tell them as production scenarios.
- Python specifics: confluent-kafka (librdkafka) config names, poll()/flush() discipline, delivery callbacks, commit after processing.
- Idempotent sinks (upserts, unique event ids), retry topics and DLQ.
