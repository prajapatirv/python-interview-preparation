/*
 * 01 - Incident triage: turn a metrics snapshot into a ranked hypothesis list
 *
 * Run:  java 01_incident_triage_runbook.java
 *
 * Encodes the reasoning behind "an API is slow / lag is growing / events are duplicated /
 * a downstream is down" as rules over signals you would pull from Grafana, Splunk and Kafka.
 * The point is the ORDER of questions and the evidence for each conclusion, not the code.
 */
import java.util.*;

class IncidentTriageRunbook {

    static class Snapshot {
        String name;
        double p99Ms = 120, baselineP99Ms = 120, errorRate = 0.002, cpuPct = 40, gcPausePct = 1, heapUsedPct = 55;
        int hikariActive = 3, hikariMax = 10, hikariPending = 0, tomcatBusy = 20, tomcatMax = 200;
        long kafkaLag = 0, lagTrendPerMin = 0; int rebalancesLastHour = 0;
        double downstreamP99Ms = 80, downstreamErrRate = 0.001; boolean recentDeploy = false;
        long duplicateEventIds = 0;
        Snapshot(String n) { name = n; }
    }

    static List<String> diagnose(Snapshot s) {
        List<String> h = new ArrayList<>();
        if (s.recentDeploy && s.errorRate > 0.02) h.add("RECENT DEPLOY correlates with errors -> compare versions in Splunk (stats count by version); roll back first, investigate second");
        if (s.hikariPending > 0 && s.hikariActive >= s.hikariMax) h.add("DB CONNECTION POOL SATURATED (" + s.hikariActive + "/" + s.hikariMax + ", " + s.hikariPending + " waiting) -> slow query / long transaction / leak; check pg_stat_activity, enable leak detection");
        if (s.gcPausePct > 10 || s.heapUsedPct > 90) h.add("MEMORY PRESSURE (GC " + s.gcPausePct + "% of time, heap " + s.heapUsedPct + "%) -> heap dump / jcmd GC.class_histogram; look for unbounded cache or leak");
        if (s.cpuPct > 85 && s.hikariPending == 0) h.add("CPU-BOUND (" + s.cpuPct + "%) -> take 3 thread dumps / async-profiler flame graph; hot loop, regex, serialization, logging");
        if (s.downstreamP99Ms > 1_000 || s.downstreamErrRate > 0.05) h.add("DOWNSTREAM DEGRADED (p99 " + (int) s.downstreamP99Ms + " ms, err " + pct(s.downstreamErrRate) + ") -> verify timeouts + circuit breaker; threads piling up waiting; fail fast/fallback");
        if (s.tomcatBusy > s.tomcatMax * 0.9) h.add("REQUEST THREADS EXHAUSTED (" + s.tomcatBusy + "/" + s.tomcatMax + ") -> a blocked dependency; thread dump groups threads by the frame they wait in");
        if (s.kafkaLag > 10_000 && s.lagTrendPerMin > 0) {
            if (s.rebalancesLastHour > 5) h.add("CONSUMER GROUP UNSTABLE (" + s.rebalancesLastHour + " rebalances/h) -> max.poll.interval.ms exceeded or pods crash-looping; reduce max.poll.records, check GC pauses, use static membership");
            else h.add("LAG GROWING +" + s.lagTrendPerMin + "/min with a stable group -> processing slower than production; check per-partition skew, downstream latency, then add consumers up to partition count");
        }
        if (s.duplicateEventIds > 0) h.add("DUPLICATE PROCESSING (" + s.duplicateEventIds + " repeated eventIds) -> at-least-once is normal; ensure idempotent consumer (processed-event table / upsert) and commit-after-process; find WHY redelivered (rebalance, crash before commit)");
        if (s.p99Ms > 3 * s.baselineP99Ms && h.isEmpty()) h.add("LATENCY UP WITHOUT A CLEAR RESOURCE SIGNAL -> use distributed traces to find the slow span; check lock contention, N+1 queries, a new code path, cold cache after deploy");
        if (h.isEmpty()) h.add("no rule matched: widen the time range, compare with the same hour last week, check change log and dependencies");
        return h;
    }

    static String pct(double d) { return String.format("%.1f%%", d * 100); }

    public static void main(String[] args) {
        List<Snapshot> incidents = new ArrayList<>();

        Snapshot a = new Snapshot("API p99 jumps from 120 ms to 4.2 s, CPU low");
        a.p99Ms = 4_200; a.hikariActive = 10; a.hikariPending = 37; a.cpuPct = 22; incidents.add(a);

        Snapshot b = new Snapshot("Consumer lag grows 40k/min after a deploy, rebalances every minute");
        b.kafkaLag = 2_400_000; b.lagTrendPerMin = 40_000; b.rebalancesLastHour = 41; b.recentDeploy = true; b.gcPausePct = 12; incidents.add(b);

        Snapshot c = new Snapshot("Checkout errors 18% since payment provider incident");
        c.errorRate = 0.18; c.downstreamP99Ms = 6_000; c.downstreamErrRate = 0.4; c.tomcatBusy = 196; c.p99Ms = 6_100; incidents.add(c);

        Snapshot d = new Snapshot("Customers charged twice");
        d.duplicateEventIds = 312; d.rebalancesLastHour = 9; incidents.add(d);

        Snapshot e = new Snapshot("Slow after new release, everything else normal");
        e.p99Ms = 900; e.recentDeploy = true; incidents.add(e);

        for (Snapshot s : incidents) {
            System.out.println("\n=== " + s.name + " ===");
            int i = 1;
            for (String line : diagnose(s)) System.out.println("  " + i++ + ". " + line);
        }

        System.out.println("\n=== The 6-step answer shape for any incident question ===");
        System.out.println("  1. Stabilise/mitigate first (rollback, scale, shed load, disable a flag) - customers before curiosity");
        System.out.println("  2. Scope: who/what/when? one endpoint, one version, one pod, one region, one tenant?");
        System.out.println("  3. Golden signals: latency, traffic, errors, saturation - compare with a baseline");
        System.out.println("  4. Follow one failing request end to end (correlation id -> traces -> logs)");
        System.out.println("  5. Form a hypothesis, find the evidence that would DISPROVE it, then fix and verify");
        System.out.println("  6. Write the RCA: timeline, root cause, why detection/guards failed, corrective + preventive actions");
    }
}

// EXERCISE: add two rules (disk full / DNS or certificate expiry) and one scenario each.
