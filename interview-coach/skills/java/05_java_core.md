---
id: java-core
title: Java 8, Java 11 & modern Java
order: 5
summary: OOP, collections, streams, lambdas, Optional, CompletableFuture, concurrency, Java 11-21.
crib: java/java-interview-prep/topics/01-java-core-collections-java8.md, java/java-interview-prep/topics/02-modern-java-11-to-25.md, java/java-interview-prep/topics/03-concurrency-multithreading.md
docs: java/java-interview-prep/deep_dive/01_java8_core.md, java/java-interview-prep/deep_dive/02_collections.md, java/java-interview-prep/deep_dive/03_java11_and_modern.md, java/java-interview-prep/deep_dive/04_concurrency.md
examples: java/java-interview-prep/examples/01_java8_core
keywords: java, jdk, jre, jvm, oop, interface, abstract, string, immutable, equals, hashcode, hashmap, arraylist, linkedlist, collection, collections, concurrenthashmap, stream, streams, lambda, functional interface, optional, method reference, completablefuture, thread, threads, executor, synchronized, volatile, lock, deadlock, java 8, java 11, java 17, java 21, record, sealed, virtual thread, var, exception, checked, generics, final, static, garbage, gc, heap, stack, memory, classloader, class, object, variable, type casting, casting, primitive, enum, overloading, overriding, overload, override, encapsulation, polymorphism, abstraction, finally, try, catch, main method, map, flatmap, short-circuit, cohesion, coupling, association, aggregation, composition, this(), super(), constructor, instance variable
---
Skill focus for Java 8, Java 11 & modern Java answers:
- Even for language questions, anchor in a real situation (a parallel stream that slowed a service, a HashMap key mutated after insert, CompletableFuture starving the common pool).
- Java 8: streams (lazy, stateless vs stateful ops), Optional misuse, functional interfaces, CompletableFuture and its default pool.
- Java 11: HttpClient, var, String/Files APIs. Java 17/21: records, sealed types, pattern matching, virtual threads - say which version.
- Collections and concurrency internals at the depth an experienced developer is expected to know (HashMap resize/treeify, ConcurrentHashMap, happens-before).
