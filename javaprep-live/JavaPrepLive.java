/*
 * JavaPrepLive - run the Java interview-prep examples from a browser, read the deep dives,
 * and drill the Q&A. One file, JDK 21 only (no Maven, no Gradle, no dependencies).
 *
 *   java JavaPrepLive.java                 start on http://127.0.0.1:8090
 *   java JavaPrepLive.java --port 9000     choose a port
 *   java JavaPrepLive.java --check         run every example headless and print ok/FAIL (exit 1 on failure)
 *
 * Env: JAVAPREP_ROOT (path to java-interview-prep), PORT, JAVAPREP_TIMEOUT (seconds per run, default 60)
 *
 * Security model: binds to 127.0.0.1 only; only *.java files under examples/ can be executed and
 * only whitelisted markdown files can be read; no request data ever reaches a shell.
 */
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.*;
import java.net.InetSocketAddress;
import java.net.URI;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.regex.*;
import java.util.stream.*;

class JavaPrepLive {

    // ------------------------------------------------------------------ configuration
    static Path root;            // .../java-interview-prep
    static Path appDir;          // directory containing static/index.html
    static int timeoutSeconds = 60;
    static final int MAX_LINES = 5_000;
    static final Semaphore RUN_SLOTS = new Semaphore(4);

    static final Pattern Q_RE = Pattern.compile("^###\\s+Q(\\d+)\\s+\\[(basic|intermediate|advanced|design)\\]\\s+(.*)$", Pattern.CASE_INSENSITIVE);
    static final Pattern GUIDE_SECTION_RE = Pattern.compile("^#\\s+(\\d+)\\.\\s+(.*)$");
    static final Pattern GUIDE_Q_RE = Pattern.compile("^##\\s+Q(\\d+)\\.\\s+(.*)$");
    static final Pattern SECTION_CALL_RE = Pattern.compile("\\bsection\\(\"([^\"]+)\"\\)");
    static final Pattern HEADER_TITLE_RE = Pattern.compile("^\\s*\\*\\s+(\\d+)\\s+-\\s+(.*)$");

    public static void main(String[] args) throws Exception {
        int port = Integer.parseInt(System.getenv().getOrDefault("PORT", "8090"));
        boolean check = false;
        for (int i = 0; i < args.length; i++) {
            if (args[i].equals("--port")) port = Integer.parseInt(args[++i]);
            else if (args[i].equals("--check")) check = true;
        }
        timeoutSeconds = Integer.parseInt(System.getenv().getOrDefault("JAVAPREP_TIMEOUT", "60"));
        root = locateRoot();
        appDir = locateAppDir();
        if (check) { System.exit(runCheck()); return; }

        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 0);
        server.setExecutor(Executors.newFixedThreadPool(16));
        server.createContext("/api/catalog", ex -> guard(ex, () -> json(ex, 200, catalogJson())));
        server.createContext("/api/source", ex -> guard(ex, () -> source(ex)));
        server.createContext("/api/doc", ex -> guard(ex, () -> doc(ex)));
        server.createContext("/api/qa", ex -> guard(ex, () -> json(ex, 200, qaJson())));
        server.createContext("/api/run", ex -> guard(ex, () -> run(ex)));
        server.createContext("/api/poll", ex -> guard(ex, () -> poll(ex)));
        server.createContext("/api/stop", ex -> guard(ex, () -> stop(ex)));
        server.createContext("/", ex -> guard(ex, () -> staticFile(ex)));
        server.start();
        System.out.println("JavaPrepLive  http://127.0.0.1:" + port);
        System.out.println("  content root : " + root);
        System.out.println("  java         : " + javaBinary() + "  (" + Runtime.version() + ")");
        System.out.println("  stop with Ctrl+C");
    }

    static Path locateRoot() {
        String env = System.getenv("JAVAPREP_ROOT");
        List<Path> candidates = new ArrayList<>();
        if (env != null && !env.isBlank()) candidates.add(Paths.get(env));
        Path cwd = Paths.get("").toAbsolutePath();
        candidates.add(cwd.resolve("../java-interview-prep"));
        candidates.add(cwd.resolve("java-interview-prep"));
        candidates.add(cwd);
        for (Path c : candidates) if (Files.isDirectory(c.resolve("examples"))) return c.normalize().toAbsolutePath();
        throw new IllegalStateException("java-interview-prep/examples not found; set JAVAPREP_ROOT");
    }

    static Path locateAppDir() {
        Path cwd = Paths.get("").toAbsolutePath();
        for (Path c : new Path[]{cwd, cwd.resolve("javaprep-live")})
            if (Files.isRegularFile(c.resolve("static/index.html"))) return c;
        throw new IllegalStateException("static/index.html not found; run from the javaprep-live folder");
    }

    static String javaBinary() {
        return Paths.get(System.getProperty("java.home"), "bin", System.getProperty("os.name").toLowerCase().contains("win") ? "java.exe" : "java").toString();
    }

    // ------------------------------------------------------------------ http plumbing
    interface Handler { void run() throws Exception; }

    static void guard(HttpExchange ex, Handler h) {
        try { h.run(); }
        catch (SecurityException e) { try { json(ex, 403, "{\"error\":" + q(e.getMessage()) + "}"); } catch (IOException ignored) { } }
        catch (NoSuchFileException e) { try { json(ex, 404, "{\"error\":\"not found\"}"); } catch (IOException ignored) { } }
        catch (Exception e) { try { json(ex, 500, "{\"error\":" + q(String.valueOf(e)) + "}"); } catch (IOException ignored) { } }
        finally { ex.close(); }
    }

    static Map<String, String> params(HttpExchange ex) throws IOException {
        Map<String, String> m = new HashMap<>();
        String raw = ex.getRequestURI().getRawQuery();
        if (raw == null) return m;
        for (String kv : raw.split("&")) {
            int i = kv.indexOf('=');
            if (i > 0) m.put(URLDecoder.decode(kv.substring(0, i), "UTF-8"), URLDecoder.decode(kv.substring(i + 1), "UTF-8"));
        }
        return m;
    }

    static void send(HttpExchange ex, int code, String type, byte[] body) throws IOException {
        ex.getResponseHeaders().set("Content-Type", type);
        ex.getResponseHeaders().set("Cache-Control", "no-store");
        ex.sendResponseHeaders(code, body.length);
        try (OutputStream os = ex.getResponseBody()) { os.write(body); }
    }

    static void json(HttpExchange ex, int code, String body) throws IOException {
        send(ex, code, "application/json; charset=utf-8", body.getBytes(StandardCharsets.UTF_8));
    }

    static void staticFile(HttpExchange ex) throws IOException {
        String path = ex.getRequestURI().getPath();
        if (path.equals("/")) path = "/index.html";
        Path p = appDir.resolve("static").resolve(path.substring(1)).normalize();
        if (!p.startsWith(appDir.resolve("static")) || !Files.isRegularFile(p)) { json(ex, 404, "{\"error\":\"not found\"}"); return; }
        String type = path.endsWith(".html") ? "text/html; charset=utf-8" : path.endsWith(".css") ? "text/css" : path.endsWith(".js") ? "text/javascript" : "application/octet-stream";
        send(ex, 200, type, Files.readAllBytes(p));
    }

    // ------------------------------------------------------------------ JSON helpers
    static String q(String s) {
        StringBuilder sb = new StringBuilder("\"");
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"': sb.append("\\\""); break;
                case '\\': sb.append("\\\\"); break;
                case '\n': sb.append("\\n"); break;
                case '\r': sb.append("\\r"); break;
                case '\t': sb.append("\\t"); break;
                default: if (c < 0x20) sb.append(String.format("\\u%04x", (int) c)); else sb.append(c);
            }
        }
        return sb.append('"').toString();
    }

    static String arr(Collection<String> jsonItems) { return "[" + String.join(",", jsonItems) + "]"; }

    // ------------------------------------------------------------------ catalog
    static List<Path> chapterDirs() throws IOException {
        try (Stream<Path> s = Files.list(root.resolve("examples"))) {
            return s.filter(Files::isDirectory).filter(p -> p.getFileName().toString().matches("\\d\\d_.*")).sorted().collect(Collectors.toList());
        }
    }

    static List<Path> exampleFiles(Path dir) throws IOException {
        try (Stream<Path> s = Files.list(dir)) {
            return s.filter(p -> p.toString().endsWith(".java") && !p.getFileName().toString().startsWith("_")).sorted().collect(Collectors.toList());
        }
    }

    static String humanize(String folder) {
        String[] w = folder.replaceFirst("^\\d+_", "").split("_");
        return Arrays.stream(w).map(x -> x.isEmpty() ? x : Character.toUpperCase(x.charAt(0)) + x.substring(1)).collect(Collectors.joining(" "));
    }

    static String firstHeading(Path md) {
        try { for (String l : Files.readAllLines(md, StandardCharsets.UTF_8)) if (l.startsWith("# ")) return l.substring(2).trim(); }
        catch (IOException ignored) { }
        return null;
    }

    static String catalogJson() throws IOException {
        List<String> chapters = new ArrayList<>();
        int totalExamples = 0;
        for (Path dir : chapterDirs()) {
            String folder = dir.getFileName().toString();
            Path dd = root.resolve("deep_dive").resolve(folder + ".md");
            List<String> examples = new ArrayList<>();
            for (Path f : exampleFiles(dir)) {
                List<String> lines = Files.readAllLines(f, StandardCharsets.UTF_8);
                String title = f.getFileName().toString(), summary = "";
                List<String> sections = new ArrayList<>();
                for (int i = 0; i < lines.size(); i++) {
                    String l = lines.get(i);
                    Matcher h = HEADER_TITLE_RE.matcher(l);
                    if (i < 12 && h.matches()) title = h.group(2).trim();
                    if (i < 25 && l.contains("Interview angle:")) {
                        StringBuilder sb = new StringBuilder(l.substring(l.indexOf("Interview angle:") + 16).trim());
                        for (int j = i + 1; j < Math.min(lines.size(), i + 4); j++) {        // continuation comment lines
                            String nx = lines.get(j);
                            if (!nx.matches("^\\s*\\*\\s+\\S.*") || nx.trim().equals("*/")) break;
                            sb.append(' ').append(nx.replaceFirst("^\\s*\\*\\s+", "").trim());
                        }
                        summary = sb.toString();
                    }
                    Matcher m = SECTION_CALL_RE.matcher(l);
                    while (m.find()) sections.add(q(m.group(1)));
                }
                String rel = folder + "/" + f.getFileName();
                examples.add("{\"path\":" + q(rel) + ",\"file\":" + q(f.getFileName().toString()) + ",\"title\":" + q(title)
                        + ",\"summary\":" + q(summary) + ",\"sections\":" + arr(sections) + ",\"lines\":" + lines.size() + "}");
                totalExamples++;
            }
            chapters.add("{\"id\":" + q(folder) + ",\"number\":" + Integer.parseInt(folder.substring(0, 2)) + ",\"label\":" + q(humanize(folder))
                    + ",\"title\":" + q(Files.isRegularFile(dd) ? firstHeading(dd) : humanize(folder))
                    + ",\"doc\":" + (Files.isRegularFile(dd) ? q("deep_dive/" + folder + ".md") : "null")
                    + ",\"examples\":" + arr(examples) + "}");
        }
        List<String> docs = new ArrayList<>();
        Path dd = root.resolve("deep_dive");
        if (Files.isDirectory(dd)) {
            try (Stream<Path> s = Files.list(dd)) {
                for (Path p : s.filter(x -> x.toString().endsWith(".md")).sorted().collect(Collectors.toList())) {
                    String h = firstHeading(p);
                    docs.add("{\"name\":" + q("deep_dive/" + p.getFileName()) + ",\"title\":" + q(h == null ? p.getFileName().toString() : h) + "}");
                }
            }
        }
        List<String> extra = new ArrayList<>();
        for (String n : new String[]{"README.md", "QUESTION_INDEX.md", "Java_SpringBoot_Kafka_Interview_QA_Guide.md"})
            if (Files.isRegularFile(root.resolve(n))) extra.add("{\"name\":" + q(n) + ",\"title\":" + q(n) + "}");
        return "{\"root\":" + q(root.toString()) + ",\"java\":" + q(Runtime.version().toString()) + ",\"timeoutSeconds\":" + timeoutSeconds
                + ",\"exampleCount\":" + totalExamples + ",\"chapters\":" + arr(chapters) + ",\"docs\":" + arr(docs) + ",\"extra\":" + arr(extra) + "}";
    }

    // ------------------------------------------------------------------ source + docs
    static Path exampleFile(String rel) {
        Path base = root.resolve("examples").normalize();
        Path p = base.resolve(rel).normalize();
        if (!p.startsWith(base) || !p.toString().endsWith(".java")) throw new SecurityException("not an example file");
        if (!Files.isRegularFile(p)) throw new SecurityException("no such example");
        return p;
    }

    static void source(HttpExchange ex) throws IOException {
        Path p = exampleFile(params(ex).getOrDefault("path", ""));
        send(ex, 200, "text/plain; charset=utf-8", Files.readAllBytes(p));
    }

    static void doc(HttpExchange ex) throws IOException {
        String name = params(ex).getOrDefault("name", "");
        boolean ok = name.matches("deep_dive/[A-Za-z0-9_.-]+\\.md") || name.matches("topics/[0-9][A-Za-z0-9_.-]+\\.md")
                || name.equals("README.md") || name.equals("QUESTION_INDEX.md") || name.equals("Java_SpringBoot_Kafka_Interview_QA_Guide.md");
        if (!ok) throw new SecurityException("document not allowed");
        Path p = root.resolve(name).normalize();
        if (!p.startsWith(root) || !Files.isRegularFile(p)) throw new NoSuchFileException(name);
        send(ex, 200, "text/markdown; charset=utf-8", Files.readAllBytes(p));
    }

    // ------------------------------------------------------------------ Q&A (topics/*.md + the guide)
    static String qaJson() throws IOException {
        List<String> topics = new ArrayList<>();
        Path dir = root.resolve("topics");
        if (Files.isDirectory(dir)) {
            List<Path> files;
            try (Stream<Path> s = Files.list(dir)) {
                files = s.filter(p -> p.getFileName().toString().matches("\\d\\d-.*\\.md")).sorted().collect(Collectors.toList());
            }
            for (Path f : files) topics.add(parseTopic(f));
        }
        Path guide = root.resolve("Java_SpringBoot_Kafka_Interview_QA_Guide.md");
        if (Files.isRegularFile(guide)) topics.addAll(parseGuide(guide));
        return "{\"topics\":" + arr(topics) + "}";
    }

    static String parseTopic(Path f) throws IOException {
        List<String> lines = Files.readAllLines(f, StandardCharsets.UTF_8);
        String id = f.getFileName().toString().replace(".md", ""), title = id, focus = "";
        int start = 0;
        if (!lines.isEmpty() && lines.get(0).trim().equals("---")) {
            for (int i = 1; i < lines.size(); i++) {
                String l = lines.get(i);
                if (l.trim().equals("---")) { start = i + 1; break; }
                if (l.startsWith("id:")) id = l.substring(3).trim();
                if (l.startsWith("title:")) title = l.substring(6).trim();
                if (l.startsWith("focus:")) focus = l.substring(6).trim();
            }
        }
        List<String> qs = new ArrayList<>();
        int n = 0; String level = null, qtext = null; StringBuilder ans = new StringBuilder(); boolean inCode = false;
        for (int i = start; i < lines.size(); i++) {
            String l = lines.get(i);
            if (l.trim().startsWith("```")) inCode = !inCode;
            Matcher m = inCode ? null : Q_RE.matcher(l);
            if (m != null && m.matches()) {
                if (qtext != null) qs.add(qJson(n, level, qtext, ans.toString()));
                n = Integer.parseInt(m.group(1)); level = m.group(2).toLowerCase(); qtext = m.group(3).trim(); ans.setLength(0);
            } else if (qtext != null) ans.append(l).append('\n');
        }
        if (qtext != null) qs.add(qJson(n, level, qtext, ans.toString()));
        return "{\"id\":" + q(id) + ",\"title\":" + q(title) + ",\"focus\":" + q(focus) + ",\"source\":\"topics\",\"questions\":" + arr(qs) + "}";
    }

    static List<String> parseGuide(Path f) throws IOException {
        List<String> out = new ArrayList<>();
        String curId = null, curTitle = null; List<String> qs = new ArrayList<>();
        int n = 0; String qtext = null; StringBuilder ans = new StringBuilder(); boolean inCode = false;
        for (String l : Files.readAllLines(f, StandardCharsets.UTF_8)) {
            if (l.trim().startsWith("```")) inCode = !inCode;
            Matcher s = inCode ? null : GUIDE_SECTION_RE.matcher(l);
            Matcher qm = inCode ? null : GUIDE_Q_RE.matcher(l);
            if (s != null && s.matches()) {
                if (qtext != null) qs.add(qJson(n, "guide", qtext, ans.toString()));
                qtext = null;
                if (curId != null && !qs.isEmpty()) out.add(guideTopic(curId, curTitle, qs));
                curId = "guide-" + s.group(1); curTitle = "Guide " + s.group(1) + ". " + s.group(2).trim(); qs = new ArrayList<>();
            } else if (qm != null && qm.matches()) {
                if (qtext != null) qs.add(qJson(n, "guide", qtext, ans.toString()));
                n = Integer.parseInt(qm.group(1)); qtext = qm.group(2).trim(); ans.setLength(0);
            } else if (qtext != null) ans.append(l).append('\n');
        }
        if (qtext != null) qs.add(qJson(n, "guide", qtext, ans.toString()));
        if (curId != null && !qs.isEmpty()) out.add(guideTopic(curId, curTitle, qs));
        return out;
    }

    static String guideTopic(String id, String title, List<String> qs) {
        return "{\"id\":" + q(id) + ",\"title\":" + q(title) + ",\"focus\":\"Interview Q&A Guide (Java 8/11, Spring Boot, Kafka, NoSQL, Splunk)\",\"source\":\"guide\",\"questions\":" + arr(qs) + "}";
    }

    static String qJson(int n, String level, String q, String a) {
        return "{\"n\":" + n + ",\"level\":" + q(level) + ",\"q\":" + q(q) + ",\"a\":" + q(a.trim()) + "}";
    }

    // ------------------------------------------------------------------ running examples
    static class Run {
        final String id, path;
        final List<String> lines = Collections.synchronizedList(new ArrayList<>());
        volatile boolean done; volatile int exit = -1; volatile boolean timedOut, truncated;
        volatile Process process; final long started = System.currentTimeMillis(); volatile long ended;
        Run(String id, String path) { this.id = id; this.path = path; }
    }

    static final Map<String, Run> RUNS = new ConcurrentHashMap<>();
    static final AtomicInteger RUN_SEQ = new AtomicInteger();

    static void run(HttpExchange ex) throws Exception {
        Path file = exampleFile(params(ex).getOrDefault("path", ""));
        if (!RUN_SLOTS.tryAcquire()) { json(ex, 429, "{\"error\":\"4 runs already in progress; wait or stop one\"}"); return; }
        String id = "r" + RUN_SEQ.incrementAndGet();
        Run run = new Run(id, params(ex).get("path"));
        RUNS.put(id, run);
        Thread t = new Thread(() -> execute(run, file), "run-" + id);
        t.setDaemon(true);
        t.start();
        json(ex, 200, "{\"id\":" + q(id) + "}");
    }

    static void execute(Run run, Path file) {
        try {
            ProcessBuilder pb = new ProcessBuilder(javaBinary(), "-Dfile.encoding=UTF-8", file.getFileName().toString());
            pb.directory(file.getParent().toFile());
            pb.redirectErrorStream(true);
            pb.redirectInput(ProcessBuilder.Redirect.from(new File(System.getProperty("os.name").toLowerCase().contains("win") ? "NUL" : "/dev/null")));
            Process p = pb.start();
            run.process = p;
            Thread watchdog = new Thread(() -> {
                try {
                    if (!p.waitFor(timeoutSeconds, TimeUnit.SECONDS)) { run.timedOut = true; kill(p); }
                } catch (InterruptedException ignored) { }
            });
            watchdog.setDaemon(true);
            watchdog.start();
            try (BufferedReader r = new BufferedReader(new InputStreamReader(p.getInputStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = r.readLine()) != null) {
                    if (run.lines.size() < MAX_LINES) run.lines.add(line);
                    else run.truncated = true;
                }
            }
            run.exit = p.waitFor();
        } catch (Exception e) {
            run.lines.add("[runner error] " + e);
        } finally {
            run.ended = System.currentTimeMillis();
            run.done = true;
            RUN_SLOTS.release();
        }
    }

    static void kill(Process p) {
        p.descendants().forEach(ProcessHandle::destroyForcibly);
        p.destroyForcibly();
    }

    static void poll(HttpExchange ex) throws IOException {
        Map<String, String> pr = params(ex);
        Run run = RUNS.get(pr.getOrDefault("id", ""));
        if (run == null) { json(ex, 404, "{\"error\":\"unknown run\"}"); return; }
        int from = Integer.parseInt(pr.getOrDefault("from", "0"));
        List<String> out;
        synchronized (run.lines) { out = new ArrayList<>(run.lines.subList(Math.min(from, run.lines.size()), run.lines.size())); }
        long end = run.done ? run.ended : System.currentTimeMillis();
        json(ex, 200, "{\"lines\":" + arr(out.stream().map(JavaPrepLive::q).collect(Collectors.toList())) + ",\"next\":" + (from + out.size())
                + ",\"done\":" + run.done + ",\"exit\":" + run.exit + ",\"timedOut\":" + run.timedOut + ",\"truncated\":" + run.truncated
                + ",\"elapsedMs\":" + (end - run.started) + "}");
    }

    static void stop(HttpExchange ex) throws IOException {
        Run run = RUNS.get(params(ex).getOrDefault("id", ""));
        if (run != null && run.process != null && !run.done) kill(run.process);
        json(ex, 200, "{\"stopped\":" + (run != null) + "}");
    }

    // ------------------------------------------------------------------ headless check
    static int runCheck() throws Exception {
        List<Path> all = new ArrayList<>();
        for (Path d : chapterDirs()) all.addAll(exampleFiles(d));
        ExecutorService pool = Executors.newFixedThreadPool(3);
        Map<Path, Future<String>> results = new LinkedHashMap<>();
        for (Path f : all) results.put(f, pool.submit(() -> {
            long t0 = System.currentTimeMillis();
            Process p = new ProcessBuilder(javaBinary(), f.getFileName().toString()).directory(f.getParent().toFile())
                    .redirectErrorStream(true).redirectOutput(ProcessBuilder.Redirect.DISCARD).start();
            boolean finished = p.waitFor(timeoutSeconds, TimeUnit.SECONDS);
            if (!finished) { kill(p); return "FAIL (timeout)"; }
            return p.exitValue() == 0 ? "ok   (" + (System.currentTimeMillis() - t0) / 1000.0 + "s)" : "FAIL (exit " + p.exitValue() + ")";
        }));
        int failed = 0;
        for (Map.Entry<Path, Future<String>> e : results.entrySet()) {
            String r = e.getValue().get();
            if (r.startsWith("FAIL")) failed++;
            System.out.println(r + "  " + root.relativize(e.getKey()).toString().replace('\\', '/'));
        }
        pool.shutdown();
        System.out.println("examples=" + all.size() + " failed=" + failed);
        return failed == 0 ? 0 : 1;
    }
}
