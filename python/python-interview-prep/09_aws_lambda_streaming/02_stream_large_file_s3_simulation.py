"""
Streaming a large file line-by-line (constant memory) vs. loading it fully into memory.
Simulates S3's StreamingBody with a local file so you can watch peak memory stay flat as the
file grows, using nothing but stdlib (tracemalloc).

Run me: python 02_stream_large_file_s3_simulation.py
"""
import csv
import io
import os
import tracemalloc


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


SAMPLE_PATH = "_generated_sample.csv"
ROW_COUNT = 200_000


def generate_sample_file():
    with open(SAMPLE_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["order_id", "amount"])
        for i in range(ROW_COUNT):
            writer.writerow([i, i * 1.5])


# ---------------------------------------------------------------- WRONG: load it all into memory
def load_entire_file(path):
    """This is what `s3_client.get_object(...)['Body'].read()` followed by full parsing looks
    like -- fine for a 10KB file, a real problem for a 10GB one on a memory-constrained Lambda."""
    with open(path) as f:
        content = f.read()  # the ENTIRE file, all at once
    reader = csv.DictReader(io.StringIO(content))
    total = 0
    for row in reader:
        total += float(row["amount"])
    return total


# ---------------------------------------------------------------- RIGHT: stream it
def stream_and_aggregate(path, batch_size=500):
    """Mirrors: `for row in csv.DictReader(io.TextIOWrapper(s3_response["Body"]))`.
    At any instant, only ONE row (plus a small batch buffer) is resident in memory --
    total memory use does NOT grow with file size."""
    total = 0.0
    batch = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:                 # one row in memory at a time
            batch.append(float(row["amount"]))
            if len(batch) >= batch_size:
                total += sum(batch)         # "flush" the batch downstream
                batch.clear()
        if batch:
            total += sum(batch)
    return total


def measure(fn, *args):
    tracemalloc.start()
    result = fn(*args)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, peak


if __name__ == "__main__":
    section(f"generating a {ROW_COUNT:,}-row sample CSV")
    generate_sample_file()
    size_mb = os.path.getsize(SAMPLE_PATH) / 1024 / 1024
    print(f"  file on disk: {size_mb:.2f} MB")

    section("loading the ENTIRE file into memory, then parsing")
    result_full, peak_full = measure(load_entire_file, SAMPLE_PATH)
    print(f"  total: {result_full:,.1f} | peak traced memory: {peak_full / 1024 / 1024:.2f} MB")

    section("STREAMING the file row-by-row with a bounded batch buffer")
    result_stream, peak_stream = measure(stream_and_aggregate, SAMPLE_PATH)
    print(f"  total: {result_stream:,.1f} | peak traced memory: {peak_stream / 1024 / 1024:.2f} MB")

    section("comparison")
    assert result_full == result_stream, "both approaches must agree on the answer"
    print(f"  both computed the identical total: {result_full:,.1f}")
    print(f"  full-load peak memory  : {peak_full / 1024 / 1024:7.2f} MB")
    print(f"  streaming peak memory  : {peak_stream / 1024 / 1024:7.2f} MB")
    print(f"  memory reduction       : {(1 - peak_stream / peak_full) * 100:6.1f}%")

    os.remove(SAMPLE_PATH)

# EXPERIMENT: bump ROW_COUNT to 2_000_000 and rerun -- the full-load peak memory grows roughly
# linearly with file size, while the streaming peak barely moves. That gap is exactly why a
# Lambda with 512MB configured can process a 10GB file if (and only if) it streams.
