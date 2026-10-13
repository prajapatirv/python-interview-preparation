/*
 * 01 - A real REST API (JDK HttpServer) showing the behaviours interviewers probe
 *
 * Run:  java 01_rest_api_status_codes_etag_idempotency.java
 *
 * Covers: 201 + Location, 400 vs 404 vs 409 vs 412, problem+json errors, validation,
 * ETag / If-None-Match (304), If-Match (optimistic concurrency), Idempotency-Key replay,
 * idempotent PUT/DELETE, 405 with Allow, and pagination.
 * The server and the client run in one process, so the output reads like a curl session.
 */
import com.sun.net.httpserver.*;
import java.io.*;
import java.net.*;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
import java.util.regex.*;

class RestApiStatusCodesEtagIdempotency {

    // ---- the "domain"
    static final class Order { final int id; String customer; int amount; int version = 1;
        Order(int id, String customer, int amount) { this.id = id; this.customer = customer; this.amount = amount; }
        String etag() { return "\"" + id + "-" + version + "\""; }
        String json() { return "{\"id\":" + id + ",\"customer\":\"" + customer + "\",\"amount\":" + amount + ",\"version\":" + version + "}"; } }

    static final Map<Integer, Order> DB = new ConcurrentHashMap<>();
    static final AtomicInteger SEQ = new AtomicInteger(100);
    static final Map<String, String[]> IDEMPOTENT = new ConcurrentHashMap<>();   // key -> {status, location, body}

    static final Pattern CUSTOMER = Pattern.compile("\"customer\"\\s*:\\s*\"([^\"]*)\"");
    static final Pattern AMOUNT = Pattern.compile("\"amount\"\\s*:\\s*(-?\\d+)");

    static void send(HttpExchange ex, int code, String body, String... headers) throws IOException {
        byte[] b = body.getBytes(StandardCharsets.UTF_8);
        for (int i = 0; i < headers.length; i += 2) ex.getResponseHeaders().add(headers[i], headers[i + 1]);
        if (!ex.getResponseHeaders().containsKey("Content-Type"))
            ex.getResponseHeaders().add("Content-Type", code >= 400 ? "application/problem+json" : "application/json");
        if (code == 304 || code == 204) { ex.sendResponseHeaders(code, -1); ex.close(); return; }
        ex.sendResponseHeaders(code, b.length);
        try (OutputStream os = ex.getResponseBody()) { os.write(b); }
    }

    static String problem(int status, String title, String detail) {          // RFC 7807 / 9457
        return "{\"type\":\"https://api.example.com/problems/" + title.toLowerCase().replace(' ', '-') + "\",\"title\":\"" + title
                + "\",\"status\":" + status + ",\"detail\":\"" + detail + "\"}";
    }

    static void handle(HttpExchange ex) throws IOException {
        String method = ex.getRequestMethod(), path = ex.getRequestURI().getPath(), q = ex.getRequestURI().getQuery();
        String body = new String(ex.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
        String[] seg = path.split("/");                                       // ["", "orders", "{id}"]
        Integer id = null;
        if (seg.length == 3) {
            try { id = Integer.parseInt(seg[2]); }
            catch (NumberFormatException e) { send(ex, 400, problem(400, "Bad Request", "id must be a number")); return; }
        }

        if (seg.length == 2) {                                                // collection: /orders
            if (method.equals("POST")) {
                String key = ex.getRequestHeaders().getFirst("Idempotency-Key");
                if (key != null && IDEMPOTENT.containsKey(key)) {              // replay: same answer, no second order
                    String[] saved = IDEMPOTENT.get(key);
                    send(ex, Integer.parseInt(saved[0]), saved[2], "Location", saved[1], "Idempotent-Replay", "true");
                    return;
                }
                Matcher c = CUSTOMER.matcher(body), a = AMOUNT.matcher(body);
                if (!c.find() || !a.find()) { send(ex, 400, problem(400, "Bad Request", "customer and amount are required")); return; }
                int amount = Integer.parseInt(a.group(1));
                if (amount <= 0) { send(ex, 422, problem(422, "Validation Failed", "amount must be positive")); return; }
                Order o = new Order(SEQ.incrementAndGet(), c.group(1), amount);
                DB.put(o.id, o);
                String loc = "/orders/" + o.id;
                if (key != null) IDEMPOTENT.put(key, new String[]{"201", loc, o.json()});
                send(ex, 201, o.json(), "Location", loc, "ETag", o.etag());
            } else if (method.equals("GET")) {
                int page = 0, size = 2;
                if (q != null) for (String p : q.split("&")) {
                    if (p.startsWith("page=")) page = Integer.parseInt(p.substring(5));
                    if (p.startsWith("size=")) size = Math.min(50, Integer.parseInt(p.substring(5)));   // cap page size
                }
                List<Order> all = new ArrayList<>(DB.values());
                all.sort(Comparator.comparingInt(o -> o.id));
                int from = Math.min(all.size(), page * size), to = Math.min(all.size(), from + size);
                StringBuilder sb = new StringBuilder("{\"content\":[");
                for (int i = from; i < to; i++) sb.append(i > from ? "," : "").append(all.get(i).json());
                sb.append("],\"page\":").append(page).append(",\"size\":").append(size).append(",\"total\":").append(all.size()).append("}");
                send(ex, 200, sb.toString());
            } else {
                send(ex, 405, problem(405, "Method Not Allowed", method + " not supported"), "Allow", "GET, POST");
            }
            return;
        }

        if (seg.length == 3 && id != null) {                                  // item: /orders/{id}
            Order o = DB.get(id);
            switch (method) {
                case "GET":
                    if (o == null) { send(ex, 404, problem(404, "Not Found", "order " + id + " does not exist")); return; }
                    if (o.etag().equals(ex.getRequestHeaders().getFirst("If-None-Match"))) { send(ex, 304, "", "ETag", o.etag()); return; }
                    send(ex, 200, o.json(), "ETag", o.etag(), "Cache-Control", "max-age=0, must-revalidate");
                    return;
                case "PUT":
                    if (o == null) { send(ex, 404, problem(404, "Not Found", "order " + id + " does not exist")); return; }
                    String ifMatch = ex.getRequestHeaders().getFirst("If-Match");
                    if (ifMatch == null) { send(ex, 428, problem(428, "Precondition Required", "send If-Match with the ETag you read")); return; }
                    synchronized (o) {
                        if (!o.etag().equals(ifMatch)) { send(ex, 412, problem(412, "Precondition Failed", "order changed; re-read and retry"), "ETag", o.etag()); return; }
                        Matcher a = AMOUNT.matcher(body);
                        if (a.find()) o.amount = Integer.parseInt(a.group(1));
                        o.version++;
                        send(ex, 200, o.json(), "ETag", o.etag());
                    }
                    return;
                case "DELETE":
                    DB.remove(id);
                    send(ex, 204, "");                                         // idempotent: 204 even if it was already gone
                    return;
                default:
                    send(ex, 405, problem(405, "Method Not Allowed", method + " not supported"), "Allow", "GET, PUT, DELETE");
                    return;
            }
        }
        send(ex, 404, problem(404, "Not Found", "no such resource"));
    }

    // ---- the "client" side: a tiny curl-like helper
    static HttpClient http = HttpClient.newHttpClient();
    static String base;

    static HttpResponse<String> req(String method, String path, String body, String... headers) throws Exception {
        HttpRequest.Builder b = HttpRequest.newBuilder(URI.create(base + path));
        for (int i = 0; i < headers.length; i += 2) b.header(headers[i], headers[i + 1]);
        b.method(method, body == null ? HttpRequest.BodyPublishers.noBody() : HttpRequest.BodyPublishers.ofString(body));
        return http.send(b.build(), HttpResponse.BodyHandlers.ofString());
    }

    static void show(String label, HttpResponse<String> r, String... headerNames) {
        StringBuilder h = new StringBuilder();
        for (String n : headerNames) r.headers().firstValue(n).ifPresent(v -> h.append(" ").append(n).append("=").append(v));
        String b = r.body().length() > 110 ? r.body().substring(0, 107) + "..." : r.body();
        System.out.printf("  %-34s -> %d%s %s%n", label, r.statusCode(), h, b);
    }

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    public static void main(String[] args) throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/", ex -> {
            try { handle(ex); }
            catch (Exception e) { send(ex, 500, problem(500, "Internal Server Error", "unexpected error")); }
        });
        server.setExecutor(Executors.newFixedThreadPool(4));
        server.start();
        base = "http://127.0.0.1:" + server.getAddress().getPort();
        try {
            section("1. Create: POST -> 201 Created + Location + ETag");
            HttpResponse<String> created = req("POST", "/orders", "{\"customer\":\"alice\",\"amount\":250}", "Content-Type", "application/json");
            show("POST /orders", created, "Location", "ETag");
            String loc = created.headers().firstValue("Location").get();
            req("POST", "/orders", "{\"customer\":\"bob\",\"amount\":90}");
            req("POST", "/orders", "{\"customer\":\"carol\",\"amount\":15}");

            section("2. Client errors: 400 vs 422 vs 404");
            show("POST malformed body", req("POST", "/orders", "{oops}"));
            show("POST amount = -5", req("POST", "/orders", "{\"customer\":\"x\",\"amount\":-5}"));
            show("GET /orders/abc", req("GET", "/orders/abc", null));
            show("GET /orders/999", req("GET", "/orders/999", null));

            section("3. Conditional GET: ETag -> 304 saves the body");
            HttpResponse<String> first = req("GET", loc, null);
            show("GET " + loc, first, "ETag", "Cache-Control");
            show("GET " + loc + " If-None-Match", req("GET", loc, null, "If-None-Match", first.headers().firstValue("ETag").get()), "ETag");

            section("4. Optimistic concurrency: If-Match / 412 / 428");
            String etag = first.headers().firstValue("ETag").get();
            show("PUT without If-Match", req("PUT", loc, "{\"amount\":300}"));
            show("PUT If-Match (current)", req("PUT", loc, "{\"amount\":300}", "If-Match", etag), "ETag");
            show("PUT If-Match (stale) -> lost update blocked", req("PUT", loc, "{\"amount\":999}", "If-Match", etag), "ETag");

            section("5. Idempotency-Key: a retried POST must not create a second order");
            HttpResponse<String> p1 = req("POST", "/orders", "{\"customer\":\"dave\",\"amount\":10}", "Idempotency-Key", "abc-123");
            HttpResponse<String> p2 = req("POST", "/orders", "{\"customer\":\"dave\",\"amount\":10}", "Idempotency-Key", "abc-123");
            show("POST (first)", p1, "Location");
            show("POST (retry, same key)", p2, "Location", "Idempotent-Replay");
            System.out.println("  same Location both times: " + p1.headers().firstValue("Location").equals(p2.headers().firstValue("Location")));

            section("6. Pagination (bounded page size) and method not allowed");
            show("GET /orders?page=0&size=2", req("GET", "/orders?page=0&size=2", null));
            show("GET /orders?page=1&size=2", req("GET", "/orders?page=1&size=2", null));
            show("PATCH /orders", req("PATCH", "/orders", "{}"), "Allow");

            section("7. DELETE is idempotent");
            show("DELETE " + loc, req("DELETE", loc, null));
            show("DELETE " + loc + " (again)", req("DELETE", loc, null));
            show("GET " + loc, req("GET", loc, null));
        } finally {
            server.stop(0);
            ((ExecutorService) server.getExecutor()).shutdown();
        }
    }
}

// EXERCISE: add cursor pagination (?after=<lastId>) and explain why offset pagination gets slow
// and inconsistent on a large, changing table.
