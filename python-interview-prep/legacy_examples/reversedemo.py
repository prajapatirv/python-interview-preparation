# Method 1: Slicing (most Pythonic, but they may forbid it)
def reverse_slice(s):
    return s[::-1]

# Method 2: Without built-ins — build by prepending each char
def reverse_loop(s):
    result = ""
    for ch in s:
        result = ch + result   # each new char goes to the front
    return result

# Method 3: Two-pointer swap on a char list (most efficient)
def reverse_two_pointer(s):
    chars = list(s)
    left, right = 0, len(chars) - 1
    while left < right:
        chars[left], chars[right] = chars[right], chars[left]
        left += 1
        right -= 1
    return "".join(chars)

# Method 4: Recursion
def reverse_recursive(s):
    if len(s) <= 1:
        return s
    return reverse_recursive(s[1:]) + s[0]

print(reverse_loop("hello"))   # olleh