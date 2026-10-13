/*
 * 01 - Test doubles (dummy, stub, fake, spy, mock) built by hand, plus a mini test runner
 *
 * Run:  java 01_test_doubles_and_mockito_by_hand.java
 *
 * Mockito and JUnit are conveniences over these ideas. Seeing them without a library makes
 * "stub vs mock", "state vs interaction testing" and "what should I NOT mock" easy to answer.
 */
import java.lang.reflect.*;
import java.util.*;
import java.util.function.*;

class TestDoublesAndMockitoByHand {

    // ---- code under test
    interface PaymentGateway { boolean charge(String customer, int cents); }
    interface Notifier { void send(String to, String msg); }
    interface OrderRepository { void save(String orderId, String status); Optional<String> find(String orderId); }

    static class CheckoutService {
        private final PaymentGateway gateway; private final OrderRepository repo; private final Notifier notifier;
        CheckoutService(PaymentGateway g, OrderRepository r, Notifier n) { gateway = g; repo = r; notifier = n; }
        String checkout(String orderId, String customer, int cents) {
            if (cents <= 0) throw new IllegalArgumentException("amount must be positive");
            boolean paid = gateway.charge(customer, cents);
            repo.save(orderId, paid ? "PAID" : "PAYMENT_FAILED");
            if (paid) notifier.send(customer, "Order " + orderId + " confirmed");
            return paid ? "PAID" : "PAYMENT_FAILED";
        }
    }

    // ---- hand-written doubles
    static class StubGateway implements PaymentGateway {                  // STUB: canned answers
        final boolean answer; StubGateway(boolean a) { answer = a; }
        public boolean charge(String c, int cents) { return answer; }
    }
    static class FakeRepo implements OrderRepository {                    // FAKE: working lightweight implementation
        final Map<String, String> data = new HashMap<>();
        public void save(String id, String s) { data.put(id, s); }
        public Optional<String> find(String id) { return Optional.ofNullable(data.get(id)); }
    }
    static class SpyNotifier implements Notifier {                        // SPY: records calls for later assertions
        final List<String> sent = new ArrayList<>();
        public void send(String to, String msg) { sent.add(to + ": " + msg); }
    }

    // ---- a ~20-line Mockito: dynamic proxy that records invocations and supports verify()
    static class Mock<T> implements InvocationHandler {
        final List<String> calls = new ArrayList<>();
        final Map<String, Object> stubs = new HashMap<>();
        @SuppressWarnings("unchecked")
        T proxy(Class<T> type) { return (T) Proxy.newProxyInstance(type.getClassLoader(), new Class<?>[]{type}, this); }
        public Object invoke(Object p, Method m, Object[] a) {
            String key = m.getName() + Arrays.toString(a);
            calls.add(key);
            Object r = stubs.get(key);
            if (r == null && m.getReturnType() == boolean.class) return false;
            return r;
        }
        void when(String call, Object returns) { stubs.put(call, returns); }
        void verify(String call, int times) {
            long n = calls.stream().filter(call::equals).count();
            if (n != times) throw new AssertionError("expected " + times + "x " + call + " but was " + n + " in " + calls);
        }
        void verifyNever(String method) {
            if (calls.stream().anyMatch(c -> c.startsWith(method + "["))) throw new AssertionError("unexpected call to " + method + ": " + calls);
        }
    }

    // ---- mini runner
    static int passed = 0, failed = 0;
    static void test(String name, Runnable body) {
        try { body.run(); passed++; System.out.println("  PASS " + name); }
        catch (AssertionError | RuntimeException e) { failed++; System.out.println("  FAIL " + name + " -> " + e.getMessage()); }
    }
    static void assertEquals(Object expected, Object actual) {
        if (!Objects.equals(expected, actual)) throw new AssertionError("expected <" + expected + "> but was <" + actual + ">");
    }
    static void assertThrows(Class<? extends Throwable> type, Runnable r) {
        try { r.run(); } catch (Throwable t) { if (type.isInstance(t)) return; throw new AssertionError("wrong exception " + t); }
        throw new AssertionError("expected " + type.getSimpleName());
    }

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    public static void main(String[] args) {
        section("1. State-based test with a stub + fake + spy (Arrange / Act / Assert)");
        test("successful payment saves PAID and notifies", () -> {
            FakeRepo repo = new FakeRepo(); SpyNotifier spy = new SpyNotifier();
            CheckoutService svc = new CheckoutService(new StubGateway(true), repo, spy);
            String result = svc.checkout("o-1", "alice", 500);
            assertEquals("PAID", result);
            assertEquals(Optional.of("PAID"), repo.find("o-1"));
            assertEquals(Collections.singletonList("alice: Order o-1 confirmed"), spy.sent);
        });
        test("declined payment saves PAYMENT_FAILED and sends nothing", () -> {
            FakeRepo repo = new FakeRepo(); SpyNotifier spy = new SpyNotifier();
            new CheckoutService(new StubGateway(false), repo, spy).checkout("o-2", "bob", 500);
            assertEquals(Optional.of("PAYMENT_FAILED"), repo.find("o-2"));
            assertEquals(0, spy.sent.size());
        });
        test("invalid amount is rejected", () ->
            assertThrows(IllegalArgumentException.class, () -> new CheckoutService(new StubGateway(true), new FakeRepo(), new SpyNotifier()).checkout("o-3", "c", 0)));

        section("2. Interaction-based test with a mock (verify calls)");
        test("gateway is charged exactly once with the right arguments", () -> {
            Mock<PaymentGateway> gw = new Mock<>(); gw.when("charge[alice, 500]", true);
            Mock<Notifier> notifier = new Mock<>();
            CheckoutService svc = new CheckoutService(gw.proxy(PaymentGateway.class), new FakeRepo(), notifier.proxy(Notifier.class));
            svc.checkout("o-4", "alice", 500);
            gw.verify("charge[alice, 500]", 1);
            notifier.verify("send[alice, Order o-4 confirmed]", 1);
        });
        test("no notification when payment fails (verifyNever)", () -> {
            Mock<Notifier> notifier = new Mock<>();
            new CheckoutService(new StubGateway(false), new FakeRepo(), notifier.proxy(Notifier.class)).checkout("o-5", "d", 100);
            notifier.verifyNever("send");
        });
        test("deliberately failing test shows the failure message", () -> assertEquals("PAID", "PAYMENT_FAILED"));

        System.out.println("\n  result: " + passed + " passed, " + failed + " failed (the last failure is intentional)");

        section("3. What to mock and what not to");
        System.out.println("  Mock: slow/non-deterministic/external edges (HTTP clients, time, random, message producers).");
        System.out.println("  Don't mock: value objects, the class under test, JDK types, and ORM/DB behaviour you actually depend on");
        System.out.println("              -> use Testcontainers (real PostgreSQL/Kafka/MongoDB) for repository and messaging tests.");
        System.out.println("  Too many mocks / verify() on every call = tests that mirror the implementation and break on every refactor.");

        section("4. Spring Boot test slices (know the names)");
        System.out.println("  @WebMvcTest(Controller.class)  + MockMvc + @MockBean : web layer only, fast");
        System.out.println("  @DataJpaTest                   + Testcontainers      : repositories, transactions rolled back");
        System.out.println("  @SpringBootTest(webEnvironment=RANDOM_PORT)          : full app + TestRestTemplate/WebTestClient");
        System.out.println("  @EmbeddedKafka or Testcontainers KafkaContainer      : producers/consumers/DLT behaviour");
        System.out.println("  Pyramid: many unit tests, fewer slice/integration tests, very few end-to-end; contract tests (Pact/Spring Cloud Contract) between services.");
    }
}

// EXERCISE: add argument matchers (anyString(), eq()) and 'thenThrow' to the Mock class.
