---
id: nosql
title: NoSQL: Couchbase, MongoDB, Cassandra
order: 6
summary: Modelling by access pattern, partition keys, consistency, hot partitions, choosing the store.
crib: java/java-interview-prep/topics/11-nosql-couchbase-mongodb-cassandra.md
docs: java/java-interview-prep/deep_dive/13_nosql.md
examples: java/java-interview-prep/examples/13_nosql
keywords: nosql, mongodb, mongo, cassandra, couchbase, document, cql, n1ql, sharding, shard, replica set, consistency level, quorum, cap theorem, cap, denormalize, denormalise, wide-column, key-value, ttl, vbucket, cas
---
Skill focus for NoSQL: Couchbase, MongoDB, Cassandra answers:
- Model by query/access pattern first, not by entities; denormalise deliberately.
- Partition/shard key choice and hot partitions; Cassandra primary key = partition key + clustering columns.
- Consistency: Cassandra tunable consistency (QUORUM arithmetic), MongoDB write/read concern, Couchbase durability and CAS.
- When to choose which: write-heavy time series (Cassandra), flexible documents and rich queries (MongoDB), low-latency key-value + documents (Couchbase).
- Idempotent and conditional writes for Kafka sinks.
