"""
asyncio: coroutines, gather, Semaphore for bounded concurrency, timeout/cancellation,
and a producer/consumer pipeline with asyncio.Queue.
Run me: python 03_asyncio_demo.py
"""
import asyncio
import time


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ---------------------------------------------------------------- gather: run coroutines concurrently
async def fetch(i):
    await asyncio.sleep(0.3)  # non-blocking wait -- the event loop runs other coroutines meanwhile
    return i


async def demo_gather():
    section("asyncio.gather — 20 'requests' of 0.3s complete in ~0.3s, not 6s")
    start = time.perf_counter()
    results = await asyncio.gather(*(fetch(i) for i in range(20)))
    print(f"gathered {len(results)} results in {time.perf_counter() - start:.2f}s")


# ---------------------------------------------------------------- Semaphore: bound concurrency
async def demo_semaphore():
    section("asyncio.Semaphore — cap concurrent 'in-flight requests' at 5")
    sem = asyncio.Semaphore(5)
    active = {"now": 0, "max_seen": 0}

    async def bounded_call(i):
        async with sem:
            active["now"] += 1
            active["max_seen"] = max(active["max_seen"], active["now"])
            await asyncio.sleep(0.05)
            active["now"] -= 1
        return i

    await asyncio.gather(*(bounded_call(i) for i in range(30)))
    print(f"max concurrent calls observed: {active['max_seen']} (should be <= 5)")


# ---------------------------------------------------------------- what happens if you block the loop
async def demo_blocking_mistake():
    section("blocking the event loop vs offloading with asyncio.to_thread")

    def legacy_blocking_call():
        time.sleep(0.3)  # a real blocking library call (sync SQLAlchemy, requests, etc.)
        return "done"

    start = time.perf_counter()
    # WRONG (commented out on purpose): calling legacy_blocking_call() directly inside async
    # code would freeze the entire event loop for 0.3s -- nothing else could run meanwhile.
    result = await asyncio.to_thread(legacy_blocking_call)  # runs in a worker thread instead
    print(f"offloaded blocking call via to_thread: {result} in {time.perf_counter() - start:.2f}s")


# ---------------------------------------------------------------- timeout + cancellation
async def demo_timeout():
    section("asyncio.timeout — cancel a coroutine that's taking too long")

    async def slow():
        await asyncio.sleep(5)

    try:
        async with asyncio.timeout(0.5):
            await slow()
    except TimeoutError:
        print("timed out after 0.5s, as expected")


# ---------------------------------------------------------------- producer/consumer with asyncio.Queue
async def demo_producer_consumer():
    section("producer/consumer via asyncio.Queue — the shape used by Kafka consumers feeding workers")
    queue = asyncio.Queue(maxsize=3)  # bounded -> gives natural backpressure

    async def producer():
        for i in range(6):
            await queue.put(i)
            print(f"  produced {i}")
        await queue.put(None)  # sentinel to signal "no more work"

    async def consumer():
        while (item := await queue.get()) is not None:
            await asyncio.sleep(0.05)  # simulate work
            print(f"    consumed {item}")
            queue.task_done()

    await asyncio.gather(producer(), consumer())


async def main():
    await demo_gather()
    await demo_semaphore()
    await demo_blocking_mistake()
    await demo_timeout()
    await demo_producer_consumer()


if __name__ == "__main__":
    asyncio.run(main())

# EXPERIMENT: in demo_semaphore, change Semaphore(5) to Semaphore(1) and watch max_seen drop to 1
# -- you've turned concurrent calls into fully serialized ones.
