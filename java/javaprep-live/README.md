# Java Prep Live

A local web app for the **Java interview-prep lab** in [`../java-interview-prep`](../java-interview-prep).
It is the Java counterpart of `pyprep-live`: run every example from the browser with live output,
read the long-form deep dives, and drill the question bank.

It is **one Java file plus one HTML file**. The only requirement is a JDK (21 or newer). No Maven,
no Gradle, no npm, no pip.

## Run it

```bash
cd javaprep-live
start.cmd            # Windows: opens http://127.0.0.1:8090
./start.sh           # Git Bash / Linux / macOS
java JavaPrepLive.java --port 9000     # any port
```

Stop with `Ctrl+C`.

## What you get

| Tab | What it does |
|---|---|
| **Labs** | 40+ runnable examples grouped by chapter. **Run** executes `java <file>` and streams the output; section chips jump to a numbered section of the output; **Show source** reveals the code; **Read the deep dive** opens the chapter document. |
| **Study** | The `deep_dive/` chapter documents (full question + answer treatment), the requirement coverage map, README and the Q&A guide, rendered offline. |
| **Q&A drill** | ~550 questions (`topics/*.md` plus `Java_SpringBoot_Kafka_Interview_QA_Guide.md`). Search, filter by level, hide answers for self-test, **Mock: random 10**, and "I can answer this" tracking saved in your browser. |

## Headless verification

```bash
start.cmd --check          # or: java JavaPrepLive.java --check
```

Runs every example with output discarded (so encoding/stack-trace failures show up) and exits non-zero
if any fail. Same idea as `java-interview-prep/verify_examples.sh`.

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `PORT` | `8090` | HTTP port (or `--port N`) |
| `JAVAPREP_ROOT` | `../java-interview-prep` | Folder that contains `examples/`, `deep_dive/`, `topics/` |
| `JAVAPREP_TIMEOUT` | `60` | Seconds before a run is killed |

## How it works

```text
browser (static/index.html)  <->  JavaPrepLive.java (com.sun.net.httpserver, 127.0.0.1 only)
                                      |-- /api/catalog  scans examples/NN_chapter/*.java
                                      |-- /api/run + /api/poll  ProcessBuilder: java <file>, output polled by offset
                                      |-- /api/doc, /api/qa     whitelisted markdown + parsed Q&A
```

* The catalog is built by scanning `examples/NN_name/NN_file.java`; the example title comes from the
  header comment (`* NN - Title`), the outline from `section("...")` calls, and the deep-dive link from
  `deep_dive/<same folder name>.md`.
* Safety: the server binds to loopback, only executes `*.java` files under `examples/`, only serves
  whitelisted Markdown, never builds a shell command from request data, caps output at 5,000 lines
  and kills a run after the timeout. At most 4 runs execute at once.
* Examples are run as separate JVM processes with the example's chapter folder as the working directory,
  stdin closed.

## Adding content

1. Add `examples/NN_chapter/NN_file.java` (a single-file program; header comment style as in the others).
2. Add or extend `deep_dive/NN_chapter.md`.
3. `start.cmd --check` to confirm it exits 0.

Nothing in the app needs editing: the catalog is discovered.
