---
id: kafka
title: Apache Kafka
order: 1
summary: Topics, partitions, consumer groups, offsets, rebalancing, lag, performance, scaling.
crib: java/java-interview-prep/topics/09-kafka-messaging.md
docs: java/java-interview-prep/deep_dive/12_kafka.md, java/java-interview-prep/company-chase-travel/brush-up/03-kafka-producer-consumer.md
examples: java/java-interview-prep/examples/12_kafka
keywords: kafka, kafka performance, kafka tuning, tune kafka, topic, partition, consumer, producer, offset, rebalance, lag, broker, dlt, dead letter, retry topic, idempotent producer, exactly-once, schema registry, kraft, zookeeper, isr, acks, rabbitmq, streams, connect
---
Skill focus for Apache Kafka answers:
- Interviewers pull a thread: partition -> key/ordering -> hot partition -> rebalance -> commit strategy -> duplicates -> idempotency -> lag -> capacity. Connect the links.
- Always state numbers: partitions vs consumers, msg/s per consumer, lag in messages AND in time.
- Name real configs when they matter (acks, enable.idempotence, min.insync.replicas, max.poll.records, max.poll.interval.ms, session.timeout.ms, group.instance.id, partition.assignment.strategy, auto.offset.reset).
- Spring Kafka specifics where relevant: DefaultErrorHandler, DeadLetterPublishingRecoverer, @RetryableTopic, AckMode.
- Kafka 4.x facts: KRaft only (no ZooKeeper), KIP-848 consumer protocol GA, share groups (KIP-932) are preview.
- Monitoring: per-partition lag, consume vs produce rate, rebalance rate, DLT rate, under-replicated partitions.
