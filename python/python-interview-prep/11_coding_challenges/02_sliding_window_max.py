"""
Problem: return the maximum of every contiguous window of size k in an array.
Input:  nums=[1,3,-1,-3,5,3,6,7], k=3
Output: [3,3,5,5,6,7]

Naive approach: for each window, scan all k elements -> O(n*k).
Optimal: a monotonic deque of INDICES, values decreasing left to right. The front is always the
current window's max. O(n) total -- each index is pushed and popped at most once.

Run me: python 02_sliding_window_max.py
Run the tests: pytest 02_sliding_window_max.py -v
"""
from collections import deque


def max_sliding_window_naive(nums: list[int], k: int) -> list[int]:
    """O(n*k) -- fine for small k, degrades badly as k grows."""
    return [max(nums[i:i + k]) for i in range(len(nums) - k + 1)]


def max_sliding_window_deque(nums: list[int], k: int) -> list[int]:
    """O(n) -- a monotonic decreasing deque of indices."""
    dq: deque[int] = deque()  # stores indices; nums[dq[0]] is always the current window's max
    result = []
    for i, n in enumerate(nums):
        # drop indices whose values are smaller than the incoming one -- they can NEVER be the
        # max of any future window that also contains index i
        while dq and nums[dq[-1]] < n:
            dq.pop()
        dq.append(i)

        if dq[0] <= i - k:  # the front index has fallen out of the current window
            dq.popleft()

        if i >= k - 1:  # window is fully formed
            result.append(nums[dq[0]])
    return result


if __name__ == "__main__":
    nums, k = [1, 3, -1, -3, 5, 3, 6, 7], 3
    print("naive :", max_sliding_window_naive(nums, k))
    print("deque :", max_sliding_window_deque(nums, k))
    print(
        "\nWhy the deque stays monotonic decreasing: once a smaller value is behind a larger "
        "one within the current window, the smaller value can never become the max before it "
        "also falls out of the window -- so it's safe to discard immediately."
    )


# ---------------------------------------------------------------- tests
def test_naive_matches_expected():
    assert max_sliding_window_naive([1, 3, -1, -3, 5, 3, 6, 7], 3) == [3, 3, 5, 5, 6, 7]


def test_deque_matches_expected():
    assert max_sliding_window_deque([1, 3, -1, -3, 5, 3, 6, 7], 3) == [3, 3, 5, 5, 6, 7]


def test_both_approaches_agree_on_random_input():
    import random
    random.seed(42)
    for _ in range(20):
        n = random.randint(1, 15)
        nums = [random.randint(-10, 10) for _ in range(n)]
        k = random.randint(1, n)
        assert max_sliding_window_naive(nums, k) == max_sliding_window_deque(nums, k)


def test_k_equals_array_length():
    assert max_sliding_window_deque([5, 1, 3], 3) == [5]


def test_k_equals_one():
    assert max_sliding_window_deque([4, 2, 7], 1) == [4, 2, 7]
