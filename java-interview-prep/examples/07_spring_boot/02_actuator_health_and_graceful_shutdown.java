/*
 * 02 - Actuator-style health groups and graceful shutdown (runs a real HTTP server)
 *
 * Run:  java 02_actuator_health_and_graceful_shutdown.java
 *
 * Models what Kubernetes needs from a Spring Boot service:
 *   /health/liveness   -> "restart me if this fails"   (must NOT depend on downstreams)
 *   /health/readiness  -> "send me traffic?"           (may depend on DB/Kafka)
 * and a graceful shutdown: flip readiness, drain in-flight requests, then stop.
 */
import com.sun.net.httpserver.*;
import java.io.*;
import java.net.*;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;

class ActuatorHealthAndGracefulShutdown {

    static final AtomicBoolean acceptingTraffic = new AtomicBoolean(true);   // readiness state
    static final AtomicBoolean dbUp = new AtomicBoolean(true);
    static final AtomicInteger inFlight = new AtomicInteger();

    interface HealthIndicator { String name(); boolean up(); }

    static String json(boolean up, Map<String, Boolean> parts) {
        StringBuilder sb = new StringBuilder("{\"status\":\"" + (up ? "UP" : "DOWN") + "\",\"components\":{");
        int i = 0;
        for (Map.Entry<String, Boolean> e : parts.entrySet())
            sb.append(i++ > 0 ? "," : "").append("\"").append(e.getKey()).append("\":{\"status\":\"").append(e.getValue() ? "UP" : "DOWN").append("\"}");
        return sb.append("}}").toString();
    }

    static void respond(HttpExchange ex, int code, String body) throws IOException {
        byte[] b = body.getBytes(StandardCharsets.UTF_8);
        ex.getResponseHeaders().add("Content-Type", "application/json");
        ex.sendResponseHeaders(code, b.length);
        try (OutputStream os = ex.getResponseBody()) { os.write(b); }
    }

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    static String call(HttpClient c, String url) throws Exception {
        try {
            HttpResponse<String> r = c.send(HttpRequest.newBuilder(URI.create(url)).timeout(java.time.Duration.ofSeconds(3)).build(),
                    HttpResponse.BodyHandlers.ofString());
            return r.statusCode() + " " + r.body();
        } catch (ConnectException e) {
            return "connection refused (server stopped)";
        }
    }

    public static void main(String[] args) throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        ExecutorService workers = Executors.newFixedThreadPool(4);
        server.setExecutor(workers);

        server.createContext("/actuator/health/liveness", ex -> respond(ex, 200, json(true, new LinkedHashMap<>())));   // process is alive; nothing else
        server.createContext("/actuator/health/readiness", ex -> {
            Map<String, Boolean> parts = new LinkedHashMap<>();
            parts.put("readinessState", acceptingTraffic.get());
            parts.put("db", dbUp.get());
            boolean up = parts.values().stream().allMatch(b -> b);
            respond(ex, up ? 200 : 503, json(up, parts));
        });
        server.createContext("/orders", ex -> {
            inFlight.incrementAndGet();
            try {
                try { Thread.sleep(400); } catch (InterruptedException ignored) { }     // slow request
                respond(ex, 200, "{\"ok\":true}");
            } finally { inFlight.decrementAndGet(); }
        });
        server.start();
        String base = "http://127.0.0.1:" + server.getAddress().getPort();
        HttpClient client = HttpClient.newHttpClient();

        section("1. Liveness vs readiness");
        System.out.println("  liveness  -> " + call(client, base + "/actuator/health/liveness"));
        System.out.println("  readiness -> " + call(client, base + "/actuator/health/readiness"));
        dbUp.set(false);
        System.out.println("  after the DB goes down:");
        System.out.println("  liveness  -> " + call(client, base + "/actuator/health/liveness") + "   <- still UP: do NOT restart pods because a DB is down");
        System.out.println("  readiness -> " + call(client, base + "/actuator/health/readiness") + "   <- 503: remove from load balancer, no restart");
        dbUp.set(true);

        section("2. Graceful shutdown while a request is in flight");
        CompletableFuture<String> slow = CompletableFuture.supplyAsync(() -> {
            try { return call(client, base + "/orders"); } catch (Exception e) { return "error " + e; }
        });
        Thread.sleep(100);                                                   // the request is now being processed
        System.out.println("  in-flight requests before SIGTERM: " + inFlight.get());
        // What Spring does on SIGTERM with server.shutdown=graceful:
        acceptingTraffic.set(false);                                          // 1. readiness -> REFUSING_TRAFFIC
        System.out.println("  readiness after SIGTERM -> " + call(client, base + "/actuator/health/readiness"));
        long t0 = System.currentTimeMillis();
        while (inFlight.get() > 0 && System.currentTimeMillis() - t0 < 5_000) Thread.sleep(20);   // 2. drain (timeout-per-shutdown-phase)
        System.out.println("  drained after ~" + ((System.currentTimeMillis() - t0) / 100 * 100) + " ms, in flight now: " + inFlight.get());
        server.stop(0);                                                       // 3. stop accepting, then destroy beans
        workers.shutdown();
        System.out.println("  the slow request still completed: " + slow.get());
        System.out.println("  after stop: " + call(client, base + "/actuator/health/liveness"));

        section("3. Kubernetes settings that make this work");
        System.out.println("  server.shutdown=graceful");
        System.out.println("  spring.lifecycle.timeout-per-shutdown-phase=30s");
        System.out.println("  terminationGracePeriodSeconds: 45     (> the drain timeout)");
        System.out.println("  preStop: sleep 5                      (let the load balancer / endpoints update first)");
        System.out.println("  management.endpoint.health.probes.enabled=true  (liveness & readiness groups)");
        System.out.println("  Secure the rest of /actuator: expose only health,info,prometheus; separate management port.");
    }
}

// EXERCISE: add a startup probe state so readiness stays DOWN until a cache warm-up finishes.
