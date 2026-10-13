# Schema Registry — reference notes (concept-only; see below for a runnable snippet)

Kafka brokers store bytes and validate nothing. A Schema Registry gives producers and consumers a
shared contract, and — critically — lets that contract *evolve* without a coordinated,
big-bang redeploy of every service touching the topic.

## Wire format (Confluent)

```
byte 0        : magic byte (always 0)
bytes 1-4     : schema ID, big-endian int
bytes 5+      : the actual serialized (Avro/Protobuf/JSON) payload
```

Only 5 bytes of overhead ride along with every message — the schema itself is looked up (and
cached) from the registry by ID, not re-sent each time.

```python
import struct

def schema_id_of(raw: bytes) -> int:
    magic, schema_id = struct.unpack(">bI", raw[:5])
    assert magic == 0, "not Confluent-framed"
    return schema_id
```

## Compatibility modes

| Mode | Guarantee | You may... |
|---|---|---|
| `BACKWARD` (default) | new-schema readers can read old-schema data | add a field **with a default**, or remove a field |
| `FORWARD` | old-schema readers can read new-schema data | add a field, or remove an *optional* field |
| `FULL` | both directions | intersection of the two rules above |
| `NONE` | no checks | anything (not recommended for shared topics) |

The `_TRANSITIVE` variants check compatibility against **every** previous version, not just the
latest — use these for topics with many long-lived consumers.

## Safe vs. unsafe Avro changes (assuming `BACKWARD`)

**Safe:**
- add a field **with a `default`**
- remove a field
- widen a type via a union with `null` (put `"null"` first, `default: null`)
- add an alias for a renamed field

**Unsafe (will fail the compatibility check, and should):**
- add a field **without** a default
- change a field's type incompatibly (`string` → `int`)
- rename a field without an alias
- remove an enum symbol that old data might still contain

```json
// v1
{"type": "record", "name": "Order", "fields": [
  {"name": "id", "type": "string"},
  {"name": "amount", "type": "double"}
]}

// v2 — BACKWARD-compatible: new field has a default, so old readers/writers keep working
{"type": "record", "name": "Order", "fields": [
  {"name": "id", "type": "string"},
  {"name": "amount", "type": "double"},
  {"name": "currency", "type": "string", "default": "INR"}
]}
```

## Producer/consumer with the registry (conceptual — needs `confluent-kafka[avro]` + a running registry)

```python
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer, AvroDeserializer
from confluent_kafka.serialization import SerializationContext, MessageField

sr = SchemaRegistryClient({"url": "http://localhost:8081"})
avro_serializer = AvroSerializer(sr, open("order_v2.avsc").read())

# producer.produce("orders", value=avro_serializer(
#     order_dict, SerializationContext("orders", MessageField.VALUE)))

avro_deserializer = AvroDeserializer(sr)
# order_dict = avro_deserializer(msg.value(), SerializationContext(msg.topic(), MessageField.VALUE))
```

In production, set `auto.register.schemas=False` and register schemas through CI/CD after an
explicit compatibility check (`POST /compatibility/subjects/{subject}/versions/latest` against
the registry's REST API) — never let a random service deployment silently change a shared
contract.

## Exercise

Write out an Avro schema for an `OrderShipped` event (v1), then write a v2 that adds a `carrier`
field. Decide: does it need a default? What compatibility mode would reject a v2 that changed
`tracking_number` from `string` to `int`, and why is that rejection the *correct* behavior rather
than an annoyance?
