"""
Context managers: class-based __enter__/__exit__, @contextmanager, ExitStack, and an async version.
Run me: python 05_context_managers.py
"""
import asyncio
import time
from contextlib import ExitStack, contextmanager, suppress, asynccontextmanager


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ---------------------------------------------------------------- class-based context manager
section("class-based context manager: a fake DB transaction")


class Transaction:
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        print(f"  BEGIN {self.name}")
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            print(f"  COMMIT {self.name}")
        else:
            print(f"  ROLLBACK {self.name} (because of {exc_type.__name__}: {exc})")
        return False  # False = don't swallow the exception


with Transaction("orders"):
    print("  ... doing work ...")

try:
    with Transaction("payments"):
        raise ValueError("insufficient funds")
except ValueError:
    print("  caller sees the exception (we returned False above)")


# ---------------------------------------------------------------- @contextmanager (generator form)
section("@contextmanager — code before yield is __enter__, `finally` is __exit__")


@contextmanager
def timer(label):
    start = time.perf_counter()
    try:
        yield
    finally:
        print(f"  {label}: {(time.perf_counter() - start) * 1000:.2f}ms")


with timer("sum of a million"):
    sum(range(1_000_000))


# ---------------------------------------------------------------- suppress()
section("contextlib.suppress — silence a specific expected exception")
import os

with suppress(FileNotFoundError):
    os.remove("this_file_does_not_exist.tmp")
print("  no crash, suppress() ate the FileNotFoundError")


# ---------------------------------------------------------------- ExitStack for a dynamic number of resources
section("ExitStack — manage an unknown-at-write-time number of context managers")


@contextmanager
def fake_resource(name):
    print(f"  open {name}")
    try:
        yield name
    finally:
        print(f"  close {name}")


resource_names = ["conn-1", "conn-2", "conn-3"]
with ExitStack() as stack:
    resources = [stack.enter_context(fake_resource(n)) for n in resource_names]
    print("  using:", resources)
# all three close automatically, in reverse order, even if one had raised


# ---------------------------------------------------------------- async context manager
section("async context manager — the shape used for Kafka/DB clients in 06_kafka and 05_web_apis_fastapi")


class FakeProducer:
    async def start(self):
        print("  producer connected")

    async def stop(self):
        print("  producer flushed & closed")

    async def send(self, topic, value):
        print(f"  sent to {topic}: {value}")


@asynccontextmanager
async def producer():
    p = FakeProducer()
    await p.start()
    try:
        yield p
    finally:
        await p.stop()  # always runs, even on error


async def main():
    async with producer() as p:
        await p.send("orders", "hello")


asyncio.run(main())

# EXPERIMENT: make fake_resource's `yield name` raise an exception after opening "conn-2" and
# confirm conn-1 still gets closed cleanly by ExitStack.
