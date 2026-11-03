/*
 * 09 - Vector search and LLM sampling from scratch: cosine, HNSW-style ANN, hybrid search, recall, top-p
 *
 * Run:  java 09_vector_search_and_llm_sampling_from_scratch.java
 *
 * Interview angle: "how does a vector database actually find the nearest neighbours?", "why does
 * hybrid search help?", "what do temperature and top-p do?". No libraries and no model: small
 * hand-made vectors and a seeded random dataset, so the numbers are reproducible and the mechanism
 * is visible. A real system swaps in an embedding model and a real store. Answers: banks 67 and 69.
 */
import java.util.*;
import java.util.stream.*;

class VectorSearchFromScratch {

    static int checks = 0;
    static void section(String t) { System.out.println("\n=== " + t + " ==="); }
    static void check(String label, Object expected, Object actual) {
        checks++;
        if (!Objects.equals(expected, actual))
            throw new AssertionError(label + ": expected " + expected + " but got " + actual);
        System.out.println("  ok  " + label + " -> " + actual);
    }
    static double round(double v) { return Math.round(v * 1000) / 1000.0; }

    static double dot(double[] a, double[] b) { double s = 0; for (int i = 0; i < a.length; i++) s += a[i] * b[i]; return s; }
    static double norm(double[] a) { return Math.sqrt(dot(a, a)); }
    static double cosine(double[] a, double[] b) { return dot(a, b) / (norm(a) * norm(b)); }
    static double euclidean(double[] a, double[] b) { double s = 0; for (int i = 0; i < a.length; i++) s += (a[i] - b[i]) * (a[i] - b[i]); return Math.sqrt(s); }
    static double[] normalise(double[] a) { double n = norm(a); return Arrays.stream(a).map(v -> v / n).toArray(); }

    // ---- a small navigable-small-world graph: the base layer of HNSW, without the upper layers ----
    static final class Graph {
        final double[][] data;
        final List<List<Integer>> links = new ArrayList<>();
        long comparisons = 0;
        Graph(double[][] data, int m, int efBuild) {
            this.data = data;
            for (int i = 0; i < data.length; i++) {
                links.add(new ArrayList<>());
                if (i == 0) continue;
                for (int neighbour : search(data[i], efBuild, i).stream().limit(m).toList()) {
                    links.get(i).add(neighbour);
                    links.get(neighbour).add(i);        // two-way links are what keep the graph navigable
                }
            }
        }
        double distance(double[] q, int id) { comparisons++; return euclidean(q, data[id]); }

        /** Greedy beam search: always expand the closest unexplored node, stop when the beam stops improving. */
        List<Integer> search(double[] q, int ef, int limit) {
            Set<Integer> seen = new HashSet<>(List.of(0));
            PriorityQueue<double[]> frontier = new PriorityQueue<>(Comparator.comparingDouble(e -> e[0]));
            PriorityQueue<double[]> best = new PriorityQueue<>((x, y) -> Double.compare(y[0], x[0]));
            double start = distance(q, 0);
            frontier.add(new double[] {start, 0});
            best.add(new double[] {start, 0});
            while (!frontier.isEmpty()) {
                double[] current = frontier.poll();
                if (best.size() >= ef && current[0] > best.peek()[0]) break;
                for (int next : links.get((int) current[1])) {
                    if (next >= limit || !seen.add(next)) continue;
                    double d = distance(q, next);
                    if (best.size() < ef || d < best.peek()[0]) {
                        frontier.add(new double[] {d, next});
                        best.add(new double[] {d, next});
                        if (best.size() > ef) best.poll();
                    }
                }
            }
            return best.stream().sorted(Comparator.comparingDouble(e -> e[0])).map(e -> (int) e[1]).toList();
        }
    }

    static List<Integer> exactTopK(double[][] data, double[] q, int k) {
        return IntStream.range(0, data.length).boxed()
                        .sorted(Comparator.comparingDouble(i -> euclidean(q, data[i]))).limit(k).toList();
    }

    /** Clustered data, because real embeddings cluster by meaning. Uniform noise has no structure to navigate. */
    static double[][] centres(int clusters, int dim, long seed) {
        Random r = new Random(seed);
        double[][] out = new double[clusters][dim];
        for (double[] c : out) for (int d = 0; d < dim; d++) c[d] = r.nextGaussian() * 1.5;
        return out;
    }
    static double[][] sample(double[][] centres, int n, long seed) {
        Random r = new Random(seed);
        int dim = centres[0].length;
        double[][] out = new double[n][dim];
        for (double[] v : out) {
            double[] c = centres[r.nextInt(centres.length)];
            for (int d = 0; d < dim; d++) v[d] = c[d] + r.nextGaussian();
        }
        return out;
    }

    /** Word chunker from the handbook, plus the one fix it needs: stop once the end has been reached. */
    static List<String> chunk(String text, int size, int overlap) {
        if (overlap >= size) throw new IllegalArgumentException("overlap must be smaller than size");
        String[] words = text.trim().split("\\s+");
        List<String> out = new ArrayList<>();
        for (int i = 0; i < words.length; i += size - overlap) {
            out.add(String.join(" ", Arrays.copyOfRange(words, i, Math.min(i + size, words.length))));
            if (i + size >= words.length) break;      // without this, a tail chunk repeats text already covered
        }
        return out;
    }

    /** Reciprocal Rank Fusion: uses rank positions only, so BM25 and cosine scores never need comparing. */
    static List<String> rrf(int k, List<List<String>> rankings) {
        Map<String, Double> score = new HashMap<>();
        for (List<String> ranking : rankings)
            for (int rank = 0; rank < ranking.size(); rank++)
                score.merge(ranking.get(rank), 1.0 / (k + rank + 1), Double::sum);
        return score.entrySet().stream()
                    .sorted(Map.Entry.<String, Double>comparingByValue().reversed().thenComparing(Map.Entry.comparingByKey()))
                    .map(Map.Entry::getKey).toList();
    }

    static double[] softmax(double[] logits, double temperature) {
        double[] e = Arrays.stream(logits).map(l -> Math.exp(l / temperature)).toArray();
        double total = Arrays.stream(e).sum();
        return Arrays.stream(e).map(v -> v / total).toArray();
    }

    /** Tokens kept by top-p: smallest set, most likely first, whose cumulative probability reaches p. */
    static int topPCount(double[] probs, double p) {
        double[] desc = Arrays.stream(probs).boxed().sorted(Comparator.reverseOrder()).mapToDouble(d -> d).toArray();
        double cumulative = 0;
        for (int i = 0; i < desc.length; i++) { cumulative += desc[i]; if (cumulative >= p) return i + 1; }
        return desc.length;
    }

    public static void main(String[] args) {
        section("1. The three similarity metrics (bank 67 Q3)");
        double[] a = {1, 2, 3}, b = {4, 5, 6};
        check("dot product of [1,2,3] and [4,5,6]", 32.0, dot(a, b));
        check("cosine", 0.975, round(cosine(a, b)));
        check("euclidean", 5.196, round(euclidean(a, b)));
        double[] twice = {2, 4, 6};
        check("cosine ignores magnitude: a and 2a are identical in direction", 1.0, round(cosine(a, twice)));
        check("dot product does not", 28.0, dot(a, twice));
        check("euclidean does not either", 3.742, round(euclidean(a, twice)));
        check("once normalised, dot product equals cosine", round(cosine(a, b)), round(dot(normalise(a), normalise(b))));

        section("2. Exact search compared with approximate search (bank 67 Q4)");
        int n = 5_000, k = 10;
        double[][] centres = centres(40, 32, 42L);
        double[][] data = sample(centres, n, 7L);
        double[][] queries = sample(centres, 50, 99L);     // a different seed: queries must not be stored vectors
        Graph graph = new Graph(data, 12, 64);
        System.out.printf("  %-20s %-14s %s%n", "method", "recall@10", "avg distance computations");
        System.out.printf("  %-20s %-14s %d%n", "exact", "1.000", n);
        double lowEfRecall = 0, highEfRecall = 0;
        for (int ef : new int[] {10, 20, 50, 100, 200}) {
            graph.comparisons = 0;
            double hits = 0;
            for (double[] q : queries) {
                Set<Integer> truth = new HashSet<>(exactTopK(data, q, k));
                hits += graph.search(q, ef, n).stream().limit(k).filter(truth::contains).count();
            }
            double recall = hits / (k * queries.length);
            if (ef == 10) lowEfRecall = recall;
            if (ef == 200) highEfRecall = recall;
            System.out.printf("  %-20s %-14.3f %d%n", "ANN ef=" + ef, recall, graph.comparisons / queries.length);
        }
        check("a wider beam trades work for recall", true, highEfRecall >= lowEfRecall);
        check("ANN at ef=200 is close to exact", true, highEfRecall > 0.9);

        section("3. Chunking with overlap (bank 67 Q6)");
        String doc = IntStream.rangeClosed(1, 200).mapToObj(i -> "w" + i).collect(Collectors.joining(" "));
        List<String> chunks = chunk(doc, 80, 15);
        check("chunk 1 starts at word 1", "w1", chunks.get(0).split(" ")[0]);
        check("chunk 2 starts at word 66: 15 words repeat", "w66", chunks.get(1).split(" ")[0]);
        check("chunk 2 ends at word 145", "w145", chunks.get(1).split(" ")[79]);
        check("number of chunks for 200 words", 3, chunks.size());
        check("the last chunk ends at the last word", "w200", chunks.get(2).substring(chunks.get(2).lastIndexOf(' ') + 1));
        try { chunk(doc, 10, 10); throw new AssertionError(); }
        catch (IllegalArgumentException e) { check("overlap >= size would loop forever, so it is refused", "IllegalArgumentException", e.getClass().getSimpleName()); }

        section("4. Hybrid search with reciprocal rank fusion (bank 67 Q8)");
        List<String> keyword = List.of("ERR-4021 runbook", "payment FAQ", "login guide");
        List<String> vector = List.of("payment FAQ", "refund policy", "ERR-4021 runbook");
        List<String> fused = rrf(60, List.of(keyword, vector));
        check("items both searches found rise to the top, in either order", Set.of("ERR-4021 runbook", "payment FAQ"), new HashSet<>(fused.subList(0, 2)));
        check("rank 2 + rank 1 beats rank 1 + rank 3", "payment FAQ", fused.get(0));
        check("the semantic-only hit survives", true, fused.contains("refund policy"));
        check("the keyword-only hit survives", true, fused.contains("login guide"));

        section("5. Measuring retrieval (bank 67 Q10)");
        Set<String> relevant = Set.of("c1", "c2", "c3", "c4");
        List<String> retrieved = List.of("c1", "c9", "c3");
        long hit = retrieved.stream().filter(relevant::contains).count();
        check("recall@3 = relevant found / all relevant", 0.5, hit / (double) relevant.size());
        check("precision@3 = relevant found / k", 0.667, round(hit / (double) retrieved.size()));

        section("6. Temperature, top-k and top-p (bank 69 Q3)");
        double[] logits = {3.0, 2.0, 1.0, 0.5, 0.1};
        double[] cold = softmax(logits, 0.2), neutral = softmax(logits, 1.0), hot = softmax(logits, 2.0);
        check("low temperature concentrates on the top token", true, cold[0] > 0.99);
        check("at T=1 the top token has", 0.61, round(neutral[0]));
        check("high temperature flattens the distribution", 0.401, round(hot[0]));
        check("probabilities always sum to 1", 1.0, round(Arrays.stream(hot).sum()));
        check("top-p 0.9 keeps 3 tokens at T=1", 3, topPCount(neutral, 0.9));
        check("top-p 0.9 keeps 1 token at T=0.2", 1, topPCount(cold, 0.9));
        check("top-p 0.9 keeps 4 tokens at T=2: it adapts, unlike a fixed top-k", 4, topPCount(hot, 0.9));

        section("7. Token budget and the cost of a request (bank 69 Q6, Q8)");
        int window = 128_000;
        int[] budget = {window * 10 / 100, window * 40 / 100, window * 30 / 100, window * 20 / 100};
        check("the four parts fill the window exactly", window, Arrays.stream(budget).sum());
        check("system instructions at 10 percent", 12_800, budget[0]);
        double cost = 1_000 / 1_000_000.0 * 3 + 500 / 1_000_000.0 * 12;   // illustrative rates, per million tokens
        check("1,000 input and 500 output tokens at $3 and $12 per million", 0.009, round(cost));
        check("at 1 million requests a month", 9_000L, Math.round(cost * 1_000_000));

        System.out.println("\nAll " + checks + " checks passed.");
    }
}
