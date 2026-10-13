"""
Problem: reverse a string in-place, O(1) extra space, O(n) time -- WITHOUT using slicing
(the "obvious" `s[::-1]` answer is too easy; interviewers usually ask for the two-pointer swap
to see if you can reason about mutation and indices).

The Python subtlety: strings are IMMUTABLE, so "in-place" is impossible on a str directly --
you convert to a list of characters first (mutable), swap in place, then rejoin.

Run me: python 04_reverse_string.py
Run the tests: pytest 04_reverse_string.py -v
"""


def reverse_string_two_pointer(s: str) -> str:
    """O(n) time, O(n) space for the list conversion (unavoidable since str is immutable) --
    but O(1) EXTRA space beyond that single copy, and the actual swapping is in-place on the list."""
    chars = list(s)
    left, right = 0, len(chars) - 1
    while left < right:
        chars[left], chars[right] = chars[right], chars[left]
        left += 1
        right -= 1
    return "".join(chars)


def reverse_string_recursive(s: str) -> str:
    """O(n) time, but O(n) call-stack depth -- shown for completeness; the iterative two-pointer
    version above is what you'd actually want in an interview or in production (no recursion
    limit risk on long strings)."""
    if len(s) <= 1:
        return s
    return reverse_string_recursive(s[1:]) + s[0]


def reverse_string_slice(s: str) -> str:
    """The one-liner. Fine to mention you know it exists, but most interviewers will ask you to
    implement the mechanism yourself -- that's what the two-pointer version demonstrates."""
    return s[::-1]


if __name__ == "__main__":
    word = "hello"
    print("two-pointer:", reverse_string_two_pointer(word))
    print("recursive  :", reverse_string_recursive(word))
    print("slice      :", reverse_string_slice(word))

    print("\nwhy 'in-place' needs a list first:")
    s = "abc"
    chars = list(s)
    chars[0] = "z"  # this works -- lists are mutable
    print(f"  list(s) can be mutated: {chars}")
    try:
        s[0] = "z"  # type: ignore  -- strings are immutable, this always raises
    except TypeError as e:
        print(f"  s[0] = 'z' on the original str raises: {e}")


# ---------------------------------------------------------------- tests
def test_two_pointer_basic():
    assert reverse_string_two_pointer("hello") == "olleh"


def test_two_pointer_empty():
    assert reverse_string_two_pointer("") == ""


def test_two_pointer_single_char():
    assert reverse_string_two_pointer("x") == "x"


def test_two_pointer_even_length():
    assert reverse_string_two_pointer("abcd") == "dcba"


def test_all_approaches_agree():
    for word in ["", "a", "ab", "racecar", "Hello, World!"]:
        expected = word[::-1]
        assert reverse_string_two_pointer(word) == expected
        assert reverse_string_recursive(word) == expected
        assert reverse_string_slice(word) == expected
