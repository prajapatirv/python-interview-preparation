# What we learned from popular interview-prep sites (2026-10)

Reviewed: interviewing.io, Pramp (now hosted on Aced Practice), Hello Interview, InterviewBuddy,
Big Interview, GeeksforGeeks (Java and Kafka question lists), intervue.io (Kafka questions),
Hello Interview's Kafka deep dive, Educative's interview page. Not reviewable by automated fetch:
LeetCode and devgenius.io/Medium (HTTP 403), javarevisited's list (paywalled after the intro). Their
content was used only to check coverage gaps and UX ideas — nothing is copied.

## Content findings

- The big question lists (GfG: 91 Kafka questions; intervue.io: 100) are **definition-style**:
  one to five sentences per answer. That is exactly the gap this app fills with scenario answers.
- intervue.io groups questions by **experience band** (0–2, 3–6, 6–8, 8–10, 10+ years) and its 10+
  band is judgement/behavioural ("persuade a team to adopt event-driven"). → our four levels with
  year hints, and the Leadership topic.
- Hello Interview's Kafka deep dive centres on **partitioning strategy and hot partitions**, consumer
  failure and retries (retry topic + DLQ), and says expectations scale with level.
- Consumer-side questions present in those lists but missing from our scenario bank before this
  work, now covered in `interview-scenarios/02_kafka_consumers.md`: `commitSync` vs `commitAsync`,
  `auto.offset.reset`, the heartbeat thread vs `max.poll.interval.ms`, assignment strategies and
  KIP-848, lag that appears only under production load, a consumer group that silently stops.
- Still worth adding as scenario banks later (present in the crib sheets/guides, not yet in
  scenario form): producer `acks`/idempotence, ISR and `min.insync.replicas`, log compaction,
  Schema Registry evolution, Kafka Streams vs a plain consumer, Connect, MirrorMaker/DR, security.

## UX patterns adopted

| Pattern (seen on) | In the coach |
|---|---|
| Attempt first, then model answer (Big Interview, Pramp) | **Practice mode** hides the answer until you have tried |
| Multi-dimension scorecard, not one number (Big Interview, InterviewBuddy) | Five dimensions: scenario, depth, trade-offs, monitoring, clarity |
| "In a hurry" / fast-track path (Hello Interview, Big Interview) | **Quick revision**: 60-second answers only |
| Level-specific tracks (interviewing.io, intervue.io) | Level filter with year bands; grading calibrated to level |
| Progress over time (InterviewBuddy, Big Interview) | "I can answer this" per question; score history per topic |
| Job-description tie-in (Big Interview) | **Job description** screen: plan + likely questions |
| Written post-session feedback with strengths and gaps (interviewing.io) | Scorecard sections "What you did well" / "What was missing" + follow-up |
| AI tutor next to the material (Hello Interview) | "Go deeper" and "Ask anything", grounded on the bank |

Not adopted (out of scope for a self-study tool): live peer matching, video recording, paid expert sessions.

## Second pass (same day): remaining sites and the interview feedback

- **GeeksforGeeks Java, experienced section:** GC (minor/major/full), memory leaks, JDBC, fail-fast vs
  fail-safe iterators, Comparable vs Comparator. Performance coverage there is shallow — definitions only.
- **Educative:** organised around coding *patterns* (its "Grokking" course, 24–26 patterns) plus system design,
  API design and low-level design, with role/company/date-based personalised plans. A future idea for the
  coach's Coding topic: group coding questions by pattern (two pointers, sliding window, BFS/DFS, heaps, DP...).
- **Interview feedback received (2026-10-13)** named four weak areas. None of the reviewed sites covers them in
  scenario form, so they became four new scenario banks (45 questions): API response time/throughput,
  CPU/memory efficiency, performance-measurement tools, and Kafka tuning at scale — plus a dedicated
  *Performance engineering* topic in the coach.
