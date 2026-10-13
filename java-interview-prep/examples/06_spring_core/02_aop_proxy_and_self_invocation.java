/*
 * 02 - How Spring AOP / @Transactional really works: proxies and the self-invocation trap
 *
 * Run:  java 02_aop_proxy_and_self_invocation.java
 *
 * Spring wraps your bean in a proxy; the proxy runs advice (begin tx / commit / rollback), then
 * delegates to the real object. A call from INSIDE the object never goes through the proxy.
 * Here the proxy is a JDK dynamic proxy - the same mechanism Spring uses for interface-based beans.
 */
import java.lang.annotation.*;
import java.lang.reflect.*;
import java.util.*;

class AopProxyAndSelfInvocation {

    @Retention(RetentionPolicy.RUNTIME) @Target(ElementType.METHOD) @interface Transactional { }

    static final List<String> LOG = new ArrayList<>();

    interface TransferService {
        void transfer(String from, String to, int amount);
        void audit(String msg);                     // annotated, but see the self-invocation demo
        void failing();
    }

    static class TransferServiceImpl implements TransferService {
        @Transactional
        public void transfer(String from, String to, int amount) {
            LOG.add("  business: move " + amount + " " + from + " -> " + to);
            audit("transfer done");                // THIS CALL IS this.audit(...): bypasses the proxy
        }
        @Transactional
        public void audit(String msg) { LOG.add("  business: audit '" + msg + "'"); }
        @Transactional
        public void failing() { throw new IllegalStateException("insufficient funds"); }
    }

    /** What @EnableTransactionManagement + TransactionInterceptor do, in 25 lines. */
    static class TxHandler implements InvocationHandler {
        private final Object target;
        TxHandler(Object target) { this.target = target; }

        @Override public Object invoke(Object proxy, Method m, Object[] args) throws Throwable {
            Method impl = target.getClass().getMethod(m.getName(), m.getParameterTypes());
            if (!impl.isAnnotationPresent(Transactional.class)) return invoke0(impl, args);
            LOG.add("[tx] BEGIN  (" + m.getName() + ")");
            try {
                Object r = invoke0(impl, args);
                LOG.add("[tx] COMMIT (" + m.getName() + ")");
                return r;
            } catch (InvocationTargetException e) {
                Throwable cause = e.getCause();
                // Spring's default: roll back on RuntimeException/Error, COMMIT on checked exceptions.
                boolean rollback = cause instanceof RuntimeException || cause instanceof Error;
                LOG.add("[tx] " + (rollback ? "ROLLBACK" : "COMMIT") + " (" + m.getName() + ") because " + cause.getClass().getSimpleName());
                throw cause;
            }
        }
        private Object invoke0(Method impl, Object[] args) throws Throwable {
            try { return impl.invoke(target, args); }
            catch (InvocationTargetException e) { throw e; }
        }
    }

    static void flush() { LOG.forEach(System.out::println); LOG.clear(); }
    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    public static void main(String[] args) {
        TransferService proxy = (TransferService) Proxy.newProxyInstance(
                TransferService.class.getClassLoader(),
                new Class<?>[]{TransferService.class},
                new TxHandler(new TransferServiceImpl()));

        section("1. Calling through the proxy: transaction wraps the method");
        proxy.audit("direct call");
        flush();

        section("2. Self-invocation: transfer() -> this.audit() has NO transaction of its own");
        proxy.transfer("A", "B", 10);
        flush();
        System.out.println("  Look: only ONE BEGIN/COMMIT (for transfer). audit() ran inside it, advice for audit was skipped.");
        System.out.println("  With REQUIRES_NEW on audit() you would silently NOT get a new transaction. Same for @Async, @Cacheable, @Retryable.");

        section("3. Rollback rule: runtime exceptions roll back, checked ones do not");
        try { proxy.failing(); } catch (IllegalStateException e) { System.out.println("  caller saw: " + e.getMessage()); }
        flush();
        System.out.println("  Use @Transactional(rollbackFor = Exception.class) if checked exceptions must roll back.");

        section("4. Fixes for self-invocation");
        System.out.println("  1. Move the method to another bean (cleanest) - call crosses the proxy boundary.");
        System.out.println("  2. Inject the bean into itself via @Lazy / ObjectProvider and call self.audit().");
        System.out.println("  3. AspectJ weaving (mode = ASPECTJ) - advice is compiled into the class, no proxy needed.");

        section("5. JDK proxy vs CGLIB");
        System.out.println("  JDK dynamic proxy : requires an interface; proxy implements the interface.");
        System.out.println("  CGLIB             : subclasses the class -> cannot proxy final classes/methods; Boot defaults to CGLIB (proxyTargetClass=true).");
        System.out.println("  Consequence: private/final methods and direct field access on a proxied bean see the proxy, not the target.");
        System.out.println("  proxy class is a JDK proxy: " + Proxy.isProxyClass(proxy.getClass()) + "  (" + proxy.getClass().getSimpleName().replaceAll("[0-9]+", "N") + ")");
    }
}

// EXERCISE: add a @Cacheable-style advice to the same handler and show it is also skipped on self-invocation.
