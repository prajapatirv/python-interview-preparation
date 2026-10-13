"""Fixtures: a tiny fake workspace (skills + content) so unit tests never depend on the real repos.
``test_real_repo.py`` covers the real content."""
import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config  # noqa: E402


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip("\n"), encoding="utf-8")


SCENARIO = """
---
id: kafka-consumers
title: Kafka consumers
stack: java
skill: kafka
---
Intro text.

### Q1 [senior] How do you handle consumer-group rebalancing in production?
tags: rebalancing, static-membership

**The live scenario**
Deploys caused a 400k lag spike.

**How I answer it**
1. Use the cooperative-sticky assignor.

```properties
# not a heading
group.instance.id=${POD_NAME}
```

**Follow-ups to expect**
- *Why not raise max.poll.interval.ms?* -> it hides slow consumers.

**60-second answer**
Diagnose, make it incremental, make it rare.

### Q2 [fresher] What is a consumer group?
tags: consumer-groups

**The live scenario**
Six partitions, ten pods.

**60-second answer**
Each partition goes to one member.
"""

CRIB = """
---
id: 09-kafka
title: Kafka
---
### Q1 [basic] What is Kafka?
A distributed log.

### Q2 [design] Design a Kafka pipeline.
Start with keys.
"""

GUIDE = """
# Guide

# 1. Core Java Fundamentals

## Q1. What is the difference between `==` and `equals()`?
Reference vs value equality.

# 8. Apache Kafka

## Q2. How do you scale Kafka consumers?
Add partitions.

# B. Fresher questions

## B1. What is an enum
A fixed set of constants.
"""

DEEP = """
# Kafka deep dive

## Interview questions and full answers

### Q1. What is lag?
Log-end minus committed.

### Q2. Why rebalance?
Membership changes.

## A worked example
Not a question.
"""


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    root = tmp_path
    write(root / "skills/java/_persona.md", """
        ---
        stack: java
        title: Java
        order: 1
        content: java/prep
        guides: java/prep/Guide.md
        tagline: test stack
        ---
        You are a test persona.
        """)
    write(root / "skills/java/01_kafka.md", """
        ---
        id: kafka
        title: Apache Kafka
        order: 1
        summary: Kafka things.
        crib: java/prep/topics/09-kafka.md
        docs: java/prep/deep_dive/12_kafka.md
        examples: java/prep/examples/12_kafka
        keywords: kafka, consumer, partition, rebalance
        ---
        Kafka skill pack.
        """)
    write(root / "skills/java/02_core.md", """
        ---
        id: java-core
        title: Core Java
        order: 2
        summary: Core.
        keywords: java, equals, string
        ---
        Core pack.
        """)
    write(root / "skills/java/99_general.md", """
        ---
        id: general
        title: General
        order: 99
        summary: Mixed.
        ---
        General pack.
        """)
    write(root / "java/prep/interview-scenarios/02_kafka_consumers.md", SCENARIO)
    write(root / "java/prep/topics/09-kafka.md", CRIB)
    write(root / "java/prep/deep_dive/12_kafka.md", DEEP)
    write(root / "java/prep/Guide.md", GUIDE)
    write(root / "java/prep/examples/12_kafka/01_demo.java", "class A {}")
    monkeypatch.setattr(config, "WORKSPACE_ROOT", root.resolve())
    monkeypatch.setattr(config, "SKILLS_DIR", (root / "skills").resolve())
    monkeypatch.setattr(config, "AI_MODE", "mock")
    monkeypatch.setattr(config, "DATA_DIR", (root / "data").resolve())
    return root


@pytest.fixture
def client(workspace):
    from fastapi.testclient import TestClient
    from app.main import create_app
    return TestClient(create_app())
