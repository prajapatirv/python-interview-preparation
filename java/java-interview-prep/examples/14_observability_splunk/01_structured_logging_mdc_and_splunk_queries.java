/*
 * 01 - Structured logging, correlation IDs (MDC) and the Splunk SPL you would run on them
 *
 * Run:  java 01_structured_logging_mdc_and_splunk_queries.java
 *
 * Part 1 builds JSON log events with a correlation id carried in a ThreadLocal (what SLF4J MDC is),
 * shows the classic bug (the id is lost when work hops to another thread) and the fix.
 * Part 2 loads those events and evaluates, in Java, what the SPL commands would return
 * (stats count by, timechart, percentiles) so you can see the logic behind each query.
 */
import java.util.*;
import java.util.concurrent.*;
import java.util.stream.*;

class StructuredLoggingMdcAndSplunkQueries {

    // ---- a minimal MDC and JSON logger
    static final ThreadLocal<Map<String, String>> MDC = ThreadLocal.withInitial(HashMap::new);
    static final List<Map<String, Object>> SINK = Collections.synchronizedList(new ArrayList<>());   // "stdout -> forwarder -> Splunk"

    static void log(String service, String level, String msg, Object... kv) {
        Map<String, Object> e = new LinkedHashMap<>();
        e.put("level", level);
        e.put("service", service);
        e.put("correlationId", MDC.get().getOrDefault("correlationId", "-"));
        e.put("message", msg);
        for (int i = 0; i < kv.length; i += 2) e.put((String) kv[i], kv[i + 1]);
        SINK.add(e);
    }

    static String toJson(Map<String, Object> e) {
        return e.entrySet().stream()
                .map(en -> "\"" + en.getKey() + "\":" + (en.getValue() instanceof Number ? en.getValue() : "\"" + en.getValue() + "\""))
                .collect(Collectors.joining(",", "{", "}"));
    }

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    public static void main(String[] args) throws Exception {

        section("1. One structured JSON line per event");
        MDC.get().put("correlationId", "req-7f3a");
        log("order-service", "INFO", "order accepted", "orderId", 1001, "duration_ms", 42, "endpoint", "POST /orders");
        System.out.println("  " + toJson(SINK.get(0)));
        System.out.println("  Fields > prose: Splunk extracts JSON automatically, so 'duration_ms' becomes numeric and aggregatable.");

        section("2. MDC is thread-local: the id is LOST on a different thread");
        ExecutorService pool = Executors.newFixedThreadPool(2);
        pool.submit(() -> log("order-service", "INFO", "async step, id NOT propagated")).get();
        System.out.println("  async event correlationId = " + SINK.get(SINK.size() - 1).get("correlationId") + "   <- cannot be joined to the request in Splunk");

        // Fix: capture the context and restore it inside the task (Spring: TaskDecorator; Micrometer context-propagation).
        Map<String, String> captured = new HashMap<>(MDC.get());
        pool.submit(() -> {
            MDC.get().putAll(captured);
            try { log("order-service", "INFO", "async step, id propagated"); }
            finally { MDC.get().clear(); }                             // ALWAYS clear: pooled threads are reused
        }).get();
        pool.shutdown();
        System.out.println("  fixed event correlationId  = " + SINK.get(SINK.size() - 1).get("correlationId"));
        System.out.println("  Across services: send X-Correlation-Id / W3C traceparent in HTTP headers and Kafka record headers.");
        MDC.get().clear();

        section("3. Simulate an hour of traffic from two services");
        Random r = new Random(11);
        String[] endpoints = {"GET /orders", "POST /orders", "GET /orders/{id}", "POST /payments"};
        for (int minute = 0; minute < 60; minute++) {
            boolean incident = minute >= 40 && minute < 50;                // payment provider degraded for 10 minutes
            for (int i = 0; i < 20; i++) {
                String ep = endpoints[r.nextInt(endpoints.length)];
                boolean pay = ep.contains("payments");
                int dur = (int) (20 + r.nextInt(60) + (pay && incident ? 1_500 + r.nextInt(1_500) : 0) + (r.nextInt(100) == 0 ? 800 : 0));
                boolean err = pay && incident && r.nextInt(100) < 55;
                MDC.get().put("correlationId", "c-" + minute + "-" + i);
                log(pay ? "payment-service" : "order-service", err ? "ERROR" : "INFO", err ? "provider timeout" : "handled",
                        "endpoint", ep, "duration_ms", dur, "minute", minute, "version", minute < 45 ? "1.4.0" : "1.4.1", "exception", err ? "ProviderTimeoutException" : "");
            }
        }
        MDC.get().clear();
        System.out.println("  events indexed: " + SINK.size());

        section("4. SPL: index=app level=ERROR | stats count by service, exception | sort - count");
        SINK.stream().filter(e -> "ERROR".equals(e.get("level")))
                .collect(Collectors.groupingBy(e -> e.get("service") + " / " + e.get("exception"), Collectors.counting()))
                .entrySet().stream().sorted(Map.Entry.<String, Long>comparingByValue().reversed())
                .forEach(en -> System.out.println("  " + en.getKey() + " = " + en.getValue()));

        section("5. SPL: ... level=ERROR | timechart span=10m count   (when did it start?)");
        Map<Integer, Long> buckets = SINK.stream().filter(e -> "ERROR".equals(e.get("level")))
                .collect(Collectors.groupingBy(e -> ((Integer) e.get("minute")) / 10 * 10, TreeMap::new, Collectors.counting()));
        for (int b = 0; b < 60; b += 10) System.out.printf("  minute %2d-%2d : %3d %s%n", b, b + 9, buckets.getOrDefault(b, 0L), "#".repeat((int) (buckets.getOrDefault(b, 0L) / 4)));

        section("6. SPL: ... | stats count avg(duration_ms) p95(duration_ms) by endpoint | sort - p95");
        Map<String, List<Integer>> byEndpoint = SINK.stream().filter(e -> e.containsKey("duration_ms"))
                .collect(Collectors.groupingBy(e -> (String) e.get("endpoint"), TreeMap::new, Collectors.mapping(e -> (Integer) e.get("duration_ms"), Collectors.toList())));
        System.out.printf("  %-18s %6s %8s %8s %8s%n", "endpoint", "count", "avg", "p95", "p99");
        byEndpoint.entrySet().stream()
                .sorted((a, b) -> Integer.compare(pct(b.getValue(), 95), pct(a.getValue(), 95)))
                .forEach(en -> System.out.printf("  %-18s %6d %8.0f %8d %8d%n", en.getKey(), en.getValue().size(),
                        en.getValue().stream().mapToInt(i -> i).average().orElse(0), pct(en.getValue(), 95), pct(en.getValue(), 99)));
        System.out.println("  Averages hide tail latency: always show p95/p99, and compare against the previous period.");

        section("7. SPL: trace one request   index=app correlationId=\"c-42-3\" | sort _time");
        SINK.stream().filter(e -> "c-42-3".equals(e.get("correlationId"))).forEach(e -> System.out.println("  " + toJson(e)));

        section("8. SPL: which version introduced the errors?  | stats count by version");
        SINK.stream().filter(e -> "ERROR".equals(e.get("level")))
                .collect(Collectors.groupingBy(e -> (String) e.get("version"), TreeMap::new, Collectors.counting()))
                .forEach((v, c) -> System.out.println("  version " + v + " : " + c + " errors"));
        System.out.println("  Errors in 1.4.0 AND 1.4.1 and tied to a time window => external dependency, not the deploy.");

        section("9. Good-log checklist");
        System.out.println("  timestamp, level, service, env, version, correlationId/traceId, operation, duration_ms, outcome, error code");
        System.out.println("  never: secrets, tokens, full card/PII, entire request bodies, the same stack trace at every layer");
        System.out.println("  one log per outcome (not per step); sample DEBUG; keep cardinality of metric labels low (not userId)");
    }

    static int pct(List<Integer> v, int p) {
        List<Integer> s = new ArrayList<>(v);
        Collections.sort(s);
        return s.get(Math.max(0, (int) Math.ceil(p / 100.0 * s.size()) - 1));
    }
}

// EXERCISE: write the SPL (and the Java equivalent) for "error RATE per service per 5 minutes".
