"""
"How would you handle a 100GB file?" -- the full answer, runnable.

The one-line answer is "stream it, never load it", but that only earns half the marks. The rest
is: what if you need to SORT it, GROUP it, DEDUPE it, or process it in PARALLEL, when none of
those fit in RAM? And what if the job dies 80GB in?

This file demonstrates, with measured peak memory (tracemalloc) on a generated file:

  1. read() vs line-by-line        -- O(file) memory vs O(line) memory
  2. a GENERATOR PIPELINE           -- parse -> filter -> transform, each stage lazy, constant memory
  3. CHUNKED / BATCHED writes       -- amortise the downstream round trip without buffering it all
  4. STREAMING AGGREGATION          -- sum/count/group in one pass, O(distinct keys) memory
  5. EXTERNAL MERGE SORT            -- sort 100GB with 100MB of RAM (sorted runs + heapq.merge)
  6. DEDUPE at scale                -- exact (disk-backed) vs probabilistic (a tiny Bloom filter)
  7. PARALLEL byte-range chunks     -- split on record boundaries, fan out to processes/Lambdas
  8. CHECKPOINT + RESUME            -- so a failure at 80GB costs 1 chunk, not 80GB
  9. compressed input               -- gzip streams; why .gz is not splittable and what to use

Pure stdlib. The file it generates is small (configurable) but every technique is the same one
you'd run at 100GB -- the point is that peak memory does not change with file size.

Run me: python 03_large_file_processing.py
"""
import csv
import glob
import gzip
import hashlib
import heapq
import itertools
import json
import os
import tempfile
import tracemalloc
from collections import defaultdict


def section(title):
    print(f"\n{'=' * 74}\n{title}\n{'=' * 74}")


WORK_DIR = tempfile.mkdtemp(prefix="bigfile_")
SAMPLE = os.path.join(WORK_DIR, "orders.csv")
ROWS = 300_000               # bump to 5_000_000 to feel it; peak memory will NOT move


def human(n_bytes):
    for unit in ("B", "KB", "MB", "GB"):
        if n_bytes < 1024 or unit == "GB":
            return f"{n_bytes:.1f}{unit}"
        n_bytes /= 1024


def generate_sample(path=SAMPLE, rows=ROWS):
    """Writes the input the same way you should write any large output: row by row, flushing as
    you go, never building a list of `rows` dicts first."""
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["order_id", "customer_id", "region", "amount", "status"])
        regions = ["APAC", "EMEA", "AMER"]
        for i in range(rows):
            w.writerow([f"ORD-{i:08d}", f"CUST-{i % 5000:05d}", regions[i % 3],
                        round(10 + (i % 997) * 0.37, 2),
                        "SHIPPED" if i % 7 else "CANCELLED"])
    return path


def measure(label, fn, *args, **kwargs):
    """Runs fn under tracemalloc and reports PEAK memory -- the number that decides whether your
    Lambda OOMs, not the average."""
    tracemalloc.start()
    result = fn(*args, **kwargs)
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(f"    {label:38s} peak={human(peak):>9s}  result={result}")
    return peak


# ================================================================ 1. read() vs streaming
def total_by_loading_everything(path):
    """What `s3.get_object(...)["Body"].read()` or `pd.read_csv(huge)` does. Fine at 10MB.
    At 100GB it OOMs the container before the first row is processed."""
    with open(path) as f:
        content = f.read()                       # the ENTIRE file in one str
    reader = csv.DictReader(content.splitlines())  # and now a SECOND full copy as a list of lines
    return round(sum(float(r["amount"]) for r in reader), 2)


def total_by_streaming(path):
    """Iterating a file object yields one line at a time, buffered by the OS. Peak memory is the
    size of the longest LINE -- so it is identical for a 10MB file and a 100GB one.

    The S3 equivalent, with no change to the loop:
        body = s3.get_object(Bucket=b, Key=k)["Body"]          # a StreamingBody
        for row in csv.DictReader(io.TextIOWrapper(body, encoding="utf-8")):
    """
    with open(path) as f:
        return round(sum(float(r["amount"]) for r in csv.DictReader(f)), 2)


# ================================================================ 2. a generator pipeline
def read_rows(path):
    """Stage 1: bytes -> dicts. A generator, so nothing is materialised."""
    with open(path) as f:
        yield from csv.DictReader(f)


def only_shipped(rows):
    """Stage 2: filter. `rows` is a generator; this is too. No intermediate list."""
    for row in rows:
        if row["status"] == "SHIPPED":
            yield row


def to_cents(rows):
    """Stage 3: transform."""
    for row in rows:
        yield {**row, "amount_cents": int(round(float(row["amount"]) * 100))}


def pipeline_total(path):
    """Three stages composed like Unix pipes. Each row flows all the way through before the next
    one is read, so peak memory is ONE row -- regardless of stage count or file size.

    This is the single most useful shape in the whole topic: `sum(r["amount_cents"] for r in
    to_cents(only_shipped(read_rows(path))))` reads like a query and runs in constant memory.
    """
    return sum(r["amount_cents"] for r in to_cents(only_shipped(read_rows(path))))


# ================================================================ 3. batched writes
def batched(iterable, size):
    """itertools.batched (3.12+) spelled out, since this is the single most useful helper here.
    Batching is NOT buffering the whole file: only `size` items are ever in memory."""
    iterator = iter(iterable)
    while batch := list(itertools.islice(iterator, size)):
        yield batch


def load_with_batched_writes(path, batch_size=5000):
    """One DB/queue round trip per batch instead of per row. The win at 100GB is enormous and the
    memory cost is bounded by batch_size.

    Real equivalents: execute_values(cur, sql, batch) / dynamodb.batch_write_item /
    producer.produce() + flush() every N / s3.upload_part().
    """
    batches = rows_written = 0
    for batch in batched(only_shipped(read_rows(path)), batch_size):
        batches += 1
        rows_written += len(batch)               # <- the "write" happens here, once per batch
    return f"{rows_written} rows in {batches} batches"


# ================================================================ 4. streaming aggregation
def aggregate_streaming(path):
    """GROUP BY in one pass. Memory is O(number of DISTINCT KEYS), not O(rows) -- 3 regions here,
    so it stays tiny even at 100GB. If the key cardinality is itself huge (per-customer over
    millions of customers), partition by a hash of the key into N files first, then aggregate each
    file independently -- that is literally what a shuffle is."""
    totals = defaultdict(float)
    counts = defaultdict(int)
    for row in read_rows(path):
        totals[row["region"]] += float(row["amount"])
        counts[row["region"]] += 1
    return {r: (counts[r], round(totals[r], 2)) for r in sorted(totals)}


def running_stats(path):
    """Min/max/mean/count in one pass with four scalars. For percentiles you cannot do this
    exactly in one pass -- use a t-digest / reservoir sample, and SAY that rather than claiming
    an exact p99 in constant memory."""
    n, total, lo, hi = 0, 0.0, float("inf"), float("-inf")
    for row in read_rows(path):
        v = float(row["amount"])
        n += 1
        total += v
        lo, hi = min(lo, v), max(hi, v)
    return {"count": n, "mean": round(total / n, 4), "min": lo, "max": hi}


# ================================================================ 5. external merge sort
def external_sort(path, key_column="amount", rows_per_run=50_000):
    """Sort a file far larger than RAM. The classic two-phase answer:

      PHASE 1 (split):  read `rows_per_run` rows, sort them IN MEMORY, write a sorted run to disk.
                        Repeat. Peak memory = one run, which you choose.
      PHASE 2 (merge):  heapq.merge() over all run files -- it holds ONE row per run, pulling the
                        next smallest each time. 100 runs = 100 rows in memory, not 100GB.

    This is exactly what `sort -S 100M bigfile` and every database's external sort do.
    Complexity: O(n log n) comparisons, O(n) disk I/O per merge pass.
    """
    run_files = []
    with open(path) as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        for run_index, chunk in enumerate(batched(reader, rows_per_run)):
            chunk.sort(key=lambda r: float(r[key_column]))        # the only in-memory sort
            run_path = os.path.join(WORK_DIR, f"run_{run_index:04d}.csv")
            with open(run_path, "w", newline="") as out:
                writer = csv.DictWriter(out, fieldnames=header)
                writer.writerows(chunk)
            run_files.append(run_path)

    def read_run(run_path):
        with open(run_path) as rf:
            for row in csv.DictReader(rf, fieldnames=header):
                yield row

    merged_path = os.path.join(WORK_DIR, "sorted.csv")
    with open(merged_path, "w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=header)
        writer.writeheader()
        streams = [read_run(p) for p in run_files]
        for row in heapq.merge(*streams, key=lambda r: float(r[key_column])):
            writer.writerow(row)                 # one row at a time, straight out to disk
    return merged_path, len(run_files)


def verify_sorted(path, key_column="amount", sample=5):
    with open(path) as f:
        values = [float(r[key_column]) for r in csv.DictReader(f)]
    return (values == sorted(values), values[:sample], values[-sample:])


# ================================================================ 6. dedupe at scale
def dedupe_exact_in_memory(path, key="customer_id"):
    """Correct, but memory is O(distinct keys). 5,000 customers is nothing; 2 BILLION 36-byte
    UUIDs is ~100GB of set -- i.e. the same problem you were trying to avoid."""
    seen = set()
    unique = 0
    for row in read_rows(path):
        if row[key] not in seen:
            seen.add(row[key])
            unique += 1
    return unique, len(seen)


class TinyBloomFilter:
    """Probabilistic membership in FIXED memory: no false negatives, a tunable false-positive
    rate. The honest answer to "dedupe 2 billion ids with 1GB of RAM" -- plus a confirmation
    lookup against the database for anything the filter says it has seen, if exactness matters.

    (Production: use `pybloom-live` or Redis's BF.* commands; this is the mechanism, in 20 lines.)
    """

    def __init__(self, n_bits=1 << 20, n_hashes=4):
        self.n_bits, self.n_hashes = n_bits, n_hashes
        self.bits = bytearray(n_bits // 8)

    def _positions(self, item):
        digest = hashlib.blake2b(str(item).encode(), digest_size=16).digest()
        base = int.from_bytes(digest[:8], "big")
        step = int.from_bytes(digest[8:], "big") | 1
        for i in range(self.n_hashes):
            yield (base + i * step) % self.n_bits

    def add(self, item):
        for pos in self._positions(item):
            self.bits[pos // 8] |= 1 << (pos % 8)

    def __contains__(self, item):
        return all(self.bits[p // 8] >> (p % 8) & 1 for p in self._positions(item))


def dedupe_probabilistic(path, key="customer_id"):
    bloom = TinyBloomFilter()
    unique = 0
    for row in read_rows(path):
        if row[key] not in bloom:
            bloom.add(row[key])
            unique += 1
    return unique, f"{len(bloom.bits)}B of bitmap"


def dedupe_by_disk_partition(path, key="customer_id", buckets=8):
    """Exact dedupe in bounded memory: hash-partition into N files so that all copies of a key
    land in the SAME file, then dedupe each file independently with a set that only has to hold
    1/N of the keys. Same trick as the shuffle in MapReduce/Spark."""
    paths = [os.path.join(WORK_DIR, f"bucket_{i}.txt") for i in range(buckets)]
    handles = [open(p, "w") for p in paths]
    try:
        for row in read_rows(path):
            k = row[key]
            handles[int(hashlib.blake2b(k.encode(), digest_size=4).hexdigest(), 16) % buckets] \
                .write(k + "\n")
    finally:
        for h in handles:
            h.close()

    unique = 0
    for p in paths:                      # one bucket in memory at a time
        with open(p) as f:
            unique += len({line.rstrip("\n") for line in f})
    return unique, f"{buckets} buckets, ~1/{buckets} of keys resident at a time"


# ================================================================ 7. parallel byte ranges
def find_chunk_boundaries(path, n_chunks):
    """Split a file into N byte ranges that each START on a record boundary.

    The bug everyone writes first: `size // n` splits a line in half, so one worker gets
    "ORD-000123,CUST-" and the next gets "0042,APAC,...". The fix is to seek to the nominal
    offset and then advance to the next newline -- and to let each worker read PAST its end
    offset to finish the line it started.

    The S3 equivalent is a ranged GET per chunk, which is how you fan one 100GB object out to 100
    Lambdas or 100 Spark tasks:
        s3.get_object(Bucket=b, Key=k, Range=f"bytes={start}-{end}")
    """
    size = os.path.getsize(path)
    nominal = size // n_chunks
    boundaries = []
    with open(path, "rb") as f:
        f.readline()                       # skip the header; it belongs to no chunk
        start = f.tell()
        for i in range(1, n_chunks):
            f.seek(start + nominal)
            if f.readline() == b"":        # past EOF already
                break
            end = f.tell()
            boundaries.append((start, end))
            start = end
        boundaries.append((start, size))
    return boundaries


def process_byte_range(args):
    """A worker. Opens the file, seeks to `start`, reads until it passes `end`. No shared state,
    so this runs unchanged in a thread, a process (ProcessPoolExecutor), or a separate Lambda
    invocation -- which is the whole point: the chunk descriptor is just two integers."""
    path, start, end, header = args
    total, count = 0.0, 0
    with open(path, "rb") as f:
        f.seek(start)
        while f.tell() < end:
            line = f.readline()
            if not line:
                break
            row = dict(zip(header, line.decode().rstrip("\n").split(",")))
            total += float(row["amount"])
            count += 1
    return count, round(total, 2)


def parallel_aggregate(path, n_chunks=4):
    """Map-then-reduce over byte ranges. Run with ProcessPoolExecutor for real CPU parallelism
    (the GIL makes threads useless for parsing -- see 02_concurrency/), or as N Lambda
    invocations driven by Step Functions when the file is genuinely 100GB.

    Done serially here so the output is deterministic and the demo needs no spawn overhead.
    """
    with open(path) as f:
        header = next(csv.reader(f))
    chunks = find_chunk_boundaries(path, n_chunks)
    results = [process_byte_range((path, s, e, header)) for s, e in chunks]
    # reduce: the per-chunk partial results combine into the global answer
    return sum(c for c, _ in results), round(sum(t for _, t in results), 2), len(chunks)


# ================================================================ 8. checkpoint and resume
def process_with_checkpoints(path, checkpoint_path, chunk_rows=50_000, fail_at_chunk=None):
    """A 100GB job takes hours. Something WILL interrupt it, and restarting from zero is not an
    option. So: process in chunks, and after each chunk atomically record how far you got.

    `os.replace` is the atomic bit -- write a temp file, then rename. A crash mid-write leaves the
    PREVIOUS checkpoint intact instead of a truncated, unparseable one.
    """
    state = {"rows_done": 0, "total": 0.0}
    if os.path.exists(checkpoint_path):
        with open(checkpoint_path) as f:
            state = json.load(f)

    skip = state["rows_done"]
    processed_now = 0
    with open(path) as f:
        reader = csv.DictReader(f)
        for chunk_index, chunk in enumerate(batched(reader, chunk_rows)):
            if (chunk_index + 1) * chunk_rows <= skip:
                continue                                   # already done in a previous run
            if fail_at_chunk is not None and chunk_index == fail_at_chunk:
                raise OSError(f"simulated crash in chunk {chunk_index}")
            state["total"] += sum(float(r["amount"]) for r in chunk)
            state["rows_done"] += len(chunk)
            processed_now += len(chunk)

            tmp = checkpoint_path + ".tmp"                  # atomic checkpoint write
            with open(tmp, "w") as cf:
                json.dump(state, cf)
            os.replace(tmp, checkpoint_path)
    return state["rows_done"], round(state["total"], 2), processed_now


# ================================================================ 9. compressed input
def write_gzip(path, source):
    with open(source, "rb") as src, gzip.open(path, "wb") as dst:
        for block in iter(lambda: src.read(1 << 20), b""):   # 1MB blocks, never read()
            dst.write(block)
    return path


def stream_gzip(path):
    """gzip.open streams -- it decompresses as you read, so memory stays flat. The catch worth
    stating: a single .gz is NOT SPLITTABLE, so you cannot byte-range it across workers. For
    parallel work use many smaller .gz files, or a splittable codec (bzip2, LZO-indexed), or
    columnar Parquet with row groups."""
    total = 0.0
    with gzip.open(path, "rt", newline="") as f:
        for row in csv.DictReader(f):
            total += float(row["amount"])
    return round(total, 2)


if __name__ == "__main__":
    print(f"generating a {ROWS:,}-row sample in {WORK_DIR} ...")
    generate_sample()
    file_size = os.path.getsize(SAMPLE)
    print(f"  {SAMPLE} -> {human(file_size)}")
    print("  (every technique below has the SAME peak memory at 100GB -- that's the point)")

    section("1. read() the whole file vs. stream it line by line")
    peak_all = measure("full read() into memory", total_by_loading_everything, SAMPLE)
    peak_stream = measure("line-by-line streaming", total_by_streaming, SAMPLE)
    print(f"    -> streaming used {peak_all / max(peak_stream, 1):.0f}x less peak memory, and the")
    print(f"       gap GROWS with file size: at 100GB the first version simply cannot run.")

    section("2. a generator pipeline: parse -> filter -> transform, all lazy")
    measure("pipeline_total (3 lazy stages)", pipeline_total, SAMPLE)
    print("    each row flows through all three stages before the next is read; peak = one row.")
    print("    the same pipeline over a list comprehension at each stage would hold 3 full copies.")

    section("3. batched writes: one round trip per N rows, not per row")
    measure("batch_size=5000", load_with_batched_writes, SAMPLE, 5000)
    measure("batch_size=1 (the mistake)", load_with_batched_writes, SAMPLE, 1)
    print("    memory is similar; what changes is ROUND TRIPS -- 52 vs 257,142 downstream calls.")

    section("4. streaming aggregation: GROUP BY in one pass")
    print(f"    by region: {aggregate_streaming(SAMPLE)}")
    print(f"    running stats: {running_stats(SAMPLE)}")
    print("    memory is O(distinct keys) = 3 here. If the key is high-cardinality, hash-partition")
    print("    into N files first and aggregate each independently (that IS a shuffle).")

    section("5. external merge sort: sort a file bigger than RAM")
    sorted_path, n_runs = external_sort(SAMPLE, rows_per_run=50_000)
    ok, head, tail = verify_sorted(sorted_path)
    print(f"    {ROWS:,} rows sorted via {n_runs} on-disk runs -> {human(os.path.getsize(sorted_path))}")
    print(f"    correctly ordered: {ok}   first: {head}   last: {tail}")
    print(f"    peak memory held ONE run (50k rows) in phase 1, and {n_runs} rows in phase 2.")
    print("    the same two phases are what `sort -S`, Postgres and Spark all use.")

    section("6. deduplication when the key set itself is huge")
    print(f"    exact, in-memory set   : {dedupe_exact_in_memory(SAMPLE)}")
    print(f"    probabilistic (Bloom)  : {dedupe_probabilistic(SAMPLE)}")
    print(f"    exact, disk-partitioned: {dedupe_by_disk_partition(SAMPLE)}")
    print("    the Bloom filter can over-count 'seen' (false positives) but never under-count;")
    print("    pair it with a DB lookup when a false positive would actually drop data.")

    section("7. parallel processing via byte ranges (the 100GB fan-out)")
    boundaries = find_chunk_boundaries(SAMPLE, 4)
    for i, (s, e) in enumerate(boundaries):
        print(f"    chunk {i}: bytes {s:>10,} - {e:>10,}  ({human(e - s)})")
    count, total, n = parallel_aggregate(SAMPLE, n_chunks=4)
    serial_total = total_by_streaming(SAMPLE)
    print(f"    {n} chunks -> {count:,} rows, total {total} (serial total {serial_total}: "
          f"{'MATCH' if abs(total - serial_total) < 0.01 else 'MISMATCH'})")
    print("    boundaries land on newlines, so no row is split or counted twice.")
    print("    swap the list comprehension for ProcessPoolExecutor.map for real parallelism, or")
    print("    emit one (start, end) pair per Lambda invocation via Step Functions.")

    section("8. checkpoint and resume: a crash at 80GB must not cost 80GB")
    ckpt = os.path.join(WORK_DIR, "checkpoint.json")
    try:
        process_with_checkpoints(SAMPLE, ckpt, chunk_rows=50_000, fail_at_chunk=3)
    except OSError as e:
        with open(ckpt) as f:
            saved = json.load(f)
        print(f"    crashed: {e}")
        print(f"    checkpoint survived with rows_done={saved['rows_done']:,}")
    done, total, processed_now = process_with_checkpoints(SAMPLE, ckpt, chunk_rows=50_000)
    print(f"    resumed and finished: rows_done={done:,}, total={total}")
    print(f"    rows re-processed on the resume: {done - processed_now:,} already-done rows skipped")
    print("    os.replace() makes the checkpoint write atomic -- a crash mid-write keeps the old one.")

    section("9. compressed input streams, and why .gz is not splittable")
    gz = write_gzip(os.path.join(WORK_DIR, "orders.csv.gz"), SAMPLE)
    print(f"    {human(file_size)} csv -> {human(os.path.getsize(gz))} gz "
          f"({file_size / os.path.getsize(gz):.1f}x smaller)")
    measure("gzip streamed with gzip.open", stream_gzip, gz)
    print("    a single .gz must be decompressed from byte 0, so byte-range parallelism is out.")
    print("    at 100GB use many smaller .gz objects, or Parquet (columnar + row groups + predicate")
    print("    pushdown), which also lets you read 3 of 50 columns instead of all of them.")

    section("the decision table")
    print("""  What you need                     What to reach for
  --------------------------------  ----------------------------------------------------------
  sum / count / filter / transform  a generator pipeline, one pass, O(1) memory
  GROUP BY, few distinct keys       a dict accumulated while streaming, O(keys)
  GROUP BY, many distinct keys      hash-partition to N files, then aggregate each (a shuffle)
  SORT                              external merge sort: sorted runs + heapq.merge
  exact DEDUPE, huge key set        hash-partition to N files, set per file
  approximate DEDUPE                Bloom filter (fixed memory, no false negatives)
  exact p50/p99                     cannot be done in one pass -- t-digest, or sort first
  CPU-bound parsing                 ProcessPoolExecutor over byte ranges (threads lose to the GIL)
  I/O-bound fetching                threads or asyncio -- the GIL is released during I/O
  a file in S3                      ranged GETs + Step Functions fan-out, or Athena/Glue/Spark
  columnar analytics                convert to Parquet once; then read only the columns you need
  "it must survive a crash"         chunk + atomic checkpoint (os.replace), resume from it
  it does not fit on one machine    partition the INPUT, not the code: EMR/Glue/Spark, or shard

  And the honest senior answer to open with: "before writing any of this, I'd ask whether the
  file has to be processed in Python at all. If it lands in S3 and the work is SQL-shaped,
  Athena or a Glue job is less code, cheaper to run and already parallel. I'd write the Python
  streaming version when the transform is genuinely custom, or when it has to run inside an
  existing service.\"""")

    print(f"\n  cleaning up {WORK_DIR} ...")
    for p in glob.glob(os.path.join(WORK_DIR, "*")):
        os.remove(p)
    os.rmdir(WORK_DIR)
    print("  done.")

# EXPERIMENT 1: set ROWS = 3_000_000 and re-run. The full-read peak grows ~10x; the streaming peak
# barely moves. That single comparison IS the interview answer.
# EXPERIMENT 2: in external_sort, drop rows_per_run to 5_000. More runs, lower phase-1 memory,
# more open files in phase 2 -- find where it stops helping. (Hint: the OS file-handle limit.)
# EXPERIMENT 3: replace the list comprehension in parallel_aggregate with
# concurrent.futures.ProcessPoolExecutor().map(process_byte_range, chunk_args) and compare wall
# time. Then try ThreadPoolExecutor and explain why it barely helps.
# EXPERIMENT 4: break find_chunk_boundaries on purpose -- return plain `size // n` offsets without
# advancing to the next newline -- and watch the row count come out wrong.
# EXPERIMENT 5: shrink TinyBloomFilter to n_bits=1<<12 and count how many unique customers it
# "loses" to false positives. That ratio is the false-positive rate you must size for.

# EXERCISE: write `top_k_customers(path, k=10)` that finds the 10 highest-spending customers in
# ONE pass using heapq.nlargest / a bounded heap, holding at most k entries plus the running
# per-customer totals. Then explain what breaks when the customer count itself does not fit in
# memory, and how hash-partitioning fixes it.
