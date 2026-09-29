"""
Problem: group words that are anagrams of each other.
Input:  ["eat","tea","tan","ate","nat","bat"]
Output: [["eat","tea","ate"], ["tan","nat"], ["bat"]]  (order of groups/within groups may vary)

Key insight: two words are anagrams iff sorting their characters gives the same string/sequence.
Use that as a hash map key.

Run me directly for a demo: python 01_anagram_grouping.py
Run the tests: pytest 01_anagram_grouping.py -v
"""
from collections import defaultdict
from itertools import groupby


# ---------------------------------------------------------------- approach 1: sort-based key
def group_anagrams_sorted_key(words: list[str]) -> list[list[str]]:
    """O(n * k log k) time (k = avg word length), O(n * k) space."""
    groups: dict[tuple, list[str]] = defaultdict(list)
    for word in words:
        key = tuple(sorted(word))  # "eat" -> ('a', 'e', 't')
        groups[key].append(word)
    return list(groups.values())


# ---------------------------------------------------------------- approach 2: character-frequency key
def group_anagrams_freq_key(words: list[str]) -> list[list[str]]:
    """O(n * k) time -- avoids the sort entirely, faster for long words. O(n * k) space."""
    groups: dict[tuple, list[str]] = defaultdict(list)
    for word in words:
        freq = [0] * 26
        for ch in word:
            freq[ord(ch) - ord("a")] += 1
        groups[tuple(freq)].append(word)
    return list(groups.values())


# ---------------------------------------------------------------- approach 3: functional one-liner
def group_anagrams_functional(words: list[str]) -> list[list[str]]:
    """Same O(n log n) idea as approach 1, expressed with itertools.groupby (needs pre-sorting
    the whole list by key first, since groupby only groups CONSECUTIVE equal keys)."""
    key_fn = lambda w: sorted(w)  # noqa: E731 -- fine for a short, self-contained demo
    return [list(group) for _, group in groupby(sorted(words, key=key_fn), key=key_fn)]


if __name__ == "__main__":
    words = ["eat", "tea", "tan", "ate", "nat", "bat"]
    print("sort-based key :", group_anagrams_sorted_key(words))
    print("freq-based key :", group_anagrams_freq_key(words))
    print("functional     :", group_anagrams_functional(words))
    print(
        "\nComplexity trade-off to state out loud: approach 1 is O(n * k log k); approach 2 is "
        "O(n * k) -- faster for very long words since it skips the sort, at the cost of a fixed "
        "26-length list allocation per word (only correct for lowercase a-z input as written)."
    )


# ---------------------------------------------------------------- tests
def _normalize(groups):
    """Order-independent comparison: a set of frozensets."""
    return {frozenset(g) for g in groups}


def test_sorted_key():
    result = group_anagrams_sorted_key(["eat", "tea", "tan", "ate", "nat", "bat"])
    assert _normalize(result) == {frozenset(["eat", "tea", "ate"]), frozenset(["tan", "nat"]), frozenset(["bat"])}


def test_freq_key():
    result = group_anagrams_freq_key(["eat", "tea", "tan", "ate", "nat", "bat"])
    assert _normalize(result) == {frozenset(["eat", "tea", "ate"]), frozenset(["tan", "nat"]), frozenset(["bat"])}


def test_functional():
    result = group_anagrams_functional(["eat", "tea", "tan", "ate", "nat", "bat"])
    assert _normalize(result) == {frozenset(["eat", "tea", "ate"]), frozenset(["tan", "nat"]), frozenset(["bat"])}


def test_empty_input():
    assert group_anagrams_sorted_key([]) == []


def test_single_word():
    assert group_anagrams_sorted_key(["x"]) == [["x"]]
