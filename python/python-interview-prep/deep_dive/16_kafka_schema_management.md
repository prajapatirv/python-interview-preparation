# Deep Dive 16 — Schema Management in Kafka (Schema Registry, Avro / Protobuf / JSON Schema)

> Runnable companions: [`06_kafka/05_schema_registry_avro_notes.md`](../06_kafka/05_schema_registry_avro_notes.md) ·
> [`06_kafka/06_schema_registry_simulation.py`](../06_kafka/06_schema_registry_simulation.py) —
> a dependency-free simulation of the wire format and compatibility checking.
> Related deep dives: [Kafka core](13_kafka_core.md) · [Failure handling](15_kafka_failure_handling.md) ·
> [Framework development](11_python_framework_development.md)

## What interviewers are actually probing

**Kafka stores bytes.** Brokers do not validate payloads, so any producer can publish anything and
break every consumer downstream. Schema management is how a multi-team event platform stays
functional as teams deploy independently.

The questions cluster around four things: **how the registry works** (including the wire format —
people who've actually debugged this know the magic byte), **subject naming strategies**,
**compatibility modes** (and which direction you upgrade first), and **which schema changes are
safe**. The last one is the most commonly asked and the most commonly fumbled.

---

## Must-know points

- Schema Registry stores **versioned schemas per subject** and returns a **global schema ID**.
- **Confluent wire format**: magic byte `0` + **4-byte big-endian schema ID** + serialised payload.
- **Subject naming**: `TopicNameStrategy` (default, `<topic>-value`), `RecordNameStrategy`,
  `TopicRecordNameStrategy`.
- **Compatibility**: `BACKWARD` (default), `FORWARD`, `FULL`, their `_TRANSITIVE` forms, `NONE`.
- **Safe evolution**: add optional fields **with defaults**; never change types or reuse field
  numbers.
- **`auto.register.schemas=false` in production** — register through CI/CD, not from a running
  service.

---

## Interview questions and full answers

### Q1. Why do we need schema management in Kafka?

**Because Kafka brokers don't validate payloads.** A topic is a byte log. If the `orders` producer
team renames `total` to `total_amount`, every consumer breaks — at runtime, in production, with no
warning at deploy time.

Schemas solve four distinct problems:

1. **A contract between teams.** The schema is the API of the topic. Without one, the contract is
   "whatever the producer happened to send last Tuesday", discovered by reading production data.
2. **Compact binary serialisation.** Avro/Protobuf are far smaller than JSON — no repeated field
   names per record. On a high-volume topic that's a large reduction in network, disk and
   retention cost.
3. **Safe evolution.** With a registry enforcing compatibility, producers and consumers can be
   deployed **independently** — no coordinated big-bang release across five teams.
4. **Documentation that can't drift**, because it's the same artefact the serialiser uses.

**The failure mode without a registry**, and worth describing concretely: a producer adds a required
field. Old consumers deserialise into a model missing that field and either crash or silently drop
it. The failure appears in a **different team's service**, hours later, with no obvious link to the
deploy that caused it. That's the incident schema management prevents.

**It also prevents most poison pills** — see
[Failure handling Q2](15_kafka_failure_handling.md#q2-what-is-a-poison-pill-message-and-how-do-you-handle-it).
Catching a bad schema at CI is infinitely cheaper than catching it in a DLQ.

---

### Q2. What is Confluent Schema Registry and how does it work?

A **REST service** that stores schemas under **subjects** with **versions**, assigns each unique
schema a **global ID**, and **checks compatibility** on registration.

**The flow:**

```
PRODUCER                     SCHEMA REGISTRY                    CONSUMER
   │                                │                               │
   │ 1. register/lookup schema      │                               │
   ├───────────────────────────────>│                               │
   │ 2. schema ID = 42              │                               │
   │<───────────────────────────────┤                               │
   │                                │                               │
   │ 3. produce: [0][0,0,0,42][avro bytes]                          │
   ├──────────────> KAFKA ──────────────────────────────────────────>│
   │                                │                               │
   │                                │ 4. "what is schema 42?"       │
   │                                │<──────────────────────────────┤
   │                                │ 5. the writer schema (CACHED) │
   │                                ├──────────────────────────────>│
   │                                │            6. decode, resolve  │
   │                                │               against reader   │
```

**Key properties:**

- **Only the 5-byte header travels with each record**, never the schema itself. On a 200-byte
  message that's 2.5% overhead; embedding the schema would often exceed the payload.
- **Clients cache aggressively.** The registry is consulted on first sight of a schema ID, then
  cached in memory. A registry outage does **not** immediately stop a running pipeline — it stops
  *new* schema registrations and cold starts. Worth saying, because people assume it's a hard
  dependency on the hot path.
- **The registry stores its data in a Kafka topic** (`_schemas`, compacted), so it's as durable as
  the cluster itself and can be rebuilt by replaying that topic.
- **Schema resolution**: the consumer decodes with the **writer's** schema and projects onto its own
  **reader** schema. That projection — driven by defaults and aliases — is what makes evolution work.

**Alternatives** worth naming: **AWS Glue Schema Registry** (native to MSK, IAM-integrated),
**Apicurio** (open source, Red Hat), **Karapace** (open source, Aiven, Confluent-API-compatible).

---

### Q3. Describe the Confluent wire format.

```
Byte 0      : magic byte, always 0x00
Bytes 1-4   : schema ID, 4-byte BIG-ENDIAN signed int
Bytes 5..n  : the serialised payload
              (for Protobuf, message-index bytes come first, then the payload)
```

```python
import struct

def schema_id_of(raw: bytes) -> int:
    magic, sid = struct.unpack(">bI", raw[:5])      # ">" = big-endian
    assert magic == 0, "not Confluent-framed"
    return sid
```

**Why this is worth knowing rather than trivia:** it's the **first thing you check when
deserialisation fails**. Dump the first 5 bytes of the failing message:

- **Starts with `0x00`** → correctly framed; the problem is the schema itself or a registry lookup.
- **Starts with `0x7B`** (`{`) → someone produced **plain JSON** to an Avro topic. Very common when a
  test script or a different team's service writes to the wrong topic.
- **Anything else** → corruption, wrong serialiser, or a non-Confluent producer.

That five-second check saves hours, and mentioning it signals you've actually debugged a Kafka
pipeline rather than only read about one.

**The schema ID is global**, not per-subject — the same schema registered under two subjects gets the
same ID, because the registry deduplicates by schema content.

---

### Q4. Avro vs Protobuf vs JSON Schema — how do you choose?

| | **Avro** | **Protobuf** | **JSON Schema** |
|---|---|---|---|
| **Encoding** | Compact binary | Compact binary | Text (JSON) |
| **Size** | Smallest | Very small | **Largest** (3–10×) |
| **Speed** | Fast | **Fastest** | Slowest |
| **Human readable?** | No | No | **Yes** |
| **Schema needed to read?** | **Yes, always** | No (self-describing enough) | No |
| **Evolution mechanism** | Field **names** + defaults | Field **numbers** | JSON Schema rules |
| **Code generation** | Optional | **Strong**, many languages | Optional |
| **Ecosystem fit** | **Kafka/Hadoop/Spark native** | gRPC, polyglot microservices | Web, browsers |

**Choosing:**

- **Avro** — the Kafka/Confluent default and the best fit for **data pipelines and lakes**. Excellent
  evolution via defaults and aliases, and it's what Spark, Hive, Flink and most lake tooling expect
  natively. **Pick this unless you have a specific reason not to.**
- **Protobuf** — best when you're already **gRPC-heavy** and want one IDL across services and events,
  or need strong generated types in many languages. Evolution is by **field number**, which is
  stricter and arguably safer.
- **JSON Schema** — when **human readability and debuggability outweigh efficiency**: low-volume
  topics, browser-facing events, or a team without binary-format tooling. You can read messages
  straight off the topic with `kafka-console-consumer`, which is genuinely valuable during
  development.

**The most important practical difference:** **Avro requires the writer's schema to read anything.**
There is no way to partially decode an Avro record without it. That makes the registry a hard
dependency for consumption (though caching softens it) and makes raw-byte debugging painful. Protobuf
and JSON degrade more gracefully.

**Don't mix formats on one topic.** Pick one per topic and enforce it.

---

### Q5. What is a subject, and what are the subject naming strategies?

A **subject** is the scope under which schema **versions** and **compatibility** are tracked. Choosing
the strategy determines what "compatible" is checked *against*.

| Strategy | Subject name | Use when |
|---|---|---|
| **TopicNameStrategy** (default) | `<topic>-key`, `<topic>-value` | One record type per topic — the normal case |
| **RecordNameStrategy** | `<fully.qualified.RecordName>` | Multiple event types across topics; evolution follows the **type**, wherever it appears |
| **TopicRecordNameStrategy** | `<topic>-<RecordName>` | Multiple event types in **one** topic, evolved **per topic** |

**Why the non-default strategies exist:** with `TopicNameStrategy` a topic can hold exactly **one**
value type, because there's one subject and one compatibility lineage. But a common and legitimate
design puts **several event types on one topic** — `OrderPlaced`, `OrderPaid`, `OrderShipped` — so
that they share a partition (and therefore ordering) per order.

For that, `TopicRecordNameStrategy` gives each record type its own subject *within* the topic, so
`OrderPlaced` and `OrderShipped` evolve independently.

```python
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import (
    SerializationContext, MessageField, topic_record_subject_name_strategy,
)

ser = AvroSerializer(
    sr_client, schema_str,
    conf={"subject.name.strategy": topic_record_subject_name_strategy},
)
```

**The trade-off to state:** multiple types per topic preserves cross-type ordering for an entity
(which is often exactly what you want for an order lifecycle), but it complicates consumers — they
must handle a **union** of types and skip the ones they don't care about. With
`TopicNameStrategy` and separate topics, each consumer's contract is simpler but you lose ordering
across the lifecycle.

**Keys get their own subject too** (`<topic>-key`). People forget this and register only the value
schema; then a key schema change breaks things with no compatibility check having run.

---

### Q6. Explain the compatibility modes.

This is the highest-frequency question in this topic, and the part people get backwards is **which
side you upgrade first**.

| Mode | Meaning | You may | **Upgrade first** |
|---|---|---|---|
| **`BACKWARD`** (default) | A **new**-schema **consumer** can read **old** data | Delete fields; add fields **with defaults** | **Consumers** |
| **`FORWARD`** | An **old**-schema **consumer** can read **new** data | Add fields; delete **optional** fields | **Producers** |
| **`FULL`** | Both | Only add/remove fields **with defaults** | Either |
| **`*_TRANSITIVE`** | Checked against **all** previous versions, not just the latest | — | — |
| **`NONE`** | No checks | Anything | — |

**The mnemonic that makes it stick:**

- **BACKWARD** = the new code can read **backwards in time**, i.e. old data. So you deploy the **new
  consumers first**; they can handle both old and new messages. Then producers switch over.
- **FORWARD** = old code can read data from the **future**. So you deploy the **new producers
  first**; existing consumers keep working. Then upgrade consumers at leisure.

**Why `BACKWARD` is the default:** in Kafka, data is **retained**. A consumer reading a 7-day topic
from the beginning will encounter old-schema messages *today*. It must be able to read them. That's
the common case, so `BACKWARD` is the sensible default.

**Choosing `FORWARD`:** when you can't control or coordinate consumer upgrades — many downstream
teams, external consumers, or consumers you don't own. Producers move forward and nobody breaks.

**The `_TRANSITIVE` distinction genuinely matters.** Plain `BACKWARD` only checks the **latest**
version. So v1 → v2 → v3 can each be individually compatible while **v3 cannot read v1 data**.
With a 30-day retention window, a consumer reading from the beginning hits v1 messages and fails.
**`BACKWARD_TRANSITIVE` checks against every previous version** and is what you want for topics with
long retention or replay requirements.

```bash
# Set per subject
curl -X PUT http://localhost:8081/config/orders-value \
     -H "Content-Type: application/vnd.schemaregistry.v1+json" \
     -d '{"compatibility": "BACKWARD_TRANSITIVE"}'
```

**`NONE` is a decision to have no contract.** Sometimes legitimate for a scratch/dev topic; never for
a shared production one.

---

### Q7. Which schema changes are safe under `BACKWARD` compatibility in Avro?

**Safe:**

| Change | Why |
|---|---|
| **Add a field WITH a default** | Reading old data, the missing field takes the default |
| **Remove a field** | The new reader simply ignores it in old data |
| **Add an alias** to a field | Lets the reader match a renamed field to its old name |
| **Widen to a union with null** (`["null","string"]`, default `null`) | Old non-null values still decode |
| **Add an enum symbol** — *only* with a `default` symbol set on the enum | Old readers map unknown symbols to the default |
| **Reorder fields** | Avro matches by **name**, not position |

**Unsafe:**

| Change | Why it breaks |
|---|---|
| **Add a field WITHOUT a default** | Old data has no value and no fallback → decode error |
| **Change a field's type incompatibly** (`string` → `int`) | The bytes can't be reinterpreted |
| **Rename a field without an alias** | Avro matches by name; the old name is now unknown and the new one is missing |
| **Remove an enum symbol** old data may contain | No mapping for that value, unless a default symbol exists |
| **Change a field from optional to required** | Old records with null fail |
| **Change the record's name or namespace** | It's a different type entirely |

```json
// v1
{"type": "record", "name": "Order", "namespace": "com.shop",
 "fields": [
   {"name": "id",     "type": "string"},
   {"name": "amount", "type": "double"}
 ]}

// v2 — BACKWARD compatible
{"type": "record", "name": "Order", "namespace": "com.shop",
 "fields": [
   {"name": "id",       "type": "string"},
   {"name": "amount",   "type": "double"},
   {"name": "currency", "type": "string",           "default": "INR"},
   {"name": "coupon",   "type": ["null", "string"], "default": null}
 ]}
```

**Two details that catch people out:**

1. **In a union, the default must match the FIRST type in the union.** `["null","string"]` with
   `"default": null` is correct. `["string","null"]` with `"default": null` is **invalid** — the
   default must be a `string`. Always put `"null"` first.
2. **A default is not the same as "nullable".** `{"name":"currency","type":"string","default":"INR"}`
   is a **required** string that defaults when *absent from old data* — you still cannot write `null`
   to it. For genuinely nullable, use the union.

**The renaming workflow**, since renames are so common:

```json
{"name": "total_amount", "type": "double", "aliases": ["amount"]}
```

The alias tells the reader "if you see `amount` in the writer's schema, that's me". This is the
correct way to rename a field without breaking historical data.

---

### Q8. What are Protobuf schema evolution rules?

Protobuf identifies fields by **number**, not name — which changes the rules in a way worth knowing:

**Safe:**
- **Add new fields** with new numbers — old readers ignore unknown fields (they're preserved in
  unknown-field storage and round-tripped).
- **Rename a field** — wire-safe, since only the number matters.
- **Remove a field** — **but mark it `reserved`**.
- Widen `int32` → `int64`, `sint32` → `sint64` (compatible varint encodings).

**Unsafe:**
- **Change an existing field's number** — it becomes a different field.
- **Change an existing field's type** incompatibly (`int32` → `string`).
- **Reuse the number of a deleted field** — old data with the old meaning decodes as the new field.
  **This is the classic Protobuf disaster**, which is why `reserved` exists.

```protobuf
message Order {
  reserved 3, 7 to 9;                  // NEVER reuse these numbers
  reserved "old_field_name";           // nor these names

  string id = 1;
  double amount = 2;
  optional string coupon = 4;          // proto3 `optional` -> explicit presence tracking
}
```

**The proto3 presence gotcha:** in proto3 (before the `optional` keyword returned in 3.15) every
scalar field has an implicit zero default and **no presence tracking**. You cannot distinguish "the
producer set `amount` to 0" from "the producer didn't set `amount`". For a monetary field that's a
correctness problem. Use the `optional` keyword or a wrapper type (`google.protobuf.DoubleValue`).

**Renaming caveat:** renaming is wire-safe but **breaks the JSON mapping** (which uses names) and
breaks generated code for every consumer — so it's a source-compatibility break even though it isn't
a wire break. Treat it as breaking in practice.

---

### Q9. Produce Avro messages with `confluent-kafka-python` and Schema Registry.

```python
from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import (
    SerializationContext, MessageField, StringSerializer,
)

schema_str = open("schemas/order_v2.avsc").read()

sr = SchemaRegistryClient({"url": "http://localhost:8081"})

avro_ser = AvroSerializer(
    sr, schema_str,
    conf={
        "auto.register.schemas": False,   # CI registers; the service must not (see Q11)
        "use.latest.version": False,
    },
)
key_ser = StringSerializer("utf_8")

p = Producer({"bootstrap.servers": "localhost:9092", "enable.idempotence": True})

order = {"id": "o-1", "amount": 499.0, "currency": "INR", "coupon": None}
p.produce(
    "orders",
    key=key_ser(order["id"]),
    value=avro_ser(order, SerializationContext("orders", MessageField.VALUE)),
)
p.flush()
```

**Points to note:**

- **`SerializationContext`** tells the serialiser the topic and whether it's the key or the value —
  that's how the subject name is derived (`orders-value`).
- **`auto.register.schemas=False`** means the serialiser **looks up** the schema rather than
  registering it. If the schema isn't already in the registry, it fails loudly at startup — which is
  what you want (Q11).
- **The dict must match the schema exactly.** A missing required field or an extra key raises at
  serialisation time, before anything reaches Kafka. That's the validation you're paying for.
- There's also a **`SerializingProducer`** that wires the serialisers in, so `produce()` takes plain
  Python objects — cleaner, though the explicit form shows what's happening.

**A practical tip:** keep `.avsc` files **in the repo, version-controlled, next to the code**, and
register them from CI. The schema is source, not configuration.

---

### Q10. Consume Avro messages with the deserialiser.

```python
from confluent_kafka import Consumer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.serialization import SerializationContext, MessageField

sr = SchemaRegistryClient({"url": "http://localhost:8081"})

# No schema argument -> the WRITER's schema is resolved from the ID in each message
avro_de = AvroDeserializer(sr)

# Or pass YOUR schema as the reader schema to project onto your version:
# avro_de = AvroDeserializer(sr, schema_str=open("schemas/order_v1.avsc").read())

c = Consumer({
    "bootstrap.servers": "localhost:9092",
    "group.id": "billing",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,
})
c.subscribe(["orders"])

msg = c.poll(5.0)
order = avro_de(msg.value(), SerializationContext(msg.topic(), MessageField.VALUE))
print(order["id"], order.get("currency"))
```

**The reader-schema point is the important one.** Without a reader schema you get whatever the
producer wrote — including fields your code doesn't know about, and *missing* fields your code
expects (because the producer was on an older version).

**Passing your own reader schema makes the resolution explicit**: Avro projects the writer's data
onto your schema, applying your defaults for fields the writer didn't have and dropping fields you
don't declare. Your code then sees a **stable shape** regardless of which producer version wrote the
message. That's what makes independent deployment actually work, and it's why `order.get("currency")`
in the no-reader-schema version has to be defensive.

**Error handling:** deserialisation failures raise `ValueDeserializationError` carrying the raw
message. Route it to the DLQ — deserialisation failures are always permanent. See
[Failure handling Q12](15_kafka_failure_handling.md#q12-how-do-you-handle-deserialization-errors-in-confluent-kafka-python).

---

### Q11. Should producers auto-register schemas in production?

**No.** Set **`auto.register.schemas=false`** in production and register schemas through **CI/CD**
after an explicit compatibility check.

**Why auto-registration is dangerous:**

1. **Any deployed service can silently change a shared contract.** A developer adds a field, deploys,
   and the schema is now registered — with no review, no compatibility gate that anyone saw, and no
   record of the decision.
2. **A bug becomes a schema.** Accidentally serialise with the wrong model and you've registered a
   new version of a production contract.
3. **Race conditions.** Several instances deploying simultaneously can register concurrently.
4. **No audit trail.** Who changed the `orders` contract, and when? The registry knows *what*; you
   want to know *why*, which lives in a pull request.

**The correct workflow:**

```
1. Developer edits schemas/order_v3.avsc          (source-controlled, reviewed)
2. CI runs a compatibility check against the registry   -> FAILS THE BUILD if breaking
3. Code review approves both the code and the schema change
4. On merge, CI registers the new version
5. The service deploys with auto.register.schemas=false and LOOKS UP the schema
```

If the schema isn't registered, the service **fails at startup** — loudly, in staging, before any
customer is affected. That's the behaviour you want.

**`use.latest.version=true`** is a related setting: the producer uses the latest registered version
rather than the one compiled into it. Useful in some workflows, but it means your producer's
behaviour can change without a deploy — usually you want the explicit version.

---

### Q12. How do you check compatibility before deploying?

Call the registry's compatibility endpoint in the pipeline and **fail the build** if incompatible.

```python
import requests, json, sys

SR = "http://localhost:8081"
H = {"Content-Type": "application/vnd.schemaregistry.v1+json"}

def check(subject: str, schema_path: str, schema_type="AVRO"):
    schema = open(schema_path).read()
    r = requests.post(
        f"{SR}/compatibility/subjects/{subject}/versions/latest",
        headers=H,
        params={"verbose": "true"},          # explains WHY it's incompatible
        data=json.dumps({"schema": schema, "schemaType": schema_type}),
    )
    r.raise_for_status()
    body = r.json()
    if not body["is_compatible"]:
        print(f"BREAKING CHANGE in {subject}:", body.get("messages"), file=sys.stderr)
        sys.exit(1)
    print(f"{subject}: compatible")

check("orders-value", "schemas/order_v3.avsc")
```

**Use `versions/latest` or `versions/-1`?** For a `*_TRANSITIVE` compatibility setting, check against
**all** versions by using the subject-level endpoint — `POST /compatibility/subjects/{s}/versions`
with `verbose=true` — which honours the configured transitive mode. The `latest` endpoint checks only
against the most recent version.

**`verbose=true` is worth it** — instead of just `false`, you get a message like
`"Schema being registered is incompatible with an earlier schema for subject ... reader field
'currency' is missing a default value"`, which tells the developer exactly what to fix.

**Other tooling:** the Confluent Maven/Gradle plugins do this for JVM projects; `kafka-schema-registry
-maven-plugin` has a `test-compatibility` goal. For Python, the small script above in a pre-merge CI
job is the standard approach.

**Also check the reverse direction in CI:** register the *new* schema in a throwaway registry and
verify your *existing consumers'* schemas can still read data written with it. That catches the case
the registry's one-directional check misses.

---

### Q13. How do you handle a truly breaking schema change?

Sometimes you genuinely must break — a field's type was wrong from the start, or the domain model has
fundamentally changed. **Don't force it into the same subject** with `NONE` compatibility; that just
breaks consumers at runtime instead of at CI.

**The migration:**

1. **Create a new topic** (`orders.v2`) or a new record type. A new topic is cleaner — different
   subject, independent retention, no ambiguity about which schema a message uses.
2. **Dual-write** from the producer to both `orders` and `orders.v2` for a transition period. Or run
   a **translation stream** — a small consumer reading `orders`, converting, and producing to
   `orders.v2` — which means producers don't change at all.
3. **Migrate consumers one at a time** to the new topic, verifying each.
4. **Monitor the old topic's consumer groups** until traffic reaches zero.
5. **Wait a full business cycle** — month-end jobs, quarterly reports, any batch consumer you forgot.
6. **Retire** the old topic.

**The translation-stream option is usually best**, because it decouples the timelines entirely:
producers keep writing v1, the stream keeps v2 populated, and consumers move when they're ready. It
also gives you a single place where the mapping logic lives and can be tested.

**Communicate through a data-contract process**: a versioning policy, a deprecation notice with a
sunset date, and owner contacts for every topic. This is the same discipline as
[API versioning](11_python_framework_development.md#q8-how-do-you-implement-api-versioning-without-breaking-clients)
— same problem, different transport.

---

### Q14. What are data contracts and schema references?

**Schema references** let one schema **import another**, so shared types are defined once:

```json
// address.avsc  -> subject "com.shop.Address"
{"type": "record", "name": "Address", "namespace": "com.shop",
 "fields": [{"name": "city", "type": "string"},
            {"name": "pincode", "type": "string"}]}

// order.avsc — references it rather than inlining
{"type": "record", "name": "Order", "namespace": "com.shop",
 "fields": [{"name": "id", "type": "string"},
            {"name": "ship_to", "type": "com.shop.Address"}]}
```

```python
from confluent_kafka.schema_registry import Schema, SchemaReference

sr.register_schema("orders-value", Schema(
    order_schema_str, "AVRO",
    references=[SchemaReference("com.shop.Address", "com.shop.Address", version=1)],
))
```

Two uses: **shared types** across many schemas (define `Address` once, evolve it once), and **a union
of event types in one topic** — a `TopicRecordNameStrategy` topic whose value schema is a union of
`OrderPlaced | OrderPaid | OrderShipped`, each referenced.

**Data contracts** are the newer Schema Registry capability that turns the schema into something
**enforceable** beyond structure:

- **Metadata and tags** — mark fields as `PII`, attach an owner, a domain, an SLA.
- **Data-quality rules** — CEL expressions validated on produce/consume, e.g.
  `amount > 0 && currency in ['INR','USD']`. Structural validity isn't semantic validity; this closes
  that gap.
- **Field-level encryption (CSFLE)** — fields tagged `PII` are encrypted client-side, so the broker
  and anyone browsing the topic never see plaintext. This is a serious compliance capability.
- **Migration rules** — declarative transformations applied during schema evolution, so consumers on
  an old version still receive correctly-shaped data.

**The framing to give:** a schema says *what shape the data is*. A data contract says *what the data
means, who owns it, what's valid, and what's sensitive* — and enforces it. It's the natural next step
once several teams depend on the same topics, and it moves data governance from a wiki page into the
pipeline.

---

## Worked example — register a schema, set compatibility, list versions via the REST API

The registry is a plain REST service, so you can do everything with `requests`. This is what a CI
step looks like.

```python
import requests, json

SR = "http://localhost:8081"
H = {"Content-Type": "application/vnd.schemaregistry.v1+json"}
subject = "orders-value"

# 1. Enforce BACKWARD_TRANSITIVE for this subject — checks against ALL previous versions
r = requests.put(f"{SR}/config/{subject}", headers=H,
                 data=json.dumps({"compatibility": "BACKWARD_TRANSITIVE"}))
r.raise_for_status()

# 2. Check compatibility BEFORE registering (the CI gate)
schema = open("schemas/order_v2.avsc").read()
r = requests.post(f"{SR}/compatibility/subjects/{subject}/versions/latest",
                  headers=H, params={"verbose": "true"},
                  data=json.dumps({"schema": schema, "schemaType": "AVRO"}))
result = r.json()
assert result["is_compatible"], f"breaking change: {result.get('messages')}"

# 3. Register the new version (the CI/CD step, NOT the service)
r = requests.post(f"{SR}/subjects/{subject}/versions", headers=H,
                  data=json.dumps({"schema": schema, "schemaType": "AVRO"}))
print("schema id", r.json()["id"])

# 4. Inspect
print("versions:", requests.get(f"{SR}/subjects/{subject}/versions").json())
print("latest:", requests.get(f"{SR}/subjects/{subject}/versions/latest").json())
print("global config:", requests.get(f"{SR}/config").json())
print("all subjects:", requests.get(f"{SR}/subjects").json())
```

**Useful endpoints to know:**

| Endpoint | Purpose |
|---|---|
| `GET /subjects` | List all subjects |
| `GET /subjects/{s}/versions` | Version numbers for a subject |
| `GET /schemas/ids/{id}` | Fetch a schema by its global ID — **for decoding a mystery message** |
| `POST /compatibility/subjects/{s}/versions/latest` | Check without registering |
| `PUT /config/{s}` | Set per-subject compatibility |
| `DELETE /subjects/{s}/versions/{v}` | **Soft** delete |
| `DELETE /subjects/{s}?permanent=true` | **Hard** delete — dangerous |

**On deletion:** a soft delete hides the version but keeps the ID resolvable, so existing messages
still decode. A **permanent delete makes every message written with that schema undecodable
forever** — the data is still in Kafka but unreadable. Treat permanent deletes as destructive
operations requiring the same care as dropping a table.

---

## Hands-on drills

1. Run [`06_schema_registry_simulation.py`](../06_kafka/06_schema_registry_simulation.py) — it
   implements the wire format and compatibility checks with no infrastructure. Then do it against a
   real registry.
2. Produce an Avro message, then read the raw bytes with a plain consumer. Decode the magic byte and
   schema ID by hand with `struct.unpack(">bI", raw[:5])`, then fetch that schema via
   `GET /schemas/ids/{id}`.
3. Produce **plain JSON** to an Avro topic. Watch the consumer fail, dump the first 5 bytes, and
   recognise `0x7B` as `{`.
4. Register v1, then try registering a v2 that adds a field **without** a default under `BACKWARD`.
   Read the `verbose=true` error. Add the default and watch it pass.
5. Register v1 → v2 → v3 where each is individually `BACKWARD`-compatible but v3 cannot read v1.
   Switch the subject to `BACKWARD_TRANSITIVE` and watch v3 be rejected.
6. Write `["string","null"]` with `"default": null` and read the error. Fix it to `["null","string"]`.
7. Rename a field with and without `aliases`. Produce with the old schema, consume with the new one,
   and observe the difference.
8. Set `auto.register.schemas=false`, delete the schema from the registry, and confirm the producer
   fails at startup rather than at first message.
9. Configure `TopicRecordNameStrategy` and put two different record types on one topic. Inspect the
   subjects that result.

---

## The 60-second spoken answer

> "Kafka brokers store bytes and validate nothing, so without schema management any producer can
> break every downstream consumer. Schema Registry stores versioned schemas per subject, assigns each
> a global ID, and enforces compatibility on registration. The wire format is a magic byte zero, a
> four-byte big-endian schema ID, then the payload — so only five bytes travel per message, and
> dumping those first bytes is the fastest way to debug a deserialisation failure: `0x7B` means
> someone produced plain JSON to an Avro topic. Subjects default to `<topic>-value` via
> TopicNameStrategy; I'd use TopicRecordNameStrategy when several event types share a topic to keep
> per-entity ordering. On compatibility, BACKWARD is the default and means a new consumer can read
> old data — so you upgrade consumers first — while FORWARD means old consumers can read new data, so
> you upgrade producers first. I use BACKWARD_TRANSITIVE on topics with long retention, because plain
> BACKWARD only checks the latest version and v3 can end up unable to read v1 data that's still in
> the log. Safe Avro changes are adding a field with a default, removing a field, and renaming via an
> alias; unsafe ones are adding a required field, changing a type, or renaming without an alias. And
> I always set `auto.register.schemas=false` in production — schemas are source-controlled and
> registered by CI after a compatibility check that fails the build, so a breaking change is caught
> at merge time rather than by a consumer at 3am."
