/*
 * 02 - Metrics that matter: RED/USE, percentiles, SLOs, error budgets, burn-rate alerts
 *
 * Run:  java 02_metrics_percentiles_slo_and_alerting.java
 *
 * Interview angle: "what do you monitor for a Spring Boot service?", "why p99 not average?",
 * "what is an SLO / error budget?", "how do you alert without waking people for noise?".
 */
import java.util.*;
import java.util.stream.*;

class MetricsPercentilesSloAndAlerting {

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    static double pct(double[] sorted, double p) { return sorted[Math.max(0, (int) Math.ceil(p / 100 * sorted.length) - 1)]; }

    public static void main(String[] args) {

        section("1. Why averages lie: 1,000 requests, 2% are slow");
        Random r = new Random(5);
        double[] lat = new double[1_000];
        for (int i = 0; i < lat.length; i++) lat[i] = i % 50 == 0 ? 3_000 + r.nextInt(1_000) : 40 + r.nextInt(40);
        double avg = Arrays.stream(lat).average().orElse(0);
        double[] sorted = lat.clone(); Arrays.sort(sorted);
        System.out.printf("  avg=%.0f ms  p50=%.0f  p95=%.0f  p99=%.0f  max=%.0f%n", avg, pct(sorted, 50), pct(sorted, 95), pct(sorted, 99), sorted[sorted.length - 1]);
        System.out.println("  The average looks 'fine'; 1 in 50 users waits 3-4 seconds. Percentiles cannot be averaged across hosts:");
        System.out.println("  aggregate HISTOGRAM BUCKETS (Micrometer publishPercentileHistogram) and compute the quantile centrally.");

        section("2. RED for services, USE for resources");
        System.out.println("  RED  (request-driven): Rate (req/s), Errors (5xx %), Duration (p50/p95/p99)");
        System.out.println("  USE  (resources)     : Utilization, Saturation (queue depth, thread pool, lag), Errors");
        System.out.println("  Spring Boot out of the box (Micrometer): http.server.requests, jvm.memory.used, jvm.gc.pause, hikaricp.connections.*,");
        System.out.println("  tomcat.threads.busy, kafka.consumer.fetch.manager.records.lag.max, executor.queued");

        section("3. SLI -> SLO -> error budget");
        double slo = 0.999;                                    // 99.9% of requests succeed in < 500 ms over 30 days
        long monthlyRequests = 30L * 24 * 3600 * 50;           // 50 req/s average
        double budgetRequests = monthlyRequests * (1 - slo);
        double budgetMinutes = 30 * 24 * 60 * (1 - slo);
        System.out.printf("  SLO %.1f%% over 30 days: budget = %,.0f bad requests (~%.0f min of full outage)%n", slo * 100, budgetRequests, budgetMinutes);
        System.out.println("  Budget left -> ship features; budget gone -> freeze risky changes, fix reliability.");

        section("4. Burn-rate alerting (Google SRE multi-window)");
        double[] errRates = {0.0005, 0.002, 0.0144, 0.05};     // observed error ratio over the window
        for (double er : errRates) {
            double burn = er / (1 - slo);
            String action = burn >= 14.4 ? "PAGE now (budget gone in ~2 days)" : burn >= 6 ? "PAGE (gone in ~5 days)" : burn >= 1 ? "TICKET (on pace to exhaust)" : "ok";
            System.out.printf("  error ratio %.2f%% -> burn rate %5.1fx -> %s%n", er * 100, burn, action);
        }
        System.out.println("  Page on symptoms users feel (errors, latency), not causes (CPU 80%). Pair a long and a short window to avoid flapping.");

        section("5. Saturation signals often explain the symptom");
        int poolMax = 10, busy = 10, queued = 37; double dbWaitMs = 850;
        System.out.printf("  hikari: active=%d/%d pending=%d  connection-acquire p95=%.0f ms%n", busy, poolMax, queued, dbWaitMs);
        System.out.println("  => requests are queueing for a DB connection: latency up, CPU low. Fix the slow query / pool sizing, not the app threads.");
        System.out.println("  Pool size ~ (cores * 2) + effective spindles is a starting point; more connections often makes the DB slower.");

        section("6. Cardinality and cost");
        System.out.println("  label 'endpoint' (50 values) x 'status' (6) x 'method' (4) = 1,200 series: fine");
        System.out.println("  label 'userId' (5,000,000 values) = millions of series: breaks Prometheus. Put ids in logs/traces, not metric labels.");

        section("7. Three signals, one story");
        System.out.println("  metrics -> something is wrong (alert) | traces -> where in the call graph | logs -> why (exception, payload id)");
        System.out.println("  Tooling map: Micrometer -> Prometheus -> Grafana | OpenTelemetry -> Jaeger/Tempo | JSON logs -> Splunk/ELK");
        System.out.println("  Splunk can also do metrics and ITSI/Observability Cloud for traces, but the pattern is identical.");
    }
}

// EXERCISE: given a 99.95% SLO and 2 small incidents of 8 and 15 minutes this month, how much budget is left?
