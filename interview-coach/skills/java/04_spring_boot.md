---
id: spring-boot
title: Spring & Spring Boot
order: 4
summary: IoC/DI, auto-configuration, profiles, transactions, data access, security, actuator.
crib: java/java-interview-prep/topics/05-spring-core-boot.md, java/java-interview-prep/topics/06-spring-data-jpa-transactions-security.md
docs: java/java-interview-prep/deep_dive/06_spring_core.md, java/java-interview-prep/deep_dive/07_spring_boot.md, java/java-interview-prep/deep_dive/09_spring_data_jpa.md, java/java-interview-prep/deep_dive/10_spring_security.md, java/java-interview-prep/company-chase-travel/brush-up/02-database-connection-spring-boot.md
examples: java/java-interview-prep/examples/07_spring_boot
keywords: spring, spring boot, bean, autowired, dependency injection, ioc, auto-configuration, autoconfiguration, @transactional, transaction, propagation, jpa, hibernate, n+1, spring data, actuator, profile, application.yml, properties, spring security, jwt, oauth, @springbootapplication, aop, proxy, starter, controller advice, autowire, cross-cutting, concern, aspect
---
Skill focus for Spring & Spring Boot answers:
- Explain the mechanism behind the magic: proxies (why @Transactional fails on self-invocation or private methods), bean lifecycle, auto-configuration conditions.
- Production stories: transactions that did not roll back, N+1 queries, connection-pool exhaustion, slow startup, wrong profile in prod.
- Actuator, Micrometer metrics, health groups for Kubernetes probes.
- Security: stateless JWT vs sessions, method security, CORS/CSRF trade-offs.
