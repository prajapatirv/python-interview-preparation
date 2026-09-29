# Deep Dive — long-form interview Q&A

The topic folder `README.md` files are **crib sheets**: one or two lines per concept, for
revision the morning of an interview.

**These 21 files are the opposite.** Each one is a long-form treatment of a single topic with
multi-paragraph answers, working code, the trade-offs, the failure modes, and — where it
matters — the Java contrast. Read these to *understand*; read the crib sheets to *revise*.

Every file follows the same shape:

1. **What interviewers are actually probing** — why the topic comes up and what separates a
   3-year answer from a 10-year one.
2. **Must-know points** — the compressed version.
3. **Interview questions and full answers** — the substance, with runnable code.
4. **A worked example** — the pieces combined into something realistic.
5. **Hands-on drills** — do these; reading is not enough.
6. **The 60-second spoken answer** — what to actually say out loud.

---

## The 21 deep dives

### Core language

| # | Topic | Runnable companion |
|---|---|---|
| [01](01_data_structures_collections.md) | **Data structures** (list/tuple/dict/set/frozenset) + `collections` | [`01_data_structures.py`](../01_python_core/01_data_structures.py) |
| [02](02_comprehensions_map_filter_reduce.md) | **Comprehensions**, and `map`/`filter`/`reduce` | [`02_comprehensions.py`](../01_python_core/02_comprehensions.py) · [`10_map_filter_reduce.py`](../01_python_core/10_map_filter_reduce.py) |
| [03](03_decorators.md) | **Writing and using custom decorators** | [`03_decorators.py`](../01_python_core/03_decorators.py) |
| [04](04_generators_iterators.md) | **Generators, iterators and iterables** | [`04_generators_iterators.py`](../01_python_core/04_generators_iterators.py) |
| [05](05_context_managers_descriptors_metaclasses.md) | **Context managers, descriptors, metaclasses** | [`05_context_managers.py`](../01_python_core/05_context_managers.py) · [`06_descriptors_metaclasses.py`](../01_python_core/06_descriptors_metaclasses.py) |
| [06](06_oop_inheritance_mro.md) | **OOP in depth** — multiple/multilevel inheritance, MRO, `super()` | [`07_oop_inheritance_mro.py`](../01_python_core/07_oop_inheritance_mro.py) |
| [07](07_concurrency.md) | **Concurrency** — threading / multiprocessing / asyncio | [`02_concurrency/`](../02_concurrency/) |
| [08](08_error_handling.md) | **Error handling** | [`08_exception_handling.py`](../01_python_core/08_exception_handling.py) |

### Data and web

| # | Topic | Runnable companion |
|---|---|---|
| [09](09_pandas.md) | **Pandas for data handling** | [`03_pandas_data_handling/`](../03_pandas_data_handling/) |
| [10](10_web_frameworks.md) | **Django / Flask / FastAPI** (FastAPI in depth) | [`05_web_apis_fastapi/`](../05_web_apis_fastapi/) |
| [11](11_python_framework_development.md) | **Python framework development** | [`12_framework_internals/`](../12_framework_internals/) |
| [12](12_scaling_applications.md) | **Scaling applications & handling challenges** | [`08_scaling_production_resilience/`](../08_scaling_production_resilience/) |

### Kafka

| # | Topic | Runnable companion |
|---|---|---|
| [13](13_kafka_core.md) | **Kafka core** — topics, partitions, replication, producers, consumers | [`01_producer_basics.py`](../06_kafka/01_producer_basics.py) · [`02_consumer_basics.py`](../06_kafka/02_consumer_basics.py) |
| [14](14_kafka_pipelines_delivery_semantics.md) | **Designing Kafka pipelines & delivery semantics** | [`03_delivery_semantics.py`](../06_kafka/03_delivery_semantics.py) |
| [15](15_kafka_failure_handling.md) | **Failure handling** — retry topics, DLQ, consumer idempotency | [`04_retry_topic_dlq.py`](../06_kafka/04_retry_topic_dlq.py) |
| [16](16_kafka_schema_management.md) | **Schema management** — Schema Registry, Avro/Protobuf/JSON Schema | [`06_schema_registry_simulation.py`](../06_kafka/06_schema_registry_simulation.py) |

### Architecture and production

| # | Topic | Runnable companion |
|---|---|---|
| [17](17_caching.md) | **Caching mechanisms** | [`07_caching_queues/`](../07_caching_queues/) |
| [18](18_queue_architectures.md) | **Queue-based architectures** | [`03_queue_patterns.py`](../07_caching_queues/03_queue_patterns.py) |
| [19](19_production_stability_monitoring.md) | **Production stability, alerting & monitoring** | [`05_metrics_alerting_simulation.py`](../08_scaling_production_resilience/05_metrics_alerting_simulation.py) |
| [20](20_ai_first_technologies.md) | **AI-first technologies & solutions** | [`10_genai_llm_patterns/`](../10_genai_llm_patterns/) |

### Bridge

| # | Topic | Runnable companion |
|---|---|---|
| [21](21_java_to_python_bridge.md) | **Java → Python** — syntax, idioms, and the traps | [`11_java_to_python_bridge.py`](../01_python_core/11_java_to_python_bridge.py) |

---

## Suggested reading order

**If you have a week:** `21` (bridge) → `01`–`08` (core) → `10`, `11` (frameworks) →
`13`–`16` (Kafka) → `07`, `12`, `17`, `18`, `19` (systems) → `09` (Pandas) → `20` (AI).

**If you have a day:** read the *60-second spoken answer* at the bottom of each file, then go
deep on the three topics you're weakest on. Practise saying them out loud — the gap between
"I understand this" and "I can explain this in two minutes" is where interviews are lost.

**If you have an hour:** `13` (Kafka core), `14` (delivery semantics), `07` (concurrency).
Those three come up in almost every round for this profile.

---

## Where the material comes from

Distilled from the interview-prep documents in [`../../material_ref/`](../../material_ref/) —
principally the *Python & Kafka Interview Q&A Handbook* (58 pages, 194 questions across the
14 topics this set mirrors) and *Python Advanced Interview Topics* (35 pages: framework
development, scaling, caching, queues, production stability, AI-first) — then expanded with
the trade-offs, failure modes and production detail that the source documents summarise in a
line or two.

**A note on the source PDFs:** three of the six contain real content. `Kafka_Master_Guide.pdf`,
`Kafka_Advanced_Master_Pack.pdf` and `Full_Interview_Preparation.pdf` are mostly generated
placeholder text ("Explain Kafka concept 17", "Answer includes design, trade-offs…") and were
not used beyond their few genuine sections.

---

## Day-before-interview checklist

- [ ] Explain the **GIL**, and when to use threads vs processes vs asyncio, in 60 seconds.
- [ ] Write a **decorator with arguments** (retry or timer) and a **context manager** from memory.
- [ ] Draw the **MRO for a diamond** and explain what `super()` calls, and why.
- [ ] Sketch a **FastAPI app**: router, Pydantic model, `Depends()`, exception handler, `lifespan`.
- [ ] Draw a **Kafka cluster**: topic, partitions, leader/followers, ISR, consumer group.
- [ ] Explain **at-most / at-least / exactly-once** and show *where the commit goes* in code.
- [ ] Describe the **retry-topic + DLQ** flow and how the consumer stays **idempotent**.
- [ ] State **BACKWARD vs FORWARD** compatibility and one safe/unsafe Avro change for each.
- [ ] Explain **cache-aside** and how you'd handle a **stampede**.
- [ ] Explain **SLI / SLO / error budget** and why you alert on symptoms, not causes.
- [ ] Prepare **two stories from your own projects**: one scaling/performance problem you
      diagnosed, one failure you debugged. These matter more than any answer above.
