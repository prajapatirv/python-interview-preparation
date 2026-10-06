# 09 — AWS Lambda & Streaming Large Files

Pure stdlib — no `boto3`/AWS credentials needed. S3 is simulated with a local file so the
streaming behavior (constant memory, regardless of file size) is genuinely observable.

## Crib sheet

- **Lambda handler shape**: initialize clients/connections *outside* the handler (module level)
  so they're reused across warm invocations — creating a DB connection inside the handler means
  paying that cost on every single invocation.
- **On error**: `raise` inside the handler so Lambda's built-in retry mechanism (and DLQ, if
  configured) kicks in. Swallowing exceptions silently drops failed events.
- **Never load a large file fully into memory.** Lambda's `/tmp` and memory are both bounded
  (512MB–10GB configurable). Stream from S3 using the response body's streaming interface and
  process record-by-record, batching writes downstream.
- **Batch writes, not per-record writes**: accumulate N processed records, flush to the DB/queue,
  clear the buffer, repeat — far fewer round trips than one write per record.
- **For files that exceed what one Lambda invocation can handle** (memory, or the 15-minute
  timeout): split by byte range or use Step Functions to fan out chunk-processing across many
  parallel Lambda invocations instead of one giant one.

## Files

| File | Topic |
|---|---|
| `01_lambda_handler_patterns.py` | the handler shape: module-level init, structured logging, re-raise on error |
| `02_stream_large_file_s3_simulation.py` | streaming a "large" file line-by-line with constant memory, vs. loading it all at once |
| `03_large_file_processing.py` | the full "how would you handle a 100GB file?" answer — generator pipelines, batched writes, streaming aggregation, **external merge sort**, dedupe (Bloom filter + disk partitioning), **parallel byte-range chunks**, atomic checkpoint/resume, gzip vs Parquet |

> **Deep dive**: [30 — Handling a 100GB file](../deep_dive/30_large_file_processing.md) — which
> operations are one-pass and which aren't, how to sort/dedupe/join beyond RAM, how to split on
> record boundaries for parallel workers, how to survive a crash at 80GB, and when the right answer
> is Athena/DuckDB/Spark instead of Python.

## Exercise

Modify `02_stream_large_file_s3_simulation.py`'s streaming reader to also track a **running
checksum** (e.g. a rolling count of malformed rows) without ever holding more than one row in
memory at a time — this is the shape of a real Lambda that validates a large CSV upload before
accepting it.
