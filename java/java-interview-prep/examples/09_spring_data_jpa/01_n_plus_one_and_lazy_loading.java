/*
 * 01 - The JPA N+1 select problem, lazy loading, and the fixes (simulated persistence layer)
 *
 * Run:  java 01_n_plus_one_and_lazy_loading.java
 *
 * A fake "database" counts SQL statements. Entities hold lazy proxies exactly like Hibernate's:
 * touching the association triggers a query. Compare: naive loop, JOIN FETCH, batch size, DTO projection.
 */
import java.util.*;
import java.util.function.*;
import java.util.stream.*;

class NPlusOneAndLazyLoading {

    // ---- the fake database
    static int queries = 0;
    static final List<String> SQL = new ArrayList<>();
    static void sql(String s) { queries++; SQL.add(s); }

    static final List<long[]> AUTHORS = new ArrayList<>();                   // {id}
    static final Map<Long, String> AUTHOR_NAME = new HashMap<>();
    static final List<long[]> BOOKS = new ArrayList<>();                     // {id, authorId}

    // ---- entities
    static class Author {
        final long id; final String name;
        private List<Long> bookIds;                                          // lazily loaded collection
        private final Function<Long, List<Long>> loader;
        Author(long id, String name, Function<Long, List<Long>> loader) { this.id = id; this.name = name; this.loader = loader; }
        List<Long> getBooks() {                                              // the lazy proxy hit
            if (bookIds == null) bookIds = loader.apply(id);
            return bookIds;
        }
        void prime(List<Long> ids) { bookIds = ids; }
    }

    // ---- repository operations producing "SQL"
    static List<Author> findAllAuthors() {
        sql("select * from author");
        return AUTHORS.stream().map(a -> new Author(a[0], AUTHOR_NAME.get(a[0]), NPlusOneAndLazyLoading::loadBooks)).collect(Collectors.toList());
    }

    static List<Long> loadBooks(long authorId) {
        sql("select id from book where author_id = " + authorId);
        return BOOKS.stream().filter(b -> b[1] == authorId).map(b -> b[0]).collect(Collectors.toList());
    }

    static List<Author> findAllWithBooksJoinFetch() {
        sql("select a.*, b.id from author a left join fetch book b on b.author_id = a.id");
        Map<Long, List<Long>> grouped = BOOKS.stream().collect(Collectors.groupingBy(b -> b[1], Collectors.mapping(b -> b[0], Collectors.toList())));
        return AUTHORS.stream().map(a -> {
            Author au = new Author(a[0], AUTHOR_NAME.get(a[0]), id -> { throw new IllegalStateException("should not load"); });
            au.prime(grouped.getOrDefault(a[0], Collections.emptyList()));
            return au;
        }).collect(Collectors.toList());
    }

    /** @BatchSize(size=N): when ONE collection is touched, load for up to N pending owners with a single IN query. */
    static List<Author> findAllWithBatchSize(int batch) {
        sql("select * from author");
        List<Author> out = new ArrayList<>();
        List<Author> pending = new ArrayList<>();
        for (long[] a : AUTHORS) {
            Author au = new Author(a[0], AUTHOR_NAME.get(a[0]), null) {
                @Override List<Long> getBooks() {
                    if (super.bookIds == null) {
                        int idx = pending.indexOf(this);
                        List<Author> chunk = pending.subList(idx - idx % batch, Math.min(pending.size(), idx - idx % batch + batch));
                        sql("select id, author_id from book where author_id in (" + chunk.stream().map(x -> String.valueOf(x.id)).collect(Collectors.joining(",")) + ")");
                        for (Author c : chunk) c.prime(BOOKS.stream().filter(b -> b[1] == c.id).map(b -> b[0]).collect(Collectors.toList()));
                    }
                    return super.bookIds;
                }
            };
            pending.add(au);
            out.add(au);
        }
        return out;
    }

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    static void reset() { queries = 0; SQL.clear(); }

    static int countBooks(List<Author> authors) { int n = 0; for (Author a : authors) n += a.getBooks().size(); return n; }

    public static void main(String[] args) {
        for (long i = 1; i <= 100; i++) {
            AUTHORS.add(new long[]{i});
            AUTHOR_NAME.put(i, "Author-" + i);
            for (int b = 0; b < 3; b++) BOOKS.add(new long[]{i * 10 + b, i});
        }

        section("1. Naive: iterate authors and touch author.getBooks()  ->  1 + N queries");
        reset();
        int books = countBooks(findAllAuthors());
        System.out.println("  books=" + books + "  queries=" + queries + "  first three: " + SQL.subList(0, 3));
        System.out.println("  100 authors => 101 round trips. On a 2 ms network hop that is 200 ms of pure waiting, per request.");

        section("2. Fix A: JOIN FETCH / @EntityGraph -> 1 query");
        reset();
        books = countBooks(findAllWithBooksJoinFetch());
        System.out.println("  books=" + books + "  queries=" + queries + "  " + SQL);
        System.out.println("  Caveats: fetching TWO collections multiplies rows (cartesian product) / MultipleBagFetchException;");
        System.out.println("           with pagination Hibernate paginates IN MEMORY (HHH000104 warning) - use a two-step query instead.");

        section("3. Fix B: @BatchSize(size = 25) (or hibernate.default_batch_fetch_size) -> 1 + N/25");
        reset();
        books = countBooks(findAllWithBatchSize(25));
        System.out.println("  books=" + books + "  queries=" + queries);
        System.out.println("  Works with pagination and multiple collections; a good global default (e.g. 16-50).");

        section("4. Fix C: project only what the use case needs (DTO / interface projection)");
        reset();
        sql("select a.id, a.name, count(b.id) from author a left join book b on b.author_id = a.id group by a.id, a.name");
        System.out.println("  queries=" + queries + "  -> no entities, no lazy proxies, no dirty checking, less memory");
        System.out.println("  Use entities for write models; projections for read models (list screens, reports).");

        section("5. Related traps");
        System.out.println("  LazyInitializationException : touching a lazy association after the session/transaction closed.");
        System.out.println("     fix by fetching what you need in the transaction; avoid spring.jpa.open-in-view=true (hides N+1 into the view layer).");
        System.out.println("  @ManyToOne / @OneToOne default to EAGER: set fetch = LAZY explicitly.");
        System.out.println("  Detect: spring.jpa.show-sql / hibernate.generate_statistics, datasource-proxy, or a test asserting query count.");
        System.out.println("  First-level cache = per EntityManager; second-level cache (Ehcache/Redis) is opt-in and needs invalidation thought.");
    }
}

// EXERCISE: write a test helper that fails when a use case issues more than N queries.
