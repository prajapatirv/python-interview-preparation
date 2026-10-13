/*
 * 01 - Spring Boot auto-configuration and externalized configuration, simulated
 *
 * Run:  java 01_autoconfiguration_and_externalized_config.java
 *
 * Shows WHY "just add the starter and it works": auto-configurations are candidates guarded by
 * conditions (@ConditionalOnClass / OnMissingBean / OnProperty). Your own bean makes the default
 * "back off". Then the property-source precedence that decides which value wins.
 */
import java.util.*;
import java.util.function.*;

class AutoConfigurationAndConfig {

    // ---- a tiny environment: ordered property sources, first match wins (highest precedence first)
    static class Environment {
        final LinkedHashMap<String, Map<String, String>> sources = new LinkedHashMap<>();
        final Set<String> classpath = new HashSet<>();
        Environment source(String name, Map<String, String> props) { sources.put(name, props); return this; }
        String get(String key) {
            for (Map<String, String> s : sources.values()) if (s.containsKey(key)) return s.get(key);
            return null;
        }
        String origin(String key) {
            for (Map.Entry<String, Map<String, String>> e : sources.entrySet()) if (e.getValue().containsKey(key)) return e.getKey();
            return "<not set>";
        }
    }

    // ---- the registry of beans plus condition evaluation report (what --debug prints)
    static class Context {
        final Environment env;
        final Map<String, Object> beans = new LinkedHashMap<>();
        final List<String> report = new ArrayList<>();
        Context(Environment env) { this.env = env; }
        boolean hasBean(String name) { return beans.containsKey(name); }
    }

    static class AutoConfig {
        final String name;
        final List<Predicate<Context>> conditions = new ArrayList<>();
        final List<String> reasons = new ArrayList<>();
        final Consumer<Context> body;
        AutoConfig(String name, Consumer<Context> body) { this.name = name; this.body = body; }
        AutoConfig onClass(String cls) { conditions.add(c -> c.env.classpath.contains(cls)); reasons.add("@ConditionalOnClass(" + cls + ")"); return this; }
        AutoConfig onMissingBean(String bean) { conditions.add(c -> !c.hasBean(bean)); reasons.add("@ConditionalOnMissingBean(" + bean + ")"); return this; }
        AutoConfig onProperty(String k, String v) { conditions.add(c -> v.equals(c.env.get(k))); reasons.add("@ConditionalOnProperty(" + k + "=" + v + ")"); return this; }
        void apply(Context ctx) {
            for (int i = 0; i < conditions.size(); i++) {
                if (!conditions.get(i).test(ctx)) { ctx.report.add("  NOT matched: " + name + "  -> " + reasons.get(i) + " failed"); return; }
            }
            ctx.report.add("  matched    : " + name);
            body.accept(ctx);
        }
    }

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    static List<AutoConfig> autoConfigs() {
        return Arrays.asList(
            new AutoConfig("DataSourceAutoConfiguration", c -> c.beans.put("dataSource", "HikariDataSource(" + c.env.get("spring.datasource.url") + ")"))
                .onClass("com.zaxxer.hikari.HikariDataSource").onMissingBean("dataSource"),
            new AutoConfig("JacksonAutoConfiguration", c -> c.beans.put("objectMapper", "default ObjectMapper"))
                .onClass("com.fasterxml.jackson.databind.ObjectMapper").onMissingBean("objectMapper"),
            new AutoConfig("KafkaAutoConfiguration", c -> c.beans.put("kafkaTemplate", "KafkaTemplate(" + c.env.get("spring.kafka.bootstrap-servers") + ")"))
                .onClass("org.apache.kafka.clients.producer.KafkaProducer").onMissingBean("kafkaTemplate"),
            new AutoConfig("MongoAutoConfiguration", c -> c.beans.put("mongoClient", "MongoClient"))
                .onClass("com.mongodb.client.MongoClient"),
            new AutoConfig("RedisCacheAutoConfiguration", c -> c.beans.put("cacheManager", "RedisCacheManager"))
                .onClass("org.springframework.data.redis.core.RedisTemplate").onProperty("spring.cache.type", "redis")
        );
    }

    public static void main(String[] args) {

        section("1. Starters put classes on the classpath; conditions decide what is configured");
        Environment env = new Environment()
                .source("application.yml", mapOf("spring.datasource.url", "jdbc:postgresql://db/orders", "spring.kafka.bootstrap-servers", "localhost:9092"));
        env.classpath.addAll(Arrays.asList("com.zaxxer.hikari.HikariDataSource", "com.fasterxml.jackson.databind.ObjectMapper",
                "org.apache.kafka.clients.producer.KafkaProducer"));      // like spring-boot-starter-web + data-jpa + spring-kafka
        Context ctx = new Context(env);
        autoConfigs().forEach(a -> a.apply(ctx));
        ctx.report.forEach(System.out::println);
        System.out.println("  resulting beans: " + ctx.beans.keySet());
        System.out.println("  (Real Spring: run with --debug or hit /actuator/conditions for the same report.)");

        section("2. Your own bean wins: auto-config 'backs off' via @ConditionalOnMissingBean");
        Context custom = new Context(env);
        custom.beans.put("objectMapper", "MY ObjectMapper (FAIL_ON_UNKNOWN_PROPERTIES=false, JavaTimeModule)");
        autoConfigs().forEach(a -> a.apply(custom));
        System.out.println("  objectMapper = " + custom.beans.get("objectMapper"));
        System.out.println("  Rule: define a @Bean of the same type to customise; use @ConditionalOn... in your own starters.");

        section("3. Property precedence (highest first) - which value wins?");
        Environment layered = new Environment()
                .source("command line (--server.port=9090)", mapOf("server.port", "9090"))
                .source("OS environment (SERVER_PORT/LOG_LEVEL)", mapOf("logging.level.root", "WARN", "app.timeout", "5s"))
                .source("application-prod.yml", mapOf("app.timeout", "2s", "app.region", "eu-west-1"))
                .source("application.yml", mapOf("server.port", "8080", "app.timeout", "10s", "app.region", "us-east-1", "app.name", "orders"));
        for (String key : new String[]{"server.port", "app.timeout", "app.region", "app.name", "logging.level.root"}) {
            System.out.printf("  %-20s = %-8s (from %s)%n", key, layered.get(key), layered.origin(key));
        }
        System.out.println("  Real order (summary): CLI args > SPRING_APPLICATION_JSON > OS env vars > profile files > application.yml > @PropertySource > defaults.");

        section("4. Relaxed binding: one setting, many spellings");
        for (String s : new String[]{"app.max-pool-size", "app.maxPoolSize", "APP_MAXPOOLSIZE", "app.max_pool_size"}) {
            System.out.printf("  %-20s -> canonical 'app.max-pool-size': %s%n", s, canonical(s).equals("app.max-pool-size"));
        }
        System.out.println("  Prefer kebab-case in files and UPPER_SNAKE in environment variables (Kubernetes/Docker).");

        section("5. Profiles");
        System.out.println("  spring.profiles.active=prod loads application-prod.yml on top of application.yml.");
        System.out.println("  @Profile(\"!prod\") on a bean limits it; use profiles for BEHAVIOUR, env vars/secret stores for VALUES.");
        System.out.println("  Never commit secrets: Vault / AWS Secrets Manager / Kubernetes Secrets, injected as env vars.");
    }

    static String canonical(String s) {
        String x = s.replace('_', '-').replaceAll("([a-z])([A-Z])", "$1-$2").toLowerCase();
        if (!x.contains(".")) x = x.replaceFirst("-", ".");   // APP_MAXPOOLSIZE style has no dots
        return x.replace("maxpoolsize", "max-pool-size");
    }

    static Map<String, String> mapOf(String... kv) {
        Map<String, String> m = new LinkedHashMap<>();
        for (int i = 0; i < kv.length; i += 2) m.put(kv[i], kv[i + 1]);
        return m;
    }
}

// EXERCISE: add an @ConditionalOnWebApplication-style condition and a user-supplied exclusion list
// (spring.autoconfigure.exclude) that removes DataSourceAutoConfiguration.
