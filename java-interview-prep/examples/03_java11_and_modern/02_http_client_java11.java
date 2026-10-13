/*
 * 02 - java.net.http.HttpClient (Java 11) against an embedded server
 *
 * Run:  java 02_http_client_java11.java
 *
 * Starts a tiny com.sun.net.httpserver endpoint on a random port, then calls it with the
 * Java 11 HttpClient: sync, async, timeouts, headers, POST body. No external network needed.
 */
import com.sun.net.httpserver.HttpServer;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.URI;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;

class HttpClientJava11 {

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    public static void main(String[] args) throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/hello", ex -> {
            byte[] body = ("hello from " + ex.getRequestMethod() + " ua=" + ex.getRequestHeaders().getFirst("X-Client")).getBytes(StandardCharsets.UTF_8);
            ex.getResponseHeaders().add("Content-Type", "text/plain");
            ex.sendResponseHeaders(200, body.length);
            try (OutputStream os = ex.getResponseBody()) { os.write(body); }
        });
        server.createContext("/slow", ex -> {
            try { Thread.sleep(1_000); } catch (InterruptedException ignored) { }
            ex.sendResponseHeaders(200, -1);
            ex.close();
        });
        server.createContext("/echo", ex -> {
            byte[] in = ex.getRequestBody().readAllBytes();
            ex.sendResponseHeaders(201, in.length);
            try (OutputStream os = ex.getResponseBody()) { os.write(in); }
        });
        server.start();
        String base = "http://127.0.0.1:" + server.getAddress().getPort();

        // One client for the whole app: it owns a connection pool and (optionally) HTTP/2.
        HttpClient client = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)
                .connectTimeout(Duration.ofSeconds(2))
                .build();
        try {
            section("1. Synchronous GET");
            HttpRequest get = HttpRequest.newBuilder(URI.create(base + "/hello"))
                    .header("X-Client", "java11").timeout(Duration.ofSeconds(2)).GET().build();
            HttpResponse<String> r = client.send(get, HttpResponse.BodyHandlers.ofString());
            System.out.println("  status=" + r.statusCode() + " body='" + r.body() + "' content-type=" + r.headers().firstValue("content-type").orElse("?"));

            section("2. POST with a body");
            HttpRequest post = HttpRequest.newBuilder(URI.create(base + "/echo"))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString("{\"order\":42}")).build();
            HttpResponse<String> pr = client.send(post, HttpResponse.BodyHandlers.ofString());
            System.out.println("  status=" + pr.statusCode() + " echoed=" + pr.body());

            section("3. Asynchronous: sendAsync returns a CompletableFuture");
            List<CompletableFuture<String>> calls = new ArrayList<>();
            for (int i = 0; i < 3; i++) {
                calls.add(client.sendAsync(get, HttpResponse.BodyHandlers.ofString()).thenApply(HttpResponse::body));
            }
            CompletableFuture.allOf(calls.toArray(new CompletableFuture[0])).join();
            System.out.println("  3 parallel calls -> " + calls.get(0).join());

            section("4. Per-request timeout");
            HttpRequest slow = HttpRequest.newBuilder(URI.create(base + "/slow")).timeout(Duration.ofMillis(200)).build();
            try { client.send(slow, HttpResponse.BodyHandlers.discarding()); }
            catch (HttpTimeoutException e) { System.out.println("  HttpTimeoutException: " + e.getMessage()); }
            System.out.println("  Always set BOTH connectTimeout (client) and request timeout; default is infinite.");
        } finally {
            server.stop(0);
        }

        section("5. Compared with the older options");
        System.out.println("  HttpURLConnection : legacy, blocking, awkward API");
        System.out.println("  Apache HttpClient / OkHttp: still common, richer pooling/interceptors");
        System.out.println("  Spring RestTemplate (maintenance) -> RestClient (6.1+) / WebClient; all can sit on top of JDK HttpClient");
    }
}

// EXERCISE: add a retry interceptor-like wrapper that retries idempotent GETs on 503 with backoff.
