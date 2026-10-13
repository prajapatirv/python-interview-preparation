"""Runs an example in a child process and yields log events as they happen.

Why threads + queue instead of asyncio.create_subprocess_exec?
  asyncio subprocesses need the Proactor loop on Windows, which `uvicorn --reload`
  does not give you. Popen + reader threads works identically on Windows/macOS/Linux.

Event shapes (all dicts, sent to the browser as Server-Sent Events):
  {"type": "start", "cmd": "...", "cwd": "...", "python": "3.12.4"}
  {"type": "out"|"err", "t": seconds_since_start, "line": "..."}
  {"type": "end", "code": int|None, "reason": "ok"|"error"|"timeout"|"truncated", "elapsed": s}
"""
import asyncio
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import weakref
from pathlib import Path

from .. import config
from .catalog import TEMP_PREFIX, Example

_slots: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Semaphore]" = weakref.WeakKeyDictionary()


def _semaphore() -> asyncio.Semaphore:
    """One concurrency limiter per event loop (a Semaphore must not be shared across loops)."""
    loop = asyncio.get_running_loop()
    if loop not in _slots:
        _slots[loop] = asyncio.Semaphore(config.MAX_PARALLEL_RUNS)
    return _slots[loop]


def kill_tree(proc: subprocess.Popen) -> None:
    """Kill the child and everything it spawned (multiprocessing workers, uvicorn, ...)."""
    if proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:
        proc.kill()


def build_command(example: Example, code_file: Path | None = None) -> tuple[list[str], Path]:
    """Returns (argv, cwd). cwd = the topic folder so relative paths like sample_data/ work."""
    root = config.PREP_ROOT
    if example.is_suite:
        # cwd = repo root so the repo's own pytest.ini governs discovery
        return [sys.executable, "-u", "-m", "pytest", "-v", "--color=no", "-p", "no:cacheprovider",
                str(root / example.topic)], root
    target = code_file or (root / example.topic / example.file)
    return [sys.executable, "-u", str(target)], root / example.topic


def _display(argv: list[str]) -> str:
    return " ".join(Path(a).name if os.sep in a or "/" in a else a for a in argv)


async def run_example(example: Example, code: str | None = None):
    """Async generator of log events. Closing the generator (client disconnect) kills the child."""
    tmp: Path | None = None
    proc: subprocess.Popen | None = None
    async with _semaphore():
        try:
            if code is not None and not example.is_suite:
                # Edited code runs from a temp file in the topic folder so sibling imports keep working.
                fd, name = tempfile.mkstemp(suffix=".py", prefix=TEMP_PREFIX, dir=config.PREP_ROOT / example.topic)
                os.close(fd)
                tmp = Path(name)
                tmp.write_text(code, encoding="utf-8")
            argv, cwd = build_command(example, tmp)

            env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8",
                   "PYTHONDONTWRITEBYTECODE": "1"}
            kwargs = ({"start_new_session": True} if os.name != "nt"
                      else {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP})
            proc = subprocess.Popen(argv, cwd=str(cwd), env=env, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
            loop = asyncio.get_running_loop()
            q: asyncio.Queue = asyncio.Queue()
            t0 = time.perf_counter()
            total = {"bytes": 0}

            def push(item):
                try:
                    loop.call_soon_threadsafe(q.put_nowait, item)
                except RuntimeError:          # event loop already closed (server shutting down)
                    pass

            def pump(stream, kind):
                for raw in iter(stream.readline, b""):
                    total["bytes"] += len(raw)
                    line = raw.decode("utf-8", "replace").rstrip("\r\n")
                    push((kind, round(time.perf_counter() - t0, 3), line))
                push((kind, None, None))      # EOF marker

            for stream, kind in ((proc.stdout, "out"), (proc.stderr, "err")):
                threading.Thread(target=pump, args=(stream, kind), daemon=True).start()

            yield {"type": "start", "cmd": _display(argv), "cwd": str(cwd), "python": config.PYTHON_VERSION}

            reason, open_streams = None, 2
            while open_streams:
                # Checked on every iteration, so a process that prints constantly still times out.
                if time.perf_counter() - t0 > config.RUN_TIMEOUT_S:
                    reason = "timeout"
                    kill_tree(proc)
                    break
                try:
                    kind, t, line = await asyncio.wait_for(q.get(), timeout=0.25)
                except asyncio.TimeoutError:
                    continue
                if t is None:
                    open_streams -= 1
                    continue
                yield {"type": kind, "t": t, "line": line}
                if total["bytes"] > config.MAX_OUTPUT_BYTES:
                    reason = "truncated"
                    kill_tree(proc)
                    break

            code_ = await loop.run_in_executor(None, proc.wait)
            reason = reason or ("ok" if code_ == 0 else "error")
            yield {"type": "end", "code": code_, "reason": reason,
                   "elapsed": round(time.perf_counter() - t0, 2)}
        finally:
            # also runs on client disconnect (CancelledError / GeneratorExit): Stop must kill the child
            if proc is not None:
                kill_tree(proc)           # reader threads then hit EOF and exit on their own
            if tmp is not None:
                tmp.unlink(missing_ok=True)
