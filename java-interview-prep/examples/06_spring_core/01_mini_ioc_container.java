/*
 * 01 - A miniature Spring IoC container (pure JDK, reflection + annotations)
 *
 * Run:  java 01_mini_ioc_container.java
 *
 * This mirrors the SHAPE of Spring: @Component, @Autowired constructor injection, @Scope,
 * @PostConstruct/@PreDestroy, BeanPostProcessor, circular-dependency detection. Reading it
 * is the fastest way to answer "how does Spring actually create beans?".
 */
import java.lang.annotation.*;
import java.lang.reflect.*;
import java.util.*;

class MiniIocContainer {

    // ---- the "framework" annotations
    @Retention(RetentionPolicy.RUNTIME) @interface Component { }
    @Retention(RetentionPolicy.RUNTIME) @interface Prototype { }              // like @Scope("prototype")
    @Retention(RetentionPolicy.RUNTIME) @interface PostConstruct { }
    @Retention(RetentionPolicy.RUNTIME) @interface PreDestroy { }

    interface BeanPostProcessor {
        default Object before(Object bean, String name) { return bean; }
        default Object after(Object bean, String name) { return bean; }       // AOP proxies are created HERE in Spring
    }

    // ---- the container
    static class Container {
        private final Map<Class<?>, Object> singletons = new LinkedHashMap<>();
        private final Set<Class<?>> registered = new LinkedHashSet<>();
        private final List<BeanPostProcessor> processors = new ArrayList<>();
        private final Deque<Class<?>> creating = new ArrayDeque<>();           // for cycle detection
        final List<String> events = new ArrayList<>();

        void register(Class<?>... classes) { registered.addAll(Arrays.asList(classes)); }
        void addPostProcessor(BeanPostProcessor p) { processors.add(p); }

        void refresh() {                                                        // eagerly create singletons, like ApplicationContext
            for (Class<?> c : registered) if (!c.isAnnotationPresent(Prototype.class)) getBean(c);
        }

        @SuppressWarnings("unchecked")
        <T> T getBean(Class<T> type) {
            Class<?> impl = resolve(type);
            boolean prototype = impl.isAnnotationPresent(Prototype.class);
            if (!prototype && singletons.containsKey(impl)) return (T) singletons.get(impl);
            if (creating.contains(impl)) {
                throw new IllegalStateException("Circular dependency: " + path(impl));
            }
            creating.push(impl);
            try {
                Object bean = instantiate(impl);
                bean = applyProcessors(bean, impl.getSimpleName());
                if (!prototype) singletons.put(impl, bean);
                return (T) bean;
            } finally { creating.pop(); }
        }

        private Class<?> resolve(Class<?> type) {                              // interface -> the single registered implementation
            if (!type.isInterface()) return type;
            List<Class<?>> impls = new ArrayList<>();
            for (Class<?> c : registered) if (type.isAssignableFrom(c)) impls.add(c);
            if (impls.size() != 1) throw new IllegalStateException(
                    impls.isEmpty() ? "NoSuchBeanDefinition: " + type.getSimpleName()
                                    : "NoUniqueBeanDefinition: " + type.getSimpleName() + " matches " + impls);
            return impls.get(0);
        }

        private Object instantiate(Class<?> impl) {
            try {
                Constructor<?> ctor = impl.getDeclaredConstructors()[0];       // single constructor => implicit @Autowired
                ctor.setAccessible(true);
                Object[] args = Arrays.stream(ctor.getParameterTypes()).map(this::getBean).toArray();
                events.add("instantiate " + impl.getSimpleName() + Arrays.toString(Arrays.stream(args).map(a -> a.getClass().getSimpleName()).toArray()));
                return ctor.newInstance(args);
            } catch (ReflectiveOperationException e) {
                throw new IllegalStateException("cannot create " + impl.getSimpleName(), e);
            }
        }

        private Object applyProcessors(Object bean, String name) {
            for (BeanPostProcessor p : processors) bean = p.before(bean, name);
            invokeAnnotated(bean, PostConstruct.class);
            for (BeanPostProcessor p : processors) bean = p.after(bean, name);
            return bean;
        }

        void close() {
            List<Object> beans = new ArrayList<>(singletons.values());
            Collections.reverse(beans);                                         // destroy in reverse creation order
            for (Object b : beans) invokeAnnotated(b, PreDestroy.class);
        }

        private void invokeAnnotated(Object bean, Class<? extends Annotation> ann) {
            for (Method m : bean.getClass().getDeclaredMethods()) {
                if (m.isAnnotationPresent(ann)) {
                    try { m.setAccessible(true); m.invoke(bean); events.add("@" + ann.getSimpleName() + " " + bean.getClass().getSimpleName() + "." + m.getName()); }
                    catch (ReflectiveOperationException e) { throw new IllegalStateException(e); }
                }
            }
        }

        private String path(Class<?> again) {
            List<String> names = new ArrayList<>();
            Iterator<Class<?>> it = creating.descendingIterator();
            while (it.hasNext()) names.add(it.next().getSimpleName());
            names.add(again.getSimpleName());
            return String.join(" -> ", names);
        }
    }

    // ---- application beans
    interface PaymentGateway { String charge(int cents); }

    @Component static class StripeGateway implements PaymentGateway {
        public String charge(int cents) { return "charged " + cents + " via stripe"; }
    }

    @Component static class PayPalGateway implements PaymentGateway {
        public String charge(int cents) { return "charged " + cents + " via paypal"; }
    }

    @Component static class OrderRepository {
        @PostConstruct void init() { /* e.g. warm a cache */ }
        @PreDestroy void close() { /* e.g. close a pool */ }
        String save(String o) { return "saved " + o; }
    }

    @Component static class OrderService {
        private final OrderRepository repo;          // constructor injection: final, required, testable without Spring
        private final PaymentGateway gateway;
        OrderService(OrderRepository repo, PaymentGateway gateway) { this.repo = repo; this.gateway = gateway; }
        String place(String id) { return repo.save(id) + "; " + gateway.charge(500); }
    }

    @Component @Prototype static class ShoppingCart { final List<String> items = new ArrayList<>(); }

    // circular pair
    @Component static class CycleA { CycleA(CycleB b) { } }
    @Component static class CycleB { CycleB(CycleA a) { } }

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    public static void main(String[] args) {
        section("1. Wiring, singleton scope and lifecycle");
        Container ctx = new Container();
        ctx.register(StripeGateway.class, OrderRepository.class, OrderService.class, ShoppingCart.class);
        ctx.addPostProcessor(new BeanPostProcessor() {
            @Override public Object after(Object bean, String name) { ctx.events.add("BeanPostProcessor.after(" + name + ")"); return bean; }
        });
        ctx.refresh();
        OrderService svc = ctx.getBean(OrderService.class);
        System.out.println("  " + svc.place("order-1"));
        System.out.println("  same singleton instance returned twice: " + (svc == ctx.getBean(OrderService.class)));
        ctx.close();
        ctx.events.forEach(e -> System.out.println("    event: " + e));

        section("2. Prototype scope: a new instance every time");
        ShoppingCart c1 = ctx.getBean(ShoppingCart.class), c2 = ctx.getBean(ShoppingCart.class);
        System.out.println("  c1 == c2 ? " + (c1 == c2));
        System.out.println("  Trap: injecting a prototype into a singleton injects it ONCE. Use ObjectProvider<T>/@Lookup/scoped proxy.");

        section("3. Programming to an interface: ambiguity and missing beans");
        Container amb = new Container();
        amb.register(StripeGateway.class, PayPalGateway.class);
        try { amb.getBean(PaymentGateway.class); } catch (IllegalStateException e) { System.out.println("  " + e.getMessage().replace("class MiniIocContainer$", "")); }
        System.out.println("  Spring fixes ambiguity with @Primary or @Qualifier(\"name\").");
        try { new Container().getBean(PaymentGateway.class); } catch (IllegalStateException e) { System.out.println("  " + e.getMessage()); }

        section("4. Circular constructor dependency fails fast");
        Container cyc = new Container();
        cyc.register(CycleA.class, CycleB.class);
        try { cyc.refresh(); } catch (IllegalStateException e) { System.out.println("  " + e.getMessage()); }
        System.out.println("  Spring Boot 2.6+ forbids cycles by default; fix the design (extract a third bean / use events), not with @Lazy.");

        section("5. Why constructor injection wins");
        OrderService manual = new OrderService(new OrderRepository(), cents -> "fake charge " + cents);   // no Spring needed in a unit test
        System.out.println("  unit test without a container: " + manual.place("t-1"));
    }
}

// EXERCISE: add @Qualifier support and setter injection; then break something by injecting a
// prototype into a singleton and show the single shared instance.
