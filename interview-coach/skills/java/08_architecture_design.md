---
id: architecture
title: System design & design patterns
order: 8
summary: Designing real systems end to end, and the design patterns you actually applied and why.
crib: java/java-interview-prep/topics/15-distributed-systems-system-design.md, java/java-interview-prep/topics/17-design-patterns-architecture.md
docs: java/java-interview-prep/deep_dive/16_system_design.md, java/java-interview-prep/deep_dive/17_design_patterns.md, java/java-interview-prep/deep_dive/20_design_patterns_catalogue.md
examples: java/java-interview-prep/examples/17_design_patterns
keywords: design, system design, architecture, pattern, patterns, singleton, factory, builder, strategy, observer, adapter, decorator, facade, template, solid, scalability, scale, load balancer, cache, caching, sharding, high availability, design a, end-to-end, end to end, tps, throughput, capacity
---
Skill focus for System design & design patterns answers:
- Structure: clarify requirements and numbers -> high-level components -> data model -> the 2-3 hard parts (scale, consistency, failure) -> trade-offs -> how it evolves.
- Patterns: explain the problem each solved in a real system (Strategy for pricing rules, Adapter for vendor APIs, Outbox for reliable events), not textbook UML.
- Do capacity arithmetic out loud (QPS, storage, partitions, Little's Law).
