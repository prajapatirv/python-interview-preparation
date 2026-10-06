"""
How Kafka configuration is actually done from Python: the producer and consumer settings that
matter, what each one trades away, the four profiles you'll be asked to justify (throughput /
low-latency / no-loss / exactly-once), and a validator that catches the contradictory combinations
people ship by accident.

Runs with **zero dependencies and no broker** -- the config dicts are the real confluent-kafka
keys, and the validator encodes the rules a senior engineer applies in review. Where
`confluent_kafka` is installed, the bottom section shows the exact client construction.

Run me: python 07_kafka_python_config.py
"""
import json
import os

try:
    from confluent_kafka import Consumer, Producer
except ImportError:                      # read/run this file without the dependency installed
    Consumer = Producer = None


def section(title):
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


# ---------------------------------------------------------------- the producer settings that matter
PRODUCER_SETTINGS = [
    # key, default, what it does, what it costs
    ("bootstrap.servers", "-",
     "comma-separated broker list; only used for DISCOVERY, not as a fixed target",
     "give 2-3, not 1 -- one dead bootstrap broker must not stop startup"),
    ("acks", "all",
     "0 = fire and forget, 1 = leader only, all = leader + every in-sync replica",
     "acks=all costs one extra round trip; acks=1 loses data if the leader dies before replicating"),
    ("enable.idempotence", "true",
     "sequence numbers per producer+partition so the broker drops duplicate retried batches",
     "implies acks=all, retries>0, max.in.flight<=5. Essentially free -- leave it on"),
    ("retries", "2147483647",
     "how many times librdkafka retries a failed batch internally",
     "bounded in practice by delivery.timeout.ms -- that's the knob you actually tune"),
    ("delivery.timeout.ms", "120000",
     "TOTAL time a message may spend in send + retries before the callback gets an error",
     "the real deadline. Must be >= linger.ms + request.timeout.ms"),
    ("linger.ms", "5",
     "wait this long to fill a batch before sending",
     "pure latency-for-throughput trade: 0 = lowest latency, 20-100 = far fewer requests"),
    ("batch.size", "16384",
     "max bytes per partition batch (librdkafka: batch.num.messages too)",
     "bigger = better compression and throughput, more memory per partition"),
    ("compression.type", "none",
     "none | gzip | snappy | lz4 | zstd",
     "lz4 = best throughput/CPU balance; zstd = best ratio; gzip = slowest. Set it, don't skip it"),
    ("max.in.flight.requests.per.connection", "5",
     "unacknowledged requests allowed per connection",
     ">5 with idempotence off can REORDER messages on retry -- the classic ordering bug"),
    ("buffer.memory / queue.buffering.max.kbytes", "~32MB",
     "local send queue size; when full, produce() blocks or raises BufferError",
     "a full queue is BACKPRESSURE -- handle it, never catch-and-drop"),
    ("transactional.id", "None",
     "enables transactions (and fences a previous instance with the same id)",
     "exactly-once machinery; must be STABLE per logical producer, never random per restart"),
]

# ---------------------------------------------------------------- the consumer settings that matter
CONSUMER_SETTINGS = [
    ("group.id", "-",
     "the consumer group; partitions are divided among members sharing this id",
     "change it and you re-read from auto.offset.reset -- a classic accidental replay"),
    ("enable.auto.commit", "true",
     "commits offsets on a timer in the background",
     "TRUE IS THE #1 SOURCE OF SILENT MESSAGE LOSS: it can commit a message you haven't finished"),
    ("auto.commit.interval.ms", "5000",
     "how often the auto-committer fires",
     "only relevant while auto-commit is on, which it should not be for real processing"),
    ("auto.offset.reset", "latest",
     "earliest | latest -- used ONLY when the group has no committed offset",
     "'latest' on a brand-new group silently skips the existing backlog"),
    ("max.poll.interval.ms", "300000",
     "max time between poll() calls before the broker declares you dead and rebalances",
     "slow per-message work (or a sleep in the loop) blows this and causes a rebalance storm"),
    ("session.timeout.ms", "45000",
     "heartbeat liveness window",
     "too low = spurious rebalances; too high = slow failure detection"),
    ("max.poll.records / fetch max bytes", "500",
     "how much one poll() hands you",
     "lower it when per-message work is slow -- that's the real fix for max.poll.interval breaches"),
    ("isolation.level", "read_committed",
     "read_committed hides records from aborted/open transactions",
     "required for exactly-once reads; adds a small latency (waits for the commit marker)"),
    ("partition.assignment.strategy", "cooperative-sticky",
     "range | roundrobin | sticky | cooperative-sticky",
     "cooperative-sticky = incremental rebalance: members keep most partitions, no stop-the-world"),
]


def print_table(title, rows):
    print(f"\n  {title}")
    for key, default, what, cost in rows:
        print(f"\n    {key}  (default: {default})")
        print(f"      what : {what}")
        print(f"      cost : {cost}")


# ---------------------------------------------------------------- the four profiles
def producer_config(profile, bootstrap="localhost:9092"):
    """The config you'd actually paste, per profile. Interviewers ask you to justify ONE of these;
    knowing all four and the single line that differs between them is the whole answer."""
    base = {
        "bootstrap.servers": bootstrap,
        "client.id": "orders-service-1",     # shows up in broker logs/metrics -- always set it
        "compression.type": "lz4",
    }
    if profile == "throughput":
        return base | {
            "acks": "1",                     # one round trip instead of two
            "linger.ms": 50,                 # fill big batches
            "batch.size": 262144,            # 256KB
            "enable.idempotence": False,      # must be off: idempotence forces acks=all
        }
    if profile == "low-latency":
        return base | {
            "acks": "1",
            "linger.ms": 0,                  # send immediately, batch of 1 is fine
            "compression.type": "none",      # compression costs microseconds we don't have
            "enable.idempotence": False,
        }
    if profile == "no-loss":                 # the sane DEFAULT for business data
        return base | {
            "acks": "all",
            "enable.idempotence": True,      # dedupes broker-side retries
            "delivery.timeout.ms": 120000,
            "linger.ms": 10,
            "max.in.flight.requests.per.connection": 5,
        }
    if profile == "exactly-once":
        return base | {
            "acks": "all",
            "enable.idempotence": True,
            "transactional.id": "orders-writer-1",   # STABLE per instance, not a uuid4()
            "transaction.timeout.ms": 60000,
        }
    raise ValueError(f"unknown profile {profile!r}")


def consumer_config(profile, bootstrap="localhost:9092", group="orders-consumer"):
    base = {
        "bootstrap.servers": bootstrap,
        "group.id": group,
        "client.id": "orders-consumer-1",
        "partition.assignment.strategy": "cooperative-sticky",
    }
    if profile == "at-most-once":
        return base | {
            "enable.auto.commit": True,      # commits before you finish -> loss on crash
            "auto.offset.reset": "latest",
        }
    if profile == "at-least-once":           # the sane DEFAULT; make the handler idempotent
        return base | {
            "enable.auto.commit": False,     # YOU commit, after processing succeeds
            "auto.offset.reset": "earliest",
            "max.poll.interval.ms": 300000,
            "max.poll.records": 100,
        }
    if profile == "exactly-once":
        return base | {
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
            "isolation.level": "read_committed",   # ignore aborted transactions
        }
    if profile == "slow-handler":            # per-message work takes seconds (an LLM call, an API)
        return base | {
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
            "max.poll.records": 10,          # take less per poll...
            "max.poll.interval.ms": 900000,  # ...and allow longer between polls
            "session.timeout.ms": 45000,
        }
    raise ValueError(f"unknown profile {profile!r}")


# ---------------------------------------------------------------- the validator
def validate_producer_config(cfg):
    """Returns a list of (severity, message). These are the real contradictions that ship:
    each one has cost somebody a production incident."""
    problems = []
    acks = str(cfg.get("acks", "all"))
    idempotent = cfg.get("enable.idempotence", True)
    in_flight = int(cfg.get("max.in.flight.requests.per.connection", 5))

    if idempotent and acks not in ("all", "-1"):
        problems.append(("ERROR", "enable.idempotence=True REQUIRES acks=all; the client will "
                                  "refuse to start with acks=" + acks))
    if idempotent and in_flight > 5:
        problems.append(("ERROR", "enable.idempotence=True allows max.in.flight<=5, "
                                  f"got {in_flight}"))
    if not idempotent and in_flight > 1 and int(cfg.get("retries", 1)) > 0:
        problems.append(("WARN", "retries>0 with max.in.flight>1 and idempotence OFF can "
                                 "REORDER messages on retry -- turn idempotence on"))
    if acks in ("0", "1"):
        problems.append(("WARN", f"acks={acks} will lose acknowledged messages if the partition "
                                 "leader fails before replicating. Fine for metrics, not for orders"))
    if "transactional.id" in cfg and not idempotent:
        problems.append(("ERROR", "transactions require enable.idempotence=True"))
    if cfg.get("compression.type", "none") == "none":
        problems.append(("INFO", "compression.type=none -- lz4 typically cuts network bytes 3-5x "
                                 "for JSON at negligible CPU cost"))
    if "linger.ms" in cfg and "delivery.timeout.ms" in cfg:
        if int(cfg["delivery.timeout.ms"]) <= int(cfg["linger.ms"]):
            problems.append(("ERROR", "delivery.timeout.ms must exceed linger.ms + "
                                      "request.timeout.ms"))
    if "bootstrap.servers" in cfg and len(cfg["bootstrap.servers"].split(",")) == 1:
        problems.append(("INFO", "a single bootstrap server is a startup SPOF; list 2-3"))
    return problems


def validate_consumer_config(cfg):
    problems = []
    auto_commit = cfg.get("enable.auto.commit", True)
    if auto_commit:
        problems.append(("ERROR", "enable.auto.commit=True means offsets can be committed for a "
                                  "message you have not finished processing -> SILENT LOSS on "
                                  "crash. Commit manually after the work succeeds"))
    if cfg.get("auto.offset.reset", "latest") == "latest":
        problems.append(("WARN", "auto.offset.reset=latest makes a NEW group skip the existing "
                                 "backlog. Use 'earliest' unless skipping is deliberate"))
    if "group.id" not in cfg:
        problems.append(("ERROR", "group.id is required for a subscribing consumer"))
    if int(cfg.get("max.poll.records", 500)) > 100 and \
            int(cfg.get("max.poll.interval.ms", 300000)) <= 300000:
        problems.append(("INFO", "high max.poll.records + default max.poll.interval.ms: if each "
                                 "message takes >3s you will breach the interval and rebalance"))
    if cfg.get("isolation.level") == "read_committed" and auto_commit:
        problems.append(("WARN", "read_committed with auto-commit defeats the point of "
                                 "transactional reads"))
    return problems


# ---------------------------------------------------------------- 12-factor config loading
def config_from_environment(prefix="KAFKA_"):
    """How this is wired in a real service: NOTHING hardcoded, every key from the environment,
    secrets from a secret manager -- never from the repo.

        KAFKA_BOOTSTRAP_SERVERS=b1:9092,b2:9092
        KAFKA_SECURITY_PROTOCOL=SASL_SSL
        KAFKA_SASL_MECHANISM=SCRAM-SHA-512
        KAFKA_SASL_USERNAME=...        <- from AWS Secrets Manager / SSM, injected at boot
        KAFKA_SASL_PASSWORD=...

    The mapping rule: strip the prefix, lowercase, underscores -> dots. That one line turns any
    librdkafka property into an env var with no code change per setting.
    """
    cfg = {}
    for env_key, value in os.environ.items():
        if env_key.startswith(prefix):
            cfg[env_key[len(prefix):].lower().replace("_", ".")] = value
    return cfg


MSK_IAM_NOTE = """\
  Amazon MSK, IAM auth (the common AWS setup):
    security.protocol = SASL_SSL
    sasl.mechanism    = OAUTHBEARER
    sasl.oauthbearer.token.refresh.cb = <callback using aws-msk-iam-sasl-signer-python>
    # pip install aws-msk-iam-sasl-signer-python
    #   from aws_msk_iam_sasl_signer import MSKAuthTokenProvider
    #   token, expiry_ms = MSKAuthTokenProvider.generate_auth_token("ap-south-1")
  Confluent Cloud:
    security.protocol = SASL_SSL
    sasl.mechanism    = PLAIN
    sasl.username     = <API key>      sasl.password = <API secret>
  Self-managed with SCRAM:
    security.protocol = SASL_SSL
    sasl.mechanism    = SCRAM-SHA-512
    ssl.ca.location   = /etc/ssl/certs/ca-bundle.crt"""


# ---------------------------------------------------------------- real client construction
def build_real_producer(profile="no-loss"):
    """The actual confluent-kafka call. Note what is NOT here: no retry loop of your own, no
    thread pool. librdkafka batches and retries in a background thread; your job is to call
    produce() + poll() and to handle the delivery callback."""
    if Producer is None:
        return None
    cfg = producer_config(profile)

    def on_delivery(err, msg):
        if err:                                        # THE place you learn a send failed
            print(f"    DELIVERY FAILED {err} -- persist it or alert; do not just log and move on")
        else:
            print(f"    delivered {msg.topic()}[{msg.partition()}]@{msg.offset()}")

    p = Producer(cfg)
    p.produce("orders", key=b"ORD-1", value=json.dumps({"id": "ORD-1"}).encode(),
              on_delivery=on_delivery)
    p.poll(0)        # serves delivery callbacks; without this they only fire on flush()
    p.flush(10)      # blocks until every queued message is acked -- ALWAYS call before exit
    return cfg


def build_real_consumer(profile="at-least-once"):
    """The at-least-once consume loop, in the shape that survives a rebalance."""
    if Consumer is None:
        return None
    cfg = consumer_config(profile)
    c = Consumer(cfg)
    c.subscribe(["orders"])
    try:
        while True:
            msg = c.poll(1.0)                 # never poll(0) in a tight loop -- it spins the CPU
            if msg is None:
                continue
            if msg.error():
                print(f"    consumer error: {msg.error()}")
                continue
            process(msg)                      # YOUR idempotent handler
            c.commit(message=msg, asynchronous=False)   # commit AFTER the work succeeded
    finally:
        c.close()      # leaves the group cleanly -> immediate rebalance instead of a 45s timeout
    return cfg


def process(msg):
    """Must be idempotent: at-least-once means this WILL see the same message twice."""


if __name__ == "__main__":
    section("the producer settings that matter, and what each one costs")
    print_table("PRODUCER", PRODUCER_SETTINGS)

    section("the consumer settings that matter, and what each one costs")
    print_table("CONSUMER", CONSUMER_SETTINGS)

    section("the four producer profiles -- one or two lines differ between them")
    for profile in ("throughput", "low-latency", "no-loss", "exactly-once"):
        cfg = producer_config(profile)
        print(f"\n  {profile}:")
        for k, v in cfg.items():
            print(f"    {k:42s} = {v}")

    section("the four consumer profiles")
    for profile in ("at-most-once", "at-least-once", "exactly-once", "slow-handler"):
        cfg = consumer_config(profile)
        print(f"\n  {profile}:")
        for k, v in cfg.items():
            print(f"    {k:42s} = {v}")

    section("the validator: contradictory configs that really do get shipped")
    broken_producer = {
        "bootstrap.servers": "localhost:9092",
        "acks": "1",
        "enable.idempotence": True,                      # contradicts acks=1
        "max.in.flight.requests.per.connection": 10,     # contradicts idempotence
        "transactional.id": "writer-1",
        "compression.type": "none",
    }
    print("\n  a producer config with contradictions the client will reject at startup:")
    for severity, message in validate_producer_config(broken_producer):
        print(f"    [{severity:5s}] {message}")

    print("\n  the no-loss profile, checked:")
    issues = validate_producer_config(producer_config("no-loss"))
    for severity, message in issues:
        print(f"    [{severity:5s}] {message}")
    print(f"    -> {sum(1 for s, _ in issues if s == 'ERROR')} errors "
          f"(info/warn only: a single bootstrap host in this demo)")

    broken_consumer = {
        "group.id": "orders",
        "enable.auto.commit": True,
        "auto.offset.reset": "latest",
        "isolation.level": "read_committed",
        "max.poll.records": 500,
    }
    print("\n  a consumer config with the classic silent-loss combination:")
    for severity, message in validate_consumer_config(broken_consumer):
        print(f"    [{severity:5s}] {message}")

    print("\n  the at-least-once profile, checked:")
    for severity, message in validate_consumer_config(consumer_config("at-least-once")) or \
            [("OK", "no problems found")]:
        print(f"    [{severity:5s}] {message}")

    section("configuration comes from the environment, never from the repo")
    print(config_from_environment.__doc__)
    os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", "b-1:9092,b-2:9092")
    os.environ.setdefault("KAFKA_SECURITY_PROTOCOL", "SASL_SSL")
    os.environ.setdefault("KAFKA_SASL_MECHANISM", "SCRAM-SHA-512")
    print(f"  parsed from env: {config_from_environment()}")

    section("auth config per platform")
    print(MSK_IAM_NOTE)

    section("running against a real broker")
    if Producer is None:
        print("  confluent-kafka is not installed, so the live section is skipped.")
        print("  pip install confluent-kafka, then `docker compose -f docker-compose.kafka.yml up -d`")
        print("  and re-run. build_real_producer() / build_real_consumer() above are the exact code.")
    else:
        print("  confluent-kafka IS installed -- producing one message with the no-loss profile:")
        build_real_producer("no-loss")

    section("the five answers to memorise")
    print("""  1. "How do you avoid losing messages?"
       Producer: acks=all + enable.idempotence=true + a bounded delivery.timeout.ms, and ACT on
       the delivery callback error. Consumer: enable.auto.commit=FALSE, commit after processing.
       Broker: RF=3 + min.insync.replicas=2.

  2. "How do you avoid duplicates?"
       You don't -- at-least-once guarantees you'll get them. You make the HANDLER idempotent:
       an idempotency key (event_id) with a unique index, or an UPSERT. Exactly-once semantics
       exist (transactional.id + read_committed) but only cover Kafka-to-Kafka.

  3. "Your consumer keeps rebalancing. Why?"
       Processing takes longer than max.poll.interval.ms between poll() calls. Fix the handler,
       or lower max.poll.records, or move slow work off the poll thread. Never sleep in the loop.

  4. "How do you tune for throughput?"
       linger.ms up, batch.size up, compression=lz4, and more PARTITIONS -- consumer parallelism
       is capped by partition count, not by thread count.

  5. "Where does the config live?"
       Environment variables mapped to librdkafka keys, secrets from a secret manager, one
       profile per environment, and the config validated at startup so a bad combination fails
       the deploy instead of the 3am page.""")

# EXPERIMENT 1: run validate_producer_config(producer_config("throughput")) and read the acks=1
# warning. Decide out loud whether you'd accept it for clickstream data, and for payments.
# EXPERIMENT 2: set KAFKA_ENABLE_AUTO_COMMIT=false in your shell, re-run, and watch it appear as
# `enable.auto.commit` in config_from_environment() -- that's the whole env-to-librdkafka mapping.
# EXPERIMENT 3: add a rule to validate_consumer_config() that flags session.timeout.ms greater
# than max.poll.interval.ms, and explain which failure that combination hides.

# EXERCISE: write `merge_config(defaults, env, overrides)` that layers the three sources
# (collections.ChainMap is one good answer), runs both validators, and raises at startup if any
# ERROR is present -- so a contradictory Kafka config fails the deploy, not the 3am page. Then add
# a `--dry-run` flag that prints the final merged config with sasl.password redacted.
