"""
NoSQL thinking: document-store indexes and modelling, then a Cassandra-style ring with tunable consistency.

The Python twin of java/java-interview-prep/examples/13_nosql/01_document_store_indexes_and_modeling.java
and 02_cassandra_ring_quorum_and_modeling.java (see shared/cross-stack-pairs.md). Both stores are small
standard-library simulations that COUNT the work: documents examined per query, replicas asked per
read. "Why is this query slow?" and "what does QUORUM buy you?" become numbers.

Run me: python 05_nosql_modeling_and_quorum.py
Deep dive: ../deep_dive/12_scaling_applications.md
"""
import bisect
import hashlib
import random
from collections import defaultdict


def section(title):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# ================================================================ a document store (MongoDB / Couchbase shape)
class DocumentStore:
    def __init__(self):
        self.docs, self.indexes, self.examined = {}, {}, 0

    def insert(self, doc):
        self.docs[doc["_id"]] = doc
        for field_, index in self.indexes.items():
            index[doc.get(field_)].append(doc["_id"])

    def create_index(self, field_):
        index = defaultdict(list)
        for doc in self.docs.values():
            index[doc.get(field_)].append(doc["_id"])
        self.indexes[field_] = index

    def find(self, field_, value):
        if field_ in self.indexes:                                  # IXSCAN: jump straight to the matches
            ids = self.indexes[field_].get(value, [])
            self.examined += len(ids)
            return [self.docs[i] for i in ids]
        self.examined += len(self.docs)                              # COLLSCAN: read every document
        return [d for d in self.docs.values() if d.get(field_) == value]

    def update_if_version(self, doc_id, expected_version, changes):
        """Compare-and-set on one document: the atomicity boundary of a document store."""
        doc = self.docs[doc_id]
        if doc["version"] != expected_version:
            return False
        doc.update(changes, version=expected_version + 1)
        return True


# ================================================================ a Cassandra-style ring
def token(key):
    return int(hashlib.md5(key.encode()).hexdigest(), 16) % 2**32


class Ring:
    """Consistent hashing with virtual nodes; each key lives on RF consecutive distinct nodes."""

    def __init__(self, nodes, rf=3, vnodes=16):
        self.rf, self.points = rf, sorted((token(f"{n}#{v}"), n) for n in nodes for v in range(vnodes))
        self.data = {n: {} for n in nodes}                           # node -> {key: (value, timestamp)}
        self.down = set()

    def replicas(self, key):
        i = bisect.bisect(self.points, (token(key), ""))
        owners = []
        while len(owners) < self.rf:
            node = self.points[i % len(self.points)][1]
            if node not in owners:
                owners.append(node)
            i += 1
        return owners

    def write(self, key, value, ts, w):
        acks = 0
        for node in self.replicas(key):
            if node not in self.down:
                self.data[node][key] = (value, ts)
                acks += 1
        if acks < w:
            raise RuntimeError(f"write failed: {acks} of {w} replicas acknowledged")
        return acks

    def read(self, key, r, repair=True):
        alive = [n for n in self.replicas(key) if n not in self.down]
        if len(alive) < r:
            raise RuntimeError(f"read failed: only {len(alive)} of {r} replicas reachable")
        asked = alive[:r]
        answers = {n: self.data[n].get(key, (None, -1)) for n in asked}
        value, ts = max(answers.values(), key=lambda vt: vt[1])     # last write wins, by timestamp
        if repair:                                                   # read repair: fix the stale replicas we saw
            for n, (_, t) in answers.items():
                if t < ts:
                    self.data[n][key] = (value, ts)
        return value


def main():
    random.seed(7)

    section("1. Query cost with and without an index (100,000 order documents)")
    store = DocumentStore()
    for i in range(100_000):
        store.insert({"_id": i, "customer": f"c{i % 5_000}", "status": random.choice(["NEW", "PAID", "SHIPPED"]),
                      "version": 0})
    store.examined = 0
    found = store.find("customer", "c42")
    print(f"  no index : found {len(found)} orders for c42, examined {store.examined:,} documents (COLLSCAN)")
    store.create_index("customer")
    store.examined = 0
    found = store.find("customer", "c42")
    print(f"  index    : found {len(found)} orders for c42, examined {store.examined:,} documents (IXSCAN)")
    print("  An index costs a write and memory per field, so index the queries you run, not every field.")
    print("  Low-selectivity fields (status with 3 values) make poor single-field indexes; use a compound")
    print("  index whose first field is the selective one: {customer: 1, status: 1}.")
    # EXPERIMENT: create_index("status") and query status == "PAID": it still examines ~33,000 documents.

    section("2. Embedding vs referencing: model for the read path")
    print("  embed     : an order holds its line items -> one read renders the order page; good when the")
    print("              children are bounded and always read with the parent")
    print("  reference : an order holds customer_id -> the customer changes in one place; good when the")
    print("              child is shared, large, or grows without bound (16 MB document limit in MongoDB)")
    print("  rule: model for how the data is READ; duplicate small fields when it saves a lookup")

    section("3. Atomicity boundary = one document; optimistic concurrency with a version")
    doc = store.docs[42]
    v = doc["version"]
    print(f"  user A updates order 42 at version {v}: {store.update_if_version(42, v, {'status': 'PAID'})}")
    print(f"  user B updates it with the same stale version {v}: {store.update_if_version(42, v, {'status': 'NEW'})}")
    print(f"  order 42 is now {store.docs[42]['status']} at version {store.docs[42]['version']}")
    print("  One document updates atomically. Several documents need a transaction (MongoDB 4.0+) or a saga.")

    section("4. The ring: the partition key decides which nodes own the row")
    ring = Ring([f"node{i}" for i in range(1, 7)], rf=3)
    for k in ("user:1", "user:2", "user:3"):
        print(f"  {k:<8} -> replicas {ring.replicas(k)}")
    print("  Adding a node moves only the keys next to its tokens; vnodes spread that load evenly.")

    section("5. Tunable consistency: choose R and W against N (the replication factor)")
    n = ring.rf
    for r, w in ((1, 1), (2, 2), (1, 3), (3, 1)):
        print(f"  N={n} R={r} W={w}: R+W={r + w} {'>' if r + w > n else '<='} N -> "
              f"{'every read overlaps the latest write' if r + w > n else 'a read can miss the latest write'}")
    print("  QUORUM = floor(N/2)+1 = 2 for N=3. QUORUM reads + QUORUM writes overlap; ONE is fastest.")

    section("6. What a stale read looks like, and read repair")
    key = "user:1"
    owners = ring.replicas(key)
    ring.write(key, "email=old@x.com", ts=1, w=3)
    ring.down = {owners[2]}
    ring.write(key, "email=new@x.com", ts=2, w=1)                   # the third replica misses this write
    ring.down = set()
    stale_node = owners[2]
    print(f"  {stale_node} missed the update; it still holds {ring.data[stale_node][key][0]}")
    print(f"  a read at ONE that happens to ask {stale_node}: {ring.data[stale_node][key][0]}   <- stale")
    ring.down = {owners[0]}                                         # one fresh replica is busy, so the
    value = ring.read(key, r=2)                                     # QUORUM read asks owners[1] and the stale one
    ring.down = set()
    print(f"  a read at QUORUM while {owners[0]} is busy asks {owners[1]} and {stale_node}; the newest")
    print(f"  timestamp wins: {value}")
    print(f"  ...and read repair has fixed {stale_node}: {ring.data[stale_node][key][0]}")

    section("7. Availability vs consistency with nodes down (CAP)")
    ring.down = set(owners[:2])
    for level, r in (("ONE", 1), ("QUORUM", 2)):
        try:
            print(f"  2 of 3 replicas down, read at {level:<6}: {ring.read(key, r=r)}")
        except RuntimeError as e:
            print(f"  2 of 3 replicas down, read at {level:<6}: {e}")
    print("  During a partition you pick per query: stay available (ONE) or stay consistent (QUORUM).")
    ring.down = set()

    section("8. Query-first modelling and the anti-patterns that cause incidents")
    print("  one table per query: orders_by_customer (PK customer_id, clustering order_date DESC) and")
    print("  orders_by_status are two tables with the same data - writes duplicate, reads never join")
    print("  hot partition : a partition key like 'country' puts most traffic on a few nodes; add a bucket")
    print("  huge partition: unbounded rows per key (all events of a device forever); bucket by day")
    print("  ALLOW FILTERING or secondary indexes on high-cardinality columns = a scatter-gather scan")
    print("  tombstones    : mass deletes leave markers that slow every read until compaction")


if __name__ == "__main__":
    main()


# EXERCISE 1: add a node to the Ring and count how many of 10,000 keys change owner. Compare with
#             naive `hash(key) % nodes` placement.
# EXERCISE 2: add hinted handoff: while a replica is down, keep its missed writes on another node
#             and replay them when it comes back. Which stale read in section 6 does that prevent?
