/*
 * 01 - "Scale from 100 TPS to 600 TPS": the arithmetic you should be able to do on a whiteboard
 *
 * Run:  java 01_capacity_littles_law_100_to_600_tps.java
 *
 * Little's law, the utilisation cliff, per-tier bottleneck analysis, and what caching,
 * async buffering and horizontal scaling each buy. Numbers, not adjectives.
 */
import java.util.*;

class CapacityLittlesLaw100To600Tps {

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    public static void main(String[] args) {

        section("1. Little's law: concurrency = throughput x latency  (L = lambda x W)");
        double latencySec = 0.120;
        for (int tps : new int[]{100, 300, 600}) {
            System.out.printf("  %3d TPS x %.0f ms = %.0f requests in flight at any moment%n", tps, latencySec * 1000, tps * latencySec);
        }
        System.out.println("  Threads/connections needed >= in-flight requests. This is where pools and DB connection limits bite.");

        section("2. Utilisation cliff: latency of a single server queue (M/M/1: W = S / (1 - rho))");
        double serviceMs = 20;
        System.out.println("  service time S = " + serviceMs + " ms");
        for (double rho : new double[]{0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 0.99})
            System.out.printf("  utilisation %3.0f%% -> mean response %6.0f ms  (%4.1fx)%n", rho * 100, serviceMs / (1 - rho), 1 / (1 - rho));
        System.out.println("  Plan for 50-70% peak utilisation. Past ~80% a small traffic bump makes latency explode (queueing).");

        section("3. Per-instance capacity and instance count for 600 TPS");
        double perInstanceTps = 90;                           // measured at target latency in a load test, NOT guessed
        double targetUtil = 0.65;
        int instances = (int) Math.ceil(600 / (perInstanceTps * targetUtil));
        int withNPlus1 = instances + 1;
        System.out.printf("  one instance sustains %.0f TPS at p95 target; plan %.0f%% -> usable %.0f TPS%n", perInstanceTps, targetUtil * 100, perInstanceTps * targetUtil);
        System.out.printf("  600 / %.0f = %d instances, +1 for failure/deploy (N+1) = %d%n", perInstanceTps * targetUtil, instances, withNPlus1);
        System.out.println("  Spread across >= 3 AZs so losing one zone still leaves enough capacity: 2/3 of capacity must carry 100% of load.");

        section("4. Find the bottleneck tier (it is rarely the web tier)");
        String[][] tiers = {
            {"API pods (CPU)", "8 x 90 = 720 TPS", "ok"},
            {"DB connection pool", "8 pods x 10 conns / 0.05 s = 1,600 TPS", "ok"},
            {"Primary DB writes", "~350 TPS before replication lag grows", "BOTTLENECK at 600"},
            {"Partner payment API", "rate limit 400 TPS", "BOTTLENECK at 600"},
            {"Kafka (3 brokers)", "10s of thousands msg/s", "ok"},
        };
        for (String[] t : tiers) System.out.printf("  %-22s %-42s %s%n", t[0], t[1], t[2]);

        section("5. What each lever buys at 600 TPS");
        double reads = 0.8, hitRate = 0.9;
        double dbLoad = 600 * (1 - reads) + 600 * reads * (1 - hitRate);
        System.out.printf("  cache: 80%% reads, 90%% hit rate -> DB sees %.0f TPS instead of 600 (%.0f%% less)%n", dbLoad, 100 * (1 - dbLoad / 600));
        System.out.println("  read replicas : scale READ throughput; replication lag means reads may be stale (read-your-writes needs routing)");
        System.out.println("  async / queue : absorb bursts and decouple (queue-based load levelling); accept eventual completion");
        System.out.println("  rate limiting : protect dependencies (partner 400 TPS) - shed or queue the excess, return 429/Retry-After");
        System.out.println("  batching      : 1 insert of 100 rows beats 100 inserts (network round trips, fsync)");
        System.out.println("  sharding      : last resort for write scale - needs a shard key, cross-shard queries become hard");

        section("6. Rollout plan (the answer shape)");
        System.out.println("  1. Measure: baseline p50/p95/p99, saturation (CPU, pool, queue, lag), error rate at 100 TPS");
        System.out.println("  2. Load test to 1.5x target in a prod-like env; find the first thing that breaks");
        System.out.println("  3. Remove it (index/query, cache, pool size, batching), repeat until 600 holds at < 70% utilisation");
        System.out.println("  4. Autoscale on a leading signal (queue depth / RPS per pod), not only CPU; set min replicas for warm-up");
        System.out.println("  5. Protect: timeouts, circuit breakers, rate limits, bulkheads, load shedding");
        System.out.println("  6. Verify: canary + SLO dashboards + alerts; keep a rollback; game-day a node/AZ failure");

        section("7. Autoscaling gotchas");
        System.out.println("  Spring Boot cold start 20-40 s + JIT warm-up: scale BEFORE the spike (schedule/predictive) and use readiness probes.");
        System.out.println("  HPA on CPU lags; KEDA can scale on Kafka lag. Scaling consumers beyond partitions does nothing.");
        System.out.println("  Scale-in must drain: graceful shutdown + preStop + terminationGracePeriod > longest request.");
    }
}

// EXERCISE: redo section 3 for 99.95% availability when one of three AZs can fail during a deploy.
