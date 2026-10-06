# Deep Dive 30 — Handling a 100GB File

> Runnable companion: [`09_aws_lambda_streaming/03_large_file_processing.py`](../09_aws_lambda_streaming/03_large_file_processing.py)
> Related: [`09_aws_lambda_streaming/02_stream_large_file_s3_simulation.py`](../09_aws_lambda_streaming/02_stream_large_file_s3_simulation.py)
> Related deep dives: [04 — Generators and iterators](04_generators_iterators.md) ·
> [09 — Pandas](09_pandas.md) · [07 — Concurrency](07_concurrency.md) ·
> [29 — Capacity scaling](29_capacity_scaling_tps.md) · [18 — Queue architectures](18_queue_architectures.md)

## What interviewers are actually probing

*"You have a 100GB file to process. How?"*

"Stream it, don't load it" is the first sentence and about 30% of the marks. The other 70% is what
happens when streaming isn't enough:

1. **Do you know the one-pass operations from the rest?** `sum`, `filter`, `map` and a small-cardinality
   `GROUP BY` are one-pass and O(1) memory. **Sort, dedupe, join and exact percentiles are not**, and
   each has a specific technique.
2. **Can you parallelise it correctly?** Splitting by byte range is easy; splitting *on record
   boundaries* is where people get it wrong, and the GIL means threads won't help with parsing.
3. **Does it survive a failure?** A 100GB job runs for hours. Something *will* interrupt it. If a crash
   at 80GB costs 80GB of rework, you've designed it wrong.
4. **Would you write this in Python at all?** The strongest answer opens by questioning the premise —
   if the file is in S3 and the work is SQL-shaped, Athena or a Glue job is less code, cheaper, and
   already parallel.

---

## Must-know points

- **Never `read()` the whole file.** Iterating a file object yields one line at a time; peak memory is
  the size of the longest **line**, identical for 10MB and 100GB.
- **A generator pipeline** (`parse → filter → transform`) keeps peak memory at one record regardless of
  stage count. Composition without materialisation.
- **Batch the writes, not the reads.** `itertools.batched(it, 1000)` — one downstream round trip per
  1,000 records, with only 1,000 in memory.
- **Streaming aggregation** is O(distinct keys), not O(rows). High-cardinality keys → **hash-partition
  into N files first**, then aggregate each. That *is* a shuffle.
- **Sorting bigger than RAM** = **external merge sort**: sorted runs to disk, then `heapq.merge` across
  them (one record per run in memory).
- **Exact dedupe at scale** = hash-partition so all copies of a key land in the same file, then a `set`
  per file. **Approximate** = a Bloom filter: fixed memory, no false negatives.
- **Parallelism**: split into byte ranges that **start on record boundaries**, then
  `ProcessPoolExecutor` (not threads — the GIL blocks CPU-bound parsing) or N Lambda invocations.
- **Checkpoint after each chunk, atomically** (`os.replace`), so a failure costs one chunk.
- **A single `.gz` is not splittable.** Many smaller `.gz` objects, or Parquet (columnar + row groups +
  predicate pushdown).
- **Exact percentiles cannot be computed in one pass.** t-digest, reservoir sampling, or sort first — and
  say which.
- **The best answer may be "not in Python":** Athena/Glue/Spark/DuckDB for SQL-shaped work on S3.

---

## Interview questions and full answers

### Q1. Why is `read()` wrong, and what does streaming actually cost?

```python
# WRONG — this is what s3.get_object(...)["Body"].read() and pd.read_csv(huge) do
with open(path) as f:
    content = f.read()                  # the ENTIRE file as one str
rows = csv.DictReader(content.splitlines())   # and now a SECOND full copy as a list of lines

# RIGHT — the file object is already an iterator of lines
with open(path) as f:
    total = sum(float(r["amount"]) for r in csv.DictReader(f))
```

Measured on a 12.9MB sample with `tracemalloc` (companion file):

| approach | peak memory |
|---|---|
| `read()` everything | **39.1 MB** (≈3× the file: the str, plus the split lines) |
| line-by-line streaming | **170 KB** |

**234× less, and the gap grows linearly with file size** — at 100GB the first version simply cannot run.
Note the 3× multiplier: `read()` costs more than the file size because `splitlines()` builds a list of
str objects, each with ~49 bytes of header.

**The S3 version needs no change to the loop**, which is the point worth making:

```python
body = s3.get_object(Bucket=b, Key=k)["Body"]        # a StreamingBody, not bytes
for row in csv.DictReader(io.TextIOWrapper(body, encoding="utf-8")):
    ...
```

`get_object` returns a stream; `.read()` is what materialises it. The same distinction exists in every
SDK, and calling `.read()` out of habit is the single most common version of this bug.

**What streaming costs you:** you get **one pass, forward only**. If you need the data twice you either
re-read the file (cheap for local disk, a second S3 GET charge otherwise) or `itertools.tee` (which
buffers, so it defeats the purpose). That constraint is what makes the rest of this document necessary.

---

### Q2. What is a generator pipeline and why does it matter?

Compose stages as generators; each pulls from the previous. Nothing is materialised:

```python
def read_rows(path):
    with open(path) as f:
        yield from csv.DictReader(f)                     # stage 1: bytes -> dicts

def only_shipped(rows):
    for row in rows:
        if row["status"] == "SHIPPED":                   # stage 2: filter
            yield row

def to_cents(rows):
    for row in rows:
        yield {**row, "cents": int(float(row["amount"]) * 100)}   # stage 3: transform

total = sum(r["cents"] for r in to_cents(only_shipped(read_rows(path))))
```

**Peak memory is ONE record**, regardless of file size or stage count — measured at 181 KB in the
companion. The equivalent with a list comprehension at each stage would hold three full copies of the
data.

**Why this is the most useful shape in the topic:** it reads like a query, runs in constant memory, each
stage is independently unit-testable with a list of 3 dicts, and you can insert a stage without touching
the others. It's Unix pipes in Python, and the execution model is identical — one record flows all the
way through before the next is read.

Two practical cautions:

- **`yield from` inside `with`** keeps the file open for the generator's whole life. If the consumer
  abandons it halfway, the file closes when the generator is garbage-collected — usually fine, but under
  `contextlib.closing` or an explicit `.close()` if descriptor lifetime matters.
- **An exception mid-stream leaves you partway through.** That's why checkpointing (Q7) matters, and why
  a "validate everything, then write" design is impossible at this scale — you must handle bad records
  as they arrive.

---

### Q3. What's the difference between batching and buffering?

**Batching holds N records; buffering holds the file.** Batching is how you amortise the downstream
round trip without giving up constant memory:

```python
def batched(iterable, size):                  # itertools.batched in 3.12+
    it = iter(iterable)
    while batch := list(itertools.islice(it, size)):
        yield batch

for batch in batched(only_shipped(read_rows(path)), 1000):
    db.execute_values(insert_sql, batch)      # ONE round trip per 1000 rows
```

Measured: 257,142 rows with `batch_size=5000` → **52 round trips**; with `batch_size=1` → **257,142**.
At a realistic 2ms per round trip that's 0.1 seconds versus 8.6 minutes of pure network wait. Memory
differs by a few MB.

**Choosing the batch size** — it's a genuine trade-off, not a magic number:

| Too small | Too large |
|---|---|
| round-trip cost dominates | memory grows with batch size |
| no compression benefit | a failure loses/retries the whole batch |
| | a long transaction holds locks and bloats the WAL |
| | you may exceed a hard API limit |

**500–1,000 is the usual sweet spot** for database inserts. Hard limits worth knowing:
DynamoDB `batch_write_item` is 25 items; SQS `send_message_batch` is 10 messages / 256KB; Kafka has a
message size cap (default 1MB). And for a Kafka consumer, the batch must be processable well inside
`max.poll.interval.ms` or you trigger a rebalance — see
[`06_kafka/08_kafka_to_aurora_sink.py`](../06_kafka/08_kafka_to_aurora_sink.py).

---

### Q4. Which operations are one-pass, and which are not?

**This is the question that separates a real answer from a recited one.** One pass, O(1) or O(keys)
memory:

```python
sum / count / min / max / mean          # four scalars
filter / map / transform                # nothing retained
GROUP BY with few distinct keys         # a dict, O(distinct keys)
"does any row match X?"                 # short-circuits
running variance (Welford's algorithm)  # still just scalars
```

```python
def aggregate_streaming(path):
    totals, counts = defaultdict(float), defaultdict(int)
    for row in read_rows(path):
        totals[row["region"]] += float(row["amount"])     # 3 regions -> 3 dict entries
        counts[row["region"]] += 1
    return {r: (counts[r], totals[r]) for r in totals}
```

**Memory is O(distinct keys), not O(rows)** — three regions stays tiny at 100GB. **But if the key is
high-cardinality** (per-customer over 50 million customers) the dict *is* the problem you were avoiding.
The fix is to hash-partition into N files so each customer lands in exactly one, then aggregate each file
independently with a dict holding 1/N of the keys. **That is literally what a shuffle is in
MapReduce/Spark** — and saying so demonstrates you understand the framework rather than just using it.

**NOT one-pass, and each has a specific technique:**

| Operation | Why not | Technique |
|---|---|---|
| **SORT** | the last record may belong first | external merge sort (Q5) |
| **exact DEDUPE** | must remember everything seen | hash-partition, or a Bloom filter (Q6) |
| **JOIN** | need both sides | sort-merge join, or hash the smaller side into memory |
| **exact median / p99** | depends on all values | t-digest / reservoir sample, or sort first |
| **"top k"** | needs comparison across all | a bounded heap — `heapq.nlargest(k, …)`, O(n log k) |
| **count distinct** | must remember | HyperLogLog (≈1.6KB for ±2% on billions) |

**The percentile one is the trap.** Candidates claim an exact p99 in constant memory, which is
impossible. The honest answers: a **t-digest** (≈1KB, accurate in the tails where you care), a
**reservoir sample** (k records, uniform random, then sort those), or sort the file first. Saying
"approximately, with a t-digest, and here's the error bound" is a much stronger answer than a confident
wrong one.

---

### Q5. How do you sort a file larger than RAM?

**External merge sort — two phases.** This is a classic and worth being able to write:

```python
def external_sort(path, key_column, rows_per_run=50_000):
    # PHASE 1 — SPLIT: read a chunk, sort it IN MEMORY, write a sorted run to disk. Repeat.
    run_files = []
    with open(path) as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        for i, chunk in enumerate(batched(reader, rows_per_run)):
            chunk.sort(key=lambda r: float(r[key_column]))     # the ONLY in-memory sort
            run_path = f"run_{i:04d}.csv"
            with open(run_path, "w", newline="") as out:
                csv.DictWriter(out, fieldnames=header).writerows(chunk)
            run_files.append(run_path)

    # PHASE 2 — MERGE: heapq.merge holds ONE record per run and pulls the next smallest.
    streams = [read_run(p, header) for p in run_files]
    with open("sorted.csv", "w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=header)
        writer.writeheader()
        for row in heapq.merge(*streams, key=lambda r: float(r[key_column])):
            writer.writerow(row)                                # one row at a time, straight to disk
```

**Peak memory is `rows_per_run` in phase 1 and `len(run_files)` records in phase 2** — both chosen by
you. 100GB with 100MB of RAM is 1,000 runs, and phase 2 then holds 1,000 records. The companion verifies
the output is correctly ordered.

Complexity: O(n log n) comparisons, and **O(n) disk I/O per merge pass** — which is the real cost, since
you read and write the whole dataset at least twice.

**The three follow-ups:**

- **"What if there are too many runs to merge at once?"** You hit the OS file-descriptor limit (1,024 by
  default on Linux). Then you do a **multi-way merge in passes**: merge 100 runs at a time into 10 larger
  runs, then merge those. Each pass is another full read+write, so you pick `rows_per_run` to keep it to
  one merge pass if you can.
- **"How do you pick `rows_per_run`?"** As large as memory allows — fewer runs means fewer open files and
  a cheaper merge. Measure it; don't guess.
- **"Isn't there a simpler answer?"** Yes: `sort -S 1G -t, -k4 file.csv`. GNU `sort` *is* an external
  merge sort, written in C, and it will beat your Python. Say that — and say that you know what it does
  internally, which is what the question was actually testing. Postgres, Spark and every database use the
  same two phases.

---

### Q6. How do you deduplicate 2 billion IDs?

Three answers, with explicit trade-offs — presenting all three is the strong move:

**1. Exact, in-memory set.** Correct, memory is O(distinct keys). A Python `set` of 2 billion 36-char
UUIDs is on the order of 100GB+ (each str has ~49 bytes overhead plus the set's own table) — i.e. exactly
the problem you were trying to avoid. Fine up to a few million keys; hopeless beyond.

**2. Exact, disk-partitioned.** The right answer when exactness is required:

```python
def dedupe_by_partition(path, key, buckets=64):
    # PASS 1: hash-partition so all copies of a key land in the SAME file
    handles = [open(f"bucket_{i}.txt", "w") for i in range(buckets)]
    for row in read_rows(path):
        k = row[key]
        handles[hash_stable(k) % buckets].write(k + "\n")
    for h in handles: h.close()

    # PASS 2: one bucket at a time — the set only ever holds 1/buckets of the keys
    unique = 0
    for i in range(buckets):
        with open(f"bucket_{i}.txt") as f:
            unique += len({line.rstrip("\n") for line in f})
    return unique
```

**Why it works: identical keys always hash to the same bucket**, so deduping each bucket independently
is equivalent to deduping globally. Memory is O(keys/buckets) — choose `buckets` to fit. Use a *stable*
hash (`hashlib.blake2b`), not Python's `hash()`, which is randomised per process by `PYTHONHASHSEED` and
therefore gives different partitions on a retry.

**3. Approximate — a Bloom filter.** Fixed memory, **no false negatives**, tunable false positives:

```python
class TinyBloomFilter:
    def __init__(self, n_bits=1 << 20, n_hashes=4):
        self.n_bits, self.n_hashes, self.bits = n_bits, n_hashes, bytearray(n_bits // 8)
    def _positions(self, item):
        d = hashlib.blake2b(str(item).encode(), digest_size=16).digest()
        base, step = int.from_bytes(d[:8], "big"), int.from_bytes(d[8:], "big") | 1
        for i in range(self.n_hashes):
            yield (base + i * step) % self.n_bits
    def add(self, item):
        for p in self._positions(item): self.bits[p // 8] |= 1 << (p % 8)
    def __contains__(self, item):
        return all(self.bits[p // 8] >> (p % 8) & 1 for p in self._positions(item))
```

**The asymmetry is the whole point, and you must state it:** a Bloom filter can say "seen" about
something it hasn't (false positive), never "not seen" about something it has. So for dedupe it may
**drop a legitimately new record** — unacceptable if that record is a payment. The production pattern is
**Bloom as a cheap pre-filter**: if it says "not seen", it definitively isn't, so insert; if it says
"seen", confirm against the database. That turns 2 billion lookups into a handful.

Sizing: ~1.2GB of bitmap gives roughly a 1% false-positive rate at 2 billion items with 7 hash
functions (`m = -n·ln(p)/(ln2)²`). In production use `pybloom-live`, or Redis's `BF.*` commands so the
filter is shared across workers.

**And the fourth answer worth naming:** if the data is in a database or a warehouse, dedupe is
`SELECT DISTINCT` or `INSERT … ON CONFLICT DO NOTHING` with a unique index, and the engine does all of
the above better than you will. That's also how the Kafka→Aurora sink stays idempotent.

---

### Q7. How do you parallelise it, and what's the trap?

**Split into byte ranges — but each range must START on a record boundary.** Here is the bug everyone
writes first:

```python
# WRONG — size // n splits a line in half:
#   worker 1 gets "...ORD-000123,CUST-"
#   worker 2 gets "0042,APAC,19.50\n..."
# Both rows are corrupt, and the row count comes out wrong.
```

```python
def find_chunk_boundaries(path, n_chunks):
    """Seek to the nominal offset, then ADVANCE to the next newline."""
    size = os.path.getsize(path)
    nominal, boundaries = size // n_chunks, []
    with open(path, "rb") as f:
        f.readline()                      # skip the header — it belongs to no chunk
        start = f.tell()
        for _ in range(1, n_chunks):
            f.seek(start + nominal)
            if f.readline() == b"":       # already past EOF
                break
            end = f.tell()                # the boundary is AFTER a complete line
            boundaries.append((start, end))
            start = end
        boundaries.append((start, size))
    return boundaries
```

Two rules make it correct: **advance to the next newline after seeking**, and **let each worker read past
its end offset to finish the line it started**. The companion verifies the parallel total matches the
serial total exactly.

**Then: processes, not threads.** CSV/JSON parsing is CPU-bound, so the GIL means threads give you
roughly nothing:

```python
with ProcessPoolExecutor() as pool:                   # real parallelism
    results = pool.map(process_byte_range, chunk_args)
total = sum(r[1] for r in results)                    # the reduce step
```

| Workload | Use |
|---|---|
| **parsing / computing** (CPU-bound) | `ProcessPoolExecutor` — threads are blocked by the GIL |
| **fetching many objects** (I/O-bound) | threads or asyncio — the GIL is released during I/O |
| **both** | threads/async to fetch, processes to parse |

See [07 — Concurrency](07_concurrency.md). Caveats: each process pays interpreter startup and must
**pickle** its arguments — which is exactly why `(path, start, end)` is the right chunk descriptor.
Three integers and a string serialise instantly; a chunk of *data* would not.

**And that same descriptor scales beyond one machine**, which is the point to land:

```python
# the chunk descriptor is just two integers, so it works as a Lambda event or a Step Functions item
s3.get_object(Bucket=b, Key=k, Range=f"bytes={start}-{end}")   # a ranged GET
```

One 100GB object → 100 ranged GETs → 100 Lambda invocations driven by Step Functions' Map state, or 100
Spark tasks. Same algorithm, different scheduler.

---

### Q8. How do you make it survive a failure?

**A 100GB job runs for hours. Something will interrupt it.** The design requirement is that a crash at
80GB costs one chunk, not 80GB:

```python
def process_with_checkpoints(path, checkpoint_path, chunk_rows=50_000):
    state = {"rows_done": 0, "total": 0.0}
    if os.path.exists(checkpoint_path):
        with open(checkpoint_path) as f:
            state = json.load(f)                      # RESUME

    skip = state["rows_done"]
    with open(path) as f:
        reader = csv.DictReader(f)
        for i, chunk in enumerate(batched(reader, chunk_rows)):
            if (i + 1) * chunk_rows <= skip:
                continue                              # already done in a previous run
            state["total"] += sum(float(r["amount"]) for r in chunk)
            state["rows_done"] += len(chunk)

            tmp = checkpoint_path + ".tmp"             # ATOMIC checkpoint write
            with open(tmp, "w") as cf:
                json.dump(state, cf)
            os.replace(tmp, checkpoint_path)           # rename is atomic on POSIX and Windows
    return state
```

**`os.replace` is the load-bearing line.** Writing the checkpoint in place means a crash mid-write
leaves a truncated, unparseable JSON file — and now you can't resume at all, which is worse than having
no checkpoint. Write to a temp file, then rename: the rename is atomic, so the previous checkpoint stays
intact until the new one is complete.

**The three requirements that make resume correct:**

1. **Atomic checkpoint writes** (above).
2. **Idempotent processing.** On resume you may redo part of a chunk, so the downstream write must be an
   upsert or carry a dedup key. Otherwise resuming double-counts — the same reasoning as the Kafka sink's
   `ON CONFLICT (event_id) DO NOTHING`.
3. **Checkpoint *after* the side effect commits.** Checkpoint first and a crash loses that chunk's work
   silently; this is exactly the Kafka "commit the offset before processing" bug in a different costume.

**Chunk size is a recovery-time decision:** small chunks mean frequent checkpoints (more I/O, less
rework); large chunks the reverse. Pick it from "how much rework can I tolerate?" — which for a 6-hour
job is usually "a few minutes".

For S3, the natural checkpoint is the **byte offset**, so resume is a ranged GET from there. And in a
distributed version the checkpoint moves to DynamoDB or a database table, one row per chunk with a
status — at which point you've built a small job scheduler, which is the honest moment to ask whether
Step Functions or Airflow should own this.

---

### Q9. What about compressed and columnar formats?

**gzip streams fine:**

```python
with gzip.open(path, "rt", newline="") as f:          # decompresses as you read
    for row in csv.DictReader(f):
        ...
```

Measured: 12.9MB CSV → 2.7MB gz (4.8×), peak memory 588KB. Compression is nearly always worth it, since
S3 charges for bytes transferred and the CPU cost is small.

**But a single `.gz` is NOT splittable**, and that's the important consequence: the stream must be
decompressed from byte 0, so you cannot assign byte ranges to parallel workers. Your beautiful Q7
fan-out does not work on one big `.gz`.

The options:

| Format | Splittable | Notes |
|---|---|---|
| `.gz` (one big file) | **no** | one worker, start to finish |
| many smaller `.gz` | yes, **per file** | the practical fix: 100 × 1GB objects instead of 1 × 100GB |
| `bzip2` | yes | block-based, but slow |
| `lz4` / `zstd` | yes (framed) | fast; zstd has the best ratio/speed balance today |
| **Parquet** | **yes, by row group** | columnar + predicate pushdown + per-column compression |

**Parquet is usually the right answer for analytical data, and the reason is that it changes the
complexity class, not just the constant:**

- **Columnar**: reading 3 of 50 columns reads ~6% of the bytes. A row format must read every byte of
  every row.
- **Row groups** (~128MB) are independently readable → natural parallelism.
- **Statistics per row group** (min/max/null count) → **predicate pushdown**: `WHERE date = '2026-10-01'`
  skips entire row groups without decompressing them.
- **Per-column encoding** (dictionary, RLE, delta) typically gives 5–10× over CSV.

So the senior framing: **"if this file is read more than once, I'd convert it to Parquet once and read it
many times."** A one-off CSV scan streams; a dataset gets converted.

---

### Q10. Should this be in Python at all?

**Open with this, because it's the answer a senior engineer actually gives.**

> "Before writing any of this, I'd ask whether the file has to be processed in Python. If it lands in S3
> and the work is SQL-shaped, Athena or a Glue job is less code, cheaper to run, and already parallel.
> I'd write the Python streaming version when the transform is genuinely custom, or when it has to run
> inside an existing service."

The decision table:

| Situation | Reach for |
|---|---|
| in S3, SQL-shaped, ad hoc | **Athena** (or S3 Select for simple filters) — pay per TB scanned |
| in S3, SQL-shaped, scheduled | Glue job, or Athena CTAS into Parquet |
| genuinely big and recurring | Spark / EMR / Databricks — it does all of Q4–Q7 for you |
| one machine, SQL-shaped, up to ~100GB | **DuckDB** — `SELECT … FROM 'file.parquet'`, out-of-core, astonishingly fast |
| numeric columns, fits in ~10× RAM | Polars (streaming engine) or pandas with `chunksize` |
| custom per-record transform, modest volume | **Python streaming** (this document) |
| must run inside an existing service | Python streaming |
| the file is really a stream | Kafka + consumers ([18](18_queue_architectures.md)) |

**DuckDB deserves the specific mention** because it has changed the honest answer to this question for
single-machine work: it reads Parquet and CSV from local disk or S3, spills to disk, parallelises across
cores, and does Q4–Q6 (sort, dedupe, group, join) in C++ with no cluster. For a 100GB file on one box it
will beat hand-written Python by a wide margin, and "I'd try DuckDB first" is a strong, current answer.

**And the pandas warning**, since someone always asks: `pd.read_csv("100gb.csv")` will OOM. The
mitigations are `chunksize=100_000` (which gives you an iterator of DataFrames — the batching pattern
from Q3), `usecols=[...]` to read fewer columns, `dtype={...}` to avoid object columns, and
`engine="pyarrow"`. But if you're reaching for all of those, Polars or DuckDB is the better tool. See
[09 — Pandas](09_pandas.md).

---

## The decision table (the summary to memorise)

| What you need | What to reach for | Memory |
|---|---|---|
| sum / count / filter / transform | a generator pipeline, one pass | **O(1)** |
| GROUP BY, few distinct keys | a dict accumulated while streaming | O(keys) |
| GROUP BY, many distinct keys | hash-partition to N files, aggregate each | O(keys/N) |
| SORT | external merge sort: runs + `heapq.merge` | O(run size) |
| exact DEDUPE, huge key set | hash-partition, `set` per file | O(keys/N) |
| approximate DEDUPE | Bloom filter | **fixed** |
| count distinct, approximate | HyperLogLog | ~1.6 KB |
| exact p50 / p99 | impossible in one pass — t-digest, or sort first | varies |
| top k | bounded heap, `heapq.nlargest` | O(k) |
| JOIN | sort-merge, or hash the smaller side | O(smaller side) |
| CPU-bound parsing, parallel | `ProcessPoolExecutor` over byte ranges | O(workers × chunk) |
| I/O-bound fetching, parallel | threads or asyncio | O(in-flight) |
| a file in S3 | ranged GETs + Step Functions fan-out, or Athena | O(1) per worker |
| columnar analytics | convert to Parquet once, read columns | O(row group) |
| must survive a crash | chunk + atomic checkpoint (`os.replace`) | O(chunk) |
| doesn't fit on one machine | partition the INPUT: EMR/Glue/Spark | — |

---

## A worked example

**"A vendor drops a 100GB CSV of transactions in S3 nightly. Produce a per-merchant daily summary,
rejecting malformed rows, and make it resumable."**

```
ARCHITECTURE
  S3 (100GB CSV)
    -> Step Functions: a Lambda computes byte-range chunks aligned to newlines
    -> Map state: 200 parallel Lambdas, one 500MB range each
         each: ranged GET -> stream rows -> validate -> aggregate per merchant in a dict
               -> write ONE partial-aggregate JSON to s3://staging/{run}/{chunk}.json
               -> malformed rows -> s3://quarantine/{run}/{chunk}.jsonl  (never dropped silently)
    -> reduce Lambda: read 200 partials (small!), sum per merchant, write the final report
    -> DynamoDB: one row per chunk {run_id, chunk_id, status, rows, bytes}  = the checkpoint

WHY EACH CHOICE
  byte ranges aligned to newlines  no row is split or counted twice (Q7)
  200 chunks of 500MB              each fits a Lambda's memory and the 15-minute timeout
  PARTIAL aggregates, not rows     the reduce input is 200 small files, not 100GB.
                                   This is the only reason a serverless reduce is possible.
  per-merchant dict per chunk      O(merchants in this chunk), not O(rows). If merchants were
                                   high-cardinality, chunks would be partitioned BY MERCHANT
                                   instead of by byte range -- i.e. a real shuffle (Q4).
  DynamoDB row per chunk           resume = re-run only chunks whose status != done (Q8)
  quarantine, not discard          a dropped row is a data bug nobody finds for weeks (Q4/Q5
                                   of deep dive 25: silence is the sin)
  idempotent chunk output          the key is {run}/{chunk}.json, so a retried chunk overwrites
                                   itself -- the Lambda can be retried freely

COSTS AND LIMITS, STATED UP FRONT
  200 ranged GETs of 500MB         ~$0.04 in requests + egress within the region
  200 Lambdas x ~4 min x 1GB       ~$0.30 per run
  vs. one EC2 instance streaming   ~3 hours wall clock, ~$0.50, but no parallel failure isolation
  vs. Athena over the same data    convert to Parquet once, then the query is seconds and ~$0.05.
                                   IF THE WORK IS SQL-SHAPED, THIS IS THE RIGHT ANSWER (Q10) --
                                   and "per-merchant daily totals" is exactly SQL-shaped.

SO WHAT I'D ACTUALLY RECOMMEND
  Stage 1: a Glue/Lambda job converts the nightly CSV to Parquet partitioned by date  (streaming,
           so constant memory, and it's the only custom code needed).
  Stage 2: Athena does the aggregation in SQL.
  The Python fan-out above is the right design only if the per-row transform is genuinely custom
  -- vendor-specific parsing, an external enrichment call, ML scoring. I'd say that explicitly
  rather than build the complicated thing by default.
```

**That last paragraph is the answer.** An interviewer asking this question is often checking whether you
reach for the elaborate distributed solution reflexively, or whether you can size the problem and pick
the boring tool. Build the fan-out when the transform earns it.

---

## Hands-on drills

1. Run the companion. Then set `ROWS = 3_000_000` and re-run. The full-read peak grows ~10×; the
   streaming peak barely moves. That one comparison **is** the answer to the question.
2. Build the three-stage generator pipeline, then rewrite it with a list comprehension at each stage.
   Measure both with `tracemalloc`.
3. Compare `batch_size=1` and `batch_size=5000` round-trip counts. Multiply by 2ms. That's the number to
   quote when someone asks why the loader is slow.
4. Write `external_sort` with `rows_per_run=5000`, then `50_000`, then `500_000`. Find where more runs
   stops helping — and find the file-descriptor limit on your machine.
5. Then do the same sort with `sort -S 100M` and compare wall times. Be honest about the result.
6. Break `find_chunk_boundaries` on purpose (plain `size // n`, no newline advance) and watch the row
   count come out wrong.
7. Replace the serial loop in `parallel_aggregate` with `ProcessPoolExecutor.map`, measure the speedup,
   then try `ThreadPoolExecutor` and explain why it barely helps.
8. Shrink the Bloom filter to `n_bits=1<<12` and count how many unique keys it "loses". That ratio is the
   false-positive rate you must size for.
9. Make the checkpointed job crash at chunk 3, then resume. Then make the checkpoint write non-atomic
   (write in place) and crash *during* the write. Observe that you can no longer resume at all.
10. Convert the sample to Parquet with pyarrow, then read one column with pandas and with DuckDB. Compare
    bytes read and wall time against the CSV.
11. Write `top_k_customers(path, k=10)` in one pass with a bounded heap. Then explain what breaks when
    the customer count itself doesn't fit in memory.

---

## The 60-second spoken answer

> "I'd start by asking whether it needs to be Python at all — if it's in S3 and the work is SQL-shaped,
> converting it to Parquet once and querying with Athena, or just running DuckDB on one box, is less code
> and cheaper than anything I'd write. I'd write the streaming version when the per-record transform is
> genuinely custom or it has to run inside an existing service.
>
> If it is Python: never `read()` it. Iterating a file object yields one line at a time, so peak memory
> is the longest line — identical for 10MB and 100GB — and the S3 equivalent is wrapping the
> `StreamingBody` rather than calling `.read()` on it. I compose the work as a generator pipeline, parse
> then filter then transform, so peak memory stays at one record no matter how many stages there are, and
> I batch the *writes* — about a thousand rows per round trip, which is the difference between 52 database
> calls and 257,000.
>
> The thing to be precise about is which operations are one-pass. Sum, count, filter and a
> small-cardinality GROUP BY are O(1) or O(keys). Sort, exact dedupe, joins and exact percentiles are
> not. For sorting it's an external merge sort: sort chunks in memory, write sorted runs to disk, then
> `heapq.merge` across them, which holds one record per run — that's how `sort -S`, Postgres and Spark all
> do it. For dedupe at scale I hash-partition so every copy of a key lands in the same file and then use a
> set per file, which is exactly a shuffle; or a Bloom filter if approximate is acceptable — fixed memory,
> no false negatives, but it can drop a genuinely new record, so I'd use it as a pre-filter in front of a
> database check. And I'd say plainly that an exact p99 can't be done in one pass: that's a t-digest or a
> reservoir sample.
>
> To parallelise, I split into byte ranges that each start on a record boundary — seek to the nominal
> offset then advance to the next newline, and let each worker read past its end to finish the line it
> started. Then processes, not threads, because parsing is CPU-bound and the GIL blocks threads. The
> chunk descriptor is just two integers, which is why the same algorithm works as a ranged S3 GET per
> Lambda behind a Step Functions Map state.
>
> And it has to survive failure, because a job this size runs for hours: chunk the work, checkpoint after
> each chunk, and write the checkpoint to a temp file and `os.replace` it so a crash mid-write leaves the
> previous one intact. The downstream write has to be idempotent, because a resume may redo part of a
> chunk, and the checkpoint goes *after* the side effect commits — checkpointing first is the same bug as
> committing a Kafka offset before processing.
>
> Last thing: a single gzip isn't splittable, so if I want parallelism it has to be many smaller objects
> or a columnar format. Parquet changes the complexity rather than the constant — columnar so reading 3
> of 50 columns reads 6% of the bytes, row groups for parallelism, and statistics for predicate
> pushdown. If the file is read more than once, I convert it."
