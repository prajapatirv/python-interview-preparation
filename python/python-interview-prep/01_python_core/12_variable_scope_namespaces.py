"""
Variable scope, declaration and namespaces: the LEGB rule, `global`, `nonlocal`, the class-body
scope hole, late binding in closures, and why Python has no `var`/`let` declaration at all.

The one-sentence model: **assignment creates a LOCAL name for the whole function, decided at
compile time -- not at the moment the line runs.** Almost every scope surprise in Python follows
from that single rule.

Run me: python 12_variable_scope_namespaces.py
"""
import builtins
import sys
from functools import partial


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ---------------------------------------------------------------- LEGB: the lookup order
section("LEGB -- Local, Enclosing, Global, Built-in: the order a name is searched in")

name = "global-level"  # G: module-level ("global" in Python means module-level, not program-wide)


def outer():
    name = "enclosing-level"  # E: local to outer(), enclosing for inner()

    def inner():
        name = "local-level"  # L: local to inner()
        print(f"  L wins inside inner(): {name}")

    def inner_without_local():
        print(f"  no local of its own, so E wins: {name}")

    inner()
    inner_without_local()


outer()
print(f"  at module level, G wins: {name}")
print(f"  B (built-ins) is the last stop: len resolves to {builtins.len}")


# ---------------------------------------------------------------- there is no "declaration"
section("Python has no `int x` / `var x` -- the FIRST ASSIGNMENT creates the name")

# In Java you declare a type and then assign:   int count = 0;
# In Python the assignment *is* the declaration, and the name's scope is decided by WHERE
# that assignment appears -- not by any keyword.
count = 0          # a module-level name
count_str: str     # <- an ANNOTATION ONLY. It creates no name and no value.

# Annotations live in a separate mapping, not in the namespace. On 3.14+ they are computed lazily
# (PEP 649), so read them as an *attribute* of the module object rather than as a bare name --
# a bare `__annotations__` raises NameError there until something has forced evaluation.
module_annotations = getattr(sys.modules[__name__], "__annotations__", {})
print(f"  'count_str' is annotated: {'count_str' in module_annotations}")
print(f"  ...but no such name exists yet: {'count_str' in dir()}")


# ---------------------------------------------------------------- reading before assigning
section("UnboundLocalError: the single most common scope bug")

counter = 10


def broken_increment():
    # Because `counter = ...` appears ANYWHERE in this function, the compiler marks `counter`
    # local for the WHOLE function -- including the line *before* the assignment.
    try:
        print(f"  reading counter: {counter}")
        counter = counter + 1
    except UnboundLocalError as e:
        print(f"  UnboundLocalError: {e}")


broken_increment()


def fixed_by_global():
    global counter  # "I mean the module-level one; rebind THAT"
    counter = counter + 1
    return counter


print(f"  with `global counter`: {fixed_by_global()} (module-level counter is now {counter})")


def fixed_without_global(current):
    """The better fix in production code: take it in, return it out. No shared mutable state,
    so the function is trivially testable and thread-safe."""
    return current + 1


print(f"  pure-function version: {fixed_without_global(counter)} "
      f"(module-level counter untouched: {counter})")


# ---------------------------------------------------------------- mutation vs rebinding
section("MUTATING a global object needs no `global`; REBINDING the name does")

config = {"retries": 3}
items = []


def mutate_only():
    config["retries"] = 5   # mutating the object the name points at -- no assignment to `config`
    items.append("added")   # same thing: a method call, not a rebind
    # config = {}           # <- THIS would need `global config`, because it rebinds the name


mutate_only()
print(f"  mutated without `global`: {config} {items}")
print("  rule: `global`/`nonlocal` are about REBINDING A NAME, never about changing an object.")


# ---------------------------------------------------------------- nonlocal: the closure counter
section("nonlocal -- rebind a name in the ENCLOSING function (not the module)")


def make_counter():
    total = 0

    def increment(by=1):
        nonlocal total   # without this: UnboundLocalError on `total += by`
        total += by
        return total

    def read():
        return total     # reading needs no declaration

    return increment, read


inc, read = make_counter()
inc()
inc(5)
print(f"  closure state after inc(), inc(5): {read()}")
print("  every call to make_counter() gets its OWN `total` -- a cheap object with one method.")
inc2, read2 = make_counter()
inc2()
print(f"  a second, independent counter: {read2()} (the first is still {read()})")

# A closure's captured variables are inspectable, which is useful when debugging:
print(f"  inc.__code__.co_freevars = {inc.__code__.co_freevars}")
print(f"  current cell value       = {inc.__closure__[0].cell_contents}")


# ---------------------------------------------------------------- global vs nonlocal
section("global vs nonlocal: different targets, same purpose")

level = "module"


def demo_scopes():
    level = "enclosing"

    def use_nonlocal():
        nonlocal level
        level = "rebound-by-nonlocal"

    def use_global():
        global level
        level = "rebound-by-global"

    use_nonlocal()
    print(f"  after nonlocal: the enclosing `level` = {level!r}")
    use_global()
    print(f"  after global:   the enclosing `level` is STILL {level!r} -- global was what changed")


demo_scopes()
print(f"  module-level `level` = {level!r}")
print("  `nonlocal` needs an existing enclosing binding; `global` will CREATE a module-level name.")


# ---------------------------------------------------------------- the class-body scope hole
section("a class body is NOT an enclosing scope for its methods or its comprehensions")

MULTIPLIER = 3


class Config:
    base = 10
    doubled = base * 2            # fine: plain class-body code CAN see earlier class-body names

    # tripled = [base * MULTIPLIER for _ in range(3)]
    # ^ would raise NameError. The comprehension gets its own function scope, and a class body is
    #   SKIPPED when an inner scope looks outward. It can see MULTIPLIER (a global), never `base`.
    tripled = [b * MULTIPLIER for b in (base,) * 3]   # workaround: feed it in via the iterable

    def read_base(self):
        # return base        # <- NameError: methods don't see the class body as an enclosing scope
        return self.base     # correct: go through the instance (or Config.base)


print(f"  Config.doubled = {Config.doubled}, Config.tripled = {Config.tripled}")
print(f"  Config().read_base() = {Config().read_base()}")
print("  a class body runs once, in its own namespace, which then becomes the class __dict__.")


# ---------------------------------------------------------------- late binding in loops
section("late binding: a closure captures the VARIABLE, not its value at creation time")

late = [lambda: i for i in range(3)]
print(f"  all three see the final i:   {[f() for f in late]}")

early = [lambda i=i: i for i in range(3)]              # a default arg is evaluated at `def` time
print(f"  bound via default argument:  {[f() for f in early]}")

via_partial = [partial(lambda x: x, i) for i in range(3)]
print(f"  bound via functools.partial: {[f() for f in via_partial]}")


# ---------------------------------------------------------------- comprehension scope
section("comprehensions have their own scope -- except the walrus operator, deliberately")

x = "untouched"
squares = [x * 2 for x in range(3)]     # this inner x never escapes
print(f"  after the comprehension, x is still {x!r}; squares={squares}")

if any((found := n) > 1 for n in [0, 1, 2]):
    print(f"  the walrus `:=` DOES bind in the enclosing scope, on purpose: found={found}")


# ---------------------------------------------------------------- shadowing built-ins
section("shadowing a built-in is legal and silent -- and it breaks the rest of the function")


def shadow_trap(rows):
    list = []                      # shadows the built-in `list` for this whole function
    for r in rows:
        list.append(r)
    try:
        return list(set(rows))     # now calling a list OBJECT, not the type
    except TypeError as e:
        print(f"  TypeError: {e}")
        return list


print(f"  returned: {shadow_trap(['a', 'b'])}")
print("  never shadow: list, dict, set, str, type, id, input, filter, map, sum, next, vars, bytes.")


# ---------------------------------------------------------------- inspecting namespaces
section("inspecting the namespaces: globals(), locals(), vars()")


def inspect_me(arg):
    local_only = arg * 2
    print(f"  locals() inside the function: {sorted(locals())}")
    print(f"  'name' in globals(): {'name' in globals()}  (module-level names live there)")
    return local_only


inspect_me(2)
print(f"  module globals() has {len(globals())} entries; it IS the module's __dict__.")
print("  locals() in a function is a snapshot -- writing to it does NOT create a local (CPython).")


# EXPERIMENT 1: delete the `nonlocal total` line in make_counter() and run again. Predict the exact
# error and which line raises it before you do.
# EXPERIMENT 2: uncomment `tripled = [base * MULTIPLIER for _ in range(3)]` inside Config and read
# the NameError carefully -- it names `base`, not MULTIPLIER. Explain why in one sentence.
# EXPERIMENT 3: in broken_increment(), delete the `counter = counter + 1` line but keep the print.
# The read now succeeds -- proving the error came from the ASSIGNMENT at compile time, not the read.

# EXERCISE: write `make_rate_limiter(max_calls)` returning a function that allows at most
# max_calls calls and returns False forever after. Hold the call count in a closure with
# `nonlocal` -- no globals, no class, no attributes on the function. Then rewrite it as a class
# with `__call__`, and say which you'd ship and why. (Compare with the class-based decorator in
# 03_decorators.py, which solves the same "this needs state" problem the other way.)
