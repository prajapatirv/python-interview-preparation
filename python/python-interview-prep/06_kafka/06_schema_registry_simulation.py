"""
Schema Registry, simulated: the Confluent wire format, subjects, versions and
compatibility checking — all in pure stdlib, no broker and no registry needed.

The real thing is a REST service in front of a compacted Kafka topic. This file
reproduces the parts you get asked about so you can see them execute.

Run me: python 06_schema_registry_simulation.py
Deep dive: ../deep_dive/16_kafka_schema_management.md
"""
import json
import struct


def section(title):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# ================================================================ wire format
section("1. the Confluent wire format: magic byte 0 + 4-byte schema ID + payload")


def encode(schema_id: int, payload: dict) -> bytes:
    """Frame a record the way a Confluent serializer does."""
    header = struct.pack(">bI", 0, schema_id)   # ">" = BIG-endian, b = magic, I = uint32
    return header + json.dumps(payload).encode()


def decode_header(raw: bytes):
    magic, schema_id = struct.unpack(">bI", raw[:5])
    if magic != 0:
        raise ValueError(f"not Confluent-framed: magic byte is {magic}, expected 0")
    return schema_id, raw[5:]


framed = encode(42, {"id": "o-1", "amount": 499.0})
print("raw bytes      :", framed[:20], "...")
print("first 5 bytes  :", framed[:5].hex(" "), " <- 00 | 00 00 00 2a (=42)")
sid, body = decode_header(framed)
print(f"schema id      : {sid}")
print(f"payload        : {body.decode()}")
print("\nONLY 5 bytes of overhead per record — the schema itself never travels.")

# --- the debugging trick that saves hours ---
print("\ndebugging a deserialisation failure? dump the first byte:")
for label, first_bytes in [
    ("Confluent-framed Avro", framed[:5]),
    ("plain JSON on an Avro topic", b'{"id"'),
    ("corruption / wrong serializer", b"\xff\xfe\x00\x01\x02"),
]:
    b0 = first_bytes[0]
    verdict = ("OK — framed" if b0 == 0 else
               "someone produced PLAIN JSON to an Avro topic!" if b0 == 0x7B else
               "corruption or a non-Confluent producer")
    print(f"  {label:<32} first byte 0x{b0:02x}  -> {verdict}")


# ================================================================ the registry
section("2. a minimal Schema Registry: subjects, versions, global IDs")


class SchemaRegistry:
    """Subjects hold ordered versions; every distinct schema gets a global ID."""

    def __init__(self):
        self._subjects: dict[str, list[dict]] = {}   # subject -> [schema, ...]
        self._ids: dict[str, int] = {}               # canonical schema text -> id
        self._by_id: dict[int, dict] = {}
        self._compat: dict[str, str] = {}
        self._next_id = 1

    # -- config ---------------------------------------------------------
    def set_compatibility(self, subject, mode):
        assert mode in {"BACKWARD", "BACKWARD_TRANSITIVE", "FORWARD",
                        "FULL", "NONE"}, mode
        self._compat[subject] = mode

    def compatibility(self, subject):
        return self._compat.get(subject, "BACKWARD")      # BACKWARD is the default

    # -- read -----------------------------------------------------------
    def versions(self, subject):
        return list(range(1, len(self._subjects.get(subject, [])) + 1))

    def get_by_id(self, schema_id):
        return self._by_id[schema_id]

    def latest(self, subject):
        return self._subjects[subject][-1]

    # -- write ----------------------------------------------------------
    def check_compatibility(self, subject, new_schema):
        """Return (is_compatible, [messages]) without registering anything."""
        existing = self._subjects.get(subject, [])
        if not existing:
            return True, []
        mode = self.compatibility(subject)
        if mode == "NONE":
            return True, []
        # TRANSITIVE checks EVERY previous version, not just the latest.
        targets = existing if mode.endswith("_TRANSITIVE") else [existing[-1]]
        problems = []
        for old in targets:
            if mode.startswith("BACKWARD"):
                problems += _backward_problems(old, new_schema)
            elif mode == "FORWARD":
                problems += _backward_problems(new_schema, old)
            elif mode == "FULL":
                problems += _backward_problems(old, new_schema)
                problems += _backward_problems(new_schema, old)
        return (not problems), problems

    def register(self, subject, schema):
        ok, problems = self.check_compatibility(subject, schema)
        if not ok:
            raise ValueError(f"incompatible schema for {subject}: {problems}")
        canonical = json.dumps(schema, sort_keys=True)
        if canonical not in self._ids:                  # dedupe by CONTENT
            self._ids[canonical] = self._next_id
            self._by_id[self._next_id] = schema
            self._next_id += 1
        self._subjects.setdefault(subject, []).append(schema)
        return self._ids[canonical]


def _fields(schema):
    return {f["name"]: f for f in schema["fields"]}


def _backward_problems(old, new):
    """Can a reader using `new` read data written with `old`?"""
    problems = []
    old_f, new_f = _fields(old), _fields(new)

    for name, nf in new_f.items():
        if name in old_f:
            # A type change is unsafe in either direction.
            if nf["type"] != old_f[name]["type"]:
                problems.append(
                    f"field '{name}' type changed {old_f[name]['type']} -> {nf['type']}")
        else:
            # A field the writer never wrote MUST have a default for the reader.
            aliases = nf.get("aliases", [])
            if any(a in old_f for a in aliases):
                continue                                  # renamed WITH an alias: fine
            if "default" not in nf:
                problems.append(f"new field '{name}' has no default value")
    return problems


# ================================================================ evolution
section("3. schema evolution under BACKWARD compatibility")

sr = SchemaRegistry()
SUBJECT = "orders-value"                 # TopicNameStrategy: <topic>-value

v1 = {
    "type": "record", "name": "Order", "namespace": "com.shop",
    "fields": [
        {"name": "id", "type": "string"},
        {"name": "amount", "type": "double"},
    ],
}
print("register v1 ->", "schema id", sr.register(SUBJECT, v1))

# --- SAFE: a new field WITH a default -------------------------------------
v2 = {
    "type": "record", "name": "Order", "namespace": "com.shop",
    "fields": [
        {"name": "id", "type": "string"},
        {"name": "amount", "type": "double"},
        {"name": "currency", "type": "string", "default": "INR"},
        {"name": "coupon", "type": ["null", "string"], "default": None},
    ],
}
print("register v2 ->", "schema id", sr.register(SUBJECT, v2), " (added fields WITH defaults)")

# --- UNSAFE: a new field WITHOUT a default --------------------------------
v3_bad = {
    "type": "record", "name": "Order", "namespace": "com.shop",
    "fields": [
        {"name": "id", "type": "string"},
        {"name": "amount", "type": "double"},
        {"name": "region", "type": "string"},          # no default!
    ],
}
ok, why = sr.check_compatibility(SUBJECT, v3_bad)
print(f"check  v3_bad -> compatible={ok}  {why}")

# --- UNSAFE: an incompatible type change ----------------------------------
v3_type = {
    "type": "record", "name": "Order", "namespace": "com.shop",
    "fields": [
        {"name": "id", "type": "string"},
        {"name": "amount", "type": "string"},          # double -> string
    ],
}
ok, why = sr.check_compatibility(SUBJECT, v3_type)
print(f"check  v3_type -> compatible={ok}  {why}")

# --- SAFE: a rename, but ONLY with an alias -------------------------------
v3_rename_bad = {
    "type": "record", "name": "Order", "namespace": "com.shop",
    "fields": [
        {"name": "id", "type": "string"},
        {"name": "total_amount", "type": "double"},    # renamed, no alias
    ],
}
ok, why = sr.check_compatibility(SUBJECT, v3_rename_bad)
print(f"check  rename (no alias) -> compatible={ok}  {why}")

v3_rename_ok = {
    "type": "record", "name": "Order", "namespace": "com.shop",
    "fields": [
        {"name": "id", "type": "string"},
        {"name": "total_amount", "type": "double", "aliases": ["amount"]},
    ],
}
ok, why = sr.check_compatibility(SUBJECT, v3_rename_ok)
print(f"check  rename (WITH alias) -> compatible={ok}")
print(f"\nsubject {SUBJECT!r} versions: {sr.versions(SUBJECT)}")


# ================================================================ transitive
section("4. why BACKWARD_TRANSITIVE matters on a long-retention topic")

sr2 = SchemaRegistry()
S = "events-value"

# v1 has a STRING field 'a'.
v1e = {"type": "record", "name": "E", "fields": [
    {"name": "a", "type": "string"}]}

# v2 DROPS 'a' (removing a field is BACKWARD-safe) and adds 'b' with a default.
v2e = {"type": "record", "name": "E", "fields": [
    {"name": "b", "type": "string", "default": ""}]}

# v3 re-introduces 'a', but as an INT, with a default.
# vs v2: 'a' is simply a new field with a default -> looks fine.
# vs v1: 'a' changed string -> int -> BROKEN.
v3e = {"type": "record", "name": "E", "fields": [
    {"name": "b", "type": "string", "default": ""},
    {"name": "a", "type": "int", "default": 0}]}

print("v1 fields:", [f["name"] + ":" + f["type"] for f in v1e["fields"]])
print("v2 fields:", [f["name"] + ":" + f["type"] for f in v2e["fields"]], "(dropped 'a')")
print("v3 fields:", [f["name"] + ":" + f["type"] for f in v3e["fields"]], "('a' is back, as int)")

sr2.register(S, v1e)
sr2.register(S, v2e)

ok_latest, why_latest = sr2.check_compatibility(S, v3e)        # only vs v2
print(f"\nBACKWARD (vs latest only)    -> compatible={ok_latest}  {why_latest}")
print("   v2 has no field 'a' at all, so 'a:int' looks like a harmless new field. PASSES.")

sr2.set_compatibility(S, "BACKWARD_TRANSITIVE")
ok_all, why_all = sr2.check_compatibility(S, v3e)              # vs v1 AND v2
print(f"BACKWARD_TRANSITIVE (vs all) -> compatible={ok_all}  {why_all}")
print("   checked against v1 too, where 'a' was a string. CAUGHT.")
print("""
   v1 -> v2 is fine and v2 -> v3 is fine, but v3 CANNOT read v1 data. With a 30-day
   retention window, a consumer reading from the beginning hits v1 messages and fails.
   Use *_TRANSITIVE on any topic you replay or retain for a long time.""")


# ================================================================ resolution
section("5. schema resolution: a v1 reader and a v2 reader over the same bytes")


def resolve(writer_schema, reader_schema, payload: dict) -> dict:
    """Project data written with `writer_schema` onto `reader_schema`."""
    out = {}
    for name, field in _fields(reader_schema).items():
        if name in payload:
            out[name] = payload[name]
        else:
            for alias in field.get("aliases", []):      # renamed field
                if alias in payload:
                    out[name] = payload[alias]
                    break
            else:
                out[name] = field.get("default")        # the writer never wrote it
    return out                                          # fields the reader doesn't
                                                        # declare are simply dropped


written_v2 = {"id": "o-9", "amount": 250.0, "currency": "USD", "coupon": "SAVE10"}
print("bytes on the topic were written with v2:", written_v2)
print("a v2 reader sees :", resolve(v2, v2, written_v2))
print("a v1 reader sees :", resolve(v2, v1, written_v2), " <- unknown fields dropped")

written_v1 = {"id": "o-1", "amount": 100.0}
print("\nbytes written with v1:", written_v1)
print("a v2 reader sees :", resolve(v1, v2, written_v1), " <- defaults filled in")
print("\nTHAT is what lets producers and consumers deploy independently.")


# ================================================================ production
section("6. auto.register.schemas=False — why a service must not change the contract")


def producer_startup(registry, subject, schema, auto_register: bool):
    """A serializer either LOOKS UP the schema or REGISTERS it."""
    canonical = json.dumps(schema, sort_keys=True)
    if canonical in registry._ids:
        return f"OK — resolved to schema id {registry._ids[canonical]}"
    if auto_register:
        return f"registered NEW version, id {registry.register(subject, schema)} (!)"
    raise RuntimeError("schema not found in registry — FAILING AT STARTUP")


new_schema = {"type": "record", "name": "Order", "namespace": "com.shop",
              "fields": [{"name": "id", "type": "string"},
                         {"name": "amount", "type": "double"},
                         {"name": "channel", "type": "string", "default": "web"}]}

print("dev laptop, auto_register=True :")
print("  ", producer_startup(SchemaRegistry(), SUBJECT, v1, auto_register=True))

print("\nproduction, auto_register=False, schema NOT registered by CI:")
try:
    producer_startup(sr, SUBJECT, new_schema, auto_register=False)
except RuntimeError as e:
    print("  ", e)
    print("   ^ loud, at startup, in staging — NOT a silent contract change in prod.")

print("\nCI registers it first, then the service starts cleanly:")
sr.register(SUBJECT, new_schema)
print("  ", producer_startup(sr, SUBJECT, new_schema, auto_register=False))


# EXERCISE 1: add FORWARD compatibility checking and work out which side you upgrade
#             first for each mode. (Hint: BACKWARD -> consumers first.)
# EXERCISE 2: the union default rule — ["null","string"] with default null is valid,
#             but ["string","null"] with default null is NOT. Add that check.
# EXERCISE 3: implement TopicRecordNameStrategy (subject = "<topic>-<RecordName>") and
#             register two different record types on one topic.
# EXERCISE 4: add a permanent-delete method, then show that a message framed with the
#             deleted schema ID can never be decoded again.
