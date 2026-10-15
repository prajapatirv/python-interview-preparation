---
id: round-cloud-devops
title: Real interview round: KEDA and event-driven autoscaling in Kubernetes
stack: java
skill: cloud-devops
---
A question asked in a real interview round, answered from the basics.

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [senior] Do you know KEDA in Kubernetes and how does it work?
tags: keda, kubernetes, autoscaling, hpa, kafka-lag, scaledobject, event-driven, scale-to-zero, basics

**Start here: the concepts**
- **Pod:** a running copy of your application in Kubernetes. A **Deployment** keeps N pods running.
- **HPA (Horizontal Pod Autoscaler):** the built-in Kubernetes controller that changes the number of pods based on metrics, normally CPU or memory.
- **The limitation:** CPU and memory are poor signals for event-driven work. A Kafka consumer can be 20% busy while 2 million messages wait in the topic.
- **KEDA (Kubernetes Event-Driven Autoscaling):** an add-on that scales workloads on **external event sources** such as Kafka consumer lag, queue length, a Prometheus query or a cron schedule, and can scale to **zero**.
- **Scaler:** a KEDA plug-in that knows how to read one source (Kafka, RabbitMQ, SQS, Azure Service Bus, Prometheus, cron, and many more).
- **ScaledObject:** the KEDA custom resource that says "scale this Deployment using this scaler with these thresholds".
- **Metrics adapter:** KEDA exposes the external metric to the Kubernetes metrics API so the HPA can use it.

**The live scenario**
An order-events consumer runs 3 pods all day. During a sale the topic receives 50,000 messages per second and lag grows to 8 million, yet CPU on the 3 pods is only 35%, so the CPU-based HPA does nothing and customers wait 40 minutes for confirmations. With KEDA watching consumer lag, the deployment grows from 3 to 24 pods within minutes (one per partition at most), drains the backlog, and scales back down; at night a different consumer with no messages scales to zero pods and costs nothing.

**What the interviewer is really checking**
That you know why CPU-based autoscaling is wrong for queue and stream consumers, how KEDA plugs into HPA, and the practical limits such as the partition count.

**How I answer it**
1. **Problem:** event-driven workloads need scaling on backlog, not on CPU.
2. **Components:** the KEDA operator (watches `ScaledObject` resources and handles activation between 0 and 1 replicas), the metrics server (supplies external metrics), and scalers for each source. KEDA creates and manages an HPA for the 1-to-N range itself and handles 0-to-1 activation.
3. **How it works:** a scaler polls the source at an interval (for example the Kafka lag of a consumer group); the number of desired replicas is roughly `ceil(total lag / lagThreshold)`, bounded by `minReplicaCount` and `maxReplicaCount`; when there is no work it scales down, optionally to zero after a cooldown.
4. **Example `ScaledObject` for Kafka:**

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: order-consumer
spec:
  scaleTargetRef:
    name: order-consumer          # the Deployment
  minReplicaCount: 2
  maxReplicaCount: 24             # never more than the partition count
  cooldownPeriod: 120
  triggers:
    - type: kafka
      metadata:
        bootstrapServers: kafka:9092
        consumerGroup: order-consumer-group
        topic: orders
        lagThreshold: "500"
```

5. **Kafka-specific rules:** set `maxReplicaCount` at or below the number of partitions because extra consumers sit idle; each scale event triggers a consumer rebalance, so use cooperative rebalancing and sensible cooldowns to avoid flapping.
6. **Other uses:** scale on SQS or RabbitMQ queue length, on a Prometheus query (for example requests per second), or by cron (pre-scale before a known peak); scale batch **Jobs** with `ScaledJob`.
7. **Operate it:** KEDA metrics, HPA events and consumer-lag dashboards; test scale-up and scale-down under load.

**Trade-offs and what can go wrong**
- Scaling to zero adds a cold-start delay on the first message.
- Aggressive scaling causes frequent rebalances and duplicate processing; use cooldowns and idempotent consumers.
- If the sink (database) cannot absorb more consumers, scaling just moves the bottleneck and can overload it.
- Lag thresholds that are too low cause over-scaling and cost; too high delays response.
- Nodes must have capacity (cluster autoscaler) or new pods stay pending.

**How I'd monitor it**
Replica count over time against lag, scale events and their reasons, consumer-group rebalance rate, pending pods, and downstream database load.

**Follow-ups to expect**
- *KEDA vs HPA?* -> HPA scales on resource and custom metrics you must provide; KEDA supplies many ready external scalers and scale-to-zero, and it uses HPA underneath.
- *Why cap replicas at the partition count?* -> one partition is read by one consumer in a group, so extra consumers would be idle.
- *Does KEDA replace the cluster autoscaler?* -> no; KEDA scales pods, the cluster autoscaler adds nodes.
- *How do you avoid flapping?* -> cooldown, stabilisation window, and a threshold with headroom.

**60-second answer**
KEDA is Kubernetes Event-Driven Autoscaling. It scales deployments on external signals like Kafka consumer lag, queue length or a Prometheus metric instead of CPU, and it can scale to zero. You define a `ScaledObject` with a trigger, a lag threshold and min and max replicas; KEDA reads the source, exposes it as a metric and manages an HPA, and handles activation from zero. For Kafka I cap replicas at the partition count and use cooldowns, because every scale event triggers a rebalance and the database sink must handle the extra consumers.
