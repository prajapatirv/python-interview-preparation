"""
Generators, iterators, iterables, yield/yield from, send/throw, and itertools.
Run me: python 04_generators_iterators.py
"""
from itertools import accumulate, groupby, islice


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ---------------------------------------------------------------- iterable vs iterator
section("iterable vs iterator")
nums = [1, 2]
it = iter(nums)                 # list -> list_iterator
print(next(it), next(it))
print("iter(it) is it ->", iter(it) is it)  # iterators return themselves
try:
    next(it)
except StopIteration:
    print("exhausted -> StopIteration")


# ---------------------------------------------------------------- custom iterator class
section("write your own iterator (the manual, verbose way)")


class Countdown:
    def __init__(self, start):
        self.cur = start

    def __iter__(self):
        return self

    def __next__(self):
        if self.cur <= 0:
            raise StopIteration
        self.cur -= 1
        return self.cur + 1


print(list(Countdown(3)))


# ---------------------------------------------------------------- generator function (the easy way)
section("the same thing with a generator function — far less code")


def countdown(n):
    while n > 0:
        yield n
        n -= 1


g = countdown(3)
print(next(g), next(g), list(g))  # 3 2 [1]

# EXPERIMENT: call list(g) again right now -- you get [] because a generator is single-pass.
print("iterating the exhausted generator again:", list(g))


# ---------------------------------------------------------------- lazy file-like pipeline
section("why generators matter: constant-memory pipelines")


def read_lines(lines):
    for line in lines:
        yield line


def parse_errors(lines):
    for line in lines:
        if "ERROR" in line:
            yield line.strip()


fake_log = ["INFO boot", "ERROR disk full", "INFO ok", "ERROR timeout"]
for err in parse_errors(read_lines(fake_log)):
    print("  found:", err)


# ---------------------------------------------------------------- yield from
section("yield from — flatten a recursive structure")


def flatten(items):
    for x in items:
        if isinstance(x, list):
            yield from flatten(x)
        else:
            yield x


print(list(flatten([1, [2, [3, 4]], 5])))


# ---------------------------------------------------------------- send() — a coroutine-style generator
section("generator.send() — a running average accumulator")


def running_avg():
    total = count = 0
    avg = None
    while True:
        value = yield avg
        total += value
        count += 1
        avg = total / count


avg_gen = running_avg()
next(avg_gen)  # prime it (advances to the first yield)
print("send(10) ->", avg_gen.send(10))
print("send(20) ->", avg_gen.send(20))


# ---------------------------------------------------------------- itertools grab bag
section("itertools: islice, groupby, accumulate, batching")
print("first 5 of an infinite-ish range:", list(islice(range(10 ** 9), 5)))

animals = sorted(["cat", "cow", "dog", "duck"], key=lambda s: s[0])
grouped = {k: list(v) for k, v in groupby(animals, key=lambda s: s[0])}
print("grouped by first letter:", grouped)

print("running totals:", list(accumulate([1, 2, 3, 4])))


def batched(iterable, n):
    """itertools.batched exists natively in 3.12+; this is the portable version."""
    it = iter(iterable)
    while chunk := list(islice(it, n)):
        yield chunk


print("batched into 3s:", list(batched(range(7), 3)))

# EXERCISE: write a generator `paginate(fetch_page, page_size)` that lazily yields items across
# pages, stopping when a page comes back empty. Sketch the shape before checking
# 06_kafka/02_consumer_basics.py for a similar "keep pulling until exhausted" pattern.
