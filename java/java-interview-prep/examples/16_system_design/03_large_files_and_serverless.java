/*
 * 03 - Large files in constant memory, and the AWS Lambda handler patterns
 *
 * Run:  java 03_large_files_and_serverless.java
 *
 * Interview angle: "how would you process a 100 GB file?", "why does my job run out of memory?",
 * "how do you resume after a crash halfway?", "what belongs outside the Lambda handler?". The Java twin
 * of python/python-interview-prep/09_aws_lambda_streaming (see shared/cross-stack-pairs.md). A real
 * temporary CSV is generated, so every claim below is a measured number; it is deleted on exit.
 */
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

class LargeFilesAndServerless {

    static final int ROWS = 300_000;                 // EXPERIMENT: raise it; the streaming numbers do not move
    static final String[] REGIONS = {"EU", "US", "APAC", "LATAM"};

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    public static void main(String[] args) throws Exception {
        Path dir = Files.createTempDirectory("large-file-demo");
        Path csv = dir.resolve("orders.csv");
        try {
            writeFile(csv);
            run(csv);
        } finally {
            try (var s = Files.walk(dir)) { s.sorted(Comparator.reverseOrder()).forEach(p -> p.toFile().delete()); }
        }
    }

    static void writeFile(Path csv) throws IOException {
        Random rnd = new Random(42);
        try (BufferedWriter w = Files.newBufferedWriter(csv, StandardCharsets.UTF_8)) {
            w.write("order_id,region,amount_cents\n");
            for (int i = 1; i <= ROWS; i++)
                w.write(i + "," + REGIONS[rnd.nextInt(REGIONS.length)] + "," + (100 + rnd.nextInt(10_000)) + "\n");
        }
    }

    static void run(Path csv) throws Exception {
        System.out.printf("  generated %,d rows, %.1f MB%n", ROWS, Files.size(csv) / 1e6);

        section("1. Load everything vs stream line by line");
        long base = usedHeap();
        List<String> all = Files.readAllLines(csv);                     // the whole file on the heap
        long loaded = usedHeap() - base;
        System.out.printf("  readAllLines   : %,d lines, about %.0f MB of heap while held%n", all.size(), loaded / 1e6);
        all = null;
        base = usedHeap();
        long peak = 0, n = 0;
        try (BufferedReader r = Files.newBufferedReader(csv)) {
            while (r.readLine() != null)
                if (++n % 50_000 == 0) peak = Math.max(peak, usedHeap() - base);    // sample while streaming
        }
        System.out.printf("  BufferedReader : %,d lines, peak about %.0f MB above baseline (flat: one line at a time)%n", n, Math.max(0, peak) / 1e6);
        System.out.println("  Raise ROWS: the first number grows with the file, the second does not. (Approximate: GC timing.)");
        System.out.println("  Files.lines(path) is the same, lazily, as a Stream - close it (try-with-resources).");

        section("2. Streaming aggregation: GROUP BY in one pass");
        Map<String, Long> totals = aggregate(csv, 0, Files.size(csv));
        System.out.println("  revenue by region (cents): " + new TreeMap<>(totals));
        System.out.println("  Memory is O(distinct keys) = " + totals.size() + ", not O(rows). A high-cardinality key");
        System.out.println("  needs partitioning by hash(key) into files first, then one pass per partition.");

        section("3. Batched writes: one round trip per batch, not per row");
        int perRow = 0, batched = 0, batch = 0;
        try (BufferedReader r = Files.newBufferedReader(csv)) {
            r.readLine();
            while (r.readLine() != null) { perRow++; if (++batch == 1_000) { batched++; batch = 0; } }
            if (batch > 0) batched++;
        }
        System.out.printf("  insert per row : %,d round trips%n  batch of 1,000 : %,d round trips (JDBC addBatch/executeBatch, rewriteBatchedStatements)%n", perRow, batched);

        section("4. Parallel by byte ranges (the 100 GB fan-out)");
        long size = Files.size(csv);
        int workers = 4;
        ExecutorService pool = Executors.newFixedThreadPool(workers);
        List<Future<Map<String, Long>>> parts = new ArrayList<>();
        for (int i = 0; i < workers; i++) {
            long start = size * i / workers, end = size * (i + 1) / workers;
            parts.add(pool.submit(() -> aggregate(csv, start, end)));
        }
        Map<String, Long> merged = new TreeMap<>();
        for (Future<Map<String, Long>> f : parts) f.get().forEach((k, v) -> merged.merge(k, v, Long::sum));
        pool.shutdown();
        System.out.println("  " + workers + " workers, each owns the lines that START in its byte range");
        System.out.println("  same totals as one pass: " + merged.equals(new TreeMap<>(totals)));
        System.out.println("  On S3: one ranged GET (Range: bytes=start-end) per worker - Lambda fan-out, Spark, or ECS tasks.");

        section("5. Checkpoint and resume: a crash at 60% must not cost 60%");
        long crashAt = ROWS * 6L / 10, checkpointEvery = 50_000, checkpoint = 0, processed = 0;
        try (BufferedReader r = Files.newBufferedReader(csv)) {
            r.readLine();
            while (r.readLine() != null) {
                processed++;
                if (processed % checkpointEvery == 0) checkpoint = processed;        // persist offset + partial totals
                if (processed == crashAt) break;                                       // the process dies here
            }
        }
        System.out.printf("  crashed after %,d rows; last checkpoint at %,d. The restart reads %,d rows, not %,d,%n",
                processed, checkpoint, ROWS - checkpoint, ROWS);
        System.out.printf("  and rows %,d-%,d are processed a second time.%n", checkpoint + 1, processed);
        System.out.println("  Writes must be idempotent (upsert by order_id) because rows after the checkpoint run twice.");

        section("6. Compressed input");
        System.out.println("  .gz streams fine (GZIPInputStream) but is NOT splittable: one worker per file. For");
        System.out.println("  parallel reads store splittable chunks (many .gz parts, or Parquet/ORC with row groups).");

        section("7. AWS Lambda handler patterns");
        Handler h = new Handler();
        h.handle(new Event("req-1", 120), 900_000);
        h.handle(new Event("req-2", 80), 900_000);
        h.handle(new Event("req-1", 120), 900_000);                    // the same event redelivered
        System.out.println("  3 invocations on a warm container: " + Handler.CONNECTS + " connection opened, "
                + h.processed + " events processed, 1 duplicate skipped");
        h.handle(new Event("req-3", 50), 2_000);
        System.out.println("  rules: init clients in static fields (reused while warm); make the handler idempotent");
        System.out.println("  (at-least-once delivery); check remaining time and stop cleanly before the deadline.");
        System.out.println("  limits: 15 min, 10 GB memory, 10 GB /tmp, 6 MB sync payload. Cold starts: SnapStart");
        System.out.println("  for Java, keep the jar small, avoid heavy reflection at startup.");
        System.out.println("  100 GB is NOT one Lambda: fan out by byte range (Step Functions Map), or use Batch/EMR.");
    }

    static long usedHeap() {
        Runtime rt = Runtime.getRuntime();
        System.gc();
        return rt.totalMemory() - rt.freeMemory();
    }

    /** Aggregates the lines that START inside [start, end): a line crossing the boundary belongs to the earlier range. */
    static Map<String, Long> aggregate(Path csv, long start, long end) throws IOException {
        Map<String, Long> out = new HashMap<>();
        try (RandomAccessFile f = new RandomAccessFile(csv.toFile(), "r")) {
            long pos = start;
            f.seek(pos);
            if (pos > 0) {                                             // skip the partial line owned by the previous range
                f.seek(pos - 1);
                if (f.read() != '\n') { f.readLine(); }
                pos = f.getFilePointer();
            }
            BufferedReader r = new BufferedReader(new InputStreamReader(new FileInputStream(f.getFD()), StandardCharsets.UTF_8));
            String line;
            while (pos < end && (line = r.readLine()) != null) {
                pos += line.length() + 1;                              // ASCII file, '\n' endings
                if (line.startsWith("order_id")) continue;
                String[] c = line.split(",");
                out.merge(c[1], Long.parseLong(c[2]), Long::sum);
            }
        }
        return out;
    }

    record Event(String requestId, long amountCents) { }

    static class Handler {
        static int CONNECTS = 0;
        static final Object DB = connect();                            // runs once per container, not per call
        final Set<String> seen = new HashSet<>();                      // real code: a DynamoDB conditional put
        int processed = 0;

        static Object connect() { CONNECTS++; return new Object(); }

        void handle(Event e, long remainingMillis) {
            if (remainingMillis < 5_000) {
                System.out.println("  req " + e.requestId() + ": only " + remainingMillis + " ms left -> stop, return the cursor, let a retry finish");
                return;
            }
            if (!seen.add(e.requestId())) return;                      // idempotency key
            processed++;
        }
    }
}

// EXERCISE: make section 5 real - write the checkpoint (offset + partial totals) to a file every 50,000
// rows, kill the run, and resume from the file. Prove the final totals equal the one-pass totals.
