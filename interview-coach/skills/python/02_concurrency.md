---
id: python-concurrency
title: Concurrency: threads, asyncio, processes
order: 2
summary: The GIL, I/O vs CPU bound work, asyncio event loop, multiprocessing, free-threaded Python.
docs: python/python-interview-prep/deep_dive/07_concurrency.md
folders: 02_concurrency
examples: python/python-interview-prep/02_concurrency
keywords: gil, thread, threading, asyncio, async, await, event loop, multiprocessing, process pool, concurrent.futures, race condition, lock, coroutine, free-threaded, subinterpreter
---
Skill focus for Concurrency: threads, asyncio, processes answers:
- Decide by workload: I/O-bound -> asyncio or threads; CPU-bound -> processes (or native code); say why.
- Production stories: a blocking call inside async code freezing the event loop, a thread pool too small, pickling errors with ProcessPoolExecutor.
- Version facts: free-threaded builds (3.13 experimental, 3.14 officially supported) and subinterpreters - name the version.
