"""
Problem: search for a keyword in a nested dictionary. If the keyword matches a VALUE, return the
corresponding KEY.

Sounds trivial until you ask the four clarifying questions an interviewer is waiting for -- asking
them is most of the score:

  1. How deep? Dicts nested in dicts, and dicts nested in LISTS of dicts? (Almost always yes.)
  2. First match or ALL matches? (A real payload has duplicates.)
  3. Exact equality or substring / case-insensitive? ("search" hints at substring.)
  4. Just the key, or the PATH to it? ("status" appearing in 4 places is useless without a path.)

So this file builds up five versions:
  A. find_key_by_value      -- recursive, exact match, returns the first key.         O(n)
  B. find_all_keys_by_value -- recursive generator, every match, with the full path.  O(n)
  C. search_values          -- substring + case-insensitive, the "search a keyword" reading.
  D. find_iterative         -- explicit stack, no recursion: no RecursionError on deep data.
  E. find_by_key            -- the mirror question ("find every value for key X"), often asked
                               as the immediate follow-up.

Run me:          python 06_nested_dict_search.py
Run the tests:   pytest 06_nested_dict_search.py -v
"""
from collections import deque

# A realistic payload: dicts in dicts, dicts in lists, repeated values, mixed types.
SAMPLE = {
    "order_id": "ORD-1001",
    "status": "SHIPPED",
    "customer": {
        "id": 42,
        "name": "Ravi Bhalsod",
        "contact": {"email": "ravi@example.com", "phone": None},
        "address": {"city": "Pune", "country": "India", "postcode": "411001"},
    },
    "items": [
        {"sku": "WIDGET-1", "qty": 2, "status": "SHIPPED"},
        {"sku": "GIZMO-9", "qty": 1, "status": "BACKORDER",
         "supplier": {"name": "Acme", "city": "Pune"}},
    ],
    "payment": {"method": "CARD", "last4": "4242", "captured": True},
    "tags": ["priority", "gift"],
}


# ---------------------------------------------------------------- A. first key, exact match
def find_key_by_value(data, target):
    """Return the key whose value == target, searching nested dicts and lists. None if absent.

    Depth-first, returns on the first hit. O(n) in the number of nodes; recursion depth = nesting
    depth. The `is not None` check -- rather than a truthy check -- is what lets a legitimately
    falsy key (0, "", False) be returned correctly.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            if value == target:
                return key
            found = find_key_by_value(value, target)
            if found is not None:
                return found
    elif isinstance(data, (list, tuple)):
        for item in data:
            found = find_key_by_value(item, target)
            if found is not None:
                return found
    return None


# ---------------------------------------------------------------- B. every key, with its path
def find_all_keys_by_value(data, target, _path=()):
    """Yield (key, path) for EVERY value == target. `path` is the dotted route to that key, which
    is what makes the answer actionable when the same value appears in several places.

    A generator, so a caller that only wants the first match pays only for the first match:
        next(find_all_keys_by_value(doc, "SHIPPED"), None)
    """
    if isinstance(data, dict):
        for key, value in data.items():
            here = _path + (key,)
            if value == target:
                yield key, ".".join(str(p) for p in here)
            yield from find_all_keys_by_value(value, target, here)
    elif isinstance(data, (list, tuple)):
        for index, item in enumerate(data):
            yield from find_all_keys_by_value(item, target, _path + (f"[{index}]",))


# ---------------------------------------------------------------- C. the "keyword" reading
def search_values(data, keyword, exact=False, case_sensitive=False, _path=()):
    """Yield (key, value, path) wherever the keyword matches a value.

    This is the version that answers the question as literally asked -- "search for a keyword" --
    because a human searching for "pune" expects to find "Pune", and someone searching "example"
    expects to find "ravi@example.com". Non-string values are compared after str().
    """
    def matches(value):
        if value is None:
            return False
        if exact:
            return value == keyword
        text = str(value) if case_sensitive else str(value).casefold()
        needle = keyword if case_sensitive else str(keyword).casefold()
        return needle in text

    if isinstance(data, dict):
        for key, value in data.items():
            here = _path + (key,)
            if not isinstance(value, (dict, list, tuple)) and matches(value):
                yield key, value, ".".join(str(p) for p in here)
            yield from search_values(value, keyword, exact, case_sensitive, here)
    elif isinstance(data, (list, tuple)):
        for index, item in enumerate(data):
            here = _path + (f"[{index}]",)
            if not isinstance(item, (dict, list, tuple)) and matches(item):
                yield None, item, ".".join(str(p) for p in here)   # a bare list element has no key
            else:
                yield from search_values(item, keyword, exact, case_sensitive, here)


# ---------------------------------------------------------------- D. iterative, no recursion
def find_iterative(data, target, breadth_first=False):
    """Same as A, with an explicit stack instead of the call stack.

    Why it matters: Python's recursion limit is ~1000 frames, so deeply nested or
    adversarial/untrusted JSON can raise RecursionError in a recursive version. An explicit
    stack is bounded only by heap. Flip to breadth_first=True to find the SHALLOWEST match
    first -- which is usually the one a human means.
    """
    pending = deque([(data, ())])
    while pending:
        node, path = pending.popleft() if breadth_first else pending.pop()
        if isinstance(node, dict):
            for key, value in node.items():
                if value == target:
                    return key, ".".join(str(p) for p in path + (key,))
                pending.append((value, path + (key,)))
        elif isinstance(node, (list, tuple)):
            for index, item in enumerate(node):
                pending.append((item, path + (f"[{index}]",)))
    return None, None


# ---------------------------------------------------------------- E. the mirror question
def find_by_key(data, target_key, _path=()):
    """The follow-up they almost always ask: yield (value, path) for every occurrence of a KEY.
    Same traversal, opposite test -- say that out loud rather than rewriting the walk from zero."""
    if isinstance(data, dict):
        for key, value in data.items():
            here = _path + (key,)
            if key == target_key:
                yield value, ".".join(str(p) for p in here)
            yield from find_by_key(value, target_key, here)
    elif isinstance(data, (list, tuple)):
        for index, item in enumerate(data):
            yield from find_by_key(item, target_key, _path + (f"[{index}]",))


# ---------------------------------------------------------------- bonus: flatten once, query often
def flatten(data, _path=()):
    """Flatten to {dotted.path: leaf_value}. Worth it when you'll run MANY searches over the same
    document: flattening is O(n) once, then every lookup is a dict scan over leaves only --
    and you can build a value -> [paths] index from it. For a single search, A is cheaper."""
    flat = {}
    if isinstance(data, dict):
        for key, value in data.items():
            flat.update(flatten(value, _path + (str(key),)))
    elif isinstance(data, (list, tuple)):
        for index, item in enumerate(data):
            flat.update(flatten(item, _path + (f"[{index}]",)))
    else:
        flat[".".join(_path)] = data
    return flat


def build_value_index(data):
    """value -> [paths]. The right answer to "we need to do this 10,000 times a second"."""
    index = {}
    for path, value in flatten(data).items():
        try:
            index.setdefault(value, []).append(path)
        except TypeError:                     # an unhashable leaf (rare) -- skip it
            pass
    return index


if __name__ == "__main__":
    def section(title):
        print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")

    section("A. find_key_by_value -- the first key whose value matches, exactly")
    for target in ("Pune", "SHIPPED", "4242", 42, True, "not-in-the-document"):
        print(f"  {str(target):22s} -> {find_key_by_value(SAMPLE, target)!r}")
    print("  careful with True: it found 'qty' (whose value is 1), NOT 'captured' -- because in")
    print("  Python 1 == True. If that matters, also compare type(value) is type(target).")

    section("B. find_all_keys_by_value -- every match, each with its path")
    for key, path in find_all_keys_by_value(SAMPLE, "Pune"):
        print(f"  key={key!r:10s} at {path}")
    print("  'Pune' appears twice: only the path tells you WHICH one you found.")
    first = next(find_all_keys_by_value(SAMPLE, "SHIPPED"), None)
    print(f"  a generator means 'just the first' is cheap: next(...) -> {first}")

    section("C. search_values -- substring, case-insensitive (the 'keyword' reading)")
    for key, value, path in search_values(SAMPLE, "pune"):
        print(f"  key={key!r:10s} value={value!r:12s} at {path}")
    print("  ...and a partial keyword:")
    for key, value, path in search_values(SAMPLE, "example"):
        print(f"  key={key!r:10s} value={value!r:22s} at {path}")
    print("  ...and matching a bare list element (no key to return, so the path IS the answer):")
    for key, value, path in search_values(SAMPLE, "gift"):
        print(f"  key={key!r:10s} value={value!r:12s} at {path}")

    section("D. find_iterative -- no recursion limit; DFS vs BFS pick different matches")
    print(f"  depth-first  : {find_iterative(SAMPLE, 'Pune')}")
    print(f"  breadth-first: {find_iterative(SAMPLE, 'Pune', breadth_first=True)}")
    deep = current = {}
    for i in range(2000):                     # 2000 levels: far past the recursion limit
        current["child"] = {}
        current = current["child"]
    current["needle"] = "found-me"
    print(f"  2000 levels deep, iterative: {find_iterative(deep, 'found-me')[0]!r}")
    try:
        find_key_by_value(deep, "found-me")
    except RecursionError as e:
        print(f"  ...and the recursive version: RecursionError ({e})")

    section("E. find_by_key -- the mirror question: every value for a key")
    for value, path in find_by_key(SAMPLE, "status"):
        print(f"  {path:28s} = {value!r}")
    for value, path in find_by_key(SAMPLE, "name"):
        print(f"  {path:28s} = {value!r}")

    section("bonus: flatten once, then query in O(1)")
    flat = flatten(SAMPLE)
    print(f"  {len(flat)} leaves, e.g. customer.address.city = {flat['customer.address.city']!r}")
    index = build_value_index(SAMPLE)
    print(f"  index['Pune']    = {index['Pune']}")
    print(f"  index['SHIPPED'] = {index['SHIPPED']}")
    print("  O(n) to build, O(1) per lookup after -- the answer to 'now do it a million times'.")

    section("complexity and what to say")
    print("""  Every traversal here is O(n) in the number of nodes, with O(depth) extra space
  (the call stack, or the explicit stack). You cannot beat O(n) for a single search:
  the value could be in the last leaf, so you must be prepared to visit every node.

  The upgrades, in the order an interviewer asks for them:
    "all matches"      -> a generator yielding (key, path)
    "which one?"       -> carry the path down the recursion
    "it's huge/deep"   -> switch to an explicit stack (no RecursionError)
    "do it constantly" -> flatten once into a value -> [paths] index, then O(1) lookups
    "it's 100GB JSON"  -> you cannot hold it in memory at all: stream it with ijson and match
                          as events arrive (see 09_aws_lambda_streaming/03_large_file_processing.py)""")


# ---------------------------------------------------------------- tests
# (no `import pytest` on purpose -- keeps this file runnable standalone; pytest still discovers
# plain `test_*` functions.)

def test_finds_a_top_level_value():
    assert find_key_by_value({"a": 1, "b": 2}, 2) == "b"


def test_finds_a_deeply_nested_value():
    assert find_key_by_value(SAMPLE, "411001") == "postcode"
    assert find_key_by_value(SAMPLE, "ravi@example.com") == "email"


def test_finds_a_value_inside_a_list_of_dicts():
    assert find_key_by_value(SAMPLE, "GIZMO-9") == "sku"
    assert find_key_by_value(SAMPLE, "Acme") == "name"


def test_returns_none_when_absent():
    assert find_key_by_value(SAMPLE, "no-such-value") is None
    assert find_key_by_value({}, "x") is None


def test_handles_falsy_keys_and_values():
    # a falsy KEY must still be returned -- this is what breaks a truthy-check implementation
    assert find_key_by_value({0: "zero"}, "zero") == 0
    assert find_key_by_value({"": "empty-key"}, "empty-key") == ""
    # a falsy VALUE must still be findable
    assert find_key_by_value({"outer": {"flag": False}}, False) == "flag"
    assert find_key_by_value({"outer": {"count": 0}}, 0) == "count"


def test_ignores_none_values_unless_asked_for_them():
    assert find_key_by_value(SAMPLE, None) == "phone"   # None IS a findable value


def test_finds_all_matches_with_paths():
    matches = list(find_all_keys_by_value(SAMPLE, "Pune"))
    assert len(matches) == 2
    assert [k for k, _ in matches] == ["city", "city"]
    assert {p for _, p in matches} == {
        "customer.address.city",
        "items.[1].supplier.city",
    }


def test_find_all_yields_nothing_when_absent():
    assert list(find_all_keys_by_value(SAMPLE, "nope")) == []


def test_find_all_is_lazy():
    gen = find_all_keys_by_value(SAMPLE, "SHIPPED")
    first = next(gen)
    assert first == ("status", "status")      # the shallow one comes first, no full walk needed


def test_search_is_case_insensitive_substring_by_default():
    hits = list(search_values(SAMPLE, "pune"))
    assert len(hits) == 2
    assert all(v == "Pune" for _, v, _ in hits)

    partial = list(search_values(SAMPLE, "example"))
    assert [(k, v) for k, v, _ in partial] == [("email", "ravi@example.com")]


def test_search_exact_mode_requires_a_full_match():
    assert list(search_values(SAMPLE, "pune", exact=True)) == []
    assert len(list(search_values(SAMPLE, "Pune", exact=True))) == 2


def test_search_case_sensitive_mode():
    assert list(search_values(SAMPLE, "pune", case_sensitive=True)) == []
    assert len(list(search_values(SAMPLE, "Pune", case_sensitive=True))) == 2


def test_search_matches_a_bare_list_element_and_reports_no_key():
    hits = list(search_values(SAMPLE, "gift"))
    assert hits == [(None, "gift", "tags.[1]")]


def test_search_matches_non_string_values_via_str():
    hits = [(k, v) for k, v, _ in search_values(SAMPLE, "42", exact=False)]
    assert ("id", 42) in hits                # the int 42
    assert ("last4", "4242") in hits         # and the string "4242"


def test_iterative_matches_the_recursive_result():
    for target in ("411001", "GIZMO-9", "CARD", "Acme"):
        key, path = find_iterative(SAMPLE, target)
        assert key == find_key_by_value(SAMPLE, target)
        assert path is not None


def test_iterative_survives_depth_that_breaks_recursion():
    deep = current = {}
    for _ in range(3000):
        current["child"] = {}
        current = current["child"]
    current["needle"] = "found-me"

    key, path = find_iterative(deep, "found-me")
    assert key == "needle"
    assert path.endswith("child.needle")

    try:
        find_key_by_value(deep, "found-me")
        raise AssertionError("expected RecursionError from the recursive version")
    except RecursionError:
        pass


def test_breadth_first_finds_the_shallowest_match():
    doc = {"deep": {"a": {"b": {"c": "target"}}}, "shallow": "target"}
    assert find_iterative(doc, "target", breadth_first=True)[1] == "shallow"


def test_find_by_key_yields_every_occurrence():
    statuses = [v for v, _ in find_by_key(SAMPLE, "status")]
    assert statuses == ["SHIPPED", "SHIPPED", "BACKORDER"]
    assert [p for _, p in find_by_key(SAMPLE, "last4")] == ["payment.last4"]


def test_flatten_produces_leaf_paths_only():
    flat = flatten(SAMPLE)
    assert flat["customer.contact.email"] == "ravi@example.com"
    assert flat["items.[0].sku"] == "WIDGET-1"
    assert flat["tags.[0]"] == "priority"
    assert not any(isinstance(v, (dict, list)) for v in flat.values())


def test_value_index_gives_every_path_for_a_value():
    index = build_value_index(SAMPLE)
    assert sorted(index["Pune"]) == ["customer.address.city", "items.[1].supplier.city"]
    assert index["BACKORDER"] == ["items.[1].status"]


def test_tuples_are_traversed_like_lists():
    doc = {"pair": ({"k": "v"}, {"k2": "needle"})}
    assert find_key_by_value(doc, "needle") == "k2"
