"""Draft one full coding-round answer per classic problem, VERIFIED by compiling and running the Java.

    .venv/Scripts/python.exe scripts/draft_coding.py --dry-run
    .venv/Scripts/python.exe scripts/draft_coding.py --workers 4

Each answer follows the bank format (concepts, scenario, approach, complexity, runnable code, test cases,
follow-ups, 60-second answer). The model must put a self-checking single-file program (``main`` with assertions)
in the first ```java fence; the script runs it with the JDK source launcher and only keeps answers whose program
exits 0. Failures are retried once with the compiler/test output fed back.
"""
import argparse
import asyncio
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config  # noqa: E402
from app.services import ai, bank, library  # noqa: E402

PROBLEMS = [
    # (level, title, hint)
    ("fresher", "Reverse a string without using library shortcuts", "two pointers or StringBuilder; mention immutability and null/empty"),
    ("fresher", "Check whether a string is a palindrome", "two pointers; ignore case and non-alphanumerics variant"),
    ("fresher", "Check whether two strings are anagrams", "frequency array vs sorting; complexity trade-off"),
    ("fresher", "Count the frequency of each character in a string", "HashMap/array; LinkedHashMap for order; streams variant"),
    ("mid", "Find the first non-repeating character in a string", "LinkedHashMap or two-pass frequency count"),
    ("mid", "Longest substring without repeating characters", "sliding window with last-seen index map"),
    ("mid", "Valid parentheses", "stack; brackets (), [], {}"),
    ("fresher", "Two sum: find two indices whose values add up to a target", "HashMap complement; vs O(n^2) brute force"),
    ("fresher", "Find the missing number in an array of 1 to n", "sum formula or XOR; overflow note"),
    ("mid", "Maximum subarray sum (Kadane's algorithm)", "single pass; all-negative case"),
    ("fresher", "Move all zeroes to the end of an array, keeping order", "two pointers in place"),
    ("fresher", "Merge two sorted arrays into one sorted array", "two pointers; in-place variant mention"),
    ("fresher", "Binary search on a sorted array", "iterative; mid overflow; first/last occurrence follow-up"),
    ("mid", "Rotate an array by k positions", "reverse three times; k modulo n"),
    ("fresher", "Remove duplicates from a sorted array in place", "two pointers; return new length"),
    ("fresher", "Find the second highest number in an array without sorting", "single pass with two variables; duplicates"),
    ("mid", "Find duplicate elements in an array", "HashSet; sorting; Floyd for 1..n variant mention"),
    ("mid", "Java 8 streams: group employees by department and find the highest paid in each", "Collectors.groupingBy with maxBy"),
    ("mid", "Java 8 streams: find the second highest salary", "sorted/distinct/skip or Optional; empty case"),
    ("mid", "Java 8 streams: why does Collectors.toMap throw on duplicate keys and how do you handle it", "merge function; LinkedHashMap supplier"),
    ("mid", "Java 8 streams: word frequency count and top 3 words", "groupingBy counting; sorting by value"),
    ("mid", "Reverse a linked list iteratively and recursively", "own Node class; prev/curr/next"),
    ("mid", "Detect a cycle in a linked list and find its start", "Floyd tortoise and hare"),
    ("mid", "Find the middle element of a linked list in one pass", "slow and fast pointers; even length"),
    ("senior", "Validate a binary search tree", "min/max bounds recursion; why checking only children fails"),
    ("senior", "Level-order (breadth-first) traversal of a binary tree", "queue; level grouping"),
    ("senior", "Implement an LRU cache", "LinkedHashMap access order or HashMap + doubly linked list; O(1)"),
    ("senior", "Implement a thread-safe singleton", "enum or holder idiom; double-checked locking with volatile"),
    ("senior", "Implement producer-consumer with BlockingQueue", "bounded queue; poison pill; deterministic test"),
    ("senior", "Implement a simple rate limiter (token bucket)", "injectable clock for a deterministic test; refill math"),
    ("senior", "Implement retry with exponential backoff", "injectable sleeper; max attempts; only retry transient errors"),
]

FORMAT = """Write the answer in EXACTLY this Markdown structure and nothing else (no preamble):

tags: <4-7 lowercase comma-separated tags>, coding, basics

**Start here: the concepts**
<bullets in plain words: define the data structure or technique used (for example hash map, two pointers, sliding
window, stack) and what Big-O means here; no jargon without a definition>

**The live scenario**
<one short realistic situation where this problem or technique appears in real backend work, and how the
interviewer usually phrases the question>

**What the interviewer is really checking**
<one or two sentences: clarifying questions, brute force first, then improvement, complexity, edge cases>

**How I answer it**
1. Clarify and restate (input, output, constraints, edge cases to ask about).
2. The brute-force idea and its complexity.
3. The better idea, with the reason it works, in simple language.
4. Complexity of the final solution (time and space).
5. The code: ONE complete runnable single-file Java program in a ```java fence, as below.

Code rules: JDK 21, no external libraries, ASCII only, a single non-public top-level class named Solution plus
small helper classes if needed, a `public static void main(String[] args)` that runs at least 5 checks including
edge cases and THROWS AssertionError (use `if (!(cond)) throw new AssertionError(...)`) when a check fails, prints
"OK" at the end, and exits normally. Keep it under 90 lines. Comments only where the logic is not obvious.

**Trade-offs and what can go wrong**
<a small table or bullets: brute force vs final solution in time and space, and the common mistakes>

**Test cases I'd walk through**
<bullets: typical, empty or null, single element, duplicates, large input, and what each should return>

**Follow-ups to expect**
- *<follow-up question>* -> <short strong answer>
- *<follow-up question>* -> <short strong answer>

**60-second answer**
<how you would explain the approach aloud before typing, 4-6 sentences, including the complexity>"""


def find_java() -> str:
    """JAVA_BIN, then JAVA_HOME, then the newest ~/.jdks/* (IntelliJ-style), then plain ``java`` on PATH."""
    import os
    if os.environ.get("JAVA_BIN"):
        return os.environ["JAVA_BIN"]
    cands = [Path(os.environ["JAVA_HOME"]) / "bin" / "java.exe"] if os.environ.get("JAVA_HOME") else []
    cands += sorted((Path.home() / ".jdks").glob("*/bin/java.exe"), reverse=True)
    return next((str(c) for c in cands if c.is_file()), "java")


JAVA = find_java()


def run_java(code: str) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "Solution.java"
        p.write_text(code, encoding="utf-8")
        try:
            r = subprocess.run([JAVA, str(p)], capture_output=True, text=True, timeout=40, cwd=d)
        except subprocess.TimeoutExpired:
            return False, "timed out after 40 s"
        return r.returncode == 0, (r.stdout + r.stderr)[-1500:]


def extract_java(text: str) -> str | None:
    m = re.search(r"```java\n(.*?)```", text, re.S)
    return m.group(1) if m else None


async def draft(client, system, level, title, hint, sem):
    base = (f"Candidate level: {level}\n<problem>{title}</problem>\n<hint>{hint}</hint>\n\n"
            "Write a complete coding-round answer for this problem for a Java backend candidate.\n\n" + FORMAT)
    prompt, last = base, ""
    for attempt in range(3):
        async with sem:
            resp = await client.messages.create(
                model=config.ANTHROPIC_MODEL, max_tokens=9000,
                system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": prompt}])
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
        text = re.sub(r"^```(?:markdown)?\n|\n```$", "", text).strip()
        code = extract_java(text)
        _, _, qs = bank.parse_questions(f"### Q1 [{bank.normalise_level(level)}] {title}\n{text}\n")
        keys = {s["key"] for s in qs[0]["sections"]} if qs else set()
        missing = {"concepts", "scenario", "probe", "answer", "tradeoffs", "spoken"} - keys
        if code is None or missing:
            last = f"structure problem (missing {sorted(missing)}, code={'yes' if code else 'no'})"
        else:
            ok, out = run_java(code)
            if ok:
                return text
            last = out
        print(f"  retry {attempt + 1}: {title[:55]!r}: {last[:140]!r}", flush=True)
        prompt = (base + "\n\nYour previous attempt failed verification with this output:\n" + last +
                  "\nFix the program (and the explanation if it was wrong) and return the full answer again.")
    return None


async def run(args):
    lib = library.Library.load()
    stack = lib.stack("java")
    topic = lib.topic("java", "coding")
    system = ai.system_prompt(stack, topic)
    out = config.WORKSPACE_ROOT / "java" / "java-interview-prep" / "interview-scenarios" / "50_coding_round_problems.md"
    existing = out.read_text(encoding="utf-8") if out.exists() else ""
    done = {t.strip().lower() for t in re.findall(r"^### Q\d+ \[\w+\] (.+)$", existing, re.M)}
    todo = [p for p in PROBLEMS if p[1].lower() not in done]
    print(f"{len(todo)} problems to draft ({len(done)} already in {out.name})")
    if args.dry_run or not todo:
        return
    import anthropic
    client = anthropic.AsyncAnthropic()
    sem = asyncio.Semaphore(args.workers)
    results = await asyncio.gather(*[draft(client, system, *p, sem) for p in todo], return_exceptions=True)
    if not existing:
        existing = ("---\nid: coding-round-problems\ntitle: Coding round: classic problems with verified solutions\n"
                    "stack: java\nskill: coding\n---\nOne classic problem per question: approach (brute force, then better), "
                    "complexity, a complete runnable Java program, the test cases to walk through, and follow-ups. "
                    "Every program in this file was compiled and run before it was saved.\n\n"
                    "Levels: **fresher** (0-2 yrs) · **mid** (3-6) · **senior** (6-10) · **architect** (10+).\n")
    n = len(re.findall(r"^### Q\d+ ", existing, re.M))
    added = 0
    with out.open("w", encoding="utf-8", newline="\n") as f:
        f.write(existing.rstrip("\n") + "\n")
        for (level, title, _), r in zip(todo, results):
            if isinstance(r, Exception) or r is None:
                print(f"  FAILED: {title!r} {r if isinstance(r, Exception) else ''}", flush=True)
                continue
            n += 1
            added += 1
            f.write(f"\n### Q{n} [{bank.normalise_level(level)}] {title}\n{r}\n")
    print(f"wrote {added}/{len(todo)} to {out.name}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not args.dry_run and ai.mode() != "claude":
        print("No API key found: set ANTHROPIC_API_KEY in interview-coach/.env", file=sys.stderr)
        return 1
    asyncio.run(run(args))
    return 0


if __name__ == "__main__":
    sys.exit(main())
