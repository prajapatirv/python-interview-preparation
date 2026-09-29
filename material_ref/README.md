# material_ref — source interview-prep PDFs

Read-only reference. The notes in [`../python-interview-prep/`](../python-interview-prep/) — both
the folder crib sheets and the 21 [`deep_dive/`](../python-interview-prep/deep_dive/) documents —
are distilled from these.

## What's actually in each file

| File | Pages | Content | Used? |
|---|---|---|---|
| **`Python_Kafka_Interview_QA_Handbook.pdf`** | 58 | **194 questions across 14 topics** (T01–T14): data structures + `collections`, comprehensions, decorators, generators/iterators, context managers/descriptors/metaclasses, OOP & MRO, concurrency, error handling, Pandas, Django/Flask/FastAPI, Kafka core, delivery semantics, failure handling, schema management | **Yes — the spine.** The `deep_dive/` set mirrors its 14 topics |
| **`Python_Advanced_Topics_Interview.pdf`** | 35 | Sections A–G: framework development, scaling, Kafka deep dive, caching, queue architectures, production stability/alerting/monitoring, AI-first technologies | **Yes** — deep dives 11, 12, 17, 18, 19, 20 |
| **`Python_Developer_Interview_Complete.pdf`** | 37 | 19 sections: Python basic→advanced, exceptions, memory, threading, TDD, FastAPI, REST, Apache Camel, Kafka, Couchbase, Airflow, AWS Lambda, streaming large files, Java/Scala→Python migration, Terraform/Databricks, microservices & leadership | **Yes** — core language, AWS/streaming, and the Java-migration material in deep dive 21 |
| `Kafka_Master_Guide.pdf` | 2 | A one-page Kafka primer (producer, consumer, topic, partition, offset) | Minimally — superseded by the Handbook |
| `Kafka_Advanced_Master_Pack.pdf` | 4 | Two Spring Boot Kafka snippets, then **20 placeholder questions**: *"Explain Kafka concept 1 with producer, consumer, partition, offset"*, …concept 2, …concept 20 | **No** — generated filler |
| `Full_Interview_Preparation.pdf` | 9 | A short Java/Spring/microservices Q&A, then **50 placeholder sets**: *"Q: Explain architecture concept 1 / A: Answer includes design, trade-offs, scalability, and production example for fintech systems"*, ×50 | **No** — generated filler |

**In short: three of the six contain real content.** The other three are template output where the
generator never filled in the bodies. They're kept here for completeness, but nothing was drawn
from them beyond their few genuine opening sections.

## Extracting the text

These are ReportLab- and Chrome-generated PDFs. `pdftoppm`/poppler is not installed on this
machine, and the Chrome-generated ones use a subset font with a +29 glyph offset that defeats a
naive text scrape. The reliable route:

```bash
py -m pip install --target /tmp/libs pypdf
```

```python
import sys; sys.path.insert(0, "/tmp/libs")
from pypdf import PdfReader

reader = PdfReader("material_ref/Python_Kafka_Interview_QA_Handbook.pdf")
text = "\n".join(page.extract_text() or "" for page in reader.pages)
```

`pypdf` handles the font encoding correctly; a hand-rolled `zlib` + `Tj`-operator extractor does
not, and will hand you `3\WKRQ` instead of `Python`.

## Where each topic ended up

| Source topic | Deep dive |
|---|---|
| T01 Data structures + `collections` | [01](../python-interview-prep/deep_dive/01_data_structures_collections.md) |
| T02 Comprehensions | [02](../python-interview-prep/deep_dive/02_comprehensions_map_filter_reduce.md) |
| T03 Decorators | [03](../python-interview-prep/deep_dive/03_decorators.md) |
| T04 Generators, iterators, iterables | [04](../python-interview-prep/deep_dive/04_generators_iterators.md) |
| T05 Context managers, descriptors, metaclasses | [05](../python-interview-prep/deep_dive/05_context_managers_descriptors_metaclasses.md) |
| T06 OOP in depth | [06](../python-interview-prep/deep_dive/06_oop_inheritance_mro.md) |
| T07 Concurrency | [07](../python-interview-prep/deep_dive/07_concurrency.md) |
| T08 Error handling | [08](../python-interview-prep/deep_dive/08_error_handling.md) |
| T09 Pandas | [09](../python-interview-prep/deep_dive/09_pandas.md) |
| T10 Django / Flask / FastAPI | [10](../python-interview-prep/deep_dive/10_web_frameworks.md) |
| T11 Kafka core | [13](../python-interview-prep/deep_dive/13_kafka_core.md) |
| T12 Kafka pipelines & delivery semantics | [14](../python-interview-prep/deep_dive/14_kafka_pipelines_delivery_semantics.md) |
| T13 Kafka failure handling | [15](../python-interview-prep/deep_dive/15_kafka_failure_handling.md) |
| T14 Kafka schema management | [16](../python-interview-prep/deep_dive/16_kafka_schema_management.md) |
| Section A — Framework development | [11](../python-interview-prep/deep_dive/11_python_framework_development.md) |
| Section B — Scaling | [12](../python-interview-prep/deep_dive/12_scaling_applications.md) |
| Section D — Caching | [17](../python-interview-prep/deep_dive/17_caching.md) |
| Section E — Queue architectures | [18](../python-interview-prep/deep_dive/18_queue_architectures.md) |
| Section F — Production stability | [19](../python-interview-prep/deep_dive/19_production_stability_monitoring.md) |
| Section G — AI-first technologies | [20](../python-interview-prep/deep_dive/20_ai_first_technologies.md) |
| Java/Scala → Python migration | [21](../python-interview-prep/deep_dive/21_java_to_python_bridge.md) |
| Camel, Couchbase, Airflow, Terraform/Databricks | [QUESTION_INDEX.md Part 2](../python-interview-prep/QUESTION_INDEX.md) — concept-only |
