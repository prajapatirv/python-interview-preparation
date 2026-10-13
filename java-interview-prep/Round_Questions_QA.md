# Interview round question bank (simple language)

This file answers a real list of interview questions in **plain, simple English**. Every answer has the same
three parts:

1. **Simple answer** - what it is, like you would explain to a friend.
2. **Key points** - the few things the interviewer wants to hear.
3. **Real-life example** - one small, industry-style scenario (banking, e-commerce, etc.), with tiny code where it helps.

Deeper material, if you want it: **G** = `Java_SpringBoot_Kafka_Interview_QA_Guide.md`,
**S** = `Docx_Gap_Supplement_QA.md`, **D** = `deep_dive/`.

| Section | IDs | Count |
|---|---|---|
| A. Cybage list | A1-A9 | 9 |
| B. Fresher | F1-F27 | 27 |
| C. Experienced | E1-E38 | 38 |
| D. Kafka round | K1-K18 | 18 |
| E. Other | O1-O10 | 10 |

> Wording in the source list: "sort circuit" means **short-circuit**; "@configure" means **@Configuration**;
> "concern modifications" is read as **cross-cutting concerns**; "API getway" means **API gateway**.

**How to answer in the interview:** say the simple answer first (10 seconds), then the key points, then the
example. Do not start with the example.

---

# A. Cybage list

## A1. Kafka partitioning

**Simple answer:** A Kafka topic is like a big notice board. To handle lots of messages, Kafka cuts the topic into
smaller pieces called **partitions**. Each partition is a separate line of messages, in order.

**Key points:**
- Messages inside **one partition** stay in order. Across partitions there is no order guarantee.
- If you send a message **with a key** (for example `customerId`), Kafka always puts the same key into the same
  partition. So one customer's messages stay in order.
- If you send **without a key**, Kafka spreads messages across partitions.
- More partitions = more consumers can work at the same time. That is how Kafka scales.

**Real-life example (bank):** Every transaction of account `A101` must be processed in the right order
(deposit, then withdraw). So the bank uses the account number as the key. All `A101` messages go to the same
partition and are processed in order, while other accounts are processed in parallel in other partitions.

```java
kafkaTemplate.send("transactions", "A101", txn);   // "A101" is the key
```

## A2. How to add method-level security in Spring

**Simple answer:** Instead of protecting only URLs, you put the security rule **directly on the method**. Spring
checks the rule before the method runs. If the user is not allowed, the method does not run.

**Key points:**
- Turn it on with `@EnableMethodSecurity` (older versions: `@EnableGlobalMethodSecurity`).
- Use `@PreAuthorize("hasRole('ADMIN')")` to check **before** the method runs.
- Use `@PostAuthorize` to check **after** (for example, "only the owner can see the result").
- It works through a proxy, so calling the method from inside the **same class** (`this.method()`) skips the check.

**Real-life example (HR app):** Any employee can view the employee list, but only an HR manager can delete an employee.

```java
@Configuration
@EnableMethodSecurity
class SecurityConfig { }

@Service
class EmployeeService {
    public List<Employee> findAll() { ... }                 // anyone logged in

    @PreAuthorize("hasRole('HR_MANAGER')")
    public void delete(long id) { ... }                     // only HR manager
}
```

## A3. Spring transaction

**Simple answer:** A transaction means "do all the steps together, or do none". In Spring you just put
`@Transactional` on a method. Spring starts the transaction, and if the method fails, it undoes everything.

**Key points:**
- Default: it **rolls back on unchecked exceptions** (RuntimeException), not on checked ones. Use
  `rollbackFor = Exception.class` if you want that.
- `readOnly = true` for methods that only read data (a bit faster).
- It works through a proxy, so it does **not** work when you call the method from the same class.
- Put it on the **service** layer, not the controller.

**Real-life example (e-commerce):** When a customer places an order, we must (1) save the order and (2) reduce stock.
If stock update fails, the saved order must disappear. Otherwise we have an order without stock reduced.

```java
@Transactional
public void placeOrder(Order order) {
    orderRepository.save(order);           // step 1
    stockRepository.reduce(order);         // step 2 - if this throws, step 1 is undone
}
```

## A4. Database transaction

**Simple answer:** A database transaction is a group of database steps that must **all succeed or all fail**
together. The database guarantees this using the **ACID** rules.

**Key points (ACID in simple words):**
- **Atomic** - all or nothing.
- **Consistent** - data rules (like "balance cannot be negative") are never broken.
- **Isolated** - two users working at the same time do not see each other's half-finished work.
- **Durable** - once committed, the data is safe even if the server crashes.

**Real-life example (bank transfer):** Move 1000 from account 1 to account 2. If the debit works but the credit
fails, money would vanish. The transaction makes sure both happen or neither.

```sql
BEGIN;
UPDATE account SET balance = balance - 1000 WHERE id = 1;
UPDATE account SET balance = balance + 1000 WHERE id = 2;
COMMIT;        -- if anything went wrong: ROLLBACK;
```

## A5. Kafka topic vs queue

**Simple answer:** A **queue** is like a ticket counter: once a person is served, the ticket is gone, and only
one worker gets it. A **Kafka topic** is like a CCTV recording: the data stays for some days and **many different
apps can watch it**, even again from the start.

**Key points:**
- Queue: message is **deleted** after it is consumed. Kafka: message **stays** until the retention time ends.
- Queue: one message goes to **one** consumer. Kafka: **every consumer group** gets every message.
- Kafka lets you **replay** old messages. A normal queue does not.
- Use a queue for "do this job once". Use Kafka for events many systems care about.

**Real-life example (e-commerce):** When an order is placed, the **invoice service**, **warehouse service** and
**analytics service** all need to know. With Kafka, one `OrderPlaced` event is read by all three. With a queue,
only one of them would get it.

## A6. What is Lambda in AWS

**Simple answer:** AWS Lambda lets you run a small piece of code **without managing any server**. You upload the
code, AWS runs it only when something happens (an event), and you pay only for the time it runs.

**Key points:**
- Triggers: file uploaded to S3, an API call, a message in a queue, a timer.
- Scales automatically from 0 to thousands of runs.
- Limits: a run can last at most **15 minutes**; there can be a small **cold start** delay.
- It is **stateless** - do not keep data in memory between runs.
- (It is not the same as a Java lambda expression.)

**Real-life example (insurance):** A customer uploads a claim PDF to S3. That upload triggers a Lambda that reads
the file, extracts the policy number and saves it in the database. No server runs while nobody is uploading.

```java
public class ClaimHandler implements RequestHandler<S3Event, String> {
    public String handleRequest(S3Event event, Context ctx) {
        String file = event.getRecords().get(0).getS3().getObject().getKey();
        return "Processed " + file;
    }
}
```

## A7. How to enable multiple environment configuration in Spring Boot

**Simple answer:** Use **profiles**. You keep one config file for each environment (dev, test, prod) and tell
Spring which profile to use when the app starts.

**Key points:**
- Files: `application.yml` (common), `application-dev.yml`, `application-prod.yml`.
- Choose the profile: `--spring.profiles.active=prod` or env variable `SPRING_PROFILES_ACTIVE=prod`.
- `@Profile("dev")` on a bean means "create this bean only in dev".
- Never put real passwords in these files. Use environment variables or a secrets store.

**Real-life example (any company):** On a developer laptop the app talks to a local database. In production it
must talk to the real database. Same code, different profile.

```yaml
# application-dev.yml
spring.datasource.url: jdbc:postgresql://localhost/shop
# application-prod.yml
spring.datasource.url: jdbc:postgresql://prod-db.company.com/shop
```
```bash
java -jar shop.jar --spring.profiles.active=prod
```

## A8. What is the use of S3

**Simple answer:** S3 (Simple Storage Service) is AWS's **online storage for files**. Think of it as a very
safe, huge hard disk on the internet. You put files (called objects) into folders called **buckets**.

**Key points:**
- Stores any file: images, PDFs, videos, backups, logs.
- Very durable (your file is copied across many places) and almost unlimited in size.
- Cheap, and you pay for what you use.
- Can host a static website, trigger Lambda when a file arrives, and give temporary download links.

**Real-life example (bank):** Customers upload KYC documents. The app saves each file in S3 and keeps only the
S3 file path in the database, because databases are not good at storing big files.

```java
s3.putObject(b -> b.bucket("kyc-documents").key("cust-101/passport.pdf"),
             RequestBody.fromFile(file));
```

## A9. How to archive files on S3

**Simple answer:** Use an **S3 Lifecycle rule**. You tell S3: "after 30 days move this file to cheaper storage,
after 1 year move it to the cheapest archive storage, after 7 years delete it". S3 does it automatically.

**Key points:**
- Storage classes get cheaper but slower to read: **Standard -> Standard-IA -> Glacier -> Glacier Deep Archive**.
- Restoring from Glacier takes minutes to hours and may cost money.
- Turn on **versioning** to protect against accidental delete; use **Object Lock** if the law says "do not change".

**Real-life example (telecom):** Call-detail logs are needed daily for 1 month, then rarely, but the law says keep
them 7 years. A lifecycle rule moves them to Glacier after 90 days and deletes them after 7 years, saving a lot of money.

```json
{"Rules":[{"ID":"archive-logs","Status":"Enabled","Filter":{"Prefix":"logs/"},
  "Transitions":[{"Days":90,"StorageClass":"GLACIER"}],
  "Expiration":{"Days":2555}}]}
```

---

# B. Fresher questions

## F1. How to create a class and an object

**Simple answer:** A **class** is a design (blueprint). An **object** is a real thing made from that design using
the `new` keyword. One class can make many objects.

**Key points:**
- Class has **fields** (data) and **methods** (actions).
- A **constructor** sets the starting values.
- `new` creates the object in memory.

**Real-life example (college app):** `Student` is the blueprint. "Asha, 20" and "Ravi, 21" are two objects.

```java
class Student {
    String name;
    int age;
    Student(String name, int age) { this.name = name; this.age = age; }
    void show() { System.out.println(name + " is " + age); }
}

Student s1 = new Student("Asha", 20);
s1.show();   // Asha is 20
```

## F2. How to create and initialize a variable

**Simple answer:** A variable is a **named box** that stores a value. You write the type, the name, and
(optionally) the starting value: `type name = value;`.

**Key points:**
- Declare: `int age;` Initialize: `age = 25;` Both together: `int age = 25;`
- Local variables **must** be given a value before use.
- `final` makes it a constant (cannot change).
- `var` lets Java guess the type (Java 10+, only inside methods).

**Real-life example (shop billing):**

```java
int quantity = 3;                 // whole number
double price = 49.99;             // decimal
String item = "Pen";              // text
final double GST_RATE = 0.18;     // constant, never changes
double total = quantity * price * (1 + GST_RATE);
```

## F3. Why is Java platform independent

**Simple answer:** When you compile Java, you do not get machine code for one computer. You get **bytecode**.
Every computer has a **JVM** (Java Virtual Machine) that knows how to run that bytecode. So the same program
runs on Windows, Linux and Mac without changes.

**Key points:**
- `.java` -> (compiler `javac`) -> `.class` bytecode -> (JVM) -> runs.
- The **bytecode** is platform independent. The **JVM** is platform dependent (a different JVM per OS).
- This is called "Write Once, Run Anywhere".

**Real-life example (software company):** A team builds a billing application on Windows laptops and deploys the
same `.jar` file to Linux servers in production. They do not rebuild it for Linux.

## F4. How to add a value in an array at a specific position

**Simple answer:** An array has a **fixed size**, so you cannot "insert" directly. You must **shift** the
elements to the right to make space, then put the new value in. Or use an `ArrayList`, which does it for you.

**Key points:**
- `arr[2] = 99;` **replaces** the value at position 2. It does not insert.
- To insert, move elements right using a loop or `System.arraycopy`.
- Easier: `list.add(index, value)` in an `ArrayList`.

**Real-life example (queue at a bank counter):** A VIP customer must be placed at position 2 in the token list.

```java
int[] tokens = {101, 102, 103, 104, 0};     // last slot is free
int position = 2, vipToken = 999;

for (int i = tokens.length - 1; i > position; i--) {
    tokens[i] = tokens[i - 1];              // shift right
}
tokens[position] = vipToken;                // {101, 102, 999, 103, 104}

// Easy way:
List<Integer> list = new ArrayList<>(List.of(101, 102, 103, 104));
list.add(2, 999);
```

## F5. Explain `public static void main(String[] args)`

**Simple answer:** It is the **starting point** of a Java program. When you run the program, the JVM looks for
exactly this method and starts from it.

**Key points (word by word):**
- `public` - the JVM is outside your class, so it must be able to call it.
- `static` - the JVM can call it without creating an object first.
- `void` - it returns nothing.
- `main` - the fixed name the JVM looks for.
- `String[] args` - values given on the command line.

**Real-life example (batch job):** A nightly report program is started with `java Report 2026-01-31`. The date
arrives in `args[0]`.

```java
public class Report {
    public static void main(String[] args) {
        System.out.println("Report for " + args[0]);
    }
}
```

## F6. Difference between heap and stack memory

**Simple answer:** **Stack** is small, fast memory for method calls and local variables. **Heap** is big memory
where all **objects** live. When a method ends, its stack part disappears automatically. Heap objects are cleaned
by the garbage collector.

**Key points:**
| | Stack | Heap |
|---|---|---|
| Stores | local variables, method calls, references | objects, arrays |
| Per thread? | each thread has its own | shared by all threads |
| Cleanup | automatic when method ends | garbage collector |
| Error | `StackOverflowError` (too deep recursion) | `OutOfMemoryError` |
| Size / sizing | small, `-Xss` (about 1 MB per thread) | large, `-Xms` / `-Xmx` |
| Thread safety | local data is private to its thread | shared, needs care for mutable objects |
| Lifetime | tied to the method call | until no longer reachable |

**Real-life example (e-commerce):** In `Order o = new Order();`, the variable `o` (just a pointer) sits on the
stack, and the actual `Order` object with its items sits on the heap.

```text
Stack (this thread)        Heap (shared)
process() frame            Order { id, amount, items -> List }
  qty = 10                    ^
  o  -------------------------+
```

**Senior add-ons:**
- Only **local variables and parameters** are on the stack. A field such as `Department.employee` is part of its heap object.
- Setting `o = null` does not free anything; the object just becomes *eligible* for GC when nothing reachable points to it.
- Because each thread has its own stack, locals are thread-safe; the shared heap is where race conditions live.
- The JIT's *escape analysis* can skip the heap allocation for an object that never leaves a method, so "heap is slow" is a simplification.
- `StackOverflowError` -> look for runaway recursion. `OutOfMemoryError: Java heap space` -> look for a leak or oversized collection (heap dump). Class metadata lives in **Metaspace**, outside the heap.

**Say it in one line:** *Stack is per-thread method execution; heap is shared memory for objects managed by the GC.*
Full answer: `deep_dive/05_jvm_gc_performance.md` Q1.

## F7. What is the collection framework

**Simple answer:** It is Java's **ready-made set of containers** to store and handle groups of objects, so you do
not write your own list or map from scratch.

**Key points:**
- **List** - ordered, allows duplicates (`ArrayList`, `LinkedList`).
- **Set** - no duplicates (`HashSet`, `TreeSet` for sorted).
- **Map** - key and value pairs (`HashMap`, `TreeMap`).
- **Queue** - first in, first out (`ArrayDeque`, `PriorityQueue`).

**Real-life example (e-commerce):**

```java
List<String> cart = new ArrayList<>();            // items in order, duplicates allowed
Set<String> uniqueCities = new HashSet<>();       // each city once
Map<String, Double> priceList = new HashMap<>();  // product -> price
priceList.put("Pen", 10.0);
```

## F8. What is an exception

**Simple answer:** An exception is an **error that happens while the program is running** and breaks the normal
flow (for example, dividing by zero or opening a file that does not exist). Java lets you **catch** it and handle
it so the program does not crash.

**Key points:**
- Handle with `try`, `catch`, `finally`.
- **Checked** exceptions (like `IOException`) - the compiler forces you to handle them.
- **Unchecked** exceptions (like `NullPointerException`) - programming mistakes.
- `throw` raises an exception; `throws` declares it.

**Real-life example (ATM):** If a customer withdraws more than the balance, we throw an exception and show a
friendly message instead of crashing.

```java
try {
    atm.withdraw(5000);
} catch (InsufficientBalanceException e) {
    System.out.println("Not enough balance");
} finally {
    System.out.println("Please take your card");
}
```

## F9. Difference between `==` and `.equals()`

**Simple answer:** `==` checks if two variables point to the **same object**. `.equals()` checks if two objects
have the **same content**.

**Key points:**
- For primitives (`int`, `double`), `==` compares the value.
- For objects, `==` compares the memory address.
- `String`, `Integer` etc. override `equals()` to compare content.
- If you override `equals()`, also override `hashCode()`.

**Real-life example (login):** Comparing the typed password with the saved one must use `equals()`.

```java
String a = new String("hello");
String b = new String("hello");
System.out.println(a == b);        // false - two different objects
System.out.println(a.equals(b));   // true  - same content
```

## F10. Abstract class vs interface

**Simple answer:** An **abstract class** is a half-built class that child classes complete. An **interface** is a
pure contract: "any class that signs this must have these methods".

**Key points:**
| | Abstract class | Interface |
|---|---|---|
| Methods | abstract and normal | abstract (plus `default`/`static` since Java 8) |
| Variables | any | only constants |
| Constructor | yes | no |
| How many can a class use | extend **one** | implement **many** |
| When | shared code/state ("is-a") | a skill ("can-do") |

**Real-life example (payments):** `Payment` abstract class holds common code (amount, logging). `Refundable` is
an interface - only some payment types can be refunded.

```java
abstract class Payment { double amount; void log() { System.out.println("paid " + amount); } abstract void pay(); }
interface Refundable { void refund(); }
class CardPayment extends Payment implements Refundable {
    void pay()    { System.out.println("card paid"); }
    public void refund() { System.out.println("refunded to card"); }
}
```

## F11. The `static` keyword (static variable, method, block, class)

**Simple answer:** `static` means "belongs to the **class**, not to a single object". There is only one copy and
all objects share it.

**Key points:**
- **static variable** - one shared value (like a counter).
- **static method** - call it with the class name, no object needed (`Math.max(1,2)`). It cannot use instance fields directly.
- **static block** - runs **once**, when the class is first loaded. Used for one-time set-up.
- **static nested class** - an inner class that does not need an outer object.

**Real-life example (bank):** The bank's interest rate is the same for all accounts, so it is `static`.

```java
class Account {
    static double interestRate;          // one value for all accounts
    double balance;                      // different for each account

    static {                             // runs once
        interestRate = 4.5;
    }
    static double yearlyInterest(double amount) { return amount * interestRate / 100; }
}
```

## F12. What is garbage collection

**Simple answer:** Garbage collection (GC) is Java's **automatic memory cleaner**. When an object is no longer
used by anyone, the JVM removes it and frees the memory. You do not delete objects yourself.

**Key points:**
- An object is "garbage" when no live variable can reach it.
- `System.gc()` only **requests** a cleanup; it is not a command.
- GC may briefly pause the application ("stop the world").
- A **memory leak** in Java means you keep holding references (for example, a map that only grows).

**Real-life example (web app):** After each request finishes, the temporary `Order` objects created for it
become unreachable, and GC cleans them up without any code from the developer.

## F13. What is type casting

**Simple answer:** Type casting means **changing a value from one type to another**, like `int` to `double`, or a
parent object to a child type.

**Key points:**
- **Widening** (small to big, like `int` to `double`) is automatic.
- **Narrowing** (big to small, like `double` to `int`) needs `(int)` and may lose data.
- **Object casting**: upcast is automatic; downcast needs `(Dog)` and can throw `ClassCastException`.

**Real-life example (billing):**

```java
double bill = 99.75;
int rounded = (int) bill;          // 99 - decimals are cut, not rounded

Animal a = new Dog();              // upcast, automatic
Dog d = (Dog) a;                   // downcast, written by us
```

## F14. List the primitive data types

**Simple answer:** Primitives are the 8 **basic built-in types** that store simple values directly (not objects).

| Type | Size | Example | Used for |
|---|---|---|---|
| `byte` | 1 byte | `byte b = 10;` | small numbers, file data |
| `short` | 2 bytes | `short s = 100;` | small numbers |
| `int` | 4 bytes | `int age = 30;` | normal whole numbers |
| `long` | 8 bytes | `long id = 123456789L;` | big numbers (phone, IDs) |
| `float` | 4 bytes | `float f = 1.5f;` | decimals (less exact) |
| `double` | 8 bytes | `double price = 9.99;` | decimals |
| `char` | 2 bytes | `char c = 'A';` | one character |
| `boolean` | - | `boolean paid = true;` | true / false |

**Real-life example (employee record):** `int age`, `double salary`, `boolean isActive`, `char grade`.
(For money in real projects use `BigDecimal`, not `double`.)

## F15. Class variable vs instance variable

**Simple answer:** A **class variable** is `static` - one copy shared by all objects. An **instance variable**
is not static - each object has its own copy.

**Key points:**
- Class variable: change it once, every object sees the change.
- Instance variable: each object keeps its own value.

**Real-life example (car showroom):** `totalCarsSold` is shared by the whole showroom (class variable). `color`
belongs to each individual car (instance variable).

```java
class Car {
    static int totalCars = 0;     // class variable
    String color;                 // instance variable
    Car(String color) { this.color = color; totalCars++; }
}
new Car("Red"); new Car("Blue");
System.out.println(Car.totalCars);   // 2
```

## F16. `this()` vs `super()`

**Simple answer:** `this()` calls **another constructor of the same class**. `super()` calls the **constructor
of the parent class**.

**Key points:**
- Both must be the **first line** in the constructor, so you cannot use both in the same constructor.
- If you write neither, Java adds `super()` automatically.
- `this.name` / `super.name` are for fields and methods.

**Real-life example (employees):** A `Manager` is an `Employee`. The `Manager` constructor first lets the
`Employee` part set name and id.

```java
class Employee {
    String name;
    Employee(String name) { this.name = name; }
}
class Manager extends Employee {
    int teamSize;
    Manager(String name) { this(name, 5); }              // this() - another constructor here
    Manager(String name, int teamSize) {
        super(name);                                      // super() - parent constructor
        this.teamSize = teamSize;
    }
}
```

## F17. Implicit vs explicit type casting

**Simple answer:** **Implicit** casting is done by Java automatically when there is no risk (small type to big
type). **Explicit** casting is done by you with `(type)` when there is a risk of losing data (big to small).

**Key points:**
- Implicit order: `byte -> short -> int -> long -> float -> double`.
- Explicit can lose data: `(int) 3.9` becomes `3`.

**Real-life example (marks calculation):**

```java
int marks = 85;
double percentage = marks;            // implicit: 85.0
double avg = 84.6;
int rounded = (int) avg;              // explicit: 84 (decimal lost)
```

## F18. What is an enum

**Simple answer:** An enum is a **fixed list of named values**. Use it when a variable can only be one of a
small known set, so nobody can use a wrong value by mistake.

**Key points:**
- Safer than using plain strings or numbers.
- Can have fields and methods.
- Works nicely in `switch`.

**Real-life example (order status):**

```java
enum OrderStatus { CREATED, PAID, SHIPPED, DELIVERED, CANCELLED }

OrderStatus status = OrderStatus.PAID;
switch (status) {
    case PAID -> System.out.println("Pack the order");
    case SHIPPED -> System.out.println("Send tracking SMS");
    default -> System.out.println("Nothing to do");
}
```

## F19. StringBuilder vs StringBuffer (and String)

**Simple answer:** `String` cannot be changed. `StringBuilder` and `StringBuffer` **can be changed** without
creating new objects. `StringBuffer` is thread-safe (and slower); `StringBuilder` is not thread-safe (and faster).

**Key points:**
| | String | StringBuilder | StringBuffer |
|---|---|---|---|
| Can change? | No | Yes | Yes |
| Thread-safe | Yes (cannot change) | No | Yes |
| Speed | slow when joining in loops | fastest | a bit slower |

Use `StringBuilder` in normal code; `StringBuffer` only when many threads edit the same text.

**Real-life example (report):** Building a long CSV report line by line.

```java
StringBuilder csv = new StringBuilder();
for (Order o : orders) {
    csv.append(o.getId()).append(",").append(o.getAmount()).append("\n");
}
String report = csv.toString();
```

## F20. `final` vs `finally` vs `finalize`

**Simple answer:** They only sound the same.
- `final` - a **keyword**: "cannot be changed".
- `finally` - a **block**: "always run this cleanup code".
- `finalize` - an **old method** the garbage collector called before deleting an object. Do not use it now.

**Key points:**
- `final` variable = constant, `final` method = cannot override, `final` class = cannot extend.
- `finally` runs whether or not an exception happened (used to close resources).
- Use try-with-resources instead of `finalize`.

**Real-life example (database):**

```java
final int MAX_RETRIES = 3;                       // final
Connection con = null;
try {
    con = dataSource.getConnection();
    // work with DB
} finally {
    if (con != null) con.close();                // finally - always release
}
```

## F21. Method overloading vs overriding

**Simple answer:** **Overloading** = same method name, **different parameters**, in the same class.
**Overriding** = a child class gives its **own version** of a parent method.

**Key points:**
- Overloading is decided at **compile time**; overriding at **run time** (polymorphism).
- Overriding needs the same name and parameters; use `@Override`.
- You cannot overload by only changing the return type.

**Real-life example (payments):**

```java
// Overloading: same name, different inputs
class Calculator {
    double fee(double amount)               { return amount * 0.01; }
    double fee(double amount, double extra) { return amount * 0.01 + extra; }
}

// Overriding: child changes parent's behaviour
class Account { double interest() { return 3.5; } }
class SavingsAccount extends Account {
    @Override double interest() { return 4.0; }
}
```

## F22. Why is String immutable

**Simple answer:** Once a `String` is created, it **cannot be changed**. Java designed it this way for safety
and speed.

**Key points:**
- **String pool** - same text can be shared safely by many variables, saving memory.
- **Security** - things like database URLs, file paths and passwords cannot be changed after checking.
- **Thread safety** - many threads can use it without locks.
- **HashMap keys** - its hash code never changes, so it is a safe key.

**Real-life example (banking):** If someone could change the account number string after validation but before
the transfer, money could go to the wrong account. Immutability prevents this.

```java
String s = "abc";
s.concat("def");              // creates a NEW string; s is still "abc"
s = s.concat("def");          // now s points to the new "abcdef"
```

## F23. What is encapsulation

**Simple answer:** Encapsulation means **hiding the data inside a class** and allowing access only through
methods. Like an ATM: you cannot touch the cash directly; you use the buttons.

**Key points:**
- Make fields `private`; give `public` getters/setters.
- You can add checks (validation) in the setter.
- You can change the inside later without breaking the users of the class.

**Real-life example (bank account):** Nobody should set the balance to a negative value directly.

```java
class BankAccount {
    private double balance;                                 // hidden
    public void deposit(double amount) {
        if (amount <= 0) throw new IllegalArgumentException("Invalid amount");
        balance += amount;
    }
    public double getBalance() { return balance; }
}
```

## F24. When will the `finally` block not execute

**Simple answer:** `finally` runs almost always, but **not** when the program or JVM is stopped before reaching it.

**Key points:**
- `System.exit()` is called in `try` or `catch`.
- The JVM crashes or the machine is powered off / process killed.
- The thread runs an **infinite loop** or is blocked forever inside `try`.
- The thread is a daemon thread and the program ends first.

**Real-life example (batch job):** A job calls `System.exit(1)` when it finds a critical error. The cleanup in
`finally` (closing files) is skipped.

```java
try {
    System.exit(0);
} finally {
    System.out.println("never printed");
}
```

## F25. Can we use `try` without `catch`

**Simple answer:** Yes - but you need either a **`finally`** block or a **try-with-resources**. `try` alone is not allowed.

**Key points:**
- `try { } finally { }` - the exception is **not handled**, it still goes up; only cleanup runs.
- `try (Resource r = ...) { }` - the resource is closed automatically.

**Real-life example (file upload):** Always close the file, and let the caller decide how to handle an error.

```java
try (InputStream in = new FileInputStream("invoice.pdf")) {
    process(in);
}   // in.close() is called automatically, even if process() throws
```

## F26. Default value stored in local variables

**Simple answer:** **None.** A local variable (inside a method) has no default value. If you use it before giving
it a value, the code **does not compile**. (Class fields do get defaults: `0`, `false`, `null`.)

**Key points:**
- Local variable: you must initialize it.
- Instance/static field: `int` = 0, `boolean` = false, object = `null`.

**Real-life example (total calculation):**

```java
int total;                       // local, no value
// System.out.println(total);    // compile error: might not have been initialized
total = 0;                       // now fine

class Order { int quantity; String note; }   // fields: quantity = 0, note = null
```

## F27. Access modifiers in Java

**Simple answer:** They decide **who can see and use** a class, method or field.

| Modifier | Same class | Same package | Child class (other package) | Everywhere |
|---|---|---|---|---|
| `private` | Yes | No | No | No |
| (default) | Yes | Yes | No | No |
| `protected` | Yes | Yes | Yes | No |
| `public` | Yes | Yes | Yes | Yes |

**Key points:**
- Start with the **most restrictive** (`private`) and open up only if needed.
- `private` fields + `public` methods = encapsulation.

**Real-life example (employee class):** `salary` is `private` (only the class touches it), `getName()` is
`public` (anyone can call it), and `calculateBonus()` is `protected` (child classes like `Manager` can reuse it).

---

# C. Experienced candidate questions

## E1. `map` vs `flatMap`

**Simple answer:** `map` changes **each item into one new item**. `flatMap` changes each item into **many items
and then joins them into one flat list**.

**Key points:**
- `map`: 1 input -> 1 output.
- `flatMap`: 1 input -> a stream of outputs, then all are merged into one stream.
- Easy memory: map = transform, flatMap = transform + flatten.

**Real-life example (e-commerce):** You have a list of orders, and each order has a list of items. You want one
list of all items sold.

```java
List<String> allItems = orders.stream()
        .flatMap(order -> order.getItems().stream())   // each order -> many items, merged
        .toList();

List<Double> amounts = orders.stream()
        .map(Order::getAmount)                          // each order -> one amount
        .toList();
```

## E2. What is short-circuit

**Simple answer:** Short-circuit means Java **stops checking as soon as the answer is already known**. It saves
time and also prevents errors.

**Key points:**
- `&&`: if the left side is `false`, the right side is **not** evaluated.
- `||`: if the left side is `true`, the right side is **not** evaluated.
- Stream short-circuit operations: `findFirst`, `anyMatch`, `allMatch`, `noneMatch`, `limit`.
- `&` and `|` always check both sides (no short-circuit).

**Real-life example (login check):** Check that the user is not `null` **before** calling a method on it.

```java
if (user != null && user.isActive()) {      // if user is null, isActive() is never called -> no NullPointerException
    allowLogin();
}

boolean hasLargeOrder = orders.stream().anyMatch(o -> o.getAmount() > 100000);  // stops at first match
```

## E3. What is an immutable class and how do you create one

**Simple answer:** An immutable class is a class whose objects **cannot change after they are created**. Like a
printed receipt: you can read it, but if something changes you print a new one.

**Key points - the recipe:**
1. Make the class `final` (nobody can extend and break it).
2. Make all fields `private final`.
3. Set values only in the constructor; no setters.
4. If a field is a mutable object (list, date), make a **copy** when storing and when returning.

**Why it matters:** Safe to share between threads without locks; safe as a `HashMap` key; easy to understand.

**Real-life example (money in a payment system):**

```java
public final class Money {
    private final BigDecimal amount;
    private final String currency;

    public Money(BigDecimal amount, String currency) {
        this.amount = amount;
        this.currency = currency;
    }
    public Money add(Money other) {                       // returns a NEW object
        return new Money(amount.add(other.amount), currency);
    }
}
// Java 16+ shortcut: record Money(BigDecimal amount, String currency) { }
```

## E4. `@ControllerAdvice` / `@Configuration` / `@Autowired`

**Simple answer:** Three different Spring annotations with three different jobs.

**Key points:**
- **`@ControllerAdvice`** (or `@RestControllerAdvice`) - one central place to **handle exceptions** for all controllers.
- **`@Configuration`** - a class that **creates and registers beans** using `@Bean` methods.
- **`@Autowired`** - tells Spring "**give me** the object I need here" (dependency injection).

**Real-life example (REST API):** Instead of writing try/catch in every controller, the team writes one handler
that returns a clean `404` message for every "not found".

```java
@RestControllerAdvice
class GlobalExceptionHandler {
    @ExceptionHandler(OrderNotFoundException.class)
    ResponseEntity<String> notFound(OrderNotFoundException e) {
        return ResponseEntity.status(404).body(e.getMessage());
    }
}

@Configuration
class AppConfig {
    @Bean Clock clock() { return Clock.systemUTC(); }       // a bean we create ourselves
}

@Service
class OrderService {
    private final Clock clock;
    @Autowired OrderService(Clock clock) { this.clock = clock; }   // Spring injects it
}
```

## E5. PATCH vs PUT

**Simple answer:** **PUT** replaces the **whole** resource. **PATCH** changes **only the fields you send**.

**Key points:**
- PUT: send the full object; missing fields may become empty.
- PATCH: send only what changed.
- PUT is always idempotent (same call twice = same result). PATCH is idempotent only if the change is
  "set value X" and not "add 1".

**Real-life example (customer profile):** A customer only changes the phone number.

```
PUT   /customers/7  {"name":"Asha","city":"Pune","phone":"999"}   <- must send everything
PATCH /customers/7  {"phone":"999"}                               <- just the change
```

## E6. IoC (Inversion of Control)

**Simple answer:** Normally **you** create the objects you need (`new`). With IoC, you **give that job to the
framework**. Spring creates and manages the objects and hands them to you.

**Key points:**
- "Control is inverted": the framework controls object creation and lifecycle, not your code.
- The Spring container that does this is called the **IoC container** (`ApplicationContext`).
- Dependency Injection (DI) is the way IoC is done.

**Real-life example (restaurant):** Without IoC, the chef goes to the market and buys vegetables himself. With IoC,
the manager (Spring) delivers the vegetables to the chef's table. The chef only cooks.

```java
@Service
class OrderService {
    private final PaymentService paymentService;               // we did not write "new PaymentService()"
    OrderService(PaymentService paymentService) { this.paymentService = paymentService; }
}
```

## E7. AOP (Aspect-Oriented Programming)

**Simple answer:** AOP lets you add common work (logging, security, timing, transactions) to many methods
**without writing it inside each method**. You write it once and tell Spring where to apply it.

**Key points (simple terms):**
- **Aspect** - the class holding the common code.
- **Advice** - what to do and when (before, after, around).
- **Pointcut** - which methods it applies to.
- Spring does this with **proxies**.

**Real-life example (banking):** Log how long every service method takes, without touching every method.

```java
@Aspect
@Component
class TimingAspect {
    @Around("execution(* com.bank.service..*(..))")
    Object measure(ProceedingJoinPoint pjp) throws Throwable {
        long start = System.currentTimeMillis();
        try {
            return pjp.proceed();                    // run the real method
        } finally {
            System.out.println(pjp.getSignature() + " took " + (System.currentTimeMillis() - start) + " ms");
        }
    }
}
```

## E8. DI (Dependency Injection)

**Simple answer:** A class should **receive** the things it needs from outside instead of creating them itself.
This makes code loosely connected and easy to test.

**Key points:**
- Three ways: **constructor** (best), setter, field.
- Constructor injection makes dependencies clear and fields `final`.
- In tests you can pass a fake (mock) object easily.

**Real-life example (notification service):** The `OrderService` needs to send an email. It depends on an
`EmailSender` interface. In production we inject the real sender; in tests we inject a fake one.

```java
interface EmailSender { void send(String to, String msg); }

@Service
class OrderService {
    private final EmailSender emailSender;
    OrderService(EmailSender emailSender) { this.emailSender = emailSender; }
    void confirm(Order o) { emailSender.send(o.getEmail(), "Order confirmed"); }
}
```

## E9. Cohesion vs coupling

**Simple answer:** **Cohesion** = how well the things **inside** one class belong together (we want high).
**Coupling** = how much one class **depends on other classes** (we want low).

**Key points:**
- High cohesion: a class does one job well.
- Low coupling: change one class without breaking many others.
- Interfaces and dependency injection reduce coupling.

**Real-life example (e-commerce):** An `OrderService` that only handles orders is **high cohesion**. If it also
sends emails, generates PDFs and talks to the bank, it is low cohesion. If it uses an `PaymentGateway`
interface (not a specific bank class), it is **low coupling**, so you can switch banks easily.

## E10. How to convert a normal class into a singleton

**Simple answer:** A singleton allows **only one object** of the class in the whole application. You make the
constructor private and give one shared instance through a static method.

**Key points:**
- Private constructor (nobody can use `new`).
- A static field holding the single instance.
- A public static method to get it.
- It must be **thread-safe**. Best simple options: **enum** or the **holder class** idiom.
- In Spring, beans are already singletons by default.

**Real-life example (application settings):** All parts of the app should read the same `AppConfig`.

```java
public class AppConfig {
    private AppConfig() { }                                       // 1. private constructor

    private static class Holder {                                 // 2. created once, only when first used
        private static final AppConfig INSTANCE = new AppConfig();
    }
    public static AppConfig getInstance() { return Holder.INSTANCE; }   // 3. access point
}
```

## E11. What is Spring Security

**Simple answer:** Spring Security is the Spring module that **protects your application**. It checks **who you
are** (authentication) and **what you are allowed to do** (authorization).

**Key points:**
- Works as a chain of filters in front of your controllers.
- Supports username/password, JWT, OAuth2, LDAP, and more.
- Protects against common attacks (CSRF, session fixation, clickjacking headers).
- Rules by URL or by method (`@PreAuthorize`).

**Real-life example (admin portal):** Anyone can see `/public/**`. Everything else needs a valid login token.

```java
@Bean
SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
    return http
        .authorizeHttpRequests(a -> a
            .requestMatchers("/public/**").permitAll()
            .requestMatchers("/admin/**").hasRole("ADMIN")
            .anyRequest().authenticated())
        .oauth2ResourceServer(o -> o.jwt(Customizer.withDefaults()))
        .build();
}
```

## E12. "Concern modifications" (cross-cutting concerns)

**Simple answer:** A **cross-cutting concern** is something needed in many places of the application but is not
the main business logic: logging, security, transactions, caching, auditing. We keep it in **one** place instead
of copying it everywhere.

**Key points:**
- Handle with **AOP**, **filters** or **interceptors**.
- Benefit: change the logging or audit rule in one place.
- (If the interviewer meant "how do you change configuration safely", the answer is externalized config and
  profiles, see A7.)

**Real-life example (insurance):** Every claim-related method must write an audit record (who did what). Instead
of writing this in 50 methods, an AOP aspect writes the audit entry around all claim service methods.

## E13. OAuth2 vs JWT

**Simple answer:** They are **not competitors**. **OAuth2** is a **set of rules** for how an app gets permission
to access something. **JWT** is a **type of token** (a signed piece of text) that carries information. OAuth2
often uses JWT as the token.

**Key points:**
| | OAuth2 | JWT |
|---|---|---|
| What is it | an authorization framework | a token format |
| Answers | "how do I get access?" | "what is inside the token and is it genuine?" |
| Example | "Login with Google" flow | `xxxxx.yyyyy.zzzzz` token |

- JWT has 3 parts: header, payload (claims), signature.
- JWTs are stateless (server need not store them) but are hard to cancel, so keep expiry short.

**Real-life example (mobile banking app):** The user logs in through the bank's authorization server (OAuth2).
The server returns a JWT access token. The app sends this token with each API call; the API checks the signature
and expiry.

```
Authorization: Bearer eyJhbGciOiJSUzI1NiJ9....
```

## E14. Advantages of Spring MVC

**Simple answer:** Spring MVC is a clean way to build web applications by separating **Model** (data),
**View** (output) and **Controller** (request handling).

**Key points:**
- Clear separation of concerns, so code is easier to test and maintain.
- Easy annotations: `@RestController`, `@GetMapping`, `@RequestBody`.
- Automatic data binding, JSON conversion and validation (`@Valid`).
- Central exception handling (`@ControllerAdvice`) and interceptors.
- Works well with the rest of Spring (security, data, AOP).
- Request flow: client -> **DispatcherServlet** -> controller -> response.

**Real-life example (REST API):**

```java
@RestController
@RequestMapping("/orders")
class OrderController {
    @GetMapping("/{id}")
    Order get(@PathVariable long id) { return service.find(id); }   // JSON conversion is automatic
}
```

## E15. Life cycle of a Spring bean

**Simple answer:** It is the **journey of a bean** from creation to destruction, managed by Spring.

**Key points (in order):**
1. Spring **creates** the object (constructor).
2. Spring **injects** its dependencies.
3. **Initialization** callbacks run (`@PostConstruct`).
4. Bean is **ready to use**.
5. On shutdown, **destroy** callbacks run (`@PreDestroy`).

**Real-life example (cache loading):** A `ProductCache` bean loads all product prices when the application starts
and clears memory when the application stops.

```java
@Component
class ProductCache {
    @PostConstruct void load()  { System.out.println("Loading products into cache"); }
    @PreDestroy   void clear() { System.out.println("Clearing cache"); }
}
```

## E16. API Gateway

**Simple answer:** An API gateway is the **single front door** for all your microservices. Clients call only the
gateway, and it sends the request to the right service.

**Key points:**
- Routing, authentication, rate limiting, logging, SSL in one place.
- Can combine results of several services into one response.
- Clients do not need to know the internal service addresses.
- Keep business logic out of the gateway.
- Examples: Spring Cloud Gateway, Kong, AWS API Gateway, Apigee.

**Real-life example (food delivery app):** The mobile app calls `api.food.com`. The gateway checks the login token,
then routes `/orders` to the Order service and `/restaurants` to the Restaurant service.

## E17. Hierarchy of exceptions

**Simple answer:** All errors and exceptions come from one parent, `Throwable`, which splits into `Error` and
`Exception`.

```
Throwable
 |-- Error                      (serious JVM problems: OutOfMemoryError, StackOverflowError)
 `-- Exception
      |-- RuntimeException      (UNCHECKED: NullPointerException, IllegalArgumentException)
      `-- other Exceptions      (CHECKED: IOException, SQLException)
```

**Key points:**
- **Checked**: the compiler forces you to handle or declare them.
- **Unchecked** (`RuntimeException`): optional to handle; usually programming mistakes.
- **Error**: do not try to catch; the application usually cannot recover.

**Real-life example (file upload):** `IOException` (checked) - file may be missing, so you must handle it.
`NullPointerException` (unchecked) - a bug you should fix, not catch.

## E18. Difference between interface and abstract class

**Simple answer:** See F10. In one line: an **interface** is a pure contract that many classes can follow; an
**abstract class** is a partly built class that shares code with its children.

**Key points:**
- A class can **implement many** interfaces but **extend only one** class.
- Abstract class can have state (fields) and constructors; interface cannot.
- Since Java 8, interfaces can have `default` methods.

**Real-life example (notifications):** `Notifier` interface with `send()`; `EmailNotifier`, `SmsNotifier`
implement it. An abstract `BaseNotifier` can hold shared retry logic.

## E19. Can we overload the `main` method

**Simple answer:** **Yes**, you can overload it like any method. But the JVM starts the program only from
`public static void main(String[] args)`. The others run only if you call them.

**Key points:**
- Overloading = same name, different parameters.
- JVM ignores the other versions at start-up.

**Real-life example:**

```java
public class App {
    public static void main(String[] args) {        // JVM calls this one
        System.out.println("start");
        main(5);                                     // we call the overloaded one
    }
    public static void main(int times) {
        System.out.println("overloaded main " + times);
    }
}
```

## E20. ArrayList vs LinkedList

**Simple answer:** `ArrayList` stores items in a **resizable array** (fast to read by position). `LinkedList`
stores items as **linked nodes** (fast to add/remove at the ends, slow to read by position).

**Key points:**
| | ArrayList | LinkedList |
|---|---|---|
| Get by index | fast | slow (walks the list) |
| Add at end | fast | fast |
| Insert in the middle | slow (shift items) | fast once you are at the position |
| Memory | less | more (extra pointers) |

- In real projects `ArrayList` is the default choice.

**Real-life example (product list):** A product listing page reads items by index many times and rarely inserts
in the middle, so use `ArrayList`. For a queue where you only add at the end and remove from the front, use
`ArrayDeque` (or `LinkedList`).

## E21. Internal structure of HashMap

**Simple answer:** HashMap stores data in an **array of buckets**. For each key, Java calculates a **hash** to
decide the bucket. If two keys land in the same bucket, they are kept together in a list (or a tree).

**Key points:**
- Default size 16 buckets; resizes (doubles) when 75% full (load factor 0.75).
- `put`: compute hash -> find bucket -> if the same key exists (using `equals`) replace, else add.
- Many collisions: a bucket becomes a **balanced tree** after 8 entries (Java 8+), keeping lookup fast.
- Average `get`/`put` is O(1).
- Not thread-safe; use `ConcurrentHashMap` for threads.
- Good `hashCode()` and `equals()` on keys are essential.

**Real-life example (cache of customers by id):**

```java
Map<Long, Customer> cache = new HashMap<>();
cache.put(101L, new Customer("Asha"));     // hash(101) -> bucket -> stored
Customer c = cache.get(101L);              // same hash -> same bucket -> found quickly
```

## E22. Association, aggregation and composition

**Simple answer:** They describe **how two classes are related**.

| Relationship | Meaning | Lifetime | Example |
|---|---|---|---|
| **Association** | one class uses another | independent | Doctor - Patient |
| **Aggregation** | "has-a", weak ownership | part can live without the whole | Department has Employees |
| **Composition** | "has-a", strong ownership | part dies with the whole | House has Rooms |

**Real-life example (university):** If a *Department* is closed, the *Professors* still exist and can join another
department (**aggregation**). If a *Building* is destroyed, its *Rooms* are gone too (**composition**).

```java
class Building {
    private final List<Room> rooms = new ArrayList<>();      // composition: rooms created and owned here
    void addRoom(String name) { rooms.add(new Room(name)); }
}
class Department {
    private final List<Professor> professors;                // aggregation: passed in from outside
    Department(List<Professor> professors) { this.professors = professors; }
}
```

## E23. Marker interface

**Simple answer:** A marker interface has **no methods**. It is only a **tag** that tells Java or a framework
"this class is special".

**Key points:**
- Examples: `Serializable`, `Cloneable`, `RandomAccess`.
- The JVM/library checks `instanceof` to decide behaviour.
- Today, **annotations** are used for the same purpose in new code.

**Real-life example (sending an object over a network / saving to a file):** Only classes that are tagged
`Serializable` can be converted to bytes.

```java
class Customer implements Serializable {      // marker: "I can be serialized"
    String name;
}
```

## E24. Hibernate vs JPA

**Simple answer:** **JPA** is a **set of rules (a specification)** for saving Java objects in a database.
**Hibernate** is a **tool that follows those rules** (an implementation).

**Key points:**
- JPA = the interface; Hibernate = the class that implements it (like `List` and `ArrayList`).
- Code written to JPA can switch to another provider (EclipseLink).
- **Spring Data JPA** sits on top and writes repository code for you.

**Real-life example (customer table):** You write `@Entity` and `CustomerRepository extends JpaRepository`.
Behind the scenes, Hibernate generates the SQL.

```java
@Entity
class Customer { @Id @GeneratedValue Long id; String name; }

interface CustomerRepository extends JpaRepository<Customer, Long> { }
```

## E25. Spring vs Spring Boot

**Simple answer:** **Spring** is the big framework (dependency injection, MVC, security...) but needs a lot of
configuration. **Spring Boot** is built on Spring and **sets up most things automatically**, so you can start fast.

**Key points:**
- Boot gives **starters** (one dependency brings a whole set), **auto-configuration**, and an **embedded server**
  (Tomcat), so you run a simple `java -jar`.
- Boot also gives Actuator (health, metrics) and externalized config.
- Boot does not replace Spring; it makes it easy to use.

**Real-life example (new microservice):** With plain Spring, a team spends days on XML/Java config and a server.
With Spring Boot, they add `spring-boot-starter-web`, write one controller, and run it.

## E26. Design patterns

**Simple answer:** A design pattern is a **proven solution to a problem that keeps appearing** in software design.
It is like a recipe you can reuse.

**Key points:**
- **Creational** (how objects are created): Singleton, Factory, Builder.
- **Structural** (how objects are put together): Adapter, Decorator, Proxy, Facade.
- **Behavioural** (how objects talk): Strategy, Observer, Template Method.
- Spring uses many: Singleton (beans), Proxy (AOP/transactions), Template (`JdbcTemplate`), Observer (events).

**Real-life example (payments - Strategy pattern):** The checkout supports card, UPI and wallet. Instead of a huge
`if/else`, each payment method is a class with the same interface.

```java
interface PaymentStrategy { void pay(double amount); }
class UpiPayment implements PaymentStrategy { public void pay(double a) { /* UPI */ } }
class CardPayment implements PaymentStrategy { public void pay(double a) { /* card */ } }

PaymentStrategy strategy = new UpiPayment();     // chosen at runtime
strategy.pay(500);
```

## E27. Different ways to autowire an object

**Simple answer:** There are three ways to ask Spring to inject a dependency.

**Key points:**
1. **Constructor injection** - best. The object is complete when created, fields can be `final`, easy to test.
2. **Setter injection** - for optional dependencies.
3. **Field injection** (`@Autowired` on a field) - short but discouraged: hard to test.
- If there are two beans of the same type, use `@Primary` or `@Qualifier("name")`.

**Real-life example (notification):**

```java
@Service
class AlertService {
    private final Sender sender;

    AlertService(@Qualifier("smsSender") Sender sender) {   // constructor injection + choose which bean
        this.sender = sender;
    }
}
```

## E28. Can the same endpoint produce different output? How?

**Simple answer:** Yes. The same URL can return different results depending on **something the client sends**:
the `Accept` header, a request parameter, a custom header, the user's role, or the API version.

**Key points:**
- `produces` - different formats (JSON vs CSV) based on the `Accept` header.
- `params` or `headers` conditions - different methods for different parameters/headers.
- Logic based on the logged-in user (a manager sees more fields than a clerk).

**Real-life example (reports):** The same `/reports/sales` gives JSON to the web app and CSV to the finance team.

```java
@GetMapping(value = "/reports/sales", produces = "application/json")
List<Sale> json() { return service.sales(); }

@GetMapping(value = "/reports/sales", produces = "text/csv")
String csv() { return service.salesAsCsv(); }
```

## E29. How to connect two databases in Spring Boot

**Simple answer:** Define **two DataSource beans** (one per database). Mark one as `@Primary`. Give each its own
entity manager and transaction manager, and tell each repository package which one to use.

**Mental model (say it in one breath):**

```text
DataSource-1 -> EntityManagerFactory-1 -> TransactionManager-1 -> Repositories in package A -> DB-1
DataSource-2 -> EntityManagerFactory-2 -> TransactionManager-2 -> Repositories in package B -> DB-2
```

**Key points:**
- Two sets of properties in `application.yml` under your own prefix (not `spring.datasource`, which feeds the single auto-configured pool).
- Separate packages for each database's entities and repositories; `@EnableJpaRepositories(basePackages=...)` and `.packages(...)` are what bind them to the right EMF.
- One `DataSource` must be `@Primary`. Spring Boot's JPA auto-configuration (and the `EntityManagerFactoryBuilder` bean) only activates for a *single* candidate `DataSource`; with two and no `@Primary` you get `NoSuchBeanDefinitionException` or the wrong pool injected.
- `@Transactional` with no name uses the **primary** transaction manager, so a method that writes to the second DB silently runs without a transaction there. Always name it: `@Transactional("reportsTx")`.
- There is **no automatic single transaction across both databases**. That is the real interview question.

**Real-life example (retail):** Orders are saved in PostgreSQL; sales reports are read from a MySQL reporting database.

```yaml
app:
  datasource:
    orders:
      url: jdbc:postgresql://db1:5432/orders
      username: app
      password: ${ORDERS_DB_PASSWORD}
      driver-class-name: org.postgresql.Driver
    reports:
      url: jdbc:mysql://db2:3306/reports
      username: app
      password: ${REPORTS_DB_PASSWORD}
      driver-class-name: com.mysql.cj.jdbc.Driver
```

```java
@Configuration
@EnableJpaRepositories(basePackages = "com.shop.orders.repository",
                       entityManagerFactoryRef = "ordersEmf", transactionManagerRef = "ordersTx")
class OrdersDbConfig {

    @Primary @Bean @ConfigurationProperties("app.datasource.orders")
    DataSource ordersDataSource() { return DataSourceBuilder.create().build(); }

    @Primary @Bean
    LocalContainerEntityManagerFactoryBean ordersEmf(EntityManagerFactoryBuilder b,
                                                     @Qualifier("ordersDataSource") DataSource ds) {
        return b.dataSource(ds).packages("com.shop.orders.entity").persistenceUnit("orders").build();
    }

    @Primary @Bean
    PlatformTransactionManager ordersTx(@Qualifier("ordersEmf") EntityManagerFactory emf) {
        return new JpaTransactionManager(emf);
    }
}

@Configuration
@EnableJpaRepositories(basePackages = "com.shop.reports.repository",
                       entityManagerFactoryRef = "reportsEmf", transactionManagerRef = "reportsTx")
class ReportsDbConfig {
    @Bean @ConfigurationProperties("app.datasource.reports")
    DataSource reportsDataSource() { return DataSourceBuilder.create().build(); }

    @Bean
    LocalContainerEntityManagerFactoryBean reportsEmf(EntityManagerFactoryBuilder b,
                                                      @Qualifier("reportsDataSource") DataSource ds) {
        return b.dataSource(ds).packages("com.shop.reports.entity").persistenceUnit("reports").build();
    }

    @Bean
    PlatformTransactionManager reportsTx(@Qualifier("reportsEmf") EntityManagerFactory emf) {
        return new JpaTransactionManager(emf);
    }
}
```

```text
com.shop
  orders/   entity/Order.java      repository/OrderRepository.java      <- only OrdersDbConfig scans this
  reports/  entity/SalesRow.java   repository/SalesRepository.java     <- only ReportsDbConfig scans this
```

```java
@Service
class SalesService {
    @Transactional("ordersTx")                  // explicit - never rely on the default here
    public void placeOrder(Order o) { orderRepo.save(o); }

    @Transactional(value = "reportsTx", readOnly = true)
    public List<SalesRow> report() { return salesRepo.findAll(); }
}
```

**The senior part: transactions across two databases.** One service may inject repositories from both DBs, and
reads are easy (call both, merge in the service). Writes are the problem:

```text
orders DB:  INSERT order      -> COMMIT  (ordersTx)
reports DB: INSERT summary    -> FAILS   (reportsTx)
Result: order exists, summary missing. Each manager only knows its own database.
```

Options, in the order to mention them:
1. **Redesign so you don't need it.** Make one DB the system of record and derive the other (CDC / events / nightly sync). Most "two DB" cases are really read-model cases.
2. **Saga / compensating action** (microservices): do step 1, do step 2, on failure run a compensating step (cancel order). Eventual consistency; each step must be idempotent.
3. **Outbox + Kafka**: write the business row and an `outbox` row in the **same** local transaction, a relay publishes the event, the other side consumes idempotently. Gives "at-least-once, effectively once" without XA.
4. **JTA / XA (2PC)** with Atomikos or Narayana: true atomic commit across both, but needs XA-capable drivers and `XADataSource`, holds locks through prepare, is slower, has recovery logs to operate, and most brokers/NoSQL/REST don't support it. Use only when strong atomicity is a hard requirement.
5. **"Best-effort 1PC" chained managers** (Spring's old `ChainedTransactionManager`, now deprecated): commit in reverse order; if the second commit fails after the first succeeded you are inconsistent. Mention it only as a trap.

**Related variants (don't confuse them):**
- *Same schema, many databases (one per tenant/region)* -> a single set of repositories with `AbstractRoutingDataSource` choosing the `DataSource` by a thread-bound key, not two EMFs.
- *Read replica* -> a routing data source on `@Transactional(readOnly = true)`, not two repository sets.
- *Two databases, no JPA* -> two `DataSource`s with two `JdbcTemplate`s and `DataSourceTransactionManager`s. Same idea.
- *Microservices* -> prefer **database per service** and talk over APIs/events, instead of one service owning two DBs.

**Spoken answer (about 60 seconds):**
> "I define two separate `DataSource` beans with their own properties, mark one `@Primary`, and for JPA create an `EntityManagerFactory` and a `JpaTransactionManager` for each. I keep each database's entities and repositories in separate packages and bind them with `@EnableJpaRepositories(entityManagerFactoryRef, transactionManagerRef)`. In services I name the transaction manager explicitly, because the default is the primary one and a mistake there silently runs the other database without a transaction. Connecting two databases is the easy part. The hard part is atomicity across them: a normal `@Transactional` covers only one resource, so if I truly need all-or-nothing I'd weigh JTA/XA against a saga or outbox pattern, and in a microservice setup I'd usually avoid the problem with database-per-service and eventual consistency. Reading from both and combining in the service layer needs none of that."

**Follow-ups to be ready for:** why `@Primary`? what does `@Transactional` do with no name? XA vs saga trade-offs? how to test (Testcontainers, one container per DB)? connection pool sizing per DataSource (HikariCP per pool, so total = sum of both)? `ddl-auto`/Flyway per database (one migration location each)?

## E30. How to do multithreading in Spring Boot

**Simple answer:** Spring Boot's web server already handles each request in its **own thread**. To do background
work yourself, use `@Async` with a thread pool, or `ExecutorService` / `CompletableFuture`.

**Key points:**
- Add `@EnableAsync` and a configured `Executor` (thread pool).
- Put `@Async` on a method; it returns `void` or `CompletableFuture`.
- Do not call an `@Async` method from the same class (proxy limitation).
- Always use a **bounded** pool; keep shared objects thread-safe.

**Real-life example (order confirmation):** After placing an order, send the email in the background so the
customer does not wait for the email server.

```java
@EnableAsync
@Configuration
class AsyncConfig {
    @Bean Executor taskExecutor() {
        ThreadPoolTaskExecutor ex = new ThreadPoolTaskExecutor();
        ex.setCorePoolSize(4); ex.setMaxPoolSize(8); ex.setQueueCapacity(100);
        ex.initialize();
        return ex;
    }
}

@Service
class EmailService {
    @Async
    public void sendConfirmation(String to) { /* slow work runs in another thread */ }
}
```

## E31. How do you secure your REST APIs

**Simple answer:** Use layers: encrypt traffic, check who the caller is, check what they can do, validate input,
and limit abuse.

**Key points (checklist):**
1. **HTTPS** everywhere.
2. **Authentication** - JWT / OAuth2 (users), API keys or mTLS (services).
3. **Authorization** - roles and scopes; also check the user owns the data (not just the role).
4. **Input validation** (`@Valid`) and parameterized queries (stop SQL injection).
5. **Rate limiting** to stop abuse.
6. **CORS** limited to trusted sites.
7. Do not return stack traces; **log and audit** important actions.
8. Keep secrets in a vault, not in code.

**Real-life example (banking API):** Customer A must never see Customer B's account. Besides checking the token,
the code checks the account really belongs to the logged-in customer.

```java
@GetMapping("/accounts/{id}")
Account get(@PathVariable long id, Authentication auth) {
    Account a = service.find(id);
    if (!a.getOwner().equals(auth.getName())) throw new AccessDeniedException("Not your account");
    return a;
}
```

## E32. How do you make sure Kafka messages are read by the consumer

**Simple answer:** Make sure the message is **safely stored** (producer side), and the consumer **confirms**
only after it has finished the work. Then watch the **consumer lag** to confirm everything is being read.

**Key points:**
- Producer: `acks=all` so the broker confirms the write.
- Consumer: turn off auto-commit, commit the offset **after** processing.
- Failed messages go to a retry topic / dead-letter topic.
- Monitor **lag** (how far the consumer is behind).

**Real-life example (payments):** A "payment received" event must update the ledger. The consumer commits the
offset only after the ledger row is saved. If it crashes before saving, Kafka redelivers the message.

## E33. Cross-origin (CORS) errors

**Simple answer:** A browser blocks a web page from calling an API on a **different website address** unless that
API says "I allow this site". The error you see in the browser console is a CORS error.

**Key points:**
- The browser enforces it, not the server.
- Different origin means a different scheme, host or port.
- Fix on the server: allow the specific origin, methods and headers.
- Do not use `*` together with credentials.

**Real-life example:** The React app on `https://shop.com` calls the API at `https://api.shop.com`. Without CORS
configuration the browser blocks the call.

```java
@Configuration
class CorsConfig implements WebMvcConfigurer {
    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")
                .allowedOrigins("https://shop.com")
                .allowedMethods("GET", "POST", "PUT");
    }
}
```

## E34. Types of testing

**Simple answer:** Testing is done at different levels, from small to big.

**Key points:**
- **Unit testing** - one class/method alone (JUnit, Mockito).
- **Integration testing** - parts working together (service + database).
- **System / end-to-end testing** - the whole application like a user.
- **Regression testing** - check old features still work after a change.
- **Smoke / sanity testing** - quick check after a deployment.
- **Performance testing** - speed and load (JMeter).
- **Security testing**, **UAT** (user acceptance).
- **Test pyramid:** many unit tests, fewer integration tests, very few end-to-end tests.

**Real-life example (e-commerce checkout):** Unit test: the discount calculation. Integration test: order saved in
the database. End-to-end test: add to cart -> pay -> see confirmation.

## E35. Event-driven architecture in microservices

**Simple answer:** Services do not call each other directly. When something happens, a service **publishes an
event** ("OrderPlaced"). Other services that care **listen** and react on their own.

**Key points:**
- Loose coupling: the sender does not know who listens.
- Easy to add new listeners later.
- Handles spikes (the broker stores events).
- Costs: results are "eventually" consistent, debugging is harder, you need idempotent consumers.

**Real-life example (e-commerce):** One `OrderPlaced` event is used by Inventory (reserve stock), Payment (charge),
Notification (send email) and Analytics, each independently.

```
Order Service --OrderPlaced--> Kafka --> Inventory
                                      --> Payment
                                      --> Notification
```

## E36. What is a deadlock

**Simple answer:** A deadlock is when **two threads wait for each other forever**, each holding a lock the other
one needs. Nothing moves.

**Key points:**
- Happens with nested locks acquired in different orders.
- Prevent: always take locks in the **same order**, use `tryLock` with a timeout, keep locks short.
- Detect: take a thread dump (`jstack`) - it says "Found one Java-level deadlock".

**Real-life example (money transfer):** Thread 1 transfers A -> B and locks A then B. Thread 2 transfers B -> A and
locks B then A. Each waits for the other. Fix: always lock the account with the smaller id first.

```java
Account first  = a.getId() < b.getId() ? a : b;     // fixed order
Account second = a.getId() < b.getId() ? b : a;
synchronized (first) { synchronized (second) { transfer(a, b, amount); } }
```

## E37. SOLID principles

**Simple answer:** Five rules for writing code that is easy to change and maintain.

**Key points:**
- **S - Single Responsibility:** a class has one reason to change.
- **O - Open/Closed:** add new behaviour by adding code, not editing old, tested code.
- **L - Liskov Substitution:** a child class must be usable wherever its parent is expected.
- **I - Interface Segregation:** many small interfaces are better than one huge one.
- **D - Dependency Inversion:** depend on interfaces, not concrete classes.

**Real-life example (discount rules):** A shop adds a new "festival discount". With Open/Closed, you add a new
class and do not touch the existing discount code.

```java
interface Discount { double apply(double amount); }
class FestivalDiscount implements Discount { public double apply(double a) { return a * 0.8; } }  // new class only
```

## E38. How to change the port in a Spring Boot application

**Simple answer:** Set the `server.port` property. The default is `8080`.

**Key points:**
- In `application.properties`: `server.port=9090`.
- On the command line: `java -jar app.jar --server.port=9090`.
- Environment variable: `SERVER_PORT=9090`.
- `server.port=0` picks a random free port (useful for tests).

**Real-life example:** Two microservices run on the same machine in development. The Order service uses `8081`
and the Payment service uses `8082`, so they do not clash.

```yaml
server:
  port: 8081
```

---

# D. Kafka round

## K1. "In Kafka you were producing and consuming messages?"

**Simple answer:** Yes. Describe your real flow in three steps: **who sends, what is sent, who reads it and
what they do with it.**

**Key points:**
- Producer sends an event with a business key.
- Consumer group reads, does the work, then commits the offset.
- Failures go to a retry topic or a dead-letter topic.

**Real-life example (e-commerce):** The Order service sends `OrderPlaced` (key = orderId). The Inventory service
reads it and reserves stock.

```java
// Producer
kafkaTemplate.send("orders", order.getId(), order);

// Consumer
@KafkaListener(topics = "orders", groupId = "inventory")
void onOrder(Order order) {
    inventoryService.reserve(order);
}
```

## K2. How do you connect to Kafka? How do you mock a Kafka server?

**Simple answer:** You connect by giving the client the **address of the brokers** (`bootstrap.servers`). For
tests, you either start a **small fake/embedded Kafka** or use **mock classes** so no real server is needed.

**Key points:**
- Give 2-3 broker addresses; the client finds the rest.
- Test options: `@EmbeddedKafka` (in-memory broker), **Testcontainers** (real Kafka in Docker),
  `MockProducer`/`MockConsumer`, or mock `KafkaTemplate` with Mockito.

**Real-life example (unit test of an order service):**

```yaml
spring.kafka.bootstrap-servers: broker1:9092,broker2:9092
```
```java
@Test
void sendsEventWhenOrderPlaced() {
    orderService.place(order);
    verify(kafkaTemplate).send(eq("orders"), eq("42"), any());   // no real Kafka needed
}
```

## K3. Partitioning, offset, partition key - do we need to define the key, or does Kafka do it?

**Simple answer:**
- **Partition** - one ordered section of a topic.
- **Offset** - the **number** of a message inside a partition (0, 1, 2 ...). It is like a page number.
- **Partition key** - an optional value you send with the message; Kafka uses it to decide the partition.

**Key points:**
- **You do not have to define a key.** If you do not, Kafka distributes messages by itself.
- Define a key **when order matters** for one entity (same customer, same order).
- Same key = same partition = same order.

**Real-life example (ride-hailing):** All location updates of one driver must arrive in order, so `driverId` is
the key. Updates from different drivers go to different partitions and are processed in parallel.

## K4. How do you start a Kafka server in the API? What authentication do you use?

**Simple answer:** You **do not start Kafka from your API**. Kafka brokers run separately (Docker, Kubernetes, or a
managed service). Your API only **connects as a client**. For security, the client proves who it is using
**SASL (username/password or token)** and/or **SSL certificates**.

**Key points:**
- Common: `SASL_SSL` with `SCRAM-SHA-512`, or `OAUTHBEARER`, or mutual TLS (client certificate).
- The broker has **ACLs**: which user can read/write which topic.
- Local dev: run Kafka with `docker compose`.

**Real-life example (production):** The payment service has its own Kafka user that may only **write** to
`payments` and **read** from `orders`.

```properties
security.protocol=SASL_SSL
sasl.mechanism=SCRAM-SHA-512
sasl.jaas.config=org.apache.kafka.common.security.scram.ScramLoginModule required username="payment-svc" password="${KAFKA_PWD}";
```

## K5. Why were you using Kafka? What was the need?

**Simple answer:** We needed to **send events between services without making the sender wait**, handle sudden
spikes in traffic, and let several systems use the same data.

**Key points (pick the ones true for your project):**
- Decouple services (the sender does not depend on receivers).
- Absorb traffic bursts (Kafka stores messages).
- High throughput and durable storage.
- Many independent consumers; replay old data.

**Real-life example (e-commerce sale day):** Orders jump from 100 to 2000 per second. The order API puts events in
Kafka and returns quickly. Payment and warehouse services read at their own speed without the website slowing down.

## K6. How do you acknowledge a message in Kafka?

**Simple answer:** There are two acknowledgements. The **producer** gets an acknowledgement from the broker
(`acks`). The **consumer** acknowledges by **committing the offset** ("I have finished up to here").

**Key points:**
- Producer: `acks=all` is safest.
- Consumer: Kafka has no "ack per message"; you commit offsets (manually or automatically).
- In Spring: set `ack-mode: manual` and call `acknowledge()` after processing.

**Real-life example (invoice generation):** Commit only after the invoice is saved.

```yaml
spring.kafka.listener.ack-mode: manual
spring.kafka.consumer.enable-auto-commit: false
```
```java
@KafkaListener(topics = "orders")
void on(Order o, Acknowledgment ack) {
    invoiceService.create(o);
    ack.acknowledge();               // only now Kafka moves the offset forward
}
```

## K7. What is the message size limit? Can you send files to Kafka?

**Simple answer:** By default a message can be about **1 MB**. Kafka is made for **many small events**, not for
big files. For a big file, **store the file somewhere else (like S3) and send only its link in the message**.

**Key points:**
- Limits to raise together if needed: broker `message.max.bytes`, producer `max.request.size`, consumer
  `max.partition.fetch.bytes`.
- Large messages slow the whole cluster.
- The standard solution is the **claim-check pattern**: file in S3, reference in Kafka.

**Real-life example (insurance claims):** A customer uploads a 20 MB PDF. The app saves it in S3 and sends this
small event to Kafka:

```json
{ "claimId": "C-901", "documentUrl": "s3://claims/C-901/report.pdf", "sizeBytes": 20971520 }
```

## K8. How do you do unit testing in Kafka?

**Simple answer:** Test your **business logic without a real Kafka**. For the Kafka part, use a mock or a small
embedded Kafka.

**Key points:**
- Listener logic: call the method directly with a fake message.
- Producer code: mock `KafkaTemplate` and verify `send` was called.
- Integration test: `@EmbeddedKafka` or Testcontainers; use Awaitility to wait for the result.

**Real-life example (order consumer):**

```java
@Test
void reservesStockWhenOrderArrives() {
    listener.onOrder(new Order("42", "SKU-1", 2));          // call directly
    verify(inventoryService).reserve("SKU-1", 2);
}
```

## K9. Do you use a circuit breaker? If Kafka is down, how do you handle it?

**Simple answer:** Yes - we should protect the application so a Kafka problem does not freeze it. We set **short
timeouts**, wrap the send in a **circuit breaker**, and have a **fallback** so the event is not lost.

**Key points:**
- Producer sends can block (`max.block.ms`) and exhaust threads. Keep it short.
- Fallback options: **outbox table** (save in the DB and publish later), return `503`, or retry later.
- Never silently drop an important event.

**Real-life example (order service):** If Kafka is down, the order is still saved in the database together with an
"outbox" row. A background job publishes the pending rows when Kafka comes back.

```java
@CircuitBreaker(name = "kafka", fallbackMethod = "saveToOutbox")
void publish(OrderEvent e) { kafkaTemplate.send("orders", e.getOrderId(), e); }

void saveToOutbox(OrderEvent e, Throwable t) { outboxRepository.save(new OutboxRow(e)); }
```

## K10. How do you connect as a consumer?

**Simple answer:** You give the broker address, a **group id**, how to read keys/values, and then you write a
`@KafkaListener` method.

**Key points:**
- `group.id` decides which consumers share the work.
- `auto-offset-reset: earliest` - start from the beginning if no offset is saved.
- Turn off auto-commit for safe processing.

**Real-life example:**

```yaml
spring.kafka:
  bootstrap-servers: broker1:9092
  consumer:
    group-id: billing
    auto-offset-reset: earliest
    enable-auto-commit: false
    value-deserializer: org.springframework.kafka.support.serializer.JsonDeserializer
```
```java
@KafkaListener(topics = "orders")
void on(Order order) { billingService.bill(order); }
```

## K11. Multiple consumers/apps for the same message - how?

**Simple answer:** Give each application a **different `group.id`**. Each group receives **all** messages
independently. Consumers inside the **same** group share the work (each message goes to only one of them).

**Key points:**
- Different group ids = everyone gets every message.
- Same group id = load sharing.

**Real-life example (e-commerce):** The `OrderPlaced` event is needed by both Billing and Analytics.

```
topic: orders
  group "billing"   -> instances B1, B2 share the messages
  group "analytics" -> also gets every message
```

## K12. How does acknowledgement happen? What if you don't acknowledge?

**Simple answer:** Kafka tracks only the **offset** you commit. If you **do not commit**, Kafka thinks you did
not finish, so after a restart or rebalance the consumer reads those messages **again**.

**Key points:**
- Auto-commit: offsets are committed on a timer, even if your processing was not finished (risk of loss).
- Manual commit: you decide when; not committing means redelivery (so your code must be **idempotent**).
- Kafka does not "automatically acknowledge each message" in the sense of a queue.

**Real-life example (payment):** The consumer charged the card but crashed before committing. After restart, the
same message arrives again. Because the code checks "was this payment id already processed?", the customer is not
charged twice.

## K13. Do you have load balancing when connecting to Kafka? How?

**Simple answer:** You do not need a separate load balancer. The Kafka client already knows the brokers and
**spreads the work by partitions**.

**Key points:**
- Producers: messages spread across partitions (and so across brokers).
- Consumers: the **consumer group** divides partitions between instances.
- A normal TCP load balancer in front of Kafka brokers can cause problems because clients must talk to the
  specific broker that leads a partition.

**Real-life example:** A topic with 6 partitions and 3 consumer instances: each instance automatically gets 2
partitions. If one instance dies, its partitions move to the others.

## K14. Producer is a REST endpoint and Kafka goes down - will it still work?

**Simple answer:** The REST endpoint will **still be running**, but **publishing to Kafka will fail or hang**. You
must decide in advance what the endpoint should do.

**Key points - three options:**
1. **Fail fast** - return `503 Service Unavailable` (simple, no loss, user retries).
2. **Outbox** - save the event in the database in the same transaction, publish later (best: no loss, user is fine).
3. **Buffer in memory** - risky; lost if the app restarts.
- Use short timeouts so request threads are not stuck.

**Real-life example (bank transfer notification):** The transfer is saved in the database with an outbox row. Kafka
is down for 10 minutes. Customers are not affected. When Kafka returns, the outbox job sends all notifications.

## K15. How do you ensure that a message has been read by the consumer?

**Simple answer:** Check the **committed offset / consumer lag**. If the consumer group's offset has reached the
message's offset (lag = 0), the message has been read and processed.

**Key points:**
- Command: `kafka-consumer-groups --describe --group billing`.
- For business confirmation, the consumer can publish a result event or update a status ("processed").

**Real-life example (order tracking):** The Order page shows "Inventory reserved" because the inventory consumer
updated the order status after processing the event.

## K16. Can you send files through Kafka?

**Simple answer:** Technically yes (a message is bytes), but **it is not a good idea for big files**. Send the
**link** to the file instead. Small files (a few KB) are fine.

**Key points:** See K7. Use S3/object storage and the claim-check pattern.

**Real-life example (KYC):** The scanned passport goes to S3; Kafka carries `{"customerId":101,"fileUrl":"s3://..."}`.

## K17. When writing to Kafka, how do you make sure it is not overloaded and data is not lost?

**Simple answer:** **Do not lose data** by using safe producer settings. **Do not overload** by sizing
partitions, batching, setting limits, and watching the metrics.

**Key points:**
- No loss: `acks=all`, replication factor 3, `min.insync.replicas=2`, idempotent producer, commit after processing.
- No overload: enough partitions, batching and compression, client **quotas**, bounded producer buffer,
  scale consumers, retention matching disk size.
- Monitor lag, disk usage and under-replicated partitions.

**Real-life example (IoT):** 10,000 sensors send readings every second. Producers batch (`linger.ms=20`) and
compress (`lz4`), reducing the network load, while `acks=all` makes sure readings are not lost.

```properties
acks=all
enable.idempotence=true
linger.ms=20
compression.type=lz4
```

## K18. How do you mainly connect the Kafka engine with Spring?

**Simple answer:** With the **`spring-kafka`** library. `KafkaTemplate` sends messages and `@KafkaListener`
receives them. Configuration comes from `application.yml`.

**Key points:**
- Add dependency `spring-kafka`; Spring Boot auto-configures it.
- Error handling with `DefaultErrorHandler` and a dead-letter topic.
- Alternative: Spring Cloud Stream (higher-level).

**Real-life example (notification service):**

```java
@Service
class NotificationProducer {
    private final KafkaTemplate<String, String> template;
    NotificationProducer(KafkaTemplate<String, String> template) { this.template = template; }
    void send(String userId, String text) { template.send("notifications", userId, text); }
}
```

---

# E. Other questions

## O1. How do you do TDD? Which frameworks?

**Simple answer:** TDD = **write the test first**, then write just enough code to make it pass, then clean up.
The cycle is **Red -> Green -> Refactor**.

**Key points:**
- Red: the test fails (the code does not exist yet).
- Green: write the simplest code to pass.
- Refactor: improve the code while tests stay green.
- Tools: **JUnit 5**, **Mockito**, **AssertJ**, `MockMvc`, **Testcontainers**, JaCoCo (coverage).

**Real-life example (discount rule):** "Orders above 1000 get 10 percent off."

```java
@Test
void appliesTenPercentDiscountAbove1000() {                    // 1. write test first (fails)
    assertThat(new PriceCalculator().finalPrice(2000)).isEqualTo(1800);
}
// 2. write PriceCalculator.finalPrice() to pass  3. refactor
```

## O2. What kind of databases did you connect with your API?

**Simple answer:** Answer from **your own project**. A typical strong answer names one relational and one NoSQL
database and says **why**.

**Key points:**
- **Relational** (Oracle, PostgreSQL, MySQL) - transactions, joins; via Spring Data JPA or JDBC.
- **NoSQL** (MongoDB, Couchbase, Cassandra) - flexible schema or very high scale.
- Mention connection pooling (HikariCP).

**Real-life example (retail):** Orders and payments in PostgreSQL (need transactions). Product catalog in MongoDB
(flexible attributes: a phone and a shirt have different fields).

## O3. Do you implement a health check in your API? How?

**Simple answer:** Yes, using **Spring Boot Actuator**. It gives `/actuator/health` which tells whether the app
and its dependencies (database, Kafka, disk) are healthy. Kubernetes uses it to decide whether to restart the
app or send traffic.

**Key points:**
- **Liveness** - "is the app alive?" (restart if not).
- **Readiness** - "is it ready to take traffic?"
- You can write a **custom health indicator** for a dependency.

**Real-life example (payment service):** The health endpoint reports DOWN if the payment gateway is not
reachable, so the load balancer stops sending traffic.

```yaml
management.endpoints.web.exposure.include: health
management.endpoint.health.probes.enabled: true
```
```java
@Component
class GatewayHealth implements HealthIndicator {
    public Health health() {
        return gatewayReachable() ? Health.up().build() : Health.down().withDetail("gateway", "timeout").build();
    }
}
```

## O4. How do you handle large data (millions of records) in your APIs?

**Simple answer:** Never load everything into memory or return everything in one response. Read and send data in
**small parts**: pagination, streaming, batch jobs, or background processing.

**Key points:**
- **Pagination** (`Pageable`); for very deep pages use **keyset** pagination (`WHERE id > lastId LIMIT 100`).
- **Streaming** the result or **chunked** processing.
- **Spring Batch** for big jobs; **batch inserts** for writes.
- Select only the columns you need; add **indexes**.
- For a big export: return `202 Accepted`, process in the background, and give a download link later.

**Real-life example (bank statement for 5 years):** The customer asks for a download of 2 million transactions.
The API creates a job, a background worker writes a CSV to S3, and the customer gets an email with the link.

```java
Page<Transaction> page = repository.findByAccountId(id, PageRequest.of(0, 100, Sort.by("date")));
```

## O5. How do you connect to 3 different databases?

**Simple answer:** The same idea as two databases (E29): create **three DataSource beans**, each with its own
entity manager and transaction manager, and separate repository packages.

**Key points:**
- Mark one as `@Primary`.
- Name the transaction managers and select them in `@Transactional("name")`.
- If it is the **same schema in many databases (one per customer)**, use `AbstractRoutingDataSource` to pick the
  database at run time.
- No automatic single transaction across all three; use saga/outbox if consistency is required.

**Real-life example (multi-country bank):** Customers of India, UK and US are stored in three regional databases
because of data-residency rules. A routing data source picks the database from the customer's country.

## O6. Did you use Apigee? How do you publish an API to Apigee?

**Simple answer:** Apigee is a **tool for managing APIs** (gateway, security, limits, analytics, developer
portal). Publishing means: create an **API proxy** in front of your backend, add **policies**, **deploy** it, and
put it into an **API product** that developers subscribe to.

**Key points (steps):**
1. Create an **API proxy** (from an OpenAPI file or a backend URL).
2. Add **policies**: OAuth/API key check, quota, spike arrest, response caching.
3. **Deploy** the revision to an environment (test, then prod).
4. Create an **API product** and a **developer app** that gets the API key.
5. Automate with CI/CD (`apigeecli`, Maven plugin).
- If you have not used Apigee, say so honestly and explain the same ideas from another gateway you used
  (Spring Cloud Gateway, AWS API Gateway).

**Real-life example (bank open banking API):** The bank exposes `/accounts` to partner fintech apps. Apigee checks
each partner's key, allows 1000 calls per hour, and shows usage reports.

## O7. How do you secure your REST API?

**Simple answer:** Same as E31: HTTPS, token-based login (JWT/OAuth2), role checks, input validation, rate
limiting, restricted CORS and safe error messages.

**Real-life example (banking):** See E31 - the code also checks that the account belongs to the logged-in customer.

## O8. Have you handled the file system using Spring Boot?

**Simple answer:** Yes. We **upload** files with `MultipartFile`, **download** with `Resource`, and read/write
with `java.nio.file.Files`.

**Key points:**
- Validate file **size and type**.
- Never trust the original file name (path traversal like `../../etc/passwd`).
- For production, store files in object storage (S3), not on the application server disk.

**Real-life example (HR portal):** Employees upload their documents. The app cleans the file name, saves it, and
returns the stored path.

```java
@PostMapping("/documents")
String upload(@RequestParam MultipartFile file) throws IOException {
    String safeName = Path.of(file.getOriginalFilename()).getFileName().toString();   // removes ../
    Path target = Path.of("/data/docs").resolve(safeName);
    file.transferTo(target);
    return safeName;
}
```

## O9. What if the file is very large, say 200-300 MB? Can Spring Boot handle it?

**Simple answer:** Yes, if you **stream** the file and never load it fully into memory. Also raise the upload
limits and consider letting the client upload directly to S3.

**Key points:**
- Increase `spring.servlet.multipart.max-file-size` and `max-request-size`.
- Copy using streams (`Files.copy(inputStream, path)`) - small memory use.
- For download, use `StreamingResponseBody` or `Resource`.
- Better at scale: **pre-signed S3 URL** (client uploads directly), chunked/resumable upload, process
  asynchronously.
- Check gateway / load balancer timeouts and body size limits.

**Real-life example (video upload for training portal):** The API gives the browser a pre-signed S3 URL. The
300 MB video goes straight to S3, the application server never handles the bytes, and an event triggers
processing afterwards.

```yaml
spring.servlet.multipart.max-file-size: 500MB
spring.servlet.multipart.max-request-size: 500MB
```
```java
try (InputStream in = file.getInputStream()) {
    Files.copy(in, target, StandardCopyOption.REPLACE_EXISTING);   // streamed, not loaded fully
}
```

## O10. Have you managed a team? Were you part of a production release?

**Simple answer:** Answer from your **own experience** using the **STAR** method: **S**ituation, **T**ask,
**A**ction, **R**esult. Use numbers if you can.

**Key points to mention:**
- **Your role** in the release: code review, testing, deployment, monitoring, rollback plan.
- **Process**: CI/CD pipeline, approvals, release notes, canary or blue-green deployment.
- **A problem you faced** and how you solved it (a failed deployment or incident).
- **Team side**: dividing tasks, mentoring juniors, unblocking people, communicating with business.

**Real-life example (release story):**
"We released a new payment feature on Saturday night (Situation). I was responsible for the deployment and
verification (Task). I prepared a rollback plan, used a canary release to 5 percent of users, and watched error
rate in Splunk (Action). Errors stayed under 0.1 percent, so we moved to 100 percent with zero downtime (Result)."

---

# Quick self-check (answer each in 30 seconds)

1. `==` vs `equals()` and why `hashCode()` must match. (F9)
2. Name two cases where `finally` does not run. (F24)
3. Why can a local variable not be used before initialization? (F26)
4. OAuth2 vs JWT in one sentence each. (E13)
5. Two apps both need every Kafka message: what do you set? (K11)
6. Kafka is down but the REST call arrives: three options? (K14)
7. How do you upload a 300 MB file without running out of memory? (O9)
8. Why does `@PreAuthorize` not work on `this.method()`? (A2)
9. Composition vs aggregation with one example each. (E22)
10. How do you make a class a singleton, and why is the holder idiom safe? (E10)
