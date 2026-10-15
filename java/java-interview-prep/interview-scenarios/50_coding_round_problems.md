---
id: coding-round-problems
title: Coding round: classic problems with verified solutions
stack: java
skill: coding
---
One classic problem per question: approach (brute force, then better), complexity, a complete runnable Java program, the test cases to walk through, and follow-ups. Every program in this file was compiled and run before it was saved.

Levels: **fresher** (0-2 yrs) · **mid** (3-6) · **senior** (6-10) · **architect** (10+).

### Q1 [fresher] Reverse a string without using library shortcuts
tags: string, two-pointers, char-array, immutability, stringbuilder, big-o, coding, basics

**Start here: the concepts**
- **String is immutable**: once created, a Java `String` never changes. "Reversing" always means building a new string. Any `s += c` in a loop copies the whole string each time.
- **char array**: `toCharArray()` gives a mutable copy of the characters. We can swap its elements in place and wrap it back with `new String(chars)`.
- **Two pointers**: one index at the start, one at the end. Swap, move both inward, and stop when they meet. Each element is touched once.
- **Big-O**: a way to describe how work grows with input size `n`. O(n) means double the input, double the work. O(n^2) means double the input, four times the work.
- **Library shortcut**: `new StringBuilder(s).reverse()`. The interviewer wants us to show we can do it by hand.

**The live scenario**
A batch job loads 2 million email addresses and stores a reversed copy of each, so "all emails ending in @example.com" becomes a fast prefix search in the database. The interviewer usually phrases it as: "Reverse a string without using `StringBuilder.reverse()` or any library method. What is the complexity? What if the input is null or empty?"

**What the interviewer is really checking**
Whether you ask clarifying questions (null? Unicode?), start with the simple idea and then improve it, and know why `String` concatenation in a loop is slow. They also want you to state O(n) time and O(n) space, and to handle null, empty and single-character inputs without crashing.

**How I answer it**
1. **Clarify and restate.** Input is a `String`, output is a new `String` with the characters in the opposite order. I would ask: can the input be null? (I will return null.) Is it only ASCII, or can it contain emoji? (I will reverse by `char` and mention the surrogate-pair caveat.) How long can it be?
2. **Brute force.** Loop from the last index to the first and append each character to a result string with `+=`. It is correct, but each `+=` creates a new string and copies everything so far. Total work is about 1 + 2 + ... + n, which is **O(n^2) time**.
3. **Better idea.** Copy the characters into a `char[]`. Put one pointer `i` at index 0 and one pointer `j` at the last index. Swap `a[i]` and `a[j]`, then do `i++` and `j--` until `i >= j`. It works because position `k` must end up holding what was at position `n-1-k`, so swapping mirror pairs does exactly that. The middle character of an odd-length string stays where it is, which is correct. A `StringBuilder` with `append` in reverse order is equally fine, and still O(n).
4. **Complexity.** Time is **O(n)**: n/2 swaps plus one copy in and one copy out. Space is **O(n)**: one extra `char[]`, which is unavoidable because a `String` cannot be changed in place.
5. **The code.**

```java
class Solution {
    // Two pointers on a char[] copy. Null is returned as null.
    static String reverse(String s) {
        if (s == null || s.length() < 2) return s; // null, "", single char
        char[] a = s.toCharArray();
        int i = 0, j = a.length - 1;
        while (i < j) {
            char t = a[i];
            a[i] = a[j];
            a[j] = t;
            i++;
            j--;
        }
        return new String(a);
    }

    // Brute force, O(n^2): kept only to compare results on small inputs.
    static String reverseConcat(String s) {
        if (s == null) return null;
        String r = "";
        for (int k = s.length() - 1; k >= 0; k--) r += s.charAt(k);
        return r;
    }

    static void check(boolean cond, String msg) {
        if (!(cond)) throw new AssertionError(msg);
    }

    public static void main(String[] args) {
        check("olleh".equals(reverse("hello")), "typical odd length");
        check("ba".equals(reverse("ab")), "even length");
        check("".equals(reverse("")), "empty");
        check(reverse(null) == null, "null");
        check("a".equals(reverse("a")), "single char");
        check("abba".equals(reverse("abba")), "palindrome");
        check("c b a".equals(reverse("a b c")), "spaces kept");
        check("321cba".equals(reverse("abc123")), "mixed");
        check(reverse("hello").equals(reverseConcat("hello")), "matches brute force");

        String big = "ab".repeat(500_000); // 1,000,000 chars
        String r = reverse(big);
        check(r.length() == big.length(), "large length");
        check(r.charAt(0) == 'b' && r.charAt(r.length() - 1) == 'a', "large ends");
        check(reverse(r).equals(big), "reverse twice gives original");

        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| Approach | Time | Extra space | Notes |
|---|---|---|---|
| `+=` in a loop (brute force) | O(n^2) | O(n) per step, garbage for GC | Fine for 10 chars, painful for 1 million |
| `char[]` + two pointers (final) | O(n) | O(n) | One copy in, one copy out |
| `StringBuilder` append backwards | O(n) | O(n) | Also good; `.reverse()` is the shortcut to avoid |

- **Common mistakes:**
  - Forgetting null and empty checks, which gives a `NullPointerException`.
  - Looping `i <= j` or `i < n` instead of `i < j`, which swaps back and undoes the work.
  - Trying to modify the `String` itself, which is impossible.
  - Off-by-one with `length()` instead of `length() - 1`.
- **Unicode:** emoji and some rare characters use two `char`s (a surrogate pair). Reversing by `char` breaks them. This matters if user-entered text is reversed in production.
- **Hot path:** if this runs millions of times, the allocation of `char[]` and `String` adds GC pressure. Check it with a profiler or GC logs before optimising.

**Test cases I'd walk through**
- **Typical:** `"hello"` returns `"olleh"`. Swaps are (h,o) and (e,l), and the middle `l` stays.
- **Empty:** `""` returns `""`.
- **Null:** `null` returns `null` (state this contract aloud).
- **Single element:** `"a"` returns `"a"`.
- **Duplicates/palindrome:** `"abba"` returns `"abba"`, and `"aaaa"` returns `"aaaa"`.
- **Spaces and digits:** `"a b c"` returns `"c b a"`, and `"abc123"` returns `"321cba"`.
- **Large input:** 1,000,000 characters finishes in milliseconds. The brute force on the same input would take far too long. Reversing twice must give back the original.

**Follow-ups to expect**
- *Why is `String` immutable, and how does that affect your solution?* -> Immutability makes strings safe to share, cache and use as map keys, and it allows the string pool. We must therefore build a new object instead of editing the original.
- *How would you reverse the words in a sentence instead of the characters?* -> Split on spaces and reverse the array of words with the same two-pointer swap, or reverse the whole string and then reverse each word. Both are O(n).
- *How would you handle emoji (surrogate pairs)?* -> Work with code points, for example `s.codePoints().toArray()`, and reverse that `int[]`. Alternatively, swap the two chars of each pair back after the reversal.
- *Can you do it recursively?* -> Yes, `reverse(s.substring(1)) + s.charAt(0)`, but it is O(n^2) because of the copying and risks `StackOverflowError` on long input.

**60-second answer**
"First I would check the contract: if the input is null I return null, and an empty or one-character string is returned as is. A Java `String` is immutable, so I have to build a new one. The naive way is `+=` in a loop, which copies the string every time and costs O(n^2). Instead I copy the string into a `char[]`, put one pointer at the start and one at the end, swap and move inward until they meet, then build a new `String` from the array. That is O(n) time and O(n) space, and the space is needed anyway because of immutability. I would test it with a normal word, an even and an odd length, empty, null, one character, a palindrome and a million-character input. I would also mention that reversing by `char` does not handle emoji, which would need code points."

### Q2 [fresher] Check whether a string is a palindrome
tags: string, two-pointers, palindrome, char-handling, edge-cases, coding, basics

**Start here: the concepts**
- **Palindrome**: a string that reads the same forwards and backwards, such as "level". In this variant we ignore upper/lower case and skip anything that is not a letter or digit, so "A man, a plan, a canal: Panama" counts.
- **Two pointers**: two index variables, one at the start (`left`) and one at the end (`right`), that move towards each other. At each step we compare the characters they point at.
- **Big-O**: a way to describe how work grows as the input size `n` grows. O(n) time means the work grows in proportion to the length. O(1) space means the extra memory stays constant however long the input is.
- **`Character.isLetterOrDigit` and `Character.toLowerCase`**: the standard Java ways to test "is this a letter or digit?" and to compare without caring about case.

**The live scenario**
You are building a signup or search service. A product owner asks you to treat "Anna", "anna" and "A.n.n.a" as the same value, for example to detect duplicate handles or to normalise input. The palindrome check is the interview-friendly version of this "compare a cleaned string against itself" idea. The interviewer usually says: "Given a string, return true if it is a palindrome, ignoring case and non-alphanumeric characters."

**What the interviewer is really checking**
Whether you ask clarifying questions (null, empty string, what counts as a character), start with the simple clean-and-reverse idea, then improve it to two pointers with no extra memory. They also want correct complexity and careful edge cases, such as a string made only of punctuation.

**How I answer it**
1. **Clarify and restate.** Input is a `String`; output is a `boolean`. I ask: can it be null? (I'll return false.) Is an empty string a palindrome? (Yes, true.) What about a string with only punctuation? (It has nothing to mismatch, so true.) Is the input ASCII only? (I'll assume Basic Multilingual Plane characters and mention emoji as a follow-up.)
2. **Brute force.** Build a new string containing only lowercase letters and digits, reverse it, and compare it with the original cleaned string. Time is O(n) and space is O(n), because we create a copy and a reversed copy.
3. **Better idea.** Keep `left` at index 0 and `right` at the last index. Move `left` forward past any non-alphanumeric character, and move `right` backward past any non-alphanumeric character. Compare the two characters in lowercase. If they differ, we can stop immediately and return false. If they match, move both pointers inward. It works because a palindrome is symmetric: the first useful character must match the last useful one, then the second with the second last, and so on. We never need a copy, and we stop as soon as we find a mismatch.
4. **Complexity.** Time O(n), since each pointer moves at most n steps in total. Space O(1), as we only use two integers.
5. **Code.**

```java
class Solution {
    // Two pointers moving inward, skipping non letters/digits, ignoring case.
    static boolean isPalindrome(String s) {
        if (s == null) return false;
        int left = 0, right = s.length() - 1;
        while (left < right) {
            while (left < right && !Character.isLetterOrDigit(s.charAt(left))) left++;
            while (left < right && !Character.isLetterOrDigit(s.charAt(right))) right--;
            if (Character.toLowerCase(s.charAt(left))
                    != Character.toLowerCase(s.charAt(right))) {
                return false;
            }
            left++;
            right--;
        }
        return true;
    }

    // Brute force kept only to cross-check the fast version in tests.
    static boolean bruteForce(String s) {
        StringBuilder cleaned = new StringBuilder();
        for (char c : s.toCharArray()) {
            if (Character.isLetterOrDigit(c)) cleaned.append(Character.toLowerCase(c));
        }
        return cleaned.toString().contentEquals(new StringBuilder(cleaned).reverse());
    }

    static void check(String input, boolean expected) {
        boolean actual = isPalindrome(input);
        if (!(actual == expected)) {
            throw new AssertionError("Failed for [" + input + "] expected "
                    + expected + " but got " + actual);
        }
        if (input != null && !(bruteForce(input) == expected)) {
            throw new AssertionError("Brute force disagrees for [" + input + "]");
        }
    }

    public static void main(String[] args) {
        check("A man, a plan, a canal: Panama", true); // typical, mixed case and punctuation
        check("race a car", false);                    // typical, not a palindrome
        check("", true);                               // empty string
        check(null, false);                            // null input
        check("a", true);                              // single character
        check(".,!  ", true);                          // no letters or digits at all
        check("0P", false);                            // digit vs letter, must not match
        check("No 'x' in Nixon", true);                // apostrophes and spaces
        check("ab", false);                            // two different characters
        check("abBA", true);                           // case-insensitive even length
        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| Approach | Time | Space | Notes |
|---|---|---|---|
| Clean + reverse + compare | O(n) | O(n) | Easy to read, but allocates two extra strings and always scans everything |
| Two pointers (final) | O(n) | O(1) | No copies, exits early at the first mismatch |

Common mistakes:
- Forgetting the `left < right` check inside the inner `while` loops. This can run the pointers past each other, or throw `StringIndexOutOfBoundsException` on a punctuation-only string.
- Using `Character.isAlphabetic` and forgetting digits, so "0P" is mis-judged. Use `isLetterOrDigit`.
- Comparing with `==` on strings or forgetting to lowercase both sides.
- Using `s.replaceAll("[^A-Za-z0-9]", "")` in a hot path. It compiles a regex on every call and allocates a new string.
- Not deciding what null means. State your choice aloud (here: false).

**Test cases I'd walk through**
- Typical: "A man, a plan, a canal: Panama" returns true; "race a car" returns false.
- Empty string "": true, because there is nothing to mismatch. Null: false (my stated choice).
- Single character "a": true. Two different characters "ab": false.
- Only punctuation ".,! ": true, because both pointers skip everything and meet.
- Digit vs letter "0P": false, which proves digits are handled and not confused with letters.
- Large input, such as a 10 million character string: still one pass and no extra memory, so it is safe.

**Follow-ups to expect**
- *How would you check it with streams?* -> `IntStream.range(0, n / 2).allMatch(i -> s.charAt(i) == s.charAt(n - 1 - i))` works for the plain version. With cleaning it needs an extra filtered copy, so loops are better for the skip-characters variant.
- *What about emoji or characters outside the Basic Multilingual Plane?* -> Java `char` is a UTF-16 unit, so such characters use two chars (a surrogate pair). Walk with `codePointAt` and `Character.charCount`, or use code points, to avoid splitting them.
- *How would you check whether a string can be rearranged into a palindrome?* -> Count characters with a `HashMap` or `int[128]`. At most one character may have an odd count. Time O(n), space O(k), where k is the number of distinct characters.

**60-second answer**
"First I'd confirm the rules: ignore case, skip non-alphanumerics, and I'd treat empty as true and null as false. The simple idea is to clean the string, reverse it and compare, which is O(n) time but O(n) extra space. A better way is two pointers: one at the start, one at the end. I move each inward past characters that are not letters or digits, compare them in lowercase, and return false at the first mismatch. If the pointers meet, it is a palindrome. This is O(n) time because each pointer moves at most n steps, and O(1) space since I only keep two indexes. The main edge cases are an empty string, a punctuation-only string, a single character and digits mixed with letters. I'd also mention that emoji need code points rather than chars."

### Q3 [fresher] Check whether two strings are anagrams
tags: strings, anagram, frequency-array, hashmap, sorting, big-o, coding, basics

**Start here: the concepts**
- **Anagram**: two strings with exactly the same characters, each appearing the same number of times, in any order. "listen" and "silent" are anagrams. "aab" and "abb" are not.
- **Frequency array (counting)**: an `int[]` where the index is the character and the value is how many times we have seen it. It is a tiny hash map with no hashing cost.
- **Hash map**: a key-to-value lookup with roughly constant-time access. I use it as a fallback for characters outside ASCII.
- **Sorting**: arranging characters in order. If both sorted strings are equal, the strings are anagrams.
- **Big-O**: how work grows as input size `n` grows. O(n) means work grows in a straight line. O(n log n) is a little more than linear. O(n^2) means doubling the input quadruples the work.
- **Space**: the extra memory we use besides the input. A fixed-size array of 128 slots is O(1), because it does not grow with `n`.

**The live scenario**
A search or deduplication feature groups words, SKU codes or tokens that are "the same letters rearranged". Another example is a validation step that checks a user-supplied code is a permutation of an expected one. In the interview the question is usually phrased: "Given two strings, return true if one is an anagram of the other. How would you do it, and what is the complexity?"

**What the interviewer is really checking**
Whether you ask clarifying questions (case, spaces, null, Unicode), start from a simple solution, and then improve it with a reason. They also want to hear time and space complexity and see edge cases handled without prompting.

**How I answer it**
1. **Clarify and restate.** Input is two strings, output is a boolean. I ask: is it case-sensitive? Do spaces count? Can the input be null or empty? I state my assumptions: case-sensitive, every character counts, null returns false, and two empty strings are anagrams. A quick early exit: different lengths means not anagrams.
2. **Brute force.** For each character in `a`, find it in `b` and remove it. If it is not found, return false. Each search is O(n), so the total is **O(n^2)** time. Removing from a string also creates new strings, which is wasteful.
3. **Better idea 1: sort both.** Anagrams become identical strings once sorted. Time is **O(n log n)**, and space is O(n) for the char arrays. It is short and easy to get right.
4. **Better idea 2: count characters.** Walk both strings once. Add 1 for each character of `a` and subtract 1 for each character of `b`. If the strings are anagrams, every counter ends at 0. Every character in `a` is cancelled by one in `b`, and the length check guarantees nothing is left over. This is a single pass, so time is **O(n)**. Space is **O(1)** for the fixed 128-slot array, plus a small map only if non-ASCII characters appear.
5. **Final complexity:** O(n) time, O(1) space for ASCII input. For arbitrary Unicode, the extra space is bounded by the number of distinct characters.

```java
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

class Solution {
    // O(n) time. Counts ASCII in an array, other chars in a small map.
    static boolean isAnagram(String a, String b) {
        if (a == null || b == null) return false;
        if (a.length() != b.length()) return false;
        int[] ascii = new int[128];
        Map<Character, Integer> other = new HashMap<>();
        for (int i = 0; i < a.length(); i++) {
            char x = a.charAt(i);
            char y = b.charAt(i);
            if (x < 128) ascii[x]++; else other.merge(x, 1, Integer::sum);
            if (y < 128) ascii[y]--; else other.merge(y, -1, Integer::sum);
        }
        for (int c : ascii) if (c != 0) return false;
        for (int c : other.values()) if (c != 0) return false;
        return true;
    }

    // O(n log n) alternative, handy to cross-check the counting version.
    static boolean isAnagramSorted(String a, String b) {
        if (a == null || b == null || a.length() != b.length()) return false;
        char[] x = a.toCharArray();
        char[] y = b.toCharArray();
        Arrays.sort(x);
        Arrays.sort(y);
        return Arrays.equals(x, y);
    }

    static void check(boolean cond, String msg) {
        if (!(cond)) throw new AssertionError(msg);
    }

    public static void main(String[] args) {
        check(isAnagram("listen", "silent"), "typical anagram");
        check(!isAnagram("aab", "abb"), "same length, different counts");
        check(!isAnagram("abc", "abcd"), "different lengths");
        check(isAnagram("", ""), "both empty");
        check(!isAnagram(null, "a") && !isAnagram("a", null), "null input");
        check(isAnagram("a", "a") && !isAnagram("a", "b"), "single char");
        check(!isAnagram("Listen", "Silent"), "case-sensitive by assumption");
        check(isAnagram("aabbcc", "ccbbaa"), "duplicates");
        check(isAnagram("caf\u00e9", "\u00e9fac"), "non-ASCII chars");
        String big = "abcdefghij".repeat(100_000);
        String rev = new StringBuilder(big).reverse().toString();
        check(isAnagram(big, rev) && isAnagramSorted(big, rev), "large input");
        check(isAnagram("rat", "tar") == isAnagramSorted("rat", "tar"), "both methods agree");
        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| Approach | Time | Space | Notes |
|---|---|---|---|
| Brute force (find and remove) | O(n^2) | O(n) | Simple, but slow and creates many temporary strings |
| Sort and compare | O(n log n) | O(n) | Very readable, works for any characters |
| Frequency array / map | O(n) | O(1) for ASCII | Fastest, needs a decision on the character set |

Common mistakes:
- Forgetting the length check, which is a free early exit and avoids a wrong answer when one string has extra characters.
- Using `int[26]` and crashing with `ArrayIndexOutOfBoundsException` on uppercase, digits or spaces. Only use it if the question says "lowercase letters only".
- Not deciding about null, case and spaces, and not saying the decision aloud.
- Comparing `String` objects with `==` instead of `equals` (not needed here, but it is a common slip in follow-ups).
- Using `HashMap<Character,Integer>` everywhere. It works, but boxing makes it slower than the array for large inputs.

**Test cases I'd walk through**
- Typical: "listen" and "silent" returns true.
- Same length, different counts: "aab" and "abb" returns false.
- Different lengths: "abc" and "abcd" returns false immediately.
- Empty: "" and "" returns true. Null on either side returns false (my stated assumption).
- Single character: "a" and "a" returns true, "a" and "b" returns false.
- Duplicates: "aabbcc" and "ccbbaa" returns true.
- Case: "Listen" and "Silent" returns false when case-sensitive. I would lowercase both first if the interviewer wants case-insensitive.
- Large input: one million characters runs in one pass with no extra growth in memory.

**Follow-ups to expect**
- *How would you handle full Unicode, such as emojis?* -> A Java `char` is a 16-bit unit, and emojis use two (a surrogate pair). Count code points with `String.codePoints()` and a `HashMap<Integer,Integer>` instead.
- *Make it case-insensitive and ignore spaces.* -> Normalise first, for example `s.replace(" ", "").toLowerCase()`, then run the same algorithm. The extra cost is O(n).
- *How would you group a list of words into anagram groups?* -> Use a `HashMap<String, List<String>>` keyed by the sorted characters (or a count signature) of each word. Time is O(total characters x log word length).

**60-second answer**
"First I would clarify: is it case-sensitive, can the input be null or contain spaces? I'd assume case-sensitive, null returns false and two empty strings are anagrams. The simplest idea is to remove each character of one string from the other, which is O(n^2). A better idea is to sort both strings and compare them, which is O(n log n). The best idea is to count characters. I check the lengths first, then walk both strings once, adding one for each character of the first and subtracting one for the second in a 128-slot array. If every counter ends at zero, they are anagrams. That is O(n) time and O(1) space for ASCII. For non-ASCII characters I fall back to a small HashMap. I'd test empty, null, single character, duplicates and different-length inputs."

### Q4 [fresher] Count the frequency of each character in a string
tags: string, hashmap, linkedhashmap, frequency-count, streams, coding, basics

**Start here: the concepts**
- **Hash map (`HashMap`)**: a lookup table of key -> value pairs. Here the key is a character and the value is how many times we have seen it. Finding or updating a key takes about constant time on average.
- **`LinkedHashMap`**: a hash map that also remembers insertion order. It prints characters in the order they first appeared, so output is predictable.
- **Counting array**: for a small, known alphabet (for example ASCII, 128 values), `int[128]` works as a map where the character's numeric code is the index. It is faster and uses fixed memory.
- **Big-O**: a way to describe how work grows with input size. *n* is the string length and *k* is the number of distinct characters. O(n) means we touch each character once. O(k) extra space means memory grows with the number of distinct characters, not the length.
- **`char` in Java**: a 16-bit UTF-16 unit. Letters, digits and spaces are all chars, and a space is a character like any other.

**The live scenario**
You are building a text-validation service. It must flag passwords that repeat one character too often, or compute character statistics for a log line. The interviewer says: "Given a string, return how many times each character appears." Often they add: "Keep the order of first appearance," or "Can you do it with streams?"

**What the interviewer is really checking**
Whether you ask clarifying questions (case sensitivity, spaces, null, Unicode), start with the simple idea and then improve it. Also whether you pick the right collection (`HashMap`, `LinkedHashMap` or `int[]`), state O(n) time, and handle null and empty input.

**How I answer it**
1. **Clarify and restate.**
   - Input is a `String`, output is a map from character to count.
   - I ask whether it is case-sensitive (I assume yes, so `a` and `A` differ), whether spaces and punctuation count (I assume yes, every character counts), and whether order matters (I use first-appearance order).
   - For null I return an empty map. For empty input I also return an empty map.
2. **Brute force.** For each character, scan the whole string and count its occurrences. Skip characters already counted, using a "visited" list. This is O(n * n) time, and O(k) space for the visited list.
3. **Better idea.**
   - Walk the string once with a `LinkedHashMap<Character,Integer>`.
   - For each character, add 1 to its count; `merge(ch, 1, Integer::sum)` does this and handles the first-seen case.
   - This works because every character is looked up and updated in about constant time, so each character is processed exactly once.
   - If the alphabet is known to be ASCII, an `int[128]` is the same idea with an index instead of a hash.
4. **Complexity of the final solution.** Time is O(n), because one pass with O(1) average map work per character. Space is O(k), where k is the number of distinct characters (at most n).
5. **The code.**

```java
import java.util.*;
import java.util.stream.*;

class Solution {
    // Loop version: one pass, keeps first-appearance order.
    static Map<Character, Integer> count(String s) {
        Map<Character, Integer> m = new LinkedHashMap<>();
        if (s == null) return m;
        for (int i = 0; i < s.length(); i++) {
            m.merge(s.charAt(i), 1, Integer::sum);
        }
        return m;
    }

    // Streams version: same result, counts are Long because of Collectors.counting().
    static Map<Character, Long> countStream(String s) {
        if (s == null) return new LinkedHashMap<>();
        return s.chars()
                .mapToObj(c -> (char) c)
                .collect(Collectors.groupingBy(c -> c, LinkedHashMap::new, Collectors.counting()));
    }

    // Array version: only for ASCII (codes 0-127); other chars are ignored here.
    static int[] countAscii(String s) {
        int[] a = new int[128];
        if (s == null) return a;
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c < 128) a[c]++;
        }
        return a;
    }

    static void check(String name, boolean cond) {
        if (!(cond)) throw new AssertionError(name);
    }

    public static void main(String[] args) {
        check("hello keeps order", count("hello").toString().equals("{h=1, e=1, l=2, o=1}"));
        check("empty", count("").isEmpty());
        check("null", count(null).isEmpty());
        // "a b" has exactly one space, and it is counted like any other char
        Map<Character, Integer> sp = count("a b");
        check("space is counted", Integer.valueOf(1).equals(sp.get(' ')) && sp.size() == 3);
        check("single char repeated", count("aaaa").toString().equals("{a=4}"));
        Map<Character, Integer> cs = count("aA");
        check("case sensitive", cs.size() == 2 && Integer.valueOf(1).equals(cs.get('A')));

        Map<Character, Integer> loop = count("mississippi");
        Map<Character, Long> stream = countStream("mississippi");
        boolean same = loop.size() == stream.size();
        for (Map.Entry<Character, Integer> e : loop.entrySet()) {
            same &= Long.valueOf(e.getValue()).equals(stream.get(e.getKey()));
        }
        check("stream matches loop", same);
        check("array version", countAscii("abca")['a'] == 2 && countAscii("abca")['b'] == 1);
        check("large input", Integer.valueOf(500000).equals(count("ab".repeat(500000)).get('a')));
        check("stream null", countStream(null).isEmpty());
        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| Approach | Time | Space | Notes |
|---|---|---|---|
| Brute force (rescan per char) | O(n * n) | O(k) | Fine for tiny input, too slow for large strings |
| `HashMap` / `LinkedHashMap` | O(n) | O(k) | General; works for any character; `LinkedHashMap` adds a little memory for order |
| `int[128]` or `int[256]` | O(n) | O(1) fixed | Fastest, but only for a known small alphabet |
| Streams `groupingBy` | O(n) | O(k) | Very readable, but boxing makes it slower than a plain loop; counts come back as `Long` |

Common mistakes:
- Using plain `HashMap` and then expecting a specific print order. Its iteration order is not guaranteed.
- Forgetting null and empty input, which causes a `NullPointerException` on `s.length()`.
- Accidentally skipping spaces or changing case without being asked.
- Using `int[26]` and crashing with `ArrayIndexOutOfBoundsException` on uppercase, digits or spaces.
- Comparing `Integer` values with `==` outside the cached range -128 to 127. Use `equals`.
- Assuming one `char` is one visible character. Emojis use two chars (a surrogate pair).

**Test cases I'd walk through**
- `"hello"` -> `{h=1, e=1, l=2, o=1}`, in first-appearance order.
- `""` -> empty map. `null` -> empty map (or throw, if the interviewer prefers; I state my choice).
- `"a"` or `"aaaa"` -> `{a=1}` or `{a=4}` (single and all-duplicate input).
- `"a b"` -> a, space and b each appear once, so the space is counted.
- `"aA"` -> two keys, because it is case-sensitive.
- `"mississippi"` -> m=1, i=4, s=4, p=2, and the stream version gives the same result.
- A string of one million characters -> still one pass, with a map of at most k entries.

**Follow-ups to expect**
- *How would you find the first non-repeating character?* -> Build the `LinkedHashMap` counts, then return the first key whose value is 1. It is still O(n) time, and order is why we chose `LinkedHashMap`.
- *How do you handle emojis or full Unicode?* -> Iterate by code points: `s.codePoints()` or `codePointAt`, and use `Integer` keys, so a surrogate pair counts as one character.
- *Why `merge` instead of `containsKey` / `put`?* -> `merge` does the lookup and update in one call, so it is shorter and avoids the double lookup.
- *Is the stream version faster?* -> No. It is the same O(n) but with boxing overhead. Use it for readability, and a loop or array in hot paths.

**60-second answer**
"First I would clarify: is it case-sensitive, do spaces count, and what should null return? I assume every character counts and null gives an empty map. The brute-force idea is to scan the whole string for each character, which is O(n squared). The better way is one pass with a `LinkedHashMap` from character to count, using `merge(ch, 1, Integer::sum)`. Each update is O(1) on average, so total time is O(n), and space is O(k) for k distinct characters. I choose `LinkedHashMap` so the output keeps first-appearance order. If the input is known to be ASCII, an `int[128]` is faster with constant space, and a stream with `groupingBy` and `counting` is a readable alternative. I would test with empty, null, one character, repeated characters, spaces and mixed case."

### Q5 [mid] Find the first non-repeating character in a string
tags: string, hash-map, frequency-count, linkedhashmap, big-o, coding, basics

**Start here: the concepts**
- **Hash map**: a structure that stores key -> value pairs and finds a key in about constant time on average. Here the key is a character and the value is how many times it appeared.
- **Frequency count**: one pass over the data that records how often each item occurs. `map.merge(c, 1, Integer::sum)` is the idiomatic Java way.
- **Two-pass technique**: pass 1 collects the counts, pass 2 walks the string in its original order and returns the first character whose count is 1. Pass 2 is what preserves "first".
- **LinkedHashMap**: a hash map that remembers insertion order. It is an alternative: count first, then scan the map for the first entry with count 1.
- **Big-O**: describes how the work grows with input size `n`. O(n) means work grows in proportion to the length. O(n^2) means doubling the input roughly quadruples the work. O(1) space means memory does not grow with `n`.

**The live scenario**
You are building a log or event pipeline and need the first request ID, error code or token in a batch that appeared exactly once. For example, "which character or key in this stream is unique, and which came first?" The interviewer usually says: *"Given a string, return the index of the first character that does not repeat. Return -1 if there is none."*

**What the interviewer is really checking**
Whether you ask clarifying questions (case sensitivity, character set, what to return), start with the obvious O(n^2) solution, and then improve it to O(n) with a clear reason. They also want to see that you handle null, empty and all-duplicate input without being prompted.

**How I answer it**
1. **Clarify and restate.** Input is a `String`; output is the index of the first character that occurs exactly once, or -1. I would ask: Is it case-sensitive? (I assume yes, so `a` and `A` differ.) Can the input be null or empty? (Return -1.) Is it plain ASCII or full Unicode? (I assume UTF-16 `char` units and mention surrogate pairs as a caveat.)
2. **Brute force.** For each position `i`, scan the whole string to see whether the same character appears at another position `j`. The first `i` with no match is the answer. Time O(n^2), space O(1).
3. **Better idea.** The slow part is re-scanning for each character. If I count every character once up front, "does it repeat?" becomes a single map lookup. Pass 1 builds the counts. Pass 2 walks the string left to right and returns the first index whose count is 1. Scanning the original string, not the map, guarantees the answer is the first one, even with a plain `HashMap` that has no ordering.
4. **Complexity.** Time O(n), because there are two linear passes and each map operation is O(1) on average. Space O(k), where k is the number of distinct characters. That is bounded by the alphabet size, so it is effectively O(1) for ASCII.
5. **Code.**

```java
import java.util.*;

class Solution {
    // Two-pass frequency count: O(n) time, O(k) space (k = distinct chars)
    static int firstUniqueIndex(String s) {
        if (s == null || s.isEmpty()) return -1;
        Map<Character, Integer> count = new HashMap<>();
        for (int i = 0; i < s.length(); i++) {
            count.merge(s.charAt(i), 1, Integer::sum);
        }
        for (int i = 0; i < s.length(); i++) {
            if (count.get(s.charAt(i)) == 1) return i;
        }
        return -1;
    }

    // Brute force: O(n^2) time, O(1) space. Used only to cross-check.
    static int bruteForce(String s) {
        if (s == null) return -1;
        for (int i = 0; i < s.length(); i++) {
            boolean repeated = false;
            for (int j = 0; j < s.length() && !repeated; j++) {
                if (i != j && s.charAt(i) == s.charAt(j)) repeated = true;
            }
            if (!repeated) return i;
        }
        return -1;
    }

    static void check(boolean cond, String msg) {
        if (!(cond)) throw new AssertionError(msg);
    }

    public static void main(String[] args) {
        check(firstUniqueIndex("leetcode") == 0, "leetcode");
        check(firstUniqueIndex("loveleetcode") == 2, "loveleetcode");
        check(firstUniqueIndex("aabb") == -1, "all repeated");
        check(firstUniqueIndex("") == -1, "empty");
        check(firstUniqueIndex(null) == -1, "null");
        check(firstUniqueIndex("z") == 0, "single char");
        check(firstUniqueIndex("aabbc") == 4, "unique at end");
        check(firstUniqueIndex("aA") == 0, "case sensitive");

        // Large input: one million 'a' followed by a single 'b'
        String big = "a".repeat(1_000_000) + "b";
        check(firstUniqueIndex(big) == 1_000_000, "large input");

        // Cross-check against brute force on pseudo-random small strings
        Random rnd = new Random(42);
        for (int t = 0; t < 500; t++) {
            StringBuilder sb = new StringBuilder();
            int len = rnd.nextInt(12);
            for (int k = 0; k < len; k++) sb.append((char) ('a' + rnd.nextInt(4)));
            String s = sb.toString();
            check(firstUniqueIndex(s) == bruteForce(s), "mismatch for " + s);
        }
        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| Approach | Time | Space | Notes |
|---|---|---|---|
| Brute force (nested loops) | O(n^2) | O(1) | Fine for tiny strings; unusable at 1M characters |
| Two-pass `HashMap` | O(n) | O(k) | Simple and clear; boxing `Character`/`Integer` adds some overhead |
| Two-pass `int[128]` or `int[256]` | O(n) | O(1) | Fastest for ASCII or Latin-1; breaks for wider character sets |
| `LinkedHashMap` | O(n) | O(k) | Pass 2 iterates distinct keys, not the full string; useful when distinct keys are far fewer than `n` |

Common mistakes:
- Iterating a plain `HashMap` in pass 2 and assuming it returns the first one. `HashMap` has no guaranteed order.
- Forgetting null or empty input and getting a `NullPointerException`.
- Comparing `Integer` objects with `==` against values outside -128..127. Here `count.get(c) == 1` compares to an `int` literal, so it unboxes and is safe.
- Ignoring case rules or returning the character instead of the index without confirming what is asked.
- Treating `char` as a full Unicode character. Emoji and other supplementary characters are two `char` units (a surrogate pair).

**Test cases I'd walk through**
- Typical: `"leetcode"` -> 0 (`l`); `"loveleetcode"` -> 2 (`v`).
- No unique character: `"aabb"` -> -1.
- Empty or null: `""` and `null` -> -1.
- Single character: `"z"` -> 0.
- Unique character at the end: `"aabbc"` -> 4.
- Case sensitivity: `"aA"` -> 0, because `a` and `A` are different.
- Large input: one million `a` plus a final `b` -> 1,000,000, and it finishes quickly because it is linear.

**Follow-ups to expect**
- *Can you do it in a single pass?* -> Not strictly. You can use a `LinkedHashMap` (or a map of char -> first index, with -1 marking a repeat) to count in one pass, but you still need a second step to find the first entry with count 1. The work is still O(n).
- *How would you handle full Unicode?* -> Iterate by code point with `s.codePoints()` or `s.codePointAt(i)` and `Character.charCount`, and key the map on `Integer` code points. Otherwise surrogate pairs get counted as two separate characters.
- *What if the input is a huge stream and you can't hold it all?* -> Keep a map of counts for the characters seen, plus an ordered structure of candidates that have appeared once. Remove a character from the candidates when its count reaches 2. The head of the candidates is the current answer, and the memory is bounded by the alphabet.

**60-second answer**
"First I'd confirm the details: is it case-sensitive, what to return for empty or null input, and whether I return the index or the character. I'd assume the index, with -1 when there is none. The brute force checks each character against every other one, which is O(n^2) time and O(1) space. That is too slow for large inputs, so I'd count first. Pass 1 builds a `HashMap` of character -> count using `merge`. Pass 2 walks the original string left to right and returns the first index whose count is 1. Walking the string, not the map, is what guarantees the first one, because a `HashMap` has no order. That's O(n) time, and space bounded by the number of distinct characters, so effectively O(1) for ASCII. I'd cover null, empty, all-duplicates, single character and a large input. If asked, I'd mention an `int[256]` for speed with ASCII and code points for full Unicode."

### Q6 [mid] Longest substring without repeating characters
tags: sliding-window, hashmap, two-pointers, strings, java, coding, basics

**Start here: the concepts**
- **Substring**: a contiguous slice of the string. "abc" is a substring of "xabcy"; "axy" is not (that is a subsequence).
- **Hash map**: a structure that stores key -> value pairs and looks up a key in about constant time. Here the key is a character and the value is the last index where we saw it.
- **Two pointers / sliding window**: two indexes, `left` and `right`, mark a window over the string. `right` moves forward to grow the window. `left` jumps forward to shrink it when the rule is broken. Neither pointer ever moves backward.
- **Big-O**: describes how work grows with input size n. O(n) means roughly one pass. O(n^2) means work grows with the square of n, so 10x the input is about 100x the work.
- **Window invariant**: the rule that is always true. Here it is: every character inside `[left, right]` is unique.

**The live scenario**
You are on a backend team that generates short tokens or session IDs. A validation job must find the longest run of distinct characters in a token, or in a log field of up to 100,000 characters per record, across millions of records. An O(n^2) scan is too slow at that volume.
The interviewer usually phrases it as: "Given a string, find the length of the longest substring without repeating characters. What is your approach, and what is its complexity?"

**What the interviewer is really checking**
Do you ask clarifying questions (character set, null or empty input, length or the substring itself) and state the brute force before optimising? Can you explain why `left` never moves backward, give the O(n) time and bounded space, and handle edge cases like "abba", where a stale index must be ignored?

**How I answer it**
1. **Clarify and restate.**
   - Input: a string `s`. Output: an `int`, the length of the longest substring with all distinct characters.
   - Questions I would ask: Is the input ASCII or Unicode? Can it be null or empty (I return 0)? Do you want the length or the substring? (Length here.)
   - A note on Java: `charAt` returns UTF-16 code units, so emoji and other supplementary characters count as two units. I would mention this and not over-engineer it unless asked.
2. **Brute force.**
   - For each start index `i`, extend `j` while the characters are unique, using a `HashSet`, and stop at the first duplicate. Track the maximum length.
   - Time is O(n^2) in the worst case (and O(n^3) if you re-check uniqueness of every substring naively). Space is O(min(n, k)), where k is the alphabet size.
3. **Better idea.**
   - Keep one window `[left, right]` that is always duplicate-free. Store in a map the last index where each character was seen.
   - Move `right` one step at a time. If `s[right]` was last seen at index `prev` and `prev >= left`, that character is inside the window. Jump `left` to `prev + 1`, which removes the duplicate in one move instead of shrinking one step at a time.
   - The `prev >= left` check matters. A map entry with `prev < left` is stale: that character is already outside the window, so it is not a duplicate.
   - After updating, the window length is `right - left + 1`. Keep the maximum.
4. **Complexity.**
   - Time is O(n): `right` visits each index once, `left` only moves forward, and map operations are about O(1).
   - Space is O(min(n, k)) for the map, where k is the alphabet size. For ASCII that is at most 128 entries, so effectively O(1).
5. **The code.**

```java
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Random;
import java.util.Set;

class Solution {
    // Sliding window with last-seen index map: O(n) time, O(min(n,k)) space.
    static int lengthOfLongestSubstring(String s) {
        if (s == null || s.isEmpty()) return 0;
        Map<Character, Integer> last = new HashMap<>();
        int best = 0;
        int left = 0;
        for (int right = 0; right < s.length(); right++) {
            char c = s.charAt(right);
            Integer prev = last.get(c);
            // Only react if the previous sighting is inside the current window.
            if (prev != null && prev >= left) {
                left = prev + 1;
            }
            last.put(c, right);
            best = Math.max(best, right - left + 1);
        }
        return best;
    }

    // Brute force, used only to cross-check the fast version.
    static int brute(String s) {
        int best = 0;
        for (int i = 0; i < s.length(); i++) {
            Set<Character> seen = new HashSet<>();
            int j = i;
            while (j < s.length() && seen.add(s.charAt(j))) j++;
            best = Math.max(best, j - i);
        }
        return best;
    }

    static void check(String name, int actual, int expected) {
        if (!(actual == expected)) {
            throw new AssertionError(name + ": expected " + expected + " but got " + actual);
        }
    }

    public static void main(String[] args) {
        check("typical", lengthOfLongestSubstring("abcabcbb"), 3);
        check("all same", lengthOfLongestSubstring("bbbbb"), 1);
        check("pwwkew", lengthOfLongestSubstring("pwwkew"), 3);
        check("empty", lengthOfLongestSubstring(""), 0);
        check("null", lengthOfLongestSubstring(null), 0);
        check("single", lengthOfLongestSubstring("a"), 1);
        check("stale index abba", lengthOfLongestSubstring("abba"), 2);
        check("tmmzuxt", lengthOfLongestSubstring("tmmzuxt"), 5);
        check("with spaces", lengthOfLongestSubstring("a b a"), 3);

        StringBuilder big = new StringBuilder();
        for (int i = 0; i < 100_000; i++) big.append((char) ('a' + i % 26));
        check("large", lengthOfLongestSubstring(big.toString()), 26);

        Random rnd = new Random(42);
        for (int t = 0; t < 500; t++) {
            int len = rnd.nextInt(40);
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < len; i++) sb.append((char) ('a' + rnd.nextInt(5)));
            String s = sb.toString();
            check("random " + s, lengthOfLongestSubstring(s), brute(s));
        }
        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| Approach | Time | Space | Note |
|---|---|---|---|
| Brute force with a set per start | O(n^2) | O(min(n,k)) | Simple, but too slow at 100k characters or more |
| Sliding window with a `HashSet` (shrink one step at a time) | O(n) | O(min(n,k)) | Correct, but `left` moves more often |
| Sliding window with a last-seen map (final) | O(n) | O(min(n,k)) | `left` jumps in one move |
| `int[128]` or `int[256]` instead of a map | O(n) | O(1) | Fastest for known ASCII; avoids `Character` boxing |

Common mistakes:
- Forgetting `prev >= left`. On "abba", `left` would move backward at the final 'a' and give 3 instead of 2.
- Resetting the window to start at `right` on a duplicate, which is wrong: you must move to `prev + 1`.
- Updating `best` before moving `left`, which overcounts.
- Not handling null or empty input (NPE or a wrong result).
- Assuming `char` equals a full character. Emoji need code points (`s.codePoints()`).
- Using a `Map<Character,Integer>` on a hot path without noticing the boxing cost. An `int[128]` array avoids it for ASCII.

**Test cases I'd walk through**
- Typical: "abcabcbb" returns 3 (window "abc").
- All duplicates: "bbbbb" returns 1.
- Duplicate in the middle: "pwwkew" returns 3 ("wke"; note "pwke" is a subsequence, not a substring).
- Stale index: "abba" returns 2. At the last 'a', `prev = 0` is less than `left = 2`, so `left` is not moved.
- Empty string or null: returns 0.
- Single character: "a" returns 1.
- All distinct: "abcdef" returns 6.
- Large input: 100,000 characters cycling a-z returns 26 in a single pass, in milliseconds.

**Follow-ups to expect**
- *How would you return the substring itself, not just the length?* -> Track `bestStart` whenever `best` improves, then return `s.substring(bestStart, bestStart + best)`. Complexity is unchanged.
- *What if the input is full Unicode?* -> Iterate code points (`s.codePoints()`) or key the map by `Integer` code point, so surrogate pairs count as one character. Space becomes O(min(n, number of distinct code points)).
- *Can you reduce the map overhead?* -> If the alphabet is known ASCII, use `int[128]` initialised to -1. It avoids boxing and hashing, and space is constant.
- *Could you do this on a stream of characters you cannot store?* -> Only the window is needed, so you can keep the map and the current window length. Memory is bounded by the alphabet size, but you cannot reconstruct the substring without keeping the window.

**60-second answer**
"First I would clarify the input: whether it is ASCII or Unicode, what to return for null or empty, and that I return the length. The brute force tries every start index and extends until a duplicate appears, which is O(n^2). To improve it I keep a sliding window with two pointers, `left` and `right`, where all characters in the window are unique. I store each character's last-seen index in a hash map. When `s[right]` was last seen at an index at or after `left`, I jump `left` to that index plus one. The 'at or after `left`' check ignores stale entries, as in 'abba'. After each step I update the maximum with `right - left + 1`. Each pointer only moves forward, so time is O(n). Space is O(min(n, k)), where k is the alphabet size, which is constant for ASCII. I would then test with 'abcabcbb', 'abba', empty, null and a single character."

### Q7 [mid] Valid parentheses
tags: stack, string, deque, lifo, parsing, o(n), coding, basics

**Start here: the concepts**
- **Stack**: a pile where you only touch the top. The last item you put in is the first one you take out (LIFO, last in first out). In Java, use `ArrayDeque` (`push`/`pop`/`peek`) or a plain `char[]` with an index. Avoid the legacy `java.util.Stack`, which is synchronized and slower for no benefit here.
- **Why a stack fits**: brackets nest. The most recently opened bracket must be the first one closed, which is exactly LIFO.
- **Big-O**: a way to say how work grows with input size `n` (the string length). O(n) means the work grows in step with `n`. O(n^2) means doubling the input roughly quadruples the work.
- **Time vs space**: time is how many steps we run. Space is how much extra memory we use besides the input.

**The live scenario**
Your service accepts a user-defined filter expression, a templating string or a JSON-like payload, for example `{[(a+b)*c]}`. Before the expensive parser or a database query runs, you want a cheap check that the grouping is balanced, so malformed requests are rejected early with a 400. The interviewer usually says: "Given a string containing only `(`, `)`, `[`, `]`, `{`, `}`, determine whether it is valid. Open brackets must be closed by the same type and in the correct order."

**What the interviewer is really checking**
Do you ask clarifying questions (empty string, null, other characters), mention the brute force first, then move to the O(n) stack solution and explain why LIFO matches nesting? Do you handle the edge cases: closing bracket on an empty stack, leftover open brackets, and odd length?

**How I answer it**
1. **Clarify and restate.**
   - Input is a string, output is a boolean.
   - Is an empty string valid? Yes, nothing is unbalanced.
   - What about `null`? I would return `false` and say so aloud (or throw `IllegalArgumentException`, depending on the team's contract).
   - Can other characters appear? I assume only the six bracket characters, so anything else returns `false`.
   - Size: assume up to around a million characters, so avoid recursion.
2. **Brute force.**
   - Repeatedly delete the adjacent pairs `()`, `[]`, `{}` from the string until nothing changes. The string is valid if it ends up empty.
   - Each pass is O(n) and there can be up to n/2 passes, so time is O(n^2). Creating new strings each pass costs extra memory churn, O(n) space per pass.
3. **Better idea.**
   - Scan left to right once. On an opening bracket, push the closing bracket we expect to see later.
   - On a closing bracket, the top of the stack must be that exact character. If the stack is empty or the top differs, it is invalid.
   - At the end, the stack must be empty, otherwise some brackets were never closed.
   - It works because the innermost open bracket is always on top, and it must be closed before any outer one.
   - Pushing the expected closer instead of the opener removes the need for a lookup map.
4. **Complexity.** Time O(n), as each character is pushed and popped at most once. Space O(n) in the worst case, such as `((((`. I use a `char[]` of size `n` instead of `Deque<Character>` to avoid boxing.
5. **Code.**

```java
class Solution {
    static boolean isValid(String s) {
        if (s == null) return false;
        int n = s.length();
        if ((n & 1) == 1) return false; // odd length can never be balanced
        char[] stack = new char[n];     // holds the closer we expect next
        int top = 0;
        for (int i = 0; i < n; i++) {
            char c = s.charAt(i);
            switch (c) {
                case '(' -> stack[top++] = ')';
                case '[' -> stack[top++] = ']';
                case '{' -> stack[top++] = '}';
                case ')', ']', '}' -> {
                    if (top == 0 || stack[--top] != c) return false;
                }
                default -> { return false; } // not a bracket
            }
        }
        return top == 0; // leftover openers mean invalid
    }

    static void check(String in, boolean expected) {
        boolean actual = isValid(in);
        if (!(actual == expected)) {
            throw new AssertionError("input=" + in + " expected=" + expected
                    + " actual=" + actual);
        }
    }

    public static void main(String[] args) {
        check("()", true);
        check("()[]{}", true);
        check("{[()]}", true);
        check("(]", false);
        check("([)]", false);      // right types, wrong order
        check("", true);           // empty is valid
        check(null, false);        // documented choice
        check("(", false);         // odd length
        check("))", false);        // closer on empty stack
        check("((", false);        // leftover openers, even length
        check("a()", false);       // non-bracket character
        String big = "(".repeat(500_000) + ")".repeat(500_000);
        check(big, true);          // deep nesting, no recursion
        check(big + ")(", false);
        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| Approach | Time | Space | Note |
|---|---|---|---|
| Repeated `replace` of pairs | O(n^2) | O(n) per pass | Simple to write, but slow and creates garbage |
| Stack (`char[]` or `ArrayDeque`) | O(n) | O(n) | Single pass, can stop at the first error |

- Common mistakes:
  - Calling `pop`/`peek` on an empty stack (`EmptyStackException` or `NoSuchElementException`).
  - Forgetting the final "stack is empty" check, so `"(("` is wrongly accepted.
  - Only counting brackets per type, which wrongly accepts `([)]`.
  - Recursive solutions that hit `StackOverflowError` on deep input.
  - Using the legacy `Stack` class, or `Deque<Character>` in a hot path (boxing cost).
- In production, log or count the rejection reason (unexpected closer, unclosed opener, position) so you can monitor malformed-input rates, and put a maximum length on the input.

**Test cases I'd walk through**
- Typical: `"()[]{}"` returns `true`, `"{[()]}"` returns `true`.
- Wrong type: `"(]"` returns `false`.
- Wrong order: `"([)]"` returns `false` (the `)` meets `]` on top).
- Empty string: `""` returns `true`.
- Null: `null` returns `false` (state this choice).
- Single character: `"("` or `")"` returns `false`.
- Closer first: `"))"` returns `false`, because the stack is empty at the first character.
- Leftover openers: `"(("` returns `false`.
- Large input: 500,000 `(` followed by 500,000 `)` returns `true` in a single pass and about 1 MB of stack memory.

**Follow-ups to expect**
- *How would you return the index of the first error?* -> Keep the index on the stack alongside the char, or store only indexes and look up `s.charAt`. Report the failing index on a mismatch, or the index of the bottom unmatched opener at the end.
- *Can you do it in O(1) space?* -> For a single bracket type, yes: keep a counter that goes up for `(` and down for `)`, and fail if it goes negative or is not zero at the end. For mixed types, no, because the order of open types has to be remembered.
- *What if the input is a stream too large for memory?* -> Process it in chunks and keep the stack across chunks. The stack depth, not the length, is the memory cost, so cap the maximum nesting depth and reject beyond it.
- *What if other characters like letters are allowed?* -> Change the `default` branch to ignore them, and drop the odd-length shortcut.

**60-second answer**
"First I'd confirm the input is only the six bracket characters, that an empty string is valid, and how to treat null. The brute force is to keep deleting adjacent matching pairs until nothing changes. That is correct but O(n^2). The better way is a stack, because brackets nest and the most recent opener must be closed first. I scan once: for each opener I push the closer I expect, and for each closer I check the stack is not empty and the top equals it, otherwise I return false. At the end the stack must be empty, or there were unclosed openers. Time is O(n), since each character is pushed and popped at most once, and space is O(n) in the worst case. I use a `char[]` as the stack to avoid boxing and an odd-length shortcut to exit early, and I'd test empty, a single character, wrong order like `([)]`, and leftover openers like `((`."

### Q8 [fresher] Two sum: find two indices whose values add up to a target
tags: two-sum, hashmap, arrays, complement, time-complexity, space-tradeoff, coding, basics

**Start here: the concepts**
- **Array**: a fixed-size row of values. Each value has an index (its position, starting at 0).
- **HashMap**: a Java collection that stores key-value pairs. Looking up a key by value takes about the same time however many entries there are (average O(1)). Here the key is a number we have seen and the value is its index.
- **Complement**: for a number `x` and a `target`, the complement is `target - x`. It is the other number we need.
- **Big-O**: a way to describe how work grows as the input size `n` grows. O(n) means work grows in a straight line with n. O(n^2) means doubling the input roughly quadruples the work. O(1) means the work stays flat.
- **Space complexity**: how much extra memory we use. A map that may hold up to n numbers costs O(n) space.

**The live scenario**
A payments service receives a list of transaction amounts in cents. A reconciliation job must find two transactions that add up to a refund amount of exactly 5000 cents. The list can have 100,000 entries, so a slow solution would hurt. The interviewer usually says: "Given an array of integers and a target, return the indices of the two numbers that add up to the target. Assume exactly one solution, and do not use the same element twice."

**What the interviewer is really checking**
Whether you ask clarifying questions first (duplicates, negatives, no answer, return indices or values). Then whether you state the O(n^2) brute force, improve it to O(n) with a HashMap, and explain the time/space trade-off and edge cases such as null, a single element and integer overflow.

**How I answer it**
1. **Clarify and restate.** Input is an `int[] nums` and an `int target`. Output is two different indices `i` and `j` with `nums[i] + nums[j] == target`. I would ask:
   - Is there always exactly one answer? If not, I return an empty array.
   - Can the array have duplicates or negatives? Yes to both, and both must work.
   - May I use the same element twice? No, the indices must differ.
   - Is the array sorted? Assume not.
2. **Brute force.** Try every pair with two nested loops: for each `i`, check every `j > i`. Time is O(n^2) because about n*n/2 pairs are checked. Space is O(1). It is fine for 100 elements and too slow for 100,000 (about 5 billion checks).
3. **Better idea.** Walk through the array once. For each number `x`, ask "have I already seen `target - x`?" A HashMap answers that in O(1). If yes, return that stored index and the current index. If no, store `x -> its index` and move on. It works because every pair (a, b) is found when we reach the later of the two: the earlier one is already in the map. Checking the map before inserting the current number stops us using the same element twice.
4. **Complexity.** Time is O(n): one pass, with O(1) average per map operation. Space is O(n): in the worst case we store almost every number.
5. **Code.**

```java
import java.util.HashMap;
import java.util.Map;

class Solution {
    // Returns {i, j} with nums[i] + nums[j] == target, or an empty array if none.
    static int[] twoSum(int[] nums, int target) {
        if (nums == null || nums.length < 2) return new int[0];
        Map<Integer, Integer> seen = new HashMap<>(); // value -> index
        for (int i = 0; i < nums.length; i++) {
            long need = (long) target - nums[i]; // long avoids int overflow
            if (need >= Integer.MIN_VALUE && need <= Integer.MAX_VALUE) {
                Integer j = seen.get((int) need);
                if (j != null) return new int[] {j, i};
            }
            seen.put(nums[i], i); // put AFTER the check: no element used twice
        }
        return new int[0];
    }

    // O(n^2) reference used only to cross-check the fast version.
    static boolean bruteForceHasAnswer(int[] nums, int target) {
        for (int i = 0; i < nums.length; i++)
            for (int j = i + 1; j < nums.length; j++)
                if ((long) nums[i] + nums[j] == target) return true;
        return false;
    }

    static void expect(boolean cond, String msg) {
        if (!(cond)) throw new AssertionError(msg);
    }

    static void expectPair(int[] nums, int target, int[] r, String name) {
        expect(r.length == 2, name + ": expected 2 indices");
        expect(r[0] != r[1], name + ": same index used twice");
        expect((long) nums[r[0]] + nums[r[1]] == target, name + ": wrong sum");
    }

    public static void main(String[] args) {
        int[] a = {2, 7, 11, 15};
        int[] r = twoSum(a, 9);
        expectPair(a, 9, r, "typical");
        expect(r[0] == 0 && r[1] == 1, "typical indices");

        int[] b = {3, 3};
        r = twoSum(b, 6);
        expect(r[0] == 0 && r[1] == 1, "duplicates");

        int[] c = {3, 2, 4};
        r = twoSum(c, 6);
        expect(r[0] == 1 && r[1] == 2, "must not reuse 3 twice");

        int[] d = {-3, 4, 3, 90};
        expectPair(d, 0, twoSum(d, 0), "negatives");

        expect(twoSum(null, 5).length == 0, "null input");
        expect(twoSum(new int[0], 5).length == 0, "empty input");
        expect(twoSum(new int[] {5}, 5).length == 0, "single element");
        expect(twoSum(new int[] {1, 2, 3}, 10).length == 0, "no answer");

        int[] e = {Integer.MIN_VALUE, 1};
        expect(twoSum(e, Integer.MAX_VALUE).length == 0, "overflow safe");

        // Cross-check against brute force on a large input.
        int n = 20000;
        int[] big = new int[n];
        for (int i = 0; i < n; i++) big[i] = i * 3;
        int target = big[n - 1] + big[n - 2];
        r = twoSum(big, target);
        expectPair(big, target, r, "large");
        expect(!bruteForceHasAnswer(new int[] {1, 2, 3}, 10), "brute force sanity");
        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| Approach | Time | Space | Note |
|---|---|---|---|
| Brute force (two loops) | O(n^2) | O(1) | Simple, fine for tiny inputs, too slow for 100,000 items |
| HashMap complement | O(n) | O(n) | Spends memory to save time |

- **Using the same element twice**: for `[3, 2, 4]` and target 6, inserting before checking would wrongly return `[0, 0]`.
- **Overwriting duplicates**: `[3, 3]` works because we check before we insert.
- **Integer overflow**: `target - nums[i]` can overflow `int`, so I compute it as `long`.
- **Returning values instead of indices**: read the question again.
- **Null or short arrays**: return an empty array (or throw `IllegalArgumentException` if the interviewer prefers) instead of crashing.
- **Boxing cost**: `HashMap<Integer, Integer>` boxes ints into objects, which uses more memory and is slower than primitives. This is acceptable here, and I can mention it.

**Test cases I'd walk through**
- Typical: `[2,7,11,15]`, target 9 -> `[0,1]`.
- Empty or null: `[]` or `null` -> empty array, no exception.
- Single element: `[5]`, target 5 -> empty array, because one number cannot pair with itself.
- Duplicates: `[3,3]`, target 6 -> `[0,1]`.
- Same-element trap: `[3,2,4]`, target 6 -> `[1,2]`, not `[0,0]`.
- Negatives: `[-3,4,3,90]`, target 0 -> `[0,2]`.
- No answer: `[1,2,3]`, target 10 -> empty array.
- Overflow: `[Integer.MIN_VALUE, 1]`, target `Integer.MAX_VALUE` -> empty array, no wrong match.
- Large input: 20,000 elements finish instantly with the map, while brute force would do about 200 million checks.

**Follow-ups to expect**
- *What if the array is sorted?* -> Use two pointers, one at each end. If the sum is too small move the left pointer right; if it is too big move the right pointer left. That is O(n) time and O(1) space.
- *What if there are many valid pairs and I need all of them?* -> Keep the map but do not return early. Store a list of indices per value, and take care to avoid duplicate pairs. The output size can be large, so the cost depends on how many pairs there are.
- *What if the data is too big for memory?* -> Sort externally and use two pointers, or partition the data by hash so that matching numbers land in the same chunk.

**60-second answer**
First I would clarify: do I return indices, can numbers repeat, and what if there is no answer? The brute force checks every pair with two nested loops, which is O(n^2) time and O(1) space. That is too slow for 100,000 items. The better way is a HashMap from number to index. For each number I compute the complement, which is target minus the number, and look it up in the map. If it is there, I return its stored index and the current index. If not, I store the current number and continue. I check before inserting so I never reuse the same element. This is one pass, so time is O(n) and space is O(n), trading memory for speed. I would also handle null or short arrays, duplicates such as `[3,3]`, and use `long` for the subtraction to avoid overflow.

### Q9 [fresher] Find the missing number in an array of 1 to n
tags: arrays, math, xor, sum-formula, overflow, o-n-time, coding, basics

**Start here: the concepts**
- **Array**: a fixed-size row of values. Reading or visiting every element once is called a *single pass*.
- **Big-O**: a way to describe how work grows as the input grows. O(n) means the work grows in step with the array length. O(n^2) means doubling the input roughly quadruples the work. O(1) space means we use a fixed handful of variables, no matter how big the input is.
- **Sum formula**: the numbers 1 to n add up to n*(n+1)/2 (Gauss's formula). If we subtract what the array actually adds up to, the leftover is the missing number.
- **XOR (`^`)**: a bit operation where `a ^ a = 0` and `a ^ 0 = a`, and the order does not matter. If we XOR 1..n together with all array values, every number that appears twice cancels out. Only the missing number is left.
- **Overflow**: an `int` holds at most 2,147,483,647. When a result goes past that, Java wraps around silently to a wrong value, with no exception.

**The live scenario**
A nightly batch file should contain order IDs 1 to n, but one record was lost in transit. You need to find which ID is missing without loading a database or using extra memory. The interviewer usually says: "An array holds n-1 distinct numbers from 1 to n. Find the missing one. Can you do it in O(n) time and O(1) extra space?"

**What the interviewer is really checking**
Whether you ask clarifying questions (distinct? sorted? range?), state a simple brute force first, and then improve it with a clear reason. They also want to see that you know `n*(n+1)/2` can overflow `int` and that you can handle the edge cases (empty array, missing first or last number).

**How I answer it**
1. **Clarify and restate.** Input is an `int[]` of length n-1 with distinct values from 1..n, one missing, in any order. Output is the missing number. I would ask: is it sorted? Can it have duplicates? Can it be null or empty? I assume distinct and unsorted. Null throws `IllegalArgumentException`. An empty array means n = 1, so the answer is 1.
2. **Brute force.** For each candidate from 1 to n, scan the array to see if it is there. That is O(n^2) time and O(1) space. A better variant uses a `boolean[]` or `HashSet` of seen values, which is O(n) time but O(n) space. Sorting first is O(n log n).
3. **Better idea.** The full set 1..n has a known total, n*(n+1)/2. The array holds the same numbers minus one, so `expected - actual` is exactly the missing number. I only need one running total. XOR works the same way: pairs cancel, and the missing value is left. XOR cannot overflow, which makes it the safer choice.
4. **Complexity.** Time is O(n), one pass. Space is O(1), because only a few variables are used.
5. **Code.**

```java
import java.util.*;

class Solution {
    // Sum formula. Use long: n*(n+1) overflows int once n is above about 46,340.
    static int missingBySum(int[] a) {
        if (a == null) throw new IllegalArgumentException("array is null");
        long n = a.length + 1L;
        long expected = n * (n + 1) / 2;
        long actual = 0;
        for (int x : a) actual += x;
        return (int) (expected - actual);
    }

    // XOR: equal values cancel, so only the missing number survives. No overflow possible.
    static int missingByXor(int[] a) {
        if (a == null) throw new IllegalArgumentException("array is null");
        int x = 0;
        for (int i = 1; i <= a.length + 1; i++) x ^= i;
        for (int v : a) x ^= v;
        return x;
    }

    // Brute force, O(n^2): kept to cross-check the fast versions.
    static int missingBruteForce(int[] a) {
        for (int c = 1; c <= a.length + 1; c++) {
            boolean found = false;
            for (int v : a) if (v == c) { found = true; break; }
            if (!found) return c;
        }
        throw new IllegalStateException("no missing number");
    }

    static void check(boolean cond, String msg) {
        if (!(cond)) throw new AssertionError(msg);
    }

    static void checkAll(int[] a, int expected, String name) {
        check(missingBySum(a) == expected, name + " sum");
        check(missingByXor(a) == expected, name + " xor");
        check(missingBruteForce(a) == expected, name + " brute");
    }

    public static void main(String[] args) {
        checkAll(new int[]{1, 2, 4, 5}, 3, "middle");
        checkAll(new int[]{5, 3, 1, 2}, 4, "unsorted");
        checkAll(new int[]{2, 3, 4}, 1, "first missing");
        checkAll(new int[]{1, 2, 3}, 4, "last missing");
        checkAll(new int[]{}, 1, "empty means n=1");
        checkAll(new int[]{2}, 1, "single, 1 missing");
        checkAll(new int[]{1}, 2, "single, 2 missing");

        // Large input: n*(n+1)/2 is about 2e10, far past int range.
        int n = 200_000, missing = 123_456;
        int[] big = new int[n - 1];
        int k = 0;
        for (int v = 1; v <= n; v++) if (v != missing) big[k++] = v;
        check(missingBySum(big) == missing, "big sum");
        check(missingByXor(big) == missing, "big xor");

        try {
            missingBySum(null);
            throw new AssertionError("null should throw");
        } catch (IllegalArgumentException expected) {
            // expected path
        }
        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| Approach | Time | Space | Note |
|---|---|---|---|
| Nested loops | O(n^2) | O(1) | Fine only for tiny input |
| HashSet / boolean[] | O(n) | O(n) | Easy to explain, uses extra memory |
| Sort, then compare | O(n log n) | O(1) to O(n) | Mutates the input or copies it |
| Sum formula (long) | O(n) | O(1) | Simple; needs `long` |
| XOR | O(n) | O(1) | No overflow; less obvious to read |

Common mistakes:
- Computing `n * (n + 1) / 2` in `int`. The overflow is silent and gives a wrong answer for large n. Cast to `long` before multiplying: `(long) n * (n + 1) / 2`.
- Taking n as `a.length` instead of `a.length + 1`. Off-by-one errors are the most common bug here.
- Forgetting the null and empty cases.
- Assuming the array is sorted, or has no duplicates, without asking.

**Test cases I'd walk through**
- Typical `{1,2,4,5}` returns 3 (expected sum 15, actual 12).
- Unsorted `{5,3,1,2}` returns 4, so order does not matter.
- Missing first `{2,3,4}` returns 1. Missing last `{1,2,3}` returns 4.
- Empty `{}` returns 1, because n = 1.
- Single element: `{2}` returns 1 and `{1}` returns 2.
- Null throws `IllegalArgumentException` (state this choice aloud).
- Duplicates are outside the contract. Say so, and mention the sum would give a wrong answer.
- Large input with n = 200,000 and 123,456 missing returns 123,456. With an `int` sum this would overflow.

**Follow-ups to expect**
- *Why does the int version overflow, and at what n?* -> n*(n+1) exceeds 2,147,483,647 once n is above about 46,340. Use `long`, or use XOR, which never overflows.
- *What if the array is sorted?* -> Use binary search on "does a[i] equal i+1?". That is O(log n) time.
- *What if two numbers are missing?* -> Use the sum and the sum of squares to get two equations. Or XOR everything, split the numbers by one set bit of the result, and XOR each group. It is still O(n) time and O(1) space.

**60-second answer**
"First I would confirm the input: n-1 distinct numbers from 1 to n, unsorted, one missing. I would also ask how to handle null. The brute force checks each number from 1 to n against the whole array, which is O(n^2). The better idea is that 1 to n always adds up to n*(n+1)/2. So I subtract the array's sum from that, and the difference is the missing number. In Java I would compute this in `long`, because `n*(n+1)` overflows `int` once n passes about 46,000. An alternative is XOR of 1..n with every array value, where pairs cancel and the missing number is left, with no overflow risk. Both are one pass, so O(n) time and O(1) space. I would test the missing-first, missing-last, empty, single-element and large-n cases."

### Q10 [mid] Maximum subarray sum (Kadane's algorithm)
tags: array, subarray, kadane, dynamic-programming, single-pass, coding, basics

**Start here: the concepts**
- **Subarray**: a contiguous slice of the array. `[4, -1, 2]` is a subarray of `[1, 4, -1, 2]`, but `[1, 2]` is not (that would be a subsequence).
- **Kadane's algorithm**: one left-to-right pass that tracks two numbers: the best sum of a subarray *ending at the current index*, and the best sum seen anywhere so far.
- **Dynamic programming (here)**: each answer is built from the previous one. "Best ending at i" depends only on "best ending at i-1", so we keep one variable instead of a table.
- **Big-O**: how the work grows with input size `n`. O(n) means roughly one step per element. O(n^2) means work grows with the square, so 10x more data is about 100x more work. O(1) space means memory does not grow with `n`.
- **Overflow**: an `int` holds at most about 2.1 billion. Summing many large ints can exceed that and wrap to a wrong negative number, so we accumulate in a `long`.

**The live scenario**
A payments dashboard stores net revenue change per minute for the last day (1,440 values, or millions per month across merchants). Product asks: "Which stretch of consecutive minutes had the best total gain?" The interviewer phrases it as: "Given an integer array, find the contiguous subarray with the largest sum and return that sum." They often add: "What if every number is negative?"

**What the interviewer is really checking**
Whether you clarify (empty array? all negatives? may the subarray be empty?), start with a simple O(n^2) solution, then reach the O(n) single pass and explain why it is correct. They also check that you handle all-negative input and overflow, and that you test edge cases.

**How I answer it**
1. **Clarify and restate.** Input is `int[] nums`, output is the largest sum of a non-empty contiguous subarray. I ask: can the array be empty or null? (I will throw `IllegalArgumentException`.) Must the subarray be non-empty? (Yes, so for all negatives the answer is the least negative number, not 0.) Can sums exceed `int`? (Possibly, so I return `long`.)
2. **Brute force.** Try every start `i` and extend the end `j`, keeping a running sum. That is O(n^2) time and O(1) space. Recomputing each sum from scratch would be O(n^3), which I mention only to dismiss it.
3. **Better idea.** At each element I have two choices: extend the best subarray that ended at the previous index, or start fresh at this element. If the running sum before this element is negative, it can only hurt, so I drop it and start fresh. In code: `cur = max(x, cur + x)`, then `best = max(best, cur)`. Initialising `best` and `cur` with the first element (not 0) is what makes the all-negative case work.
4. **Complexity.** Time O(n), one pass. Space O(1), two `long` variables.
5. **The code:**

```java
import java.util.Random;

class Solution {
    // Kadane: best sum of a non-empty contiguous subarray.
    static long maxSubarraySum(int[] nums) {
        if (nums == null || nums.length == 0) {
            throw new IllegalArgumentException("nums must be non-empty");
        }
        long best = nums[0];
        long cur = nums[0]; // best sum of a subarray ending at index i
        for (int i = 1; i < nums.length; i++) {
            cur = Math.max(nums[i], cur + nums[i]); // extend or restart
            best = Math.max(best, cur);
        }
        return best;
    }

    // O(n^2) reference used only to cross-check the fast version.
    static long bruteForce(int[] nums) {
        long best = Long.MIN_VALUE;
        for (int i = 0; i < nums.length; i++) {
            long sum = 0;
            for (int j = i; j < nums.length; j++) {
                sum += nums[j];
                best = Math.max(best, sum);
            }
        }
        return best;
    }

    static void expect(long actual, long expected, String name) {
        if (!(actual == expected)) {
            throw new AssertionError(name + ": expected " + expected + " but got " + actual);
        }
    }

    static boolean throwsIae(int[] input) {
        try {
            maxSubarraySum(input);
            return false;
        } catch (IllegalArgumentException e) {
            return true;
        }
    }

    public static void main(String[] args) {
        expect(maxSubarraySum(new int[]{-2, 1, -3, 4, -1, 2, 1, -5, 4}), 6, "classic");
        expect(maxSubarraySum(new int[]{-3, -1, -2}), -1, "all negative");
        expect(maxSubarraySum(new int[]{5}), 5, "single");
        expect(maxSubarraySum(new int[]{-5}), -5, "single negative");
        expect(maxSubarraySum(new int[]{1, 2, 3}), 6, "all positive");
        expect(maxSubarraySum(new int[]{0, 0, 0}), 0, "zeros");
        expect(maxSubarraySum(new int[]{Integer.MAX_VALUE, Integer.MAX_VALUE}),
                4_294_967_294L, "overflow safe");
        if (!throwsIae(new int[0])) throw new AssertionError("empty must throw");
        if (!throwsIae(null)) throw new AssertionError("null must throw");

        Random rnd = new Random(42);
        for (int t = 0; t < 1000; t++) {
            int[] a = new int[1 + rnd.nextInt(20)];
            for (int i = 0; i < a.length; i++) a[i] = rnd.nextInt(101) - 50;
            expect(maxSubarraySum(a), bruteForce(a), "random #" + t);
        }
        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| Approach | Time | Space | Note |
|---|---|---|---|
| Naive (all slices, re-sum) | O(n^3) | O(1) | Only to explain the problem |
| Brute force with running sum | O(n^2) | O(1) | Fine for small n; too slow at 1M+ |
| Kadane | O(n) | O(1) | Single pass, works on streams |

Common mistakes:
- Initialising `best = 0`, which returns 0 for all-negative input. Use the first element, or `Long.MIN_VALUE` / `Integer.MIN_VALUE`.
- Using `int` for the sum, which silently wraps on large inputs. Use `long`.
- Not deciding what empty input means. State your choice (throw, or return 0) out loud.
- Using `Integer.MIN_VALUE` as the initial value with an `int` accumulator, then adding to it, which overflows.
- Using streams here. A plain loop is clearer, allocation-free and faster. Kadane's carried state does not fit `reduce` naturally.

**Test cases I'd walk through**
- Typical `[-2,1,-3,4,-1,2,1,-5,4]` returns 6 (subarray `[4,-1,2,1]`).
- All negative `[-3,-1,-2]` returns -1, the largest single element.
- Single element `[5]` returns 5, and `[-5]` returns -5.
- Empty or `null` throws `IllegalArgumentException` (or returns 0 if the interviewer defines it so).
- Duplicates and zeros `[0,0,0]` returns 0. Repeated values like `[2,2,2]` return 6.
- Large values `[MAX_INT, MAX_INT]` returns 4294967294 thanks to `long`.
- Large input (say 10 million elements) finishes in milliseconds. The O(n^2) version would not.
- A random comparison against brute force catches off-by-one or reset bugs.

**Follow-ups to expect**
- *How do you return the start and end indices too?* -> Track a `tempStart`. When you restart (`nums[i] > cur + nums[i]`), set `tempStart = i`. When `cur > best`, set `best`, `start = tempStart` and `end = i`.
- *What if the array is circular?* -> Answer = max(Kadane result, total sum - minimum subarray sum). Handle the all-negative case separately, because the minimum subarray would be the whole array and the "wrap" result would be an empty subarray.
- *What if the data arrives as a stream (for example Kafka events)?* -> Kadane keeps only two numbers, so it works online with O(1) memory. For a "best window per hour" requirement, reset the state at each window boundary.

**60-second answer**
"First I'd confirm the subarray must be contiguous and non-empty, and ask what to do for empty input. I'd say the brute force is trying every start and end with a running sum, which is O(n^2) time and O(1) space. The better idea is Kadane's algorithm. Going left to right, at each element I either extend the best subarray ending at the previous element or start fresh at this one, whichever is larger, and I keep a global maximum. If the running sum is negative, carrying it forward can only hurt, so I drop it. I initialise with the first element rather than 0, so all-negative arrays return the largest single element. I'd use a `long` accumulator to avoid int overflow. The result is O(n) time and O(1) space. I'd test it on the classic example, all negatives, a single element and empty input, and compare it against brute force on random arrays."

### Q11 [fresher] Move all zeroes to the end of an array, keeping order
tags: arrays, two-pointers, in-place, stable-order, complexity, coding, basics

**Start here: the concepts**
- **Array**: a fixed-size row of values you can read or write by position (index) in constant time.
- **Two pointers**: two index variables walking the same array. Here, `read` looks at every element, and `write` marks where the next non-zero value must go.
- **In place**: we change the given array itself and do not allocate a second array of size n.
- **Stable**: non-zero values keep their original relative order, so `[3, 0, 5]` becomes `[3, 5, 0]`, never `[5, 3, 0]`.
- **Big-O**: a way to describe how work grows as the input size n grows. O(n) means work grows in a straight line with n. O(n^2) means doubling n makes the work about four times bigger. O(1) extra space means memory use does not grow with n.

**The live scenario**
A batch job receives a fixed-size buffer of 1,000 slot IDs, where `0` means "empty slot". Before sending it downstream, you compact it so all real IDs come first, in their original order, and the empty slots sit at the end. Memory is tight, so you cannot copy the buffer.

The interviewer usually says: "Given an int array, move all zeroes to the end, keep the order of the other elements, do it in place."

**What the interviewer is really checking**
Whether you ask clarifying questions (null, empty, negatives, order), give a simple brute force first, and then improve it to one pass with O(1) extra space. They also want to hear complexity and edge cases without being prompted.

**How I answer it**
1. **Clarify and restate.**
   - Input is `int[]`, output is the same array modified.
   - I'd ask: must order of non-zeros be kept? (yes)
   - Can I use extra memory? (no, in place)
   - Can the array be null or empty? (handle both safely)
   - Negatives count as non-zero.
2. **Brute force.**
   - Option A: every time I find a zero, shift everything after it one step left and put a zero at the end. That is O(n^2) time, O(1) space.
   - Option B: copy the non-zeros into a new array, then pad with zeros. That is O(n) time but O(n) space, which breaks "in place".
3. **Better idea.**
   - Keep a `write` pointer for the next slot a non-zero value should occupy.
   - Walk `read` from left to right. When `a[read]` is non-zero, swap it with `a[write]` and move `write` forward.
   - Invariant: everything before `write` is non-zero and in original order, and everything between `write` and `read` is zero.
   - Because of that, the swap only ever moves a zero backwards past non-zeros. Order is kept and no second array is needed.
   - I skip the swap when `read == write`, which saves useless writes on arrays with no leading zeros.
4. **Complexity.** Time O(n), one pass. Extra space O(1).
5. **Code.**

```java
import java.util.Arrays;

class Solution {
    // Moves zeroes to the end in place; non-zero values keep their order.
    static void moveZeroes(int[] a) {
        if (a == null) return;
        int write = 0; // next slot that should receive a non-zero value
        for (int read = 0; read < a.length; read++) {
            if (a[read] != 0) {
                if (read != write) { // a[write] is a zero here
                    int tmp = a[write];
                    a[write] = a[read];
                    a[read] = tmp;
                }
                write++;
            }
        }
    }

    static void check(String name, int[] input, int[] expected) {
        moveZeroes(input);
        if (!Arrays.equals(input, expected)) {
            throw new AssertionError(name + ": got " + Arrays.toString(input)
                    + " expected " + Arrays.toString(expected));
        }
    }

    public static void main(String[] args) {
        check("typical", new int[]{0, 1, 0, 3, 12}, new int[]{1, 3, 12, 0, 0});
        check("empty", new int[]{}, new int[]{});
        check("single zero", new int[]{0}, new int[]{0});
        check("single non-zero", new int[]{7}, new int[]{7});
        check("all zeros", new int[]{0, 0, 0}, new int[]{0, 0, 0});
        check("no zeros", new int[]{4, 5, 6}, new int[]{4, 5, 6});
        check("negatives and duplicates", new int[]{0, -2, 0, -2, 9, 0},
                new int[]{-2, -2, 9, 0, 0, 0});
        check("zeros at end already", new int[]{1, 2, 0, 0}, new int[]{1, 2, 0, 0});

        moveZeroes(null); // must not throw

        int n = 1_000_000;
        int[] big = new int[n];
        for (int i = 0; i < n; i++) big[i] = (i % 2 == 0) ? 0 : i;
        moveZeroes(big);
        for (int i = 0; i < n; i++) {
            int expected = (i < n / 2) ? 2 * i + 1 : 0; // i-th odd number, then zeros
            if (big[i] != expected) throw new AssertionError("large input at index " + i);
        }
        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| Approach | Time | Extra space | Notes |
|---|---|---|---|
| Shift on every zero | O(n^2) | O(1) | Too slow for large arrays |
| Copy to new array, pad zeros | O(n) | O(n) | Simple, but not in place |
| Two pointers with swap (final) | O(n) | O(1) | One pass, stable, in place |

Common mistakes:
- Forgetting null or empty input and getting a `NullPointerException`.
- Sorting or partitioning the array, which breaks the order of non-zeros (and sorting is O(n log n)).
- Treating negative numbers as "empty" instead of only `0`.
- Returning a new array when the question says in place.
- Swapping in the wrong direction, or advancing `write` on zeros.

**Test cases I'd walk through**
- **Typical** `[0,1,0,3,12]` returns `[1,3,12,0,0]`.
- **Null** returns without error and changes nothing. **Empty** `[]` stays `[]`.
- **Single element**: `[0]` stays `[0]` and `[7]` stays `[7]`.
- **All zeros or no zeros**: array is unchanged, and with no zeros no swaps happen because `read == write`.
- **Duplicates and negatives** `[0,-2,0,-2,9,0]` returns `[-2,-2,9,0,0,0]`. Equal values stay in original order.
- **Large input**: 1,000,000 elements finish in one linear pass with no extra array.

**Follow-ups to expect**
- *Can you reduce the number of writes?* -> The `read != write` check already skips swaps for the leading non-zero block. Another version copies each non-zero to `a[write++]`, then fills the rest with zeros, giving at most one write per element.
- *How would you move zeroes to the front instead?* -> Mirror the idea: walk from the right with `read` and `write` both starting at the last index, and move `write` backwards.
- *What if it is a `List<Integer>` instead of an array?* -> Same two-pointer logic with `Collections.swap`. On a `LinkedList`, index access is O(n), so use an iterator or rebuild the list.

**60-second answer**
"First I'd confirm the array is `int[]`, the work must be in place, the order of non-zeros must be kept, and null or empty input should be handled safely. The brute force shifts all later elements left every time I see a zero, which is O(n^2), or copies into a new array, which costs O(n) extra space. A better way is two pointers. `read` scans the array once, and `write` marks the next slot for a non-zero value. Each time `read` finds a non-zero, I swap it into `write` and move `write` forward. This keeps everything before `write` non-zero and in original order, so the result is stable. It runs in O(n) time with O(1) extra space, and I skip the swap when both pointers are on the same index. I'd test with empty, null, all zeros, no zeros, and negatives with duplicates."

### Q12 [fresher] Merge two sorted arrays into one sorted array
tags: arrays, two-pointers, merge, sorting, in-place, complexity, coding, basics

**Start here: the concepts**
- **Sorted array:** values are in non-decreasing order, so the smallest unused value of each array is always at its front.
- **Two pointers:** two index variables, one per array. Each marks the next unused element. We compare the two elements, take the smaller one, and move only that pointer.
- **Big-O:** a way to describe how the work grows as the input grows. O(m+n) means the work grows in a straight line with the total number of elements. O(n log n) grows a bit faster because of sorting.
- **Space complexity:** the extra memory we need beyond the input. "O(1) extra" means a fixed handful of variables.
- **Stable merge:** equal values keep their original order, with ties taken from the first array.

**The live scenario**
Two services each return a page of order IDs or timestamps, already sorted. Your service must combine them into one sorted list before sending the response. The same step is the "merge" half of merge sort. The interviewer usually says: *"Given two sorted integer arrays, return one sorted array. Can you do it without sorting again? Can you do it without extra space?"*

**What the interviewer is really checking**
Do you ask clarifying questions, state the simple solution (concatenate and sort), and then use the "already sorted" property to reach O(m+n)? Do you handle empty and null inputs and duplicates, and can you explain the in-place variant (filling from the back)?

**How I answer it**
1. **Clarify and restate.**
   - Input: two `int[]` arrays, each sorted ascending. Output: one sorted `int[]` containing all elements.
   - I would ask whether duplicates are allowed (yes, keep them), whether the inputs can be null or empty (I treat null as empty), and whether I may allocate a new array or must merge in place.
2. **Brute force.** Copy both arrays into one array of size m+n and call `Arrays.sort`. Time is O((m+n) log(m+n)), space is O(m+n). It is correct but ignores the fact that the inputs are already sorted.
3. **Better idea.**
   - Put one pointer `i` at the start of `a` and one pointer `j` at the start of `b`.
   - The smallest remaining value overall must be either `a[i]` or `b[j]`, because each array is sorted. Copy the smaller one into the output and advance that pointer.
   - When one array runs out, copy the rest of the other, since it is already sorted.
   - Every element is copied exactly once, so there is no re-sorting.
   - **In-place variant:** if `a` has m real values plus n empty slots at the end (as in LeetCode 88), fill from the back. Compare the largest remaining values and write the larger at index `m+n-1`, moving left. The writes never overwrite unread values of `a`, so no extra array is needed.
4. **Complexity.**
   - New-array merge: time O(m+n), space O(m+n) for the output.
   - In-place merge: time O(m+n), extra space O(1).
5. **Code.**

```java
import java.util.Arrays;

class Solution {
    // Returns a new sorted array; null is treated as empty.
    static int[] merge(int[] a, int[] b) {
        if (a == null) a = new int[0];
        if (b == null) b = new int[0];
        int[] out = new int[a.length + b.length];
        int i = 0, j = 0, k = 0;
        while (i < a.length && j < b.length) {
            // <= takes ties from the first array, so the merge is stable
            if (a[i] <= b[j]) out[k++] = a[i++];
            else out[k++] = b[j++];
        }
        while (i < a.length) out[k++] = a[i++];
        while (j < b.length) out[k++] = b[j++];
        return out;
    }

    // a holds m real values followed by n free slots; fill from the back.
    static void mergeInPlace(int[] a, int m, int[] b, int n) {
        int i = m - 1, j = n - 1, k = m + n - 1;
        while (j >= 0) { // when b is used up, the rest of a is already in place
            if (i >= 0 && a[i] > b[j]) a[k--] = a[i--];
            else a[k--] = b[j--];
        }
    }

    private static void check(boolean cond, String msg) {
        if (!(cond)) throw new AssertionError(msg);
    }

    public static void main(String[] args) {
        // typical
        check(Arrays.equals(merge(new int[]{1, 3, 5}, new int[]{2, 4, 6}),
                new int[]{1, 2, 3, 4, 5, 6}), "typical");
        // empty and null
        check(Arrays.equals(merge(new int[]{}, new int[]{1, 2}), new int[]{1, 2}), "empty a");
        check(merge(new int[]{}, new int[]{}).length == 0, "both empty");
        check(Arrays.equals(merge(null, new int[]{7}), new int[]{7}), "null a");
        // single elements and duplicates
        check(Arrays.equals(merge(new int[]{2}, new int[]{1}), new int[]{1, 2}), "single");
        check(Arrays.equals(merge(new int[]{1, 2, 2}, new int[]{2, 2, 3}),
                new int[]{1, 2, 2, 2, 2, 3}), "duplicates");
        // extreme values: comparison, not subtraction, so no overflow
        check(Arrays.equals(merge(new int[]{Integer.MIN_VALUE, 0}, new int[]{5, Integer.MAX_VALUE}),
                new int[]{Integer.MIN_VALUE, 0, 5, Integer.MAX_VALUE}), "extremes");
        // in-place variant
        int[] x = {4, 5, 6, 0, 0, 0};
        mergeInPlace(x, 3, new int[]{1, 2, 3}, 3);
        check(Arrays.equals(x, new int[]{1, 2, 3, 4, 5, 6}), "in place");
        int[] y = {0};
        mergeInPlace(y, 0, new int[]{9}, 1);
        check(Arrays.equals(y, new int[]{9}), "in place empty a");
        // large input compared with the brute-force answer
        int n = 100_000;
        int[] p = new int[n], q = new int[n];
        for (int t = 0; t < n; t++) { p[t] = t * 2; q[t] = t * 2 + 1; }
        int[] expected = new int[2 * n];
        System.arraycopy(p, 0, expected, 0, n);
        System.arraycopy(q, 0, expected, n, n);
        Arrays.sort(expected);
        check(Arrays.equals(merge(p, q), expected), "large");
        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| Approach | Time | Extra space | Note |
|---|---|---|---|
| Concatenate + `Arrays.sort` | O((m+n) log(m+n)) | O(m+n) | Simple, but wastes the sorted property |
| Two-pointer merge, new array | O(m+n) | O(m+n) | Clean, easy to get right |
| In-place from the back | O(m+n) | O(1) | Needs spare room at the end of `a` |

- Forgetting to copy the leftovers after one array runs out.
- Merging in place from the front, which overwrites values of `a` you have not read yet.
- Using `a[i] - b[j]` to compare. It can overflow with extreme ints, so compare with `<=`.
- Using `<` instead of `<=`, which still gives sorted output but breaks stability for objects.
- Not handling null, which causes a `NullPointerException`.

**Test cases I'd walk through**
- Typical: `[1,3,5]` and `[2,4,6]` give `[1,2,3,4,5,6]`.
- Empty or null: `[]` and `[1,2]` give `[1,2]`. Both empty give `[]`. Null is treated as empty.
- Single element: `[2]` and `[1]` give `[1,2]`.
- Duplicates: `[1,2,2]` and `[2,2,3]` give `[1,2,2,2,2,3]`, with nothing dropped.
- Extreme values: `Integer.MIN_VALUE` and `Integer.MAX_VALUE` stay in the right order.
- Large input: 100,000 elements per array runs in a single pass, and the result matches the brute-force answer.

**Follow-ups to expect**
- *How would you merge k sorted arrays?* -> Use a min-heap (`PriorityQueue`) holding the current head of each array. Time is O(N log k) for N total elements, space is O(k) plus the output.
- *Why fill from the back in the in-place version?* -> The free space is at the end, so writing the largest values there never overwrites an unread element of `a`. Filling from the front would.
- *What if one array is much smaller than the other?* -> The linear merge still works. If the small array has m elements and the large one n, you can binary-search the position of each small element and use `System.arraycopy` for the blocks in between, giving about O(m log n) comparisons.

**60-second answer**
"First I would confirm both arrays are sorted ascending, that duplicates are kept, and that null or empty inputs should still work. The simple solution is to concatenate the arrays and sort, which costs O((m+n) log(m+n)). But the inputs are already sorted, so I use two pointers, one on each array. I compare the two current elements, copy the smaller into the output, and advance that pointer. When one array runs out I copy the rest of the other. Each element is copied once, so time is O(m+n) and space is O(m+n) for the output. If the first array has spare room at the end, I can merge in place by filling from the back with the larger value each time. That keeps the time at O(m+n) and the extra space at O(1)."

### Q13 [fresher] Binary search on a sorted array
tags: binary-search, arrays, sorting, two-pointers, overflow, first-last-occurrence, coding, basics

**Start here: the concepts**
- **Sorted array**: values are in order (smallest to largest), so one comparison tells us which side of the array can be thrown away.
- **Binary search**: look at the middle element. If it is the target, stop. If the target is bigger, discard the left half. If smaller, discard the right half. Repeat on what is left.
- **Big-O**: a way to describe how work grows as input size `n` grows. O(n) means "look at every element, worst case". O(log n) means "each step halves the problem". For 1,000,000 elements that is about 20 steps, not 1,000,000.
- **Iterative**: done with a `while` loop and two index variables (`lo`, `hi`), so there is no recursion and no extra stack memory.
- **Integer overflow**: a Java `int` tops out at 2,147,483,647. Adding two large ints wraps to a negative number without any error.

**The live scenario**
Your order service keeps a sorted `long[]` of 5 million order IDs loaded from a nightly file. Each request must check "have we already seen this ID?" within a millisecond, at about 2,000 requests per second. Scanning the array each time means up to 5 million comparisons per request, which is far too slow. The interviewer usually asks: "Given a sorted array and a target, return its index or -1." Then they follow up with: "What if there are duplicates? Return the first (or last) index."

**What the interviewer is really checking**
Whether you ask clarifying questions (sorted? duplicates? null or empty?), start with the simple linear scan, and then explain why sorting lets you halve the range. They also want to see correct loop boundaries (`lo <= hi`), the overflow-safe midpoint, and that you can adapt the search to find the first or last occurrence.

**How I answer it**
1. **Clarify and restate.** Input: an `int[]` sorted ascending and a `target`. Output: an index of the target, or -1 if absent. I would ask: Is it ascending? Can there be duplicates, and which index do you want? Can the array be null or empty? (I assume I return -1 for null or empty.)
2. **Brute force.** Loop from index 0 to the end and compare each element with the target. This is O(n) time and O(1) space. It works but ignores the fact that the array is sorted.
3. **Better idea.** Keep a window `[lo, hi]` that could still contain the target. Compare the middle element with the target. If the middle is too small, the target cannot be at or left of the middle, so I set `lo = mid + 1`. If it is too big, I set `hi = mid - 1`. Each step halves the window, and I stop when the window is empty (`lo > hi`). For the midpoint I use `lo + (hi - lo) / 2`, because `(lo + hi) / 2` can overflow when both are large. For first/last occurrence, when I find the target I do not stop. I record the index and keep searching left (for first) or right (for last).
4. **Complexity.** Time is O(log n) and space is O(1), because it is iterative with a few int variables.
5. **The code.**

```java
class Solution {
    // Classic binary search: index of target, or -1.
    static int search(int[] a, int target) {
        if (a == null) return -1;
        int lo = 0, hi = a.length - 1;
        while (lo <= hi) {
            int mid = lo + (hi - lo) / 2;      // overflow-safe midpoint
            if (a[mid] == target) return mid;
            if (a[mid] < target) lo = mid + 1; else hi = mid - 1;
        }
        return -1;
    }

    static int first(int[] a, int target) { return bound(a, target, true); }
    static int last(int[] a, int target) { return bound(a, target, false); }

    // On a match, remember it and keep shrinking toward the wanted side.
    private static int bound(int[] a, int target, boolean wantFirst) {
        if (a == null) return -1;
        int lo = 0, hi = a.length - 1, ans = -1;
        while (lo <= hi) {
            int mid = lo + (hi - lo) / 2;
            if (a[mid] == target) {
                ans = mid;
                if (wantFirst) hi = mid - 1; else lo = mid + 1;
            } else if (a[mid] < target) lo = mid + 1;
            else hi = mid - 1;
        }
        return ans;
    }

    static void check(boolean cond, String msg) {
        if (!(cond)) throw new AssertionError(msg);
    }

    public static void main(String[] args) {
        int[] a = {1, 3, 5, 7, 9, 11};
        check(search(a, 7) == 3, "typical hit");
        check(search(a, 1) == 0 && search(a, 11) == 5, "both ends");
        check(search(a, 4) == -1 && search(a, 0) == -1 && search(a, 99) == -1, "misses");
        check(search(new int[0], 5) == -1, "empty");
        check(search(null, 5) == -1, "null");
        check(search(new int[]{5}, 5) == 0 && search(new int[]{5}, 6) == -1, "single");

        int[] d = {2, 4, 4, 4, 4, 8, 8};
        check(first(d, 4) == 1 && last(d, 4) == 4, "duplicates 4");
        check(first(d, 8) == 5 && last(d, 8) == 6, "duplicates 8");
        check(first(d, 5) == -1 && last(d, 5) == -1, "dup miss");
        check(first(new int[]{3, 3, 3}, 3) == 0 && last(new int[]{3, 3, 3}, 3) == 2, "all same");

        int[] big = new int[1_000_000];
        for (int i = 0; i < big.length; i++) big[i] = i * 2;   // even numbers only
        check(search(big, 999_998) == 499_999, "large hit");
        check(search(big, 999_999) == -1, "large miss");

        int lo = 2_000_000_000, hi = 2_100_000_000;            // overflow demo
        check((lo + hi) / 2 < 0, "naive midpoint overflows");
        check(lo + (hi - lo) / 2 == 2_050_000_000, "safe midpoint is correct");
        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| Approach | Time | Space | Note |
|---|---|---|---|
| Linear scan | O(n) | O(1) | Works on unsorted data, simple, fine for tiny arrays |
| Binary search | O(log n) | O(1) | Needs sorted data; sorting first costs O(n log n) |
| HashSet lookup | O(1) average | O(n) | Faster per lookup, but uses extra memory and gives no ordering or first/last |

- **Overflow**: `(lo + hi) / 2` can go negative on huge arrays. Use `lo + (hi - lo) / 2`. The JDK itself uses `(lo + hi) >>> 1`.
- **Off-by-one bugs**: using `lo < hi` skips the last candidate. Setting `lo = mid` instead of `mid + 1` can loop forever.
- **Unsorted input**: binary search returns wrong answers silently, with no exception. Confirm the data is sorted.
- **Duplicates**: the plain version returns *any* matching index, not necessarily the first. `Arrays.binarySearch` behaves the same way.
- **Monitoring in a real service**: the real risk is a stale or unsorted data file. I would log the array size and a sorted-check at load time, and alert if the check fails or if lookup latency (p99) rises.

**Test cases I'd walk through**
- Typical: `{1,3,5,7,9,11}`, target 7 returns 3.
- Both ends: target 1 returns 0 and target 11 returns 5, which proves boundaries are handled.
- Not found: targets 4, 0 and 99 return -1 (in the middle, below the minimum, above the maximum).
- Empty array or null: returns -1, with no exception.
- Single element: `{5}` with target 5 returns 0, and with target 6 returns -1.
- Duplicates: `{2,4,4,4,4,8,8}`, target 4 gives first = 1 and last = 4. Target 5 gives -1 for both.
- All same: `{3,3,3}` gives first = 0 and last = 2.
- Large: 1,000,000 even numbers, target 999,998 returns 499,999 in about 20 steps. Target 999,999 returns -1.
- Overflow demo: `lo = 2,000,000,000` and `hi = 2,100,000,000`. The naive midpoint is negative, while the safe one is 2,050,000,000.

**Follow-ups to expect**
- *Why is `(lo + hi) / 2` a bug?* -> The sum can exceed `Integer.MAX_VALUE` and wrap to a negative number, giving a negative index. Use `lo + (hi - lo) / 2` or `(lo + hi) >>> 1`.
- *How do you find the first occurrence with duplicates?* -> On a match, save the index and keep searching the left half (`hi = mid - 1`). For the last occurrence, search the right half. The count of a value is `last - first + 1`.
- *Can you do it recursively, and which is better?* -> Yes, but the iterative version uses O(1) space, while recursion uses O(log n) stack space. Iterative is preferred.
- *What if the array is rotated, or you only have a sorted `List`?* -> A rotated array needs an extra check of which half is sorted, and is still O(log n). For lists, use `Collections.binarySearch`, but only with `ArrayList` (random access). On a `LinkedList` it is slow.

**60-second answer**
"First I'd confirm the array is sorted ascending and ask about duplicates and null or empty input. The brute force is a linear scan, which is O(n). Since the data is sorted, I can do better. I keep two indexes, `lo` and `hi`, and look at the middle element. If it's smaller than the target I discard the left half, and if it's bigger I discard the right half, so each step halves the search space. That gives O(log n) time and O(1) space, because it is iterative. I compute the middle as `lo + (hi - lo) / 2` to avoid integer overflow. For the first or last occurrence, when I find the target I record the index and keep searching left or right instead of returning. I'd test it with empty, single-element, missing, duplicate and large inputs."

### Q14 [mid] Rotate an array by k positions
tags: arrays, in-place, reversal, modulo, two-pointers, coding, basics

**Start here: the concepts**
- **Array rotation**: moving every element k places to the right (the last k elements wrap to the front). `[1,2,3,4,5,6,7]` rotated by 3 becomes `[5,6,7,1,2,3,4]`.
- **In-place**: the result is written into the same array, with no second array of size n. Extra memory stays constant.
- **Two pointers**: one index starts at the left end and one at the right end. They swap and move towards each other. A reversal is exactly this.
- **Modulo (`%`)**: the remainder after division. Rotating by n positions gives the same array back, so only `k % n` matters. In Java, `-1 % 5` is `-1`, not `4`, so negative k needs care.
- **Big-O**: how work or memory grows with input size. O(n) means time grows in step with the array length. O(1) space means memory does not grow.

**The live scenario**
You keep a fixed-size ring of the last 1,000 request latencies for a dashboard, or you shift a time-ordered window of hourly buckets so "today" lines up with the start of the array. The interviewer usually says: "Rotate this array to the right by k steps, in place, without using another array." They often add "k can be larger than the length" and sometimes "can you do it in O(1) extra space?"

**What the interviewer is really checking**
Whether you ask about direction, k larger than n, negative k and in-place constraints before typing. They also want to see a simple solution first, then an O(n) time, O(1) space improvement that you can justify. Handling `null`, empty and `k % n == 0` without crashing is part of that.

**How I answer it**
1. **Clarify and restate.** Input is an `int[]` and an `int k`. Output is the same array rotated right by k, in place. I would ask:
   - Is it right or left? I assume right.
   - Can k be 0, larger than n, or negative?
   - Can the array be null or empty?
   - Must it be in place?
2. **Brute force.** Shift every element one step right, k times. Each pass is O(n), so the total is O(n*k). That is far too slow if k is large. A simpler variant copies into a new array at index `(i + k) % n`. It is O(n) time but O(n) extra space.
3. **Better idea: reverse three times.**
   - Compute `shift = k mod n` first, because rotating by n is a no-op.
   - Reverse the whole array. The last `shift` elements are now at the front, but backwards. The first `n-shift` elements are at the back, also backwards.
   - Reverse the first `shift` elements to fix their order.
   - Reverse the remaining `n-shift` elements to fix theirs.
   - Example: `[1,2,3,4,5,6,7]`, shift 3. Whole reverse gives `[7,6,5,4,3,2,1]`. Reversing the first 3 gives `[5,6,7,4,3,2,1]`. Reversing the last 4 gives `[5,6,7,1,2,3,4]`.
4. **Complexity.** Time is O(n), since each element is swapped at most twice. Space is O(1): only a few local variables.
5. **The code:**

```java
import java.util.Arrays;

class Solution {
    // Rotates a to the right by k, in place. Handles null, empty, k > n, negative k.
    static void rotate(int[] a, int k) {
        if (a == null || a.length < 2) return;
        int n = a.length;
        int shift = ((k % n) + n) % n; // safe for negative k, no overflow
        if (shift == 0) return;
        reverse(a, 0, n - 1);
        reverse(a, 0, shift - 1);
        reverse(a, shift, n - 1);
    }

    static void reverse(int[] a, int i, int j) {
        while (i < j) {
            int t = a[i];
            a[i++] = a[j];
            a[j--] = t;
        }
    }

    // Reference implementation using extra space, used only to cross-check.
    static int[] reference(int[] a, int k) {
        int n = a.length;
        int[] r = new int[n];
        int shift = (int) (((k % (long) n) + n) % n);
        for (int i = 0; i < n; i++) r[(i + shift) % n] = a[i];
        return r;
    }

    static void check(String name, int[] input, int k, int[] expected) {
        int[] copy = input == null ? null : input.clone();
        rotate(copy, k);
        if (!Arrays.equals(copy, expected)) {
            throw new AssertionError(name + ": got " + Arrays.toString(copy)
                    + " expected " + Arrays.toString(expected));
        }
    }

    public static void main(String[] args) {
        check("typical", new int[]{1, 2, 3, 4, 5, 6, 7}, 3, new int[]{5, 6, 7, 1, 2, 3, 4});
        check("k zero", new int[]{1, 2, 3}, 0, new int[]{1, 2, 3});
        check("k equals n", new int[]{1, 2, 3}, 3, new int[]{1, 2, 3});
        check("k greater than n", new int[]{1, 2, 3}, 10, new int[]{3, 1, 2});
        check("negative k", new int[]{1, 2, 3, 4}, -1, new int[]{2, 3, 4, 1});
        check("huge k", new int[]{1, 2, 3}, Integer.MAX_VALUE, new int[]{3, 1, 2});
        check("duplicates", new int[]{1, 1, 2, 2}, 1, new int[]{2, 1, 1, 2});
        check("single", new int[]{9}, 5, new int[]{9});
        check("empty", new int[]{}, 2, new int[]{});
        check("null", null, 2, null);

        int[] big = new int[100_003];
        for (int i = 0; i < big.length; i++) big[i] = i * 31 % 1000;
        int[] expected = reference(big, 77_777);
        rotate(big, 77_777);
        if (!Arrays.equals(big, expected)) throw new AssertionError("large input mismatch");
        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| Approach | Time | Space | Note |
|---|---|---|---|
| Shift one step, k times | O(n*k) | O(1) | Times out for large k |
| Copy to new array at `(i+k)%n` | O(n) | O(n) | Simple and clear, but extra memory |
| Three reversals | O(n) | O(1) | Best fit for "in place" |
| Cyclic replacement (juggling) | O(n) | O(1) | Works, but harder to get right under pressure |

Common mistakes:
- Forgetting `k % n`, which causes index errors or wasted work when k >= n.
- Using `k % n` with negative k and getting a negative shift. Use `((k % n) + n) % n`.
- Writing `k + n` or `i + k` and overflowing `int` when k is near `Integer.MAX_VALUE`.
- Mixing up right and left rotation. For a left rotation, reverse the first `shift`, then the rest, then everything.
- Off-by-one on reverse bounds: the ranges are `[0, shift-1]` and `[shift, n-1]`.
- Returning a new array when the question asked for in-place, or the reverse.

**Test cases I'd walk through**
- Typical: `[1..7]`, k=3 returns `[5,6,7,1,2,3,4]`.
- Null or empty: return without exception, array unchanged.
- Single element: `[9]` with any k returns `[9]`.
- k = 0 or k = n: array unchanged.
- k > n: `[1,2,3]`, k=10 behaves like k=1 and returns `[3,1,2]`.
- Negative k: `[1,2,3,4]`, k=-1 is a left rotation by 1 and returns `[2,3,4,1]`.
- Duplicates: `[1,1,2,2]`, k=1 returns `[2,1,1,2]`. Reversal does not depend on values being distinct.
- Large input: 100,003 elements, k=77,777, compared against the copy-based reference. It finishes instantly because the work is linear.

**Follow-ups to expect**
- *How would you rotate left instead?* -> Convert it to a right rotation with `shift = n - (k mod n)`, or reverse the first `k`, then the rest, then everything.
- *Can you do it without reversing, still in O(1) space?* -> Yes, with cyclic replacement. Start at an index, move each element to `(i+shift)%n`, and repeat for `gcd(n, shift)` cycles. It is O(n) time but easier to get wrong.
- *What if it is a `List<Integer>` and not an array?* -> Use `Collections.rotate(list, k)`, which is O(n) and in place. On a `LinkedList` the cost depends on the implementation, so for a custom ring buffer I would keep a head offset and avoid moving data at all.

**60-second answer**
"First I'd confirm it's a right rotation, in place, and that k can be larger than n or negative, and that the array can be null or empty. The naive approach shifts by one k times, which is O(n times k), so I'd skip it. Rotating by n changes nothing, so I reduce k to `((k % n) + n) % n`. Then I reverse the whole array, reverse the first `shift` elements, and reverse the remaining ones. The whole-array reverse moves the last `shift` elements to the front but backwards, and the two smaller reverses put each block back in order. Each element moves at most twice, so it's O(n) time and O(1) extra space. I'd test it with k=0, k=n, k>n, a negative k, a single element, an empty array and null."

### Q15 [fresher] Remove duplicates from a sorted array in place
tags: arrays, two-pointers, in-place, sorted-array, coding, basics

**Start here: the concepts**
- **Sorted array:** equal values sit next to each other. This is the key fact: a duplicate always matches its neighbour, so we never need to remember values seen earlier.
- **In place:** we reuse the same array and do not allocate a second one. Extra memory stays constant.
- **Two pointers:** two index variables walk the same array. Here, `read` scans every element and `write` marks where the next unique value should be stored.
- **Big-O:** a way to describe how work grows with input size `n`. O(n) means work grows in a straight line with `n`. O(n^2) means doubling the input roughly quadruples the work. O(1) space means extra memory does not grow with `n`.

**The live scenario**
A nightly job reads 5 million account IDs that arrive already sorted from a database `ORDER BY`. Because of a join, many IDs repeat, and the job must de-duplicate them before calling a downstream API. The service has a tight heap, so copying 5 million values into a second structure is unwelcome. The interviewer usually phrases it as: "Given a sorted array, remove duplicates in place so each value appears once, and return the new length. Use O(1) extra memory."

**What the interviewer is really checking**
Do you ask clarifying questions (sorted? what goes after the new length?), mention the simple approach first, and then use the sorted property for a single-pass O(n) / O(1) solution? Can you handle empty, single-element and all-equal inputs without index errors?

**How I answer it**
1. **Clarify and restate.**
   - Input: an `int[]` sorted in non-decreasing order.
   - Output: `k`, the count of unique values. The first `k` slots must hold those unique values in order.
   - Questions I ask: can the array be null or empty (return 0)? Do the contents after index `k` matter (no, they are ignored)? May I use extra memory (no, in place)?
2. **Brute force.**
   - Version A: every time I see a duplicate, shift all later elements one step left. Each shift costs up to O(n), and there may be O(n) duplicates, so time is O(n^2) and space is O(1). With 5 million items this is far too slow.
   - Version B: copy into a `LinkedHashSet` or a new array. This is O(n) time but O(n) space, and it is not in place.
3. **Better idea.**
   - Since duplicates are adjacent, keep `write` at the next free slot. The first element is always unique, so `write` starts at 1.
   - Move `read` from index 1 to the end. If `nums[read]` differs from the last value we kept (`nums[write - 1]`), it is new: copy it to `nums[write]` and increase `write`.
   - Otherwise skip it. At the end, `write` is the count of unique values.
   - It works because the kept prefix is always sorted and unique, and any new value must be different from the last kept value to be unique.
4. **Complexity.** Time O(n), one pass with a constant amount of work per element. Space O(1), just two integers.
5. **Code.**

```java
import java.util.Arrays;

class Solution {
    // Returns the number of unique values; the first k slots hold them in order.
    static int removeDuplicates(int[] nums) {
        if (nums == null || nums.length == 0) return 0;
        int write = 1; // slot 0 is always unique
        for (int read = 1; read < nums.length; read++) {
            if (nums[read] != nums[write - 1]) {
                nums[write++] = nums[read];
            }
        }
        return write;
    }

    private static void check(String name, int[] input, int[] expected) {
        int k = removeDuplicates(input);
        if (k != expected.length) {
            throw new AssertionError(name + ": length " + k + " expected " + expected.length);
        }
        for (int i = 0; i < k; i++) {
            if (input[i] != expected[i]) {
                throw new AssertionError(name + ": index " + i + " is " + input[i]
                        + " expected " + expected[i]);
            }
        }
    }

    public static void main(String[] args) {
        check("typical", new int[]{0, 0, 1, 1, 1, 2, 2, 3, 3, 4}, new int[]{0, 1, 2, 3, 4});
        check("empty", new int[]{}, new int[]{});
        check("single", new int[]{7}, new int[]{7});
        check("all equal", new int[]{5, 5, 5, 5}, new int[]{5});
        check("no duplicates", new int[]{1, 2, 3}, new int[]{1, 2, 3});
        check("negatives", new int[]{-3, -3, -1, 0, 0}, new int[]{-3, -1, 0});
        check("extremes", new int[]{Integer.MIN_VALUE, Integer.MIN_VALUE, Integer.MAX_VALUE},
                new int[]{Integer.MIN_VALUE, Integer.MAX_VALUE});

        if (removeDuplicates(null) != 0) throw new AssertionError("null should return 0");

        int[] big = new int[300_000];
        for (int i = 0; i < big.length; i++) big[i] = i / 3; // 100000 unique values
        int k = removeDuplicates(big);
        if (k != 100_000) throw new AssertionError("large: length " + k);
        for (int i = 0; i < k; i++) {
            if (big[i] != i) throw new AssertionError("large: wrong value at " + i);
        }
        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| Approach | Time | Space | Note |
|---|---|---|---|
| Shift left on each duplicate | O(n^2) | O(1) | In place but slow on big inputs |
| `LinkedHashSet` / new array | O(n) | O(n) | Simple, but not in place |
| Two pointers (final) | O(n) | O(1) | Needs sorted input |

- Common mistakes:
  - Starting `read` and `write` at 0, which compares an element with itself.
  - Reading `nums[0]` on an empty array, which throws `ArrayIndexOutOfBoundsException`.
  - Forgetting to return the length, or returning `write - 1`.
  - Comparing with `nums[read - 1]` after overwriting. This can still work on sorted data, but comparing with `nums[write - 1]` is the clearer invariant.
  - Using `==` on `Integer` objects instead of `int`. Here we use primitives, so it is safe.
- Overflow is not a risk because we only compare values and never add or subtract them.
- If the input is not actually sorted, the result is silently wrong. In production, validate the sort order or trust the `ORDER BY`, and log the unique count versus input count so a sudden change shows up in monitoring.

**Test cases I'd walk through**
- Typical `[0,0,1,1,1,2,2,3,3,4]` returns 5, and the first 5 slots are `[0,1,2,3,4]`.
- Null or empty returns 0, with no exception.
- Single element `[7]` returns 1.
- All equal `[5,5,5,5]` returns 1.
- No duplicates `[1,2,3]` returns 3, and the array is unchanged.
- Negatives and extreme values (`Integer.MIN_VALUE`, `Integer.MAX_VALUE`) work, since we only compare.
- Large input of 300,000 elements with each value repeated 3 times returns 100,000 and runs in a single pass.

**Follow-ups to expect**
- *What if each value may appear at most twice?* -> Start `write` at 2 and compare `nums[read]` with `nums[write - 2]`. The same idea works for "at most k" by comparing with `nums[write - k]`.
- *What if the array is not sorted?* -> Either sort first (O(n log n)) or use a `HashSet` (O(n) time, O(n) space). The O(1)-space single pass depends on sortedness.
- *Why not use `Arrays.stream(nums).distinct().toArray()`?* -> It is short and readable, but it builds a new array and a hash-based set internally, so it uses O(n) space and is not in place.

**60-second answer**
"First I'd confirm the array is sorted, that I should return the count of unique values, and that anything after that count is ignored. The naive way is to shift elements left on every duplicate, which is O(n^2), or to copy into a set, which uses O(n) extra memory. Because the array is sorted, duplicates are always neighbours, so I use two pointers. `write` points to the next free slot and starts at 1, and `read` scans from index 1. When `nums[read]` differs from `nums[write - 1]`, I copy it to `nums[write]` and advance `write`. At the end `write` is the new length. It makes one pass, so time is O(n), and it uses only two integers, so space is O(1). I'd handle null and empty by returning 0, and I'd test single-element, all-equal and no-duplicate arrays."

### Q16 [fresher] Find the second highest number in an array without sorting
tags: arrays, single-pass, duplicates, edge-cases, coding, basics

**Start here: the concepts**
- **Array**: a fixed-size block of values you can read by index. Visiting every element once is called a *pass*.
- **Single pass with two variables**: while walking the array, keep only two facts, the biggest value seen so far (`first`) and the biggest value strictly smaller than it (`second`). Nothing else is stored.
- **Big-O**: a way to describe how work grows with input size `n`. O(n) means work grows in a straight line with the array length. O(n log n) means a bit more, which is what sorting costs. O(1) space means extra memory does not grow with `n`.
- **Sentinel**: a placeholder meaning "nothing found yet". Using `Integer.MIN_VALUE` as a sentinel is risky because that can be a real array value. A `long` sentinel avoids this.
- **Distinct second highest**: for `[5, 5, 4]` the answer is `4`, not `5`, because the second highest is the largest value *different from* the maximum.

**The live scenario**
A reporting service reads 2 million order amounts from a batch file and must show the top amount and the runner-up, for example "highest bid and next best bid" in an auction. The interviewer usually says: "Find the second largest number in an array. Don't sort it. What if there are duplicates?"

**What the interviewer is really checking**
Whether you ask about duplicates, empty arrays and negative numbers before coding, and whether you move from the easy sort-based answer to an O(n) single pass. They also watch for the classic bugs: initialising to 0 or `Integer.MIN_VALUE`, and returning the maximum when it is duplicated.

**How I answer it**
1. **Clarify and restate.** Input is an `int[]` and output is the second highest *distinct* value. I would ask: can the array be null or empty? What if there is no second value, such as `[7, 7, 7]` or one element? Can numbers be negative? My choice is to return `OptionalInt.empty()` when no answer exists, because it is clearer than a magic number.
2. **Brute force.** Sort a copy descending and take the first value different from the max. That is O(n log n) time and O(n) space for the copy. Another version scans once to find the max, then scans again for the largest value below it. That is O(n) but takes two passes.
3. **Better idea.** Walk the array once and update `first` and `second` as follows:
   - If `x > first`, the old `first` becomes `second` and `x` becomes `first`.
   - Else if `x < first` and `x > second`, then `x` becomes `second`.
   - If `x == first`, ignore it. This is what handles duplicates.

   It works because after each element, `first` and `second` are the top two distinct values of the prefix seen so far.
4. **Complexity.** Time is O(n), one pass with constant work per element. Space is O(1), two variables.
5. **The code:**

```java
import java.util.OptionalInt;

class Solution {
    // Second highest DISTINCT value; empty if it does not exist.
    static OptionalInt secondHighest(int[] a) {
        if (a == null) return OptionalInt.empty();
        // long sentinel is smaller than any int, so Integer.MIN_VALUE input still works
        long first = Long.MIN_VALUE, second = Long.MIN_VALUE;
        for (int x : a) {
            if (x > first) {
                second = first;
                first = x;
            } else if (x < first && x > second) {
                second = x;
            }
        }
        return second == Long.MIN_VALUE ? OptionalInt.empty() : OptionalInt.of((int) second);
    }

    static void check(boolean cond, String msg) {
        if (!(cond)) throw new AssertionError(msg);
    }

    public static void main(String[] args) {
        check(secondHighest(new int[]{3, 1, 4, 1, 5, 9, 2, 6}).getAsInt() == 6, "typical");
        check(secondHighest(new int[]{5, 5, 4}).getAsInt() == 4, "max duplicated");
        check(secondHighest(new int[]{9, 8, 9, 8, 7}).getAsInt() == 8, "many duplicates");
        check(secondHighest(new int[]{-3, -1, -2}).getAsInt() == -2, "negatives");
        check(secondHighest(new int[]{1, 2}).getAsInt() == 1, "two elements");
        check(secondHighest(new int[]{Integer.MIN_VALUE, Integer.MAX_VALUE}).getAsInt()
                == Integer.MIN_VALUE, "min value is a real answer");
        check(secondHighest(new int[]{7, 7, 7}).isEmpty(), "all same");
        check(secondHighest(new int[]{Integer.MIN_VALUE, Integer.MIN_VALUE}).isEmpty(), "all min");
        check(secondHighest(new int[]{42}).isEmpty(), "single element");
        check(secondHighest(new int[]{}).isEmpty(), "empty array");
        check(secondHighest(null).isEmpty(), "null array");
        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| Approach | Time | Space | Note |
|---|---|---|---|
| Sort a copy, scan for a different value | O(n log n) | O(n) | Simple, but wasteful for one answer |
| Two passes (max, then max below it) | O(n) | O(1) | Fine, but reads the data twice |
| Single pass, two variables | O(n) | O(1) | Best; needs careful duplicate handling |

Common mistakes:
- Initialising both variables to `0`, which breaks all-negative arrays.
- Initialising to `Integer.MIN_VALUE`, which cannot tell "no value yet" from a real `Integer.MIN_VALUE`. The `long` sentinel fixes this.
- Using `x >= first` or forgetting `x < first`, so a duplicated max becomes the "second" highest.
- Not handling null, empty, single-element or all-equal input, and returning a fake number such as `-1` that could be a real value.

**Test cases I'd walk through**
- Typical `[3,1,4,1,5,9,2,6]` -> `6`.
- Max duplicated `[5,5,4]` -> `4`.
- All equal `[7,7,7]` -> empty, because there is no distinct second value.
- Single element `[42]` -> empty.
- Empty array and `null` -> empty, with no exception.
- Negatives `[-3,-1,-2]` -> `-2`.
- Extremes `[MIN_VALUE, MAX_VALUE]` -> `MIN_VALUE`, which proves the sentinel is safe.
- Large input (millions of elements) -> still one pass, with constant memory.

**Follow-ups to expect**
- *How would you find the k-th highest?* -> Keep a min-heap (`PriorityQueue`) of size k. Push each element and pop when the size exceeds k. The root is the answer. Time is O(n log k) and space is O(k).
- *What if duplicates should count, so `[5,5,4]` gives `5`?* -> Change the first branch to `x >= first` and drop the `x < first` check. Then a repeated max pushes the old max into `second`.
- *Can you do it with streams?* -> Yes: `Arrays.stream(a).distinct().boxed().sorted(Comparator.reverseOrder()).skip(1).findFirst()`. It is readable but O(n log n) and allocates boxed objects, so the loop is better for large data.

**60-second answer**
"First I'd confirm what happens with duplicates and with arrays that have fewer than two distinct values. I'd assume the second highest *distinct* value and return an `OptionalInt`. The easy solution is to sort and pick the next different value, which is O(n log n). Instead I walk the array once and keep two variables, `first` and `second`. If an element is bigger than `first`, the old `first` becomes `second`. If it is smaller than `first` but bigger than `second`, it becomes `second`. If it equals `first`, I skip it, which handles duplicates. I start both as `long` minimum values so that `Integer.MIN_VALUE` in the input still works. This is O(n) time and O(1) space, and I'd test null, empty, single element, all equal and negative numbers."

### Q17 [mid] Find duplicate elements in an array
tags: arrays, hashset, hashing, sorting, floyd-cycle, duplicates, coding, basics

**Start here: the concepts**
- **HashSet**: a collection that stores each value once. `add` returns `false` if the value is already there. On average, add and lookup take constant time, written O(1).
- **Big-O**: how the work grows as the input size n grows. O(n) means one pass. O(n^2) means a loop inside a loop. O(n log n) is the cost of sorting.
- **Sorting technique**: after sorting, equal values sit next to each other, so one scan comparing neighbours finds duplicates.
- **Floyd's cycle detection (tortoise and hare)**: two pointers move through the array, one step and two steps at a time. If the array has n+1 values in the range 1..n, treating `value -> index` as a link forces a cycle, and the cycle entry is the duplicate. It needs O(1) extra space and does not modify the array.
- **Space complexity**: the extra memory used beyond the input.

**The live scenario**
You are reviewing a batch of order IDs pulled from a message queue before saving them, and the same ID can arrive twice because of retries. The interviewer says: "Given an int array, return the values that appear more than once." Then they add: "What if you can't use extra memory?" or "What if the values are 1..n?"

**What the interviewer is really checking**
Do you ask clarifying questions (return each duplicate once or every occurrence? is order important? can the array be null or huge?), start with brute force, and then improve it with a clear complexity argument? They also want to see that you know the trade-off between time and memory.

**How I answer it**
1. **Clarify and restate.** Input is `int[]`. Output is the distinct values that occur at least twice. I would ask: null or empty input? negative numbers? Is the order of the result important? May I modify the input? Can the array be very large? I assume each duplicate value is reported once, in order of first repeat.
2. **Brute force.** For each element, scan the rest of the array for an equal value. That is O(n^2) time and O(1) space. It is fine for tiny inputs and too slow for 100,000 or more elements.
3. **Better idea.** Walk the array once with a `HashSet` called `seen`. If `seen.add(x)` returns false, then x was seen before, so it is a duplicate. I put it in a `LinkedHashSet`, which keeps insertion order and does not store the same value twice. Each element costs O(1) on average, so the whole pass is linear. If memory is tight, I sort a copy and compare neighbours. For the special case of n+1 values in 1..n with exactly one repeated value, Floyd's algorithm finds it in O(1) space.
4. **Complexity.**
   - HashSet: O(n) average time, O(n) space.
   - Sorting: O(n log n) time, O(n) space for the copy. It is O(1) if you may sort in place.
   - Floyd: O(n) time, O(1) space.
5. **Code.**

```java
import java.util.*;

class Solution {
    // Main approach: one pass, O(n) average time, O(n) space.
    static List<Integer> findDuplicates(int[] a) {
        if (a == null) return new ArrayList<>();
        Set<Integer> seen = new HashSet<>();
        Set<Integer> dups = new LinkedHashSet<>();
        for (int x : a) {
            if (!seen.add(x)) dups.add(x); // add() is false when already present
        }
        return new ArrayList<>(dups);
    }

    // Low-memory alternative: sort a copy, compare neighbours. O(n log n).
    static List<Integer> findDuplicatesSorted(int[] a) {
        List<Integer> r = new ArrayList<>();
        if (a == null) return r;
        int[] c = a.clone();
        Arrays.sort(c);
        for (int i = 1; i < c.length; i++) {
            if (c[i] == c[i - 1] && (r.isEmpty() || r.get(r.size() - 1) != c[i])) {
                r.add(c[i]);
            }
        }
        return r;
    }

    // Variant: n+1 values in 1..n, exactly one value repeated. O(n) time, O(1) space.
    static int floydDuplicate(int[] nums) {
        int slow = nums[0], fast = nums[0];
        do {
            slow = nums[slow];
            fast = nums[nums[fast]];
        } while (slow != fast);
        slow = nums[0]; // restart one pointer; they meet at the cycle entry
        while (slow != fast) {
            slow = nums[slow];
            fast = nums[fast];
        }
        return slow;
    }

    static void check(boolean cond, String msg) {
        if (!(cond)) throw new AssertionError(msg);
    }

    public static void main(String[] args) {
        check(findDuplicates(new int[]{1, 2, 3, 2, 1, 2}).equals(List.of(2, 1)), "typical");
        check(findDuplicates(new int[]{}).isEmpty(), "empty");
        check(findDuplicates(null).isEmpty(), "null");
        check(findDuplicates(new int[]{5}).isEmpty(), "single");
        check(findDuplicates(new int[]{7, 7, 7}).equals(List.of(7)), "all same");
        int m = Integer.MAX_VALUE;
        check(findDuplicates(new int[]{-1, -1, m, m}).equals(List.of(-1, m)), "negative and max");
        check(findDuplicatesSorted(new int[]{4, 1, 4, 1, 1}).equals(List.of(1, 4)), "sorted variant");
        int[] big = new int[100_001];
        for (int i = 0; i < 100_000; i++) big[i] = i;
        big[100_000] = 5;
        check(findDuplicates(big).equals(List.of(5)), "large");
        check(floydDuplicate(new int[]{1, 3, 4, 2, 2}) == 2, "floyd 1");
        check(floydDuplicate(new int[]{3, 1, 3, 4, 2}) == 3, "floyd 2");
        check(floydDuplicate(new int[]{1, 1}) == 1, "floyd tiny");
        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| Approach | Time | Extra space | Notes |
|---|---|---|---|
| Nested loops | O(n^2) | O(1) | Simple, but too slow for large input |
| HashSet | O(n) average | O(n) | Fastest in practice, uses memory for boxed `Integer` objects |
| Sort then scan | O(n log n) | O(1) in place, O(n) for a copy | Loses original order, and sorting in place changes the caller's array |
| Floyd (1..n, one repeat) | O(n) | O(1) | Only valid under the strict input rules |

Common mistakes:
- Reporting the same duplicate several times: `[7,7,7]` should give `[7]`, not `[7,7]`.
- Forgetting null or empty input and getting a `NullPointerException`.
- Using Floyd on arrays that do not meet its rules. Values outside the array indexes cause an `ArrayIndexOutOfBoundsException`.
- Sorting the caller's array without saying so, which is a side effect.
- Using streams with `Collectors.groupingBy` for a simple job. It works, but it is slower and heavier than a loop.

**Test cases I'd walk through**
- Typical `[1,2,3,2,1,2]` returns `[2,1]`.
- Empty `[]` returns `[]`.
- Null returns `[]`, or you could throw an exception if the contract says so.
- Single element `[5]` returns `[]`.
- All the same `[7,7,7]` returns `[7]`.
- Negatives and `Integer.MAX_VALUE` repeated return both values. Nothing overflows because we only compare and hash.
- Large input of 100,001 elements with one repeat finishes quickly and returns that value.
- Floyd on `[1,3,4,2,2]` returns `2`.

**Follow-ups to expect**
- *What if memory is very limited and the array is huge?* -> Sort in place, which is O(n log n) with O(1) extra space, or use external sorting if the data does not fit in memory. For approximate answers, use a Bloom filter.
- *How does Floyd's algorithm work for the 1..n variant?* -> Treat `i -> nums[i]` as a linked list. Two values pointing to the same index create a cycle. The fast and slow pointers meet inside the cycle, and restarting one pointer from the start makes them meet again at the cycle entry, which is the duplicate.
- *Can you do it with streams?* -> Yes: `Arrays.stream(a).boxed().collect(Collectors.groupingBy(x -> x, Collectors.counting()))` and keep entries with a count above 1. It is still O(n) but allocates more, so I would use a loop on a hot path.

**60-second answer**
First I would clarify: should each duplicate be returned once, can the input be null or empty, and may I modify the array? The brute-force idea is two nested loops, which costs O(n^2) time and O(1) space. A better approach is to scan once with a `HashSet`: if `add` returns false, I have seen the value before, so I put it into a `LinkedHashSet` for the result. This is

### Q18 [mid] Java 8 streams: group employees by department and find the highest paid in each
tags: java8, streams, collectors, groupingby, maxby, hashmap, coding, basics

**Start here: the concepts**
- **Stream**: a pipeline that reads a collection element by element (filter, map, collect) without changing the source list.
- **Collector**: the final step of a stream that decides what result to build, for example a Map.
- **`groupingBy(classifier, downstream)`**: puts each element into a bucket in a `HashMap` keyed by the classifier (here the department). The downstream collector then reduces each bucket.
- **`maxBy(comparator)`**: a downstream collector that keeps the largest element of a bucket. It returns an `Optional` because a bucket could in theory be empty.
- **`collectingAndThen(..., Optional::get)`**: unwraps that Optional. This is safe because `groupingBy` never creates an empty bucket.
- **Hash map**: a key-to-value table with average O(1) lookup and insert.
- **Big-O**: how the work grows as the input grows. n is the number of employees and d is the number of departments.

**The live scenario**
A payroll or HR service gets a list of 50,000 employee records and the dashboard must show the top earner per department. The interviewer usually says: "Given a list of Employee(name, dept, salary), return a map from department to the highest paid employee. Use Java 8 streams." Often the follow-up is "now do it without streams".

**What the interviewer is really checking**
Whether you ask about ties, nulls and empty input before typing, and know that `groupingBy` plus `maxBy` is a single pass. They also want to see that you handle the `Optional` correctly and can state O(n) time and O(d) space.

**How I answer it**
1. **Clarify and restate.** Input is a `List<Employee>`, output is `Map<String, Employee>` (department to top earner). I would ask:
   - What if two people tie? I will keep the first one seen.
   - Can the list or an element be null? I will return an empty map for a null list and skip null elements or null departments.
   - Is salary a long or a decimal? I will use `long` (minor units) to keep the example simple.
2. **Brute force.** Collect the distinct departments, then for each department scan the whole list to find the max. That is O(n * d) time. Another option is to sort everything by salary, which is O(n log n). Both do more work than needed.
3. **Better idea.** I only need one running "best so far" per department. `groupingBy` does one pass and puts each employee in its department bucket. `maxBy` keeps only the current best in that bucket, so nothing is stored or sorted.
4. **Complexity.** Time is O(n), because each employee is looked at once with an O(1) hash lookup and one comparison. Space is O(d) for the result map, not counting the input.
5. **Code.** I show the stream version and a plain loop with `Map.merge`, and the checks confirm both give the same answer.

```java
import java.util.*;
import java.util.stream.*;

record Employee(String name, String dept, long salary) {}

class Solution {
    static Map<String, Employee> topPaidByDept(List<Employee> emps) {
        if (emps == null) return Map.of();
        return emps.stream()
            .filter(e -> e != null && e.dept() != null)
            .collect(Collectors.groupingBy(Employee::dept,
                Collectors.collectingAndThen(
                    Collectors.maxBy(Comparator.comparingLong(Employee::salary)),
                    Optional::get)));
    }

    // Same result without streams: one pass, keep the best per department.
    static Map<String, Employee> topPaidLoop(List<Employee> emps) {
        Map<String, Employee> best = new HashMap<>();
        if (emps == null) return best;
        for (Employee e : emps) {
            if (e == null || e.dept() == null) continue;
            best.merge(e.dept(), e, (a, b) -> b.salary() > a.salary() ? b : a);
        }
        return best;
    }

    static void check(boolean cond, String msg) {
        if (!cond) throw new AssertionError(msg);
    }

    public static void main(String[] args) {
        // 1. typical
        List<Employee> list = List.of(
            new Employee("Ann", "Eng", 150), new Employee("Bob", "Eng", 120),
            new Employee("Cy", "HR", 90));
        Map<String, Employee> r = topPaidByDept(list);
        check(r.size() == 2, "typical size");
        check(r.get("Eng").name().equals("Ann"), "Eng top");
        check(r.get("HR").name().equals("Cy"), "HR top");

        // 2. null and empty input
        check(topPaidByDept(null).isEmpty(), "null list");
        check(topPaidByDept(List.of()).isEmpty(), "empty list");

        // 3. single element
        check(topPaidByDept(List.of(new Employee("Zed", "Ops", 1)))
            .get("Ops").name().equals("Zed"), "single");

        // 4. tie: first seen wins (BinaryOperator.maxBy keeps the first on equal)
        List<Employee> tie = List.of(new Employee("Dee", "Ops", 100),
            new Employee("Eli", "Ops", 100));
        check(topPaidByDept(tie).get("Ops").name().equals("Dee"), "tie stream");
        check(topPaidLoop(tie).get("Ops").name().equals("Dee"), "tie loop");

        // 5. null element and null department are skipped
        List<Employee> dirty = new ArrayList<>();
        dirty.add(null);
        dirty.add(new Employee("Ghost", null, 999));
        dirty.add(new Employee("Fay", "QA", 70));
        r = topPaidByDept(dirty);
        check(r.size() == 1 && r.get("QA").name().equals("Fay"), "dirty input");

        // 6. large input: 200k employees, 100 departments, stream equals loop
        List<Employee> big = new ArrayList<>();
        for (int i = 0; i < 200_000; i++)
            big.add(new Employee("e" + i, "d" + (i % 100), i));
        Map<String, Employee> bigRes = topPaidByDept(big);
        check(bigRes.size() == 100, "big size");
        check(bigRes.get("d5").name().equals("e199905"), "big top");
        check(bigRes.equals(topPaidLoop(big)), "stream equals loop");

        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**
| Approach | Time | Space | Note |
|---|---|---|---|
| Scan the list once per department | O(n * d) | O(d) | Slow when there are many departments |
| Sort by salary, then pick first per department | O(n log n) | O(n) | Extra sorting work, and a copy of the data |
| `groupingBy` + `maxBy` (final) | O(n) | O(d) | One pass, short and readable |
| Loop with `Map.merge` | O(n) | O(d) | Same cost, easier to debug |

Common mistakes:
- Forgetting that `maxBy` returns an `Optional`, so the map type becomes `Map<String, Optional<Employee>>`.
- Not deciding how ties are handled. Here the first one seen wins.
- `groupingBy` throws a `NullPointerException` on a null key, so null departments must be filtered first.
- Comparing salaries with `a.salary() - b.salary()`, which can overflow. Use `Comparator.comparingLong`.
- Sorting the whole list when only the maximum is needed.

**Test cases I'd walk through**
- **Typical:** Eng has Ann 150 and Bob 120, HR has Cy 90. Result is Eng -> Ann, HR -> Cy.
- **Null or empty list:** returns an empty map and does not throw.
- **Single element:** a map with one entry containing that employee.
- **Duplicates (equal salary in a department):** the first one seen is kept. This is deterministic for a `List`.
- **Null element or null department:** skipped.
- **Large input:** 200,000 employees across 100 departments gives 100 entries in linear time, and the loop version produces the same map.

**Follow-ups to expect**
- *How do you get the top 3 per department?* -> Group first, then sort each bucket descending and take 3. For huge buckets, use a bounded min-heap of size 3 inside a custom collector, which costs O(n log 3).
- *How would you return just the salary, or the name, instead of the whole Employee?* -> Wrap `maxBy` with `collectingAndThen(..., o -> o.get().name())`, or use `Collectors.mapping` plus a reduce.
- *Can you make it parallel?* -> Use `parallelStream()` with `groupingByConcurrent`. `maxBy` is associative, so it is safe, but it only pays off for large lists. Note that on ties "first wins" is then not guaranteed.

**60-second answer**
"First I would confirm the input is a list of employees with a department and salary, and ask about ties and nulls. The brute force is to loop over each department and scan the whole list, which is O(n times d). The better idea is a single pass: `Collectors.groupingBy` on department, with `maxBy` on salary as the downstream collector. That keeps one running best per department in a hash map. Because `maxBy` returns an `Optional`, I wrap it in `collectingAndThen` with `Optional::get`, which is safe since no group is ever empty. I would filter out null employees and null departments first and use `Comparator.comparingLong` to avoid overflow. Time is O(n) and extra space is O(d), where d is

### Q19 [mid] Java 8 streams: find the second highest salary
tags: java8, streams, optional, distinct, sorting, single-pass, coding, basics

**Start here: the concepts**
- **Stream**: a pipeline of steps (filter, map, sorted...) applied to a collection. It is lazy: nothing runs until a terminal step such as `findFirst()` is called.
- **`distinct()`**: drops repeated values, so two people earning 300 count as one salary level. This matters because "second highest" means the second highest *distinct* value.
- **`sorted(Comparator.reverseOrder())`**: orders values from highest to lowest. Sorting costs O(n log n).
- **`skip(1)`**: throws away the first element (the highest).
- **`Optional<T>`**: a box that may be empty. It forces the caller to handle "there is no second highest" instead of getting a surprise `null`.
- **Big-O**: how the work grows as the input grows. O(n) means work grows in step with the input. O(n log n) is a bit more, and it is what sorting costs. O(1) space means extra memory stays fixed however big the input is.
- **Single pass**: one loop that tracks the two largest distinct values seen so far (`first` and `second`).

**The live scenario**
An HR or payroll service has `List<Employee>` loaded from a database. A report endpoint needs "the second highest salary" for a compensation band review, with about 50,000 employees. The interviewer usually says: "Using Java 8 streams, find the second highest salary. What if there are duplicates? What if there is only one employee?"

**What the interviewer is really checking**
- Do you ask about duplicates and empty input before coding?
- Do you reach the clean stream answer (`distinct`, `sorted`, `skip`, `Optional`)?
- Can you say it is O(n log n) and offer the O(n) single-pass alternative?
- Do you return `Optional` instead of `null` or throwing an exception?

**How I answer it**
1. **Clarify and restate.**
   - Input: a list of employees with an int salary. Output: the second highest *distinct* salary.
   - Questions I would ask:
     - Do duplicates count once? I assume yes, so [300, 300, 200] gives 200.
     - What if there is no second value (empty list, one employee, all equal)? I return `Optional.empty()`.
     - Can the list or an element be null? I guard against both.
     - Money type: int here for simplicity. Production code would use `long` cents or `BigDecimal`.
2. **Brute force.**
   - Sort the whole list descending, then walk it to find the first value different from the top.
   - It is O(n log n) time and O(n) extra space for the copy, and it is easy to get the duplicate case wrong.
3. **Better idea.**
   - The stream version is a clearer expression of the same idea: `map` to salaries, `distinct`, `sorted` descending, `skip(1)`, `findFirst`. It is still O(n log n), but short and hard to get wrong. That is my first answer.
   - If asked to optimise, I use one loop with two variables. For each salary `s`:
     - If `s > first`, the old `first` becomes `second` and `s` becomes `first`.
     - Else if `s < first` and `s > second`, then `s` becomes `second`.
     - If `s == first`, ignore it. That is what handles duplicates.
   - Boxed `Integer` variables that start as `null` avoid a bug where `Integer.MIN_VALUE` is used as "not set yet" and collides with a real salary.
4. **Complexity.**
   - Stream: O(n log n) time, O(n) space for `distinct` and `sorted`.
   - Single pass: O(n) time, O(1) space.
5. **Code.**

```java
import java.util.*;
import java.util.stream.*;

class Solution {
    record Employee(String name, int salary) {}

    // Readable version: O(n log n) time, O(n) space.
    static Optional<Integer> secondHighestStream(List<Employee> emps) {
        if (emps == null) return Optional.empty();
        return emps.stream()
                .filter(Objects::nonNull)
                .map(Employee::salary)
                .distinct()
                .sorted(Comparator.reverseOrder())
                .skip(1)
                .findFirst();
    }

    // Optimised version: O(n) time, O(1) space.
    static Optional<Integer> secondHighestLoop(List<Employee> emps) {
        if (emps == null) return Optional.empty();
        Integer first = null, second = null; // null = "not seen yet", safe for MIN_VALUE
        for (Employee e : emps) {
            if (e == null) continue;
            int s = e.salary();
            if (first == null || s > first) {
                second = first;
                first = s;
            } else if (s < first && (second == null || s > second)) {
                second = s;
            }
        }
        return Optional.ofNullable(second);
    }

    static List<Employee> of(int... salaries) {
        List<Employee> list = new ArrayList<>();
        for (int i = 0; i < salaries.length; i++) list.add(new Employee("e" + i, salaries[i]));
        return list;
    }

    static void check(String name, Optional<Integer> expected, List<Employee> in) {
        Optional<Integer> a = secondHighestStream(in);
        Optional<Integer> b = secondHighestLoop(in);
        if (!(a.equals(expected))) throw new AssertionError(name + " stream: " + a);
        if (!(b.equals(expected))) throw new AssertionError(name + " loop: " + b);
    }

    public static void main(String[] args) {
        check("typical", Optional.of(200), of(100, 300, 200));
        check("duplicate top", Optional.of(200), of(300, 300, 200));
        check("all equal", Optional.empty(), of(500, 500, 500));
        check("single", Optional.empty(), of(100));
        check("empty", Optional.empty(), of());
        check("null list", Optional.empty(), null);
        check("min value", Optional.of(Integer.MIN_VALUE), of(Integer.MIN_VALUE, 5));
        List<Employee> big = new ArrayList<>(of(IntStream.rangeClosed(1, 100_000).toArray()));
        Collections.shuffle(big, new Random(42));
        check("large", Optional.of(99_999), big);
        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| | Stream (`distinct/sorted/skip`) | Single-pass loop |
|---|---|---|
| Time | O(n log n) | O(n) |
| Space | O(n) | O(1) |
| Readability | Very high | Medium, more branches |
| Best for | Small to medium lists, most business code | Very large data, hot paths |

Common mistakes:
- Forgetting `distinct()`, so [300, 300, 200] wrongly returns 300.
- Calling `.get()` on the `Optional` and throwing `NoSuchElementException` on a one-element list.
- Using `Integer.MIN_VALUE` as the starting value in the loop.
- Sorting ascending and then taking index 1, which gives the second *lowest*.
- Not handling a null list or null elements.
- Doing a database job in memory. If the data lives in SQL, use `ORDER BY salary DESC` with `OFFSET`/`LIMIT` or `DENSE_RANK()` instead of loading everything.

**Test cases I'd walk through**
- Typical [100, 300, 200] returns 200.
- Duplicate top [300, 300, 200] returns 200.
- All equal [500, 500, 500] returns empty.
- Single element returns empty.
- Empty list or null returns empty.
- Negative or `Integer.MIN_VALUE` values still work, because the loop uses `null` as "unset".
- Large input (100,000 shuffled values) returns 99,999 and both implementations agree.

**Follow-ups to expect**
- *How would you find the Nth highest salary?* -> Use `distinct().sorted(reverseOrder()).skip(n - 1).findFirst()`. For large data with a small n, keep a min-heap (`PriorityQueue`) of size n over distinct values for O(m log n).
- *How would you get the second highest salary per department?* -> `Collectors.groupingBy(Employee::dept, ...)` with a downstream collector that applies the same distinct/sorted/skip logic to each group.
- *Why `Optional` instead of returning null or -1?* -> It makes "no answer" part of the method signature. -1 could be a valid value, and null causes NPEs later.

**60-second answer**
"First I would clarify whether duplicates count once and what to return when there is no second value. I would assume distinct values and return an `Optional`. My stream solution maps employees to salaries, calls `distinct()`, sorts in reverse order, does `skip(1)` and `findFirst()`. That gives `Optional.empty()` for empty, single-element and all-equal input, and I guard against a null list. It runs in O(n log n) time and O(n) space because of the sort. If the interviewer wants better, I do one pass with two boxed variables, `first` and `second`. Equal values are ignored, so duplicates are handled. That is O(n) time and O(1) space. For a typical report on tens of thousands of rows I would keep the stream version for readability, and for a huge dataset I would push the ranking into the database."

### Q20 [mid] Java 8 streams: why does Collectors.toMap throw on duplicate keys and how do you handle it
tags: java8, streams, collectors, hashmap, tomap, coding, basics

**Start here: the concepts**
- **Collectors.toMap(keyFn, valueFn)**: a stream collector that builds a `Map`. It calls `keyFn` and `valueFn` on each element and puts the pair into the map.
- **Duplicate key**: two elements produce the same key. With the two-argument `toMap` this is treated as a bug, so it throws `IllegalStateException` ("Duplicate key ..."). It does not silently overwrite, unlike `map.put`. Java 8 prints only the key. Java 9+ also prints the two conflicting values.
- **Merge function**: the third argument, a `BinaryOperator<V>` that takes (oldValue, newValue) and returns the value to keep. Examples: `(a, b) -> a` keeps the first, `(a, b) -> b` keeps the last, `Integer::sum` adds them.
- **Map supplier**: the fourth argument, which chooses the map type. The default is `HashMap`, which has no guaranteed order. `LinkedHashMap::new` keeps encounter order. `TreeMap::new` sorts by key.
- **Null values**: `toMap` uses `HashMap.merge` internally, which throws `NullPointerException` when a value is null. Null keys are fine for `HashMap` but not for `TreeMap`.
- **Big-O**: shows how work grows with input size n. O(n) means one pass over the data. Space O(k) means memory grows with k, the number of distinct keys.

**The live scenario**
You load 50,000 employee rows and need a `Map<dept, totalSalary>` for a report. The code works in test, then fails in production with `IllegalStateException: Duplicate key eng`, because the real data has many rows per department. The interviewer usually asks: "Why does `toMap` throw on duplicate keys, and how would you fix it? What if the output order matters?"

**What the interviewer is really checking**
That you know the three-argument and four-argument overloads of `toMap`, and that you choose the merge policy deliberately (first, last, sum or a list) instead of just making the exception go away. They also want to see you mention ordering, null values and when `groupingBy` is the better tool.

**How I answer it**
1. **Clarify and restate.** Input is a stream or list of objects. Output is a `Map` keyed by some field. Questions I would ask:
   - When two elements share a key, should I keep the first, keep the last, combine them, or fail?
   - Does the iteration order of the result matter?
   - Can values be null?
   - Is the list empty or null?
2. **Brute force.** Write a loop: for each element, check `containsKey`, then either `put` or combine the values. It is O(n) time and O(k) space. It is correct but verbose, and the duplicate policy is buried in `if` branches.
3. **Better idea.** Use the overload `toMap(key, value, mergeFn, mapSupplier)`.
   - The two-argument version is fail-fast by design. Silently dropping data would hide bugs, so the JDK throws.
   - A merge function tells the collector what to do on a collision. It is called only when the key already exists.
   - `LinkedHashMap::new` keeps the order in which keys first appeared, so output is deterministic.
   - If I need all the values per key, I use `groupingBy` with `Collectors.mapping(..., toList())` instead.
4. **Complexity.** Time is O(n), because each element is hashed once and the merge is O(1). Space is O(k) for k distinct keys. For a sequential stream there is no extra copying.
5. **Code.**

```java
import java.util.*;
import java.util.stream.*;

record Emp(String dept, String name, int salary) {}

class Solution {
    static Map<String, Integer> totalByDept(List<Emp> l) {
        return l.stream().collect(Collectors.toMap(
            Emp::dept, Emp::salary, Integer::sum, LinkedHashMap::new));
    }

    static boolean plainToMapThrows(List<Emp> l) {
        try {
            l.stream().collect(Collectors.toMap(Emp::dept, Emp::name));
            return false;
        } catch (IllegalStateException e) {
            return true;
        }
    }

    static void check(boolean cond, String msg) {
        if (!cond) throw new AssertionError(msg);
    }

    public static void main(String[] args) {
        List<Emp> list = List.of(new Emp("eng", "ann", 100),
            new Emp("ops", "bob", 80), new Emp("eng", "cy", 120));

        check(plainToMapThrows(list), "duplicate key should throw");
        check(!plainToMapThrows(List.of(list.get(0), list.get(1))), "unique keys ok");

        Map<String, String> first = list.stream().collect(Collectors.toMap(
            Emp::dept, Emp::name, (a, b) -> a, LinkedHashMap::new));
        check(first.toString().equals("{eng=ann, ops=bob}"), "keep first: " + first);

        Map<String, String> last = list.stream().collect(Collectors.toMap(
            Emp::dept, Emp::name, (a, b) -> b, LinkedHashMap::new));
        check(last.get("eng").equals("cy"), "keep last: " + last);

        check(totalByDept(list).toString().equals("{eng=220, ops=80}"), "sum");
        check(totalByDept(List.of()).isEmpty(), "empty list");

        List<Emp> opsFirst = List.of(list.get(1), list.get(0), list.get(2));
        check(new ArrayList<>(totalByDept(opsFirst).keySet()).equals(List.of("ops", "eng")),
            "insertion order kept");

        Map<String, List<String>> grouped = list.stream().collect(Collectors.groupingBy(
            Emp::dept, TreeMap::new, Collectors.mapping(Emp::name, Collectors.toList())));
        check(grouped.toString().equals("{eng=[ann, cy], ops=[bob]}"), "grouping " + grouped);

        boolean npe = false;
        try {
            Stream.of(new Emp("a", null, 1))
                .collect(Collectors.toMap(Emp::dept, Emp::name));
        } catch (NullPointerException e) {
            npe = true;
        }
        check(npe, "null value should throw NPE");

        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**
| Approach | Time | Space | Notes |
|---|---|---|---|
| Manual loop with `containsKey` | O(n) | O(k) | Verbose; policy is hidden in `if` branches |
| `toMap(k, v)` | O(n) | O(k) | Fails fast on duplicates; good when duplicates truly mean bad data |
| `toMap(k, v, merge, LinkedHashMap::new)` | O(n) | O(k) | Explicit policy and stable order |
| `groupingBy` + `mapping` | O(n) | O(n) | Keeps all values; use when you must not lose any |

Common mistakes:
- Adding `(a, b) -> a` just to silence the exception, without confirming that dropping data is acceptable.
- Expecting the default `HashMap` to keep order. Use `LinkedHashMap` or `TreeMap`.
- A null value causes an NPE even when there are no duplicates. Use `Optional`, filter nulls out, or write a manual loop.
- Using `toMap` on a parallel stream with a merge function that is not associative. Merge functions must be associative and side-effect free.
- Using `toMap` with `TreeMap::new` when a key can be null. This throws an NPE.
- Reading the stack trace: Java 8 only shows the key, so log the offending value yourself if you need to debug.

**Test cases I'd walk through**
- **Typical with duplicates, no merge**: eng, ops, eng. This throws `IllegalStateException`.
- **Keep first**: `{eng=ann, ops=bob}`.
- **Keep last**: eng maps to `cy`.
- **Sum with `LinkedHashMap`**: `{eng=220, ops=80}`.
- **Empty list**: returns an empty map, with no exception.
- **Null list**: `list.stream()` throws NPE. Guard with `Objects.requireNonNullElse` or check up front, depending on the contract.
- **Single element**: a map with one entry. The merge function is never called.
- **Order**: ops first, then eng. The key order is `[ops, eng]`.
- **Null value**: throws `NullPointerException`.
- **Large input (1M rows)**: still O(n). Memory depends on the number of distinct keys, not the number of rows.

**Follow-ups to expect**
- *How do you keep all values for a duplicate key?* -> Use `groupingBy(key, mapping(value, toList()))`. This gives `Map<K, List<V>>` and no data is lost.
- *Why does `toMap` throw instead of overwriting like `put`?* -> The designers chose fail-fast so that accidental data loss is visible. You opt in to a policy with a merge function.
- *Can you use `toMap` in a parallel stream?* -> Yes, but the merge function must be associative and stateless. For high contention, consider `toConcurrentMap`.
- *How do you handle null values?* -> Filter them out first, or substitute a default with `Optional.ofNullable(v).orElse(...)`. The alternative is a manual loop with `HashMap.put`, which allows null values.

**60-second answer**
`Collectors.toMap` with two arguments throws `IllegalStateException` on a duplicate key, because overwriting silently would hide data loss. To handle it, I first ask what the business rule is: keep first, keep last, sum, or keep everything. For the first three I use the four-argument overload, `toMap(key, value, mergeFunction, LinkedHashMap::new)`. The merge function, such as `

### Q21 [mid] Java 8 streams: word frequency count and top 3 words
tags: java8, streams, groupingby, hashmap, sorting, word-frequency, coding, basics

**Start here: the concepts**
- **Hash map**: a structure that stores key -> value pairs and finds a key in about constant time. Here the key is a word and the value is how many times it appeared.
- **`groupingBy` + `counting`**: a stream collector that puts equal items into the same bucket (a map entry) and counts the items in each bucket. It is the stream version of "loop and do `map.merge(word, 1, Integer::sum)`".
- **Top-N**: picking the N biggest items by some measure, here the count.
- **Big-O**: a way to describe how the work grows with input size. n is the number of words and d is the number of distinct words. O(n) means the work grows in step with the input.
- **Tie-break**: a second rule used when two words have the same count. Without it, the output order for ties is not guaranteed.

**The live scenario**
You are building a search-analytics or log-analysis job. Millions of query strings or log messages arrive, and the dashboard needs "the 3 most frequent terms today". The interviewer usually says: *"Given a string of text, return the 3 most frequent words. Use Java 8 streams."* Then they ask what happens with ties, case, punctuation and very large input.

**What the interviewer is really checking**
Whether you ask clarifying questions (case, punctuation, ties, fewer than 3 words), start from a simple solution, and then state the cost of sorting versus a smarter selection. They also check that you handle null and empty input and write readable stream code.

**How I answer it**
1. **Clarify and restate.**
   - Input: a `String` of text. Output: up to 3 words with their counts, most frequent first.
   - I ask whether it is case-insensitive (I assume yes), what counts as a word (I assume letters and digits, with everything else as a separator), and how to break ties (I choose alphabetical so the result is deterministic).
   - Edge cases: null, blank, fewer than 3 distinct words, and N <= 0.
2. **Brute force.**
   - For each word, scan the whole list to count it, then repeat three times to find the maximum. That is O(n * d), roughly O(n^2) in the worst case. It is easy to write but too slow for large input.
3. **Better idea.**
   - Count in one pass with a hash map, because looking up and updating a key is about O(1). `groupingBy(identity(), counting())` does exactly that.
   - Then sort the d distinct entries by count descending, then by word ascending, and take the first 3 with `limit(3)`. Sorting only the distinct words, not all n words, keeps it cheap.
4. **Complexity.**
   - Time: O(n) to count plus O(d log d) to sort, so O(n + d log d).
   - Space: O(d) for the map.
   - For a fixed small N, a min-heap of size N would bring the selection step down to O(d log N). I mention it but keep the simple sort unless asked.
5. **Code.**

```java
import java.util.*;
import java.util.function.Function;
import java.util.stream.*;

class Solution {
    // Counts words, case-insensitive, splitting on anything that is not a-z or 0-9.
    static Map<String, Long> frequencies(String text) {
        if (text == null || text.isBlank()) return Map.of();
        return Arrays.stream(text.toLowerCase(Locale.ROOT).split("[^a-z0-9]+"))
                .filter(w -> !w.isEmpty()) // split can yield a leading empty token
                .collect(Collectors.groupingBy(Function.identity(), Collectors.counting()));
    }

    // Top n by count descending, ties broken by word ascending (deterministic).
    static List<Map.Entry<String, Long>> topN(String text, int n) {
        if (n <= 0) return List.of();
        Comparator<Map.Entry<String, Long>> order = (a, b) -> {
            int c = Long.compare(b.getValue(), a.getValue());
            return c != 0 ? c : a.getKey().compareTo(b.getKey());
        };
        return frequencies(text).entrySet().stream()
                .sorted(order)
                .limit(n)
                .collect(Collectors.toList());
    }

    static String fmt(List<Map.Entry<String, Long>> list) {
        return list.stream()
                .map(e -> e.getKey() + "=" + e.getValue())
                .collect(Collectors.joining(","));
    }

    static void check(String name, String expected, String actual) {
        if (!(expected.equals(actual))) {
            throw new AssertionError(name + ": expected [" + expected + "] but got [" + actual + "]");
        }
    }

    public static void main(String[] args) {
        check("typical", "the=3,fox=2,brown=1",
                fmt(topN("the quick brown fox jumps over the lazy dog the fox", 3)));
        check("null", "", fmt(topN(null, 3)));
        check("empty", "", fmt(topN("   ", 3)));
        check("single", "hello=1", fmt(topN("Hello", 3)));
        check("case and punctuation", "go=3,java=1", fmt(topN("Go, go! GO? java", 3)));
        check("fewer than n", "a=2,b=1", fmt(topN("a b a", 3)));
        check("tie order", "a=1,b=1,c=1", fmt(topN("b a c d", 3)));
        check("n is zero", "", fmt(topN("a b a", 0)));

        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < 50000; i++) sb.append("x ");
        for (int i = 0; i < 30000; i++) sb.append("y ");
        for (int i = 0; i < 20000; i++) sb.append("z ");
        check("large", "x=50000,y=30000,z=20000", fmt(topN(sb.toString(), 3)));

        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| Approach | Time | Space | Note |
|---|---|---|---|
| Brute force (rescan per word) | O(n * d), up to O(n^2) | O(d) | Fine only for tiny input |
| `groupingBy` + full sort | O(n + d log d) | O(d) | Short, readable, the default answer |
| `groupingBy` + min-heap of size N | O(n + d log N) | O(d + N) | Better when d is huge and N is small |
| Parallel stream | Faster only on very large input | O(d) | Merging maps has a cost; measure first |

- **Common mistakes:**
  - Forgetting to lowercase, so "The" and "the" are counted separately.
  - Splitting on `" "` only, so punctuation sticks to words and blank tokens appear.
  - Leaving ties unordered, which gives a flaky output.
  - Using `Collectors.counting()` and then treating the value as `int` (it is `Long`).
  - Using `toLowerCase()` without a locale. The Turkish locale turns "I" into a dotless i, so I use `Locale.ROOT`.
  - Not handling null input, which causes a NullPointerException.
  - Trying to sort a `HashMap` directly. A `HashMap` has no order, so you must sort its entries.

**Test cases I'd walk through**
- **Typical**: "the quick brown fox jumps over the lazy dog the fox" returns `the=3, fox=2, brown=1`. The third place is a tie among count-1 words, so alphabetical order picks "brown".
- **Null or blank**: returns an empty list, not an exception.
- **Single word**: "Hello" returns `hello=1`.
- **Case and punctuation**: "Go, go! GO? java" returns `go=3, java=1`.
- **Fewer distinct words than N**: "a b a" returns `a=2, b=1` and does not pad or fail.
- **Ties**: "b a c d" returns `a=1, b=1, c=1`, which proves the order is deterministic.
- **N = 0**: returns an empty list.
- **Large input**: 100,000 words with 3 distinct values returns `x=50000, y=30000, z=20000` quickly, because the sort touches only 3 entries.

**Follow-ups to expect**
- *How would you do this without sorting everything?* -> Keep a min-heap (`PriorityQueue`) of size N. Push each entry and pop the smallest when the size goes above N. That is O(d log N) and uses O(N) extra memory.
- *What if the text does not fit in memory?* -> Stream it line by line with `Files.lines` and update a map as you go. If even the distinct words do not fit, use partitioned counting (hash words into files or shards) or an approximate structure like Count-Min Sketch.
- *Would you use `parallelStream()` here?* -> Not by default. For small input the overhead is higher than the gain. For huge input use `groupingByConcurrent` and benchmark it, because the result must not depend on the order.

**60-second answer**
"First I'd confirm the rules: is it case-insensitive, what separates words, how to break ties, and what to return if there are fewer than 3 words. The naive way is to rescan the text for every word, which is O(n squared). Instead I count in one pass with a hash map, using `groupingBy(identity(), counting())`, which is O(n) because each lookup and update is about constant time. Then I sort only the distinct entries by count descending and by word ascending for ties, and take the first 3 with `limit`. That gives O(n + d log d) time, where d is the number of distinct words, and O(d) space. I would lowercase with `Locale.ROOT`, split on

### Q22 [mid] Reverse a linked list iteratively and recursively
tags: linked-list, reverse, pointers, recursion, iteration, in-place, coding, basics

**Start here: the concepts**
- **Singly linked list**: a chain of nodes. Each node holds a value and one `next` reference to the following node. The last node's `next` is `null`. There is no index access, so you can only walk forward from the head.
- **Three-pointer technique**: `prev` is the already-reversed part, `curr` is the node being processed, and `next` is a saved reference so we don't lose the rest of the list when we overwrite `curr.next`.
- **In-place**: we re-wire existing nodes and allocate no new ones.
- **Big-O**: a way to describe how work or memory grows with input size `n`. O(n) time means one step per node. O(1) space means a fixed number of extra variables. O(n) space means memory grows with the list, which is what the recursion call stack does.
- **Recursion**: a method that calls itself on a smaller problem (here, the list without its head). Each pending call takes a stack frame.

**The live scenario**
You are in a backend coding round. The interviewer says, "Implement your own `Node` class and reverse a singly linked list. Do it iteratively, then recursively." In real work the same pointer re-wiring appears when you build an LRU cache with a hand-rolled linked list, or when you reverse a chain of event or undo records. It also matters in code that processes a chain of handlers, because deep recursion on a long chain can cause a `StackOverflowError`.

**What the interviewer is really checking**
- Whether you ask clarifying questions (empty list? in-place? can I mutate?), then state the approach before typing.
- Whether you handle `null` and single-node lists, keep the pointer order correct (save `next` first), and can explain why the recursive version costs O(n) stack.

**How I answer it**
1. **Clarify and restate.**
   - Input is the head of a singly linked list and output is the head of the reversed list.
   - I ask whether I may modify the list in place (yes) and whether it can be empty (yes, return `null`).
   - Cycles are not expected.
   - Edge cases are `null`, one node, two nodes, and duplicate values.
2. **Brute force.**
   - Copy all values into an `ArrayList` (or push them on a stack), then rewrite the values, or build a new list, in reverse order.
   - Time is O(n) and space is O(n).
   - It works, but it uses extra memory and does not really reverse the links.
3. **Better idea (iterative).**
   - Walk the list once and flip each node's `next` to point backwards.
   - Before flipping, save `curr.next` in `next`, otherwise the rest of the list is lost.
   - Then set `curr.next = prev`, move `prev = curr`, and move `curr = next`.
   - When `curr` becomes `null`, `prev` is the new head.
4. **Recursive idea.**
   - Trust that `reverse(head.next)` returns the reversed rest of the list. The old `head.next` is now the tail of that reversed part.
   - So set `head.next.next = head` to append the head after it, then `head.next = null` so the head becomes the new tail.
   - Return the new head unchanged from the deepest call.
   - The base case is `head == null || head.next == null`.
5. **Complexity.**
   - Iterative: time O(n), space O(1).
   - Recursive: time O(n), space O(n) for the call stack.
6. **The code.**

```java
import java.util.ArrayList;
import java.util.List;

class Node {
    int val;
    Node next;
    Node(int val) { this.val = val; }
}

class Solution {
    static Node reverseIterative(Node head) {
        Node prev = null, curr = head;
        while (curr != null) {
            Node next = curr.next; // save before overwriting the link
            curr.next = prev;
            prev = curr;
            curr = next;
        }
        return prev;
    }

    static Node reverseRecursive(Node head) {
        if (head == null || head.next == null) return head;
        Node newHead = reverseRecursive(head.next);
        head.next.next = head; // node after head now points back to head
        head.next = null;      // head becomes the tail
        return newHead;
    }

    static Node build(int... vals) {
        Node dummy = new Node(0), tail = dummy;
        for (int v : vals) { tail.next = new Node(v); tail = tail.next; }
        return dummy.next;
    }

    static List<Integer> toList(Node head) {
        List<Integer> out = new ArrayList<>();
        for (Node n = head; n != null; n = n.next) out.add(n.val);
        return out;
    }

    static void expect(List<Integer> actual, List<Integer> expected, String name) {
        if (!(actual.equals(expected)))
            throw new AssertionError(name + ": expected " + expected + " but got " + actual);
    }

    public static void main(String[] args) {
        expect(toList(reverseIterative(null)), List.of(), "iter null");
        expect(toList(reverseRecursive(null)), List.of(), "rec null");
        expect(toList(reverseIterative(build(7))), List.of(7), "iter single");
        expect(toList(reverseRecursive(build(7))), List.of(7), "rec single");
        expect(toList(reverseIterative(build(1, 2))), List.of(2, 1), "iter two");
        expect(toList(reverseRecursive(build(1, 2, 3, 4, 5))), List.of(5, 4, 3, 2, 1), "rec five");
        expect(toList(reverseIterative(build(1, 2, 2, 3, 1))), List.of(1, 3, 2, 2, 1), "iter dups");

        // reversing twice gives back the original order
        expect(toList(reverseRecursive(reverseIterative(build(4, 5, 6)))), List.of(4, 5, 6), "round trip");

        // large list: iterative is safe at 100_000 nodes (recursion would risk StackOverflowError)
        int n = 100_000;
        int[] big = new int[n];
        for (int i = 0; i < n; i++) big[i] = i;
        Node r = reverseIterative(build(big));
        if (!(r.val == n - 1)) throw new AssertionError("large head wrong");
        int count = 0;
        for (Node c = r; c != null; c = c.next) count++;
        if (!(count == n)) throw new AssertionError("large length wrong: " + count);

        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| Approach | Time | Space | Note |
|---|---|---|---|
| Copy to list/stack, rebuild | O(n) | O(n) | Simple, but extra memory and allocation |
| Iterative three pointers | O(n) | O(1) | Best choice in production |
| Recursive | O(n) | O(n) stack | Elegant, but deep lists can throw `StackOverflowError` (roughly 10-20k frames on a default JVM stack, depending on frame size and `-Xss`) |

Common mistakes:
- Overwriting `curr.next` before saving it, which loses the rest of the list.
- Returning `head` instead of `prev` (iterative) or forgetting `head.next = null` (recursive). The recursive mistake leaves a cycle between the first two nodes.
- Not handling `null` input, which causes a `NullPointerException` on `head.next`.
- Using recursion on a very long list in a service. A stack overflow on a request thread is hard to recover from.

**Test cases I'd walk through**
- **Typical** `1->2->3->4->5` returns `5->4->3->2->1`.
- **Empty** (`null`) returns `null` and nothing crashes.
- **Single element** `7` returns `7` unchanged.
- **Two elements** `1->2` returns `2->1`, which exercises the smallest real re-wiring.
- **Duplicates** `1->2->2->3->1` returns `1->3->2->2->1`. Nodes are re-wired by reference, not by value, so duplicates do not matter.
- **Large input** of 100,000 nodes: the iterative version finishes in a single pass. The recursive version may overflow the stack, so I would mention that rather than run it.

**Follow-ups to expect**
- *How would you reverse only a sub-range, positions m to n?* -> Walk to node m-1, reverse the next (n-m+1) nodes with the same three-pointer loop, then reconnect both ends. Time is O(n) and space is O(1).
- *Can you make the recursive version safe for very long lists?* -> Not by itself, because Java has no tail-call optimisation. Use the iterative version, or run the recursion on a thread with a bigger stack size as a workaround.
- *How would you reverse a doubly linked list?* -> Swap `next` and `prev` on every node and return the old tail as the new head. Time is O(n) and space is O(1).

**60-second answer**
"First I'd confirm the list is singly linked, that I can change it in place, and that it may be empty. The brute force copies values into a stack or list and writes them back reversed. That is O(n) time but O(n) extra space. The better way is to flip the links in one pass with three pointers: `prev`, `curr` and `next`. For each node I save `next`, point `curr.next` at `prev`, then advance both pointers. When `curr` is null, `prev` is the new head. That is O(n) time and O(1) space. The recursive version reverses the rest of the list first, then sets `head.next.next = head` and `head.next = null`. It is also O(n) time, but O(n) stack space, so a very long list could throw `StackOverflowError`. I'd use the iterative version in production, and I'd test null, one node, two nodes and duplicates."

### Q23 [mid] Detect a cycle in a linked list and find its start
tags: linked-list, two-pointers, floyd-cycle, hashset, coding, basics

**Start here: the concepts**
- **Linked list:** a chain of nodes, where each node holds a value and a reference (`next`) to the following node. The last node normally points to `null`.
- **Cycle:** a node's `next` points back to an earlier node, so walking forward never reaches `null` and a naive loop runs forever.
- **Two pointers (tortoise and hare):** two references walk the same structure at different speeds. Slow moves 1 step and fast moves 2 steps.
- **Hash set:** a collection that answers "have I seen this before?" in about constant time. Nodes are compared by reference (`==`), not by value.
- **Big-O:** a way to describe how the work (time) or extra memory (space) grows with the number of nodes `n`. O(n) means it grows in proportion to `n`. O(1) means extra memory does not grow.

**The live scenario**
A job-scheduler or workflow service stores "next step" links between tasks. A bad config makes step 7 point back to step 3, and the worker thread spins at 100% CPU, so a queue of about 50k tasks stalls. You need to detect the loop and report which step starts it. The interviewer usually asks: "Given the head of a singly linked list, tell me if it has a cycle and return the node where the cycle begins, in O(1) extra space."

**What the interviewer is really checking**
Do you ask clarifying questions, state the HashSet brute force first, and then improve to O(1) space with Floyd's algorithm? Can you explain why the second phase finds the start, and do you handle the edge cases (null, one node, self-loop, whole list is the cycle)?

**How I answer it**
1. **Clarify and restate.**
   - Input: the head node of a singly linked list. Output: the node where the cycle starts, or `null` if there is no cycle.
   - Questions I would ask: Can the list be empty? Can a node point to itself? Can I modify the nodes? Is extra memory allowed? (Return the node, not its value, because values can repeat.)
2. **Brute force.**
   - Walk the list and put each visited node in a `HashSet`. The first node already in the set is the cycle start. If we reach `null`, there is no cycle.
   - This is O(n) time and O(n) space. It is correct and simple, and I would say so, but memory grows with the list.
3. **Better idea: Floyd's tortoise and hare, in two phases.**
   - **Phase 1, detect:** slow moves 1 step and fast moves 2. If there is no cycle, fast hits `null`. If there is a cycle, both end up inside it, and fast gains exactly 1 node per step on slow, so it cannot jump over slow and they must meet.
   - **Phase 2, find the start:** let `a` be the distance from head to the cycle start, `b` the distance from the cycle start to the meeting point, and `L` the cycle length.
     - Slow walked `a+b`. Fast walked `2(a+b)`, which is `a+b` plus some whole number of laps `k*L`.
     - So `a+b = k*L`, which means `a = k*L - b`. That is the distance from the meeting point forward to the cycle start, plus whole laps.
     - Therefore, if one pointer restarts at head and the other stays at the meeting point, both moving 1 step at a time, they meet exactly at the cycle start.
4. **Complexity.** Time is O(n): the slow pointer travels at most `a + L` steps in phase 1 and at most `a` in phase 2. Space is O(1): two or three references.
5. **Code.**

```java
import java.util.*;

class Node {
    int val;
    Node next;
    Node(int val) { this.val = val; }
}

class Solution {
    // Floyd: O(n) time, O(1) space
    static Node detectCycle(Node head) {
        Node slow = head, fast = head;
        while (fast != null && fast.next != null) {
            slow = slow.next;
            fast = fast.next.next;
            if (slow == fast) {              // phase 1: met inside the cycle
                Node p = head;
                while (p != slow) {          // phase 2: both step 1 until they meet
                    p = p.next;
                    slow = slow.next;
                }
                return p;
            }
        }
        return null;
    }

    // Brute force: O(n) time, O(n) space (used to cross-check)
    static Node detectCycleSet(Node head) {
        Set<Node> seen = new HashSet<>();    // Node has no equals/hashCode override: reference identity
        for (Node cur = head; cur != null; cur = cur.next) {
            if (!seen.add(cur)) return cur;
        }
        return null;
    }

    // Builds n nodes; tail points to nodes[pos] if pos >= 0. Values repeat on purpose.
    static Node[] build(int n, int pos) {
        Node[] nodes = new Node[n];
        for (int i = 0; i < n; i++) {
            nodes[i] = new Node(i % 3);
            if (i > 0) nodes[i - 1].next = nodes[i];
        }
        if (n > 0 && pos >= 0) nodes[n - 1].next = nodes[pos];
        return nodes;
    }

    static void check(boolean cond, String msg) {
        if (!(cond)) throw new AssertionError(msg);
    }

    public static void main(String[] args) {
        check(detectCycle(null) == null, "null list");
        Node[] one = build(1, -1);
        check(detectCycle(one[0]) == null, "single node, no cycle");
        Node[] self = build(1, 0);
        check(detectCycle(self[0]) == self[0], "single node self-loop");
        Node[] linear = build(5, -1);
        check(detectCycle(linear[0]) == null, "no cycle");
        Node[] whole = build(6, 0);
        check(detectCycle(whole[0]) == whole[0], "whole list is the cycle");
        Node[] mid = build(6, 3);
        check(detectCycle(mid[0]) == mid[3], "cycle starts at index 3");
        Node[] two = build(2, 1);
        check(detectCycle(two[0]) == two[1], "two nodes, tail loops to itself");
        Node[] big = build(100_000, 99_998);
        check(detectCycle(big[0]) == big[99_998], "large input");
        check(detectCycle(big[0]) == detectCycleSet(big[0]), "matches brute force");
        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| Approach | Time | Space | Note |
|---|---|---|---|
| HashSet of nodes | O(n) | O(n) | Simplest and hard to get wrong, but memory grows with the list |
| Floyd's two pointers | O(n) | O(1) | Needs the phase 2 reasoning; no extra memory |

- Common mistakes:
  - Checking only `fast != null` and not `fast.next != null`, which causes a `NullPointerException` on odd-length lists.
  - Comparing `val` instead of node references. Values can repeat, so this gives false positives.
  - Returning the meeting point instead of running phase 2. The meeting point is usually not the cycle start.
  - Putting nodes in a `HashSet` after overriding `equals`/`hashCode` on value, which breaks the brute force. Use identity.
  - Using recursion for traversal. A 100k-node list would overflow the stack, so use loops.
- Large lists are fine because the solution is iterative and uses constant memory.

**Test cases I'd walk through**
- **Typical:** 6 nodes, tail links to index 3. It returns the node at index 3.
- **Empty or null:** returns `null`, and the loop condition never dereferences null.
- **Single element:** no cycle returns `null`. A self-loop returns that same node (slow and fast meet at head, and phase 2 returns immediately).
- **Duplicate values:** values like 0,1,2,0,1,2 do not confuse it because it compares references.
- **Whole list is a cycle:** tail links to head and it returns the head.
- **Large input:** 100,000 nodes with the cycle near the end returns the right node, with no stack overflow and no extra memory.

**Follow-ups to expect**
- *How do you find the cycle length?* -> After the meeting point, keep one pointer fixed and move the other until it returns to it, counting the steps.
- *How do you remove the cycle?* -> Find the start, then walk from it until `node.next == start` and set that `next` to `null`.
- *Why speeds 1 and 2, not 1 and 3?* -> With a speed difference of 1, the gap shrinks by exactly 1 each step, so fast cannot skip over slow. Larger differences can skip it, and meeting is no longer guaranteed in a bounded number of laps.
- *Where else does this idea appear?* -> "Find the duplicate number" in an array treats `nums[i]` as a next pointer, and it also detects loops in iterative sequences.

**60-second answer**
"First I'd confirm the input is a singly linked list head, that I return the start node or null, and that I compare nodes by reference. The brute force is a HashSet of visited nodes: the first repeat is the cycle start. That is O(n) time but O(n) space. To get O(1) space I use Floyd's tortoise and hare: slow moves 1 and fast moves 2. If fast reaches null there is no cycle. Otherwise they meet inside the cycle, because the gap closes by 1 each step. Then I put one pointer at head and keep one at the meeting point, and move both one step at a time. They meet at the cycle start, because the distance from head to the start equals the distance from the meeting point to the start, pl

### Q24 [mid] Find the middle element of a linked list in one pass
tags: linked-list, two-pointers, fast-slow-pointers, singly-linked-list, java, coding, basics

**Start here: the concepts**
- **Singly linked list:** a chain of nodes, where each node holds a value and a reference to the next node. You cannot jump to index `i`. You must walk from the head, so there is no `get(i)` in O(1) as with an array.
- **Two pointers (slow and fast):** two references walk the same list at different speeds. Here `slow` moves 1 node per step and `fast` moves 2.
- **Why it finds the middle:** when `fast` has covered the whole list, `slow` has covered exactly half of it, so `slow` is standing on the middle.
- **Big-O:** a way to describe how work grows with input size `n` (the number of nodes). O(n) means the work grows in proportion to the list length. O(1) extra space means the memory we add does not grow with `n`.
- **Even length:** there are two middle nodes. We must pick one and say which. The common convention is the second middle, so `[1,2,3,4]` returns the node with 3.

**The live scenario**
You are splitting a long chain of records, for example a linked list of pending retry tasks or a custom queue, into two halves so two workers can process them. You only have the head, and the list does not store its size. The interviewer usually says: "Given the head of a singly linked list, return the middle node. Do it in one pass. What if the length is even?"

**What the interviewer is really checking**
Do you ask about even length, null input and what to return, and do you start with the simple two-pass idea? Then can you improve it with slow/fast pointers, explain why it works, and handle the loop condition without a `NullPointerException`?

**How I answer it**
1. **Clarify and restate.**
   - Input: the head of a singly linked list. Output: the middle node.
   - For even length, which middle? I would say "second middle" and mention that the first middle is a one-line change.
   - Empty list (`null`): return `null`.
   - Can the list have a cycle? I would assume not.
   - Is `n` huge? I would use loops, not recursion, to avoid stack overflow.
2. **Brute force.**
   - Pass 1: count the nodes to get `n`.
   - Pass 2: walk `n / 2` steps from the head.
   - That is O(n) time and O(1) space, but it traverses the list twice.
   - Another variant copies all nodes into an `ArrayList` and reads index `n / 2`. That is one pass, but O(n) extra space.
3. **Better idea.**
   - Start `slow` and `fast` at the head.
   - While `fast` and `fast.next` are both non-null, move `slow` one step and `fast` two steps.
   - `fast` moves twice as fast, so when it falls off the end, `slow` has moved half as far.
   - With odd `n`, `fast` stops on the last node and `slow` is the exact middle.
   - With even `n`, `fast` becomes `null` and `slow` is the second middle.
   - The condition checks `fast != null` first and `fast.next != null` second, so we never dereference `null`.
4. **Complexity.** Time is O(n): `fast` takes about n/2 steps and `slow` about n/2. Space is O(1): two references.
5. **Code.**

```java
class Node {
    final int val;
    Node next;
    Node(int val) { this.val = val; }
}

class Solution {
    // Second middle for even length; null for an empty list.
    static Node middle(Node head) {
        Node slow = head, fast = head;
        while (fast != null && fast.next != null) {
            slow = slow.next;
            fast = fast.next.next;
        }
        return slow;
    }

    // First middle for even length (stop one step earlier).
    static Node firstMiddle(Node head) {
        if (head == null) return null;
        Node slow = head, fast = head;
        while (fast.next != null && fast.next.next != null) {
            slow = slow.next;
            fast = fast.next.next;
        }
        return slow;
    }

    static Node build(int... vals) {
        Node dummy = new Node(0), tail = dummy;
        for (int v : vals) { tail.next = new Node(v); tail = tail.next; }
        return dummy.next;
    }

    static Node range(int n) {
        Node dummy = new Node(0), tail = dummy;
        for (int i = 0; i < n; i++) { tail.next = new Node(i); tail = tail.next; }
        return dummy.next;
    }

    static Node at(Node head, int idx) {
        while (idx-- > 0) head = head.next;
        return head;
    }

    public static void main(String[] args) {
        Node odd = build(1, 2, 3, 4, 5);
        if (!(middle(odd).val == 3)) throw new AssertionError("odd length");
        Node even = build(1, 2, 3, 4);
        if (!(middle(even).val == 3)) throw new AssertionError("even length, second middle");
        if (!(firstMiddle(even).val == 2)) throw new AssertionError("even length, first middle");
        if (!(middle(build(7)).val == 7)) throw new AssertionError("single node");
        if (!(middle(build(1, 2)).val == 2)) throw new AssertionError("two nodes");
        if (!(middle(null) == null)) throw new AssertionError("null list");
        Node dup = build(5, 5, 5, 5, 5);
        if (!(middle(dup) == at(dup, 2))) throw new AssertionError("duplicates, identity");
        Node big = range(1_000_000);
        if (!(middle(big).val == 500_000)) throw new AssertionError("large list");
        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| Approach | Time | Space | Note |
|---|---|---|---|
| Count, then walk n/2 | O(n), about 1.5n steps | O(1) | Simple and safe, two passes |
| Copy to `ArrayList`, index n/2 | O(n) | O(n) | One pass, but wasteful memory on a large list |
| Slow/fast pointers | O(n), about n steps by `fast` | O(1) | One pass, the expected answer |

- **Common mistakes:**
  - Writing `fast.next != null && fast != null`, which throws `NullPointerException` on an empty list.
  - Not stating which middle is returned for even length.
  - Using recursion on a very long list, which risks `StackOverflowError`.
  - Calling `size()` on a custom node chain that has no such method.
- **Honest note:** "one pass" does not make it asymptotically faster than counting. It is still O(n), but it needs no counting step and works on streams of nodes you cannot revisit.

**Test cases I'd walk through**
- **Typical odd:** `[1,2,3,4,5]` returns the node with 3.
- **Typical even:** `[1,2,3,4]` returns the node with 3 (second middle). The first-middle variant returns 2.
- **Empty or null:** `null` returns `null`, with no exception.
- **Single element:** `[7]` returns 7, because the loop never runs.
- **Two elements:** `[1,2]` returns 2 (second middle).
- **Duplicates:** `[5,5,5,5,5]` returns the node at index 2. I compare node identity, not just the value, since values alone cannot prove the right node.
- **Large input:** 1,000,000 nodes returns the node with value 500,000, in a loop with no recursion and constant extra memory.

**Follow-ups to expect**
- *How do you return the first middle for even length?* -> Change the loop condition to `fast.next != null && fast.next.next != null`, so `slow` stops one step earlier.
- *How do you detect a cycle in a linked list?* -> Use the same slow/fast pointers (Floyd's algorithm). If `fast` ever meets `slow`, there is a cycle. If `fast` reaches `null`, there is none.
- *How would you use this to sort a linked list?* -> Merge sort. Find the middle, split the list there, sort each half recursively, then merge. It is O(n log n) time.

**60-second answer**
"First I would confirm it is a singly linked list with no size field, that I return the node and not the value, and that for even length I return the second middle. A null head returns null. The simple way is to count the nodes and then walk n/2 steps. That is O(n) time and O(1) space, but it takes two passes. The better way is slow and fast pointers. Both start at the head, slow moves one step and fast moves two, and I loop while fast and fast.next are not null. When fast reaches the end, slow has covered half the distance, so it sits on the middle. For even length it lands on the second middle. That is O(n) time and O(1) space, with a single traversal. I would test odd, even, one node, two nodes, null and a million-node list."

### Q25 [senior] Validate a binary search tree
tags: binary-search-tree, recursion, tree-traversal, inorder, bounds, validation, coding, basics

**Start here: the concepts**
- **Binary search tree (BST):** a tree where each node has at most two children. For every node, all values in its left subtree are smaller and all values in its right subtree are larger. The rule covers the whole subtree, not just the direct children.
- **Recursion with bounds:** each call carries an allowed open interval `(lo, hi)`. Going left tightens `hi` to the current value. Going right tightens `lo` to the current value.
- **In-order traversal:** visit left, then node, then right. On a valid BST this yields values in strictly increasing order. That gives a second approach: walk in order and check that each value is greater than the previous one.
- **Big-O:** a way to describe how work or memory grows with input size `n` (the number of nodes). O(n) means roughly one unit of work per node. O(h) means memory proportional to the tree height `h`.
- **Stack depth:** recursion uses the call stack, so a skewed tree (h = n) can cause `StackOverflowError`. An explicit `ArrayDeque` stack avoids this.

**The live scenario**
You keep an in-memory sorted index, such as a price-band tree or a range-lookup structure for routing rules. It is rebuilt from a snapshot after a deploy, and a bad merge could corrupt it. A startup health check must confirm the ordering invariant before the service takes traffic. The interviewer usually asks: "Given the root of a binary tree, determine whether it is a valid BST." Then they ask: "Why does checking only each node's children fail?"

**What the interviewer is really checking**
Whether you spot that the BST rule applies to entire subtrees, not just parent-child pairs. They also look at how you handle duplicates and `Integer.MIN_VALUE`/`MAX_VALUE` (use `long` bounds), and whether you know the recursion-depth risk on skewed trees.

**How I answer it**
1. **Clarify and restate.** Input is the root of a binary tree of `int` values. Output is a boolean. I would ask:
   - Are duplicates allowed? I assume not (strict BST), and I say so explicitly.
   - Can the tree be empty? An empty tree is valid.
   - Can values be `Integer.MIN_VALUE` or `Integer.MAX_VALUE`?
   - How deep can the tree be?
2. **Brute force.** For every node, scan its whole left subtree for a value >= node and its whole right subtree for a value <= node. This is O(n^2) time in a skewed tree, and O(n log n) in a balanced one. It is correct but repeats work.
3. **Better idea.** The naive shortcut is to check only `left.val < node.val < right.val`. That is wrong. In `5 -> right 6 -> left 3`, each parent-child pair looks fine, yet 3 sits in the right subtree of 5 and breaks the rule. So I pass down the allowed range. Each node must satisfy `lo < val < hi`. Going left sets `hi = node.val`, and going right sets `lo = node.val`. Each node is checked once against all its ancestors' constraints. I use `long` bounds so a node holding `Integer.MIN_VALUE` or `MAX_VALUE` does not clash with sentinel values.
4. **Complexity.** Time is O(n), since every node is visited once and the check stops at the first violation. Space is O(h) for the call stack: O(log n) for a balanced tree, O(n) for a skewed one. The iterative in-order version has the same Big-O but avoids stack overflow on deep trees.
5. **The code.**

```java
import java.util.ArrayDeque;
import java.util.Deque;

class TreeNode {
    int val;
    TreeNode left, right;
    TreeNode(int val) { this.val = val; }
    TreeNode(int val, TreeNode left, TreeNode right) {
        this.val = val; this.left = left; this.right = right;
    }
}

class Solution {
    // Recursive: pass an open interval (lo, hi) down the tree. long avoids int-edge clashes.
    static boolean isValidBST(TreeNode root) {
        return check(root, Long.MIN_VALUE, Long.MAX_VALUE);
    }

    private static boolean check(TreeNode n, long lo, long hi) {
        if (n == null) return true;
        if (n.val <= lo || n.val >= hi) return false; // strict: duplicates are invalid
        return check(n.left, lo, n.val) && check(n.right, n.val, hi);
    }

    // Iterative in-order: values must be strictly increasing. Safe for very deep trees.
    static boolean isValidBSTIterative(TreeNode root) {
        Deque<TreeNode> stack = new ArrayDeque<>();
        long prev = Long.MIN_VALUE;
        TreeNode cur = root;
        while (cur != null || !stack.isEmpty()) {
            while (cur != null) { stack.push(cur); cur = cur.left; }
            cur = stack.pop();
            if (cur.val <= prev) return false;
            prev = cur.val;
            cur = cur.right;
        }
        return true;
    }

    private static void expect(boolean expected, TreeNode root, String name) {
        if (isValidBST(root) != expected)
            throw new AssertionError("recursive failed: " + name);
        if (isValidBSTIterative(root) != expected)
            throw new AssertionError("iterative failed: " + name);
    }

    public static void main(String[] args) {
        expect(true, null, "empty tree");
        expect(true, new TreeNode(7), "single node");
        expect(true, new TreeNode(2, new TreeNode(1), new TreeNode(3)), "simple valid");
        expect(false, new TreeNode(5, new TreeNode(1),
                new TreeNode(4, new TreeNode(3), new TreeNode(6))), "right child 4 < root 5");
        // Every parent-child pair is fine, but 3 is in the right subtree of 5.
        expect(false, new TreeNode(5, new TreeNode(4),
                new TreeNode(6, new TreeNode(3), new TreeNode(7))), "deep violation");
        expect(false, new TreeNode(2, new TreeNode(2), new TreeNode(2)), "duplicates");
        expect(true, new TreeNode(Integer.MIN_VALUE, null, new TreeNode(Integer.MAX_VALUE)),
                "int extremes");
        expect(true, new TreeNode(Integer.MAX_VALUE, new TreeNode(Integer.MIN_VALUE), null),
                "int extremes left");

        // Deep right-leaning chain: the iterative version must cope with 100000 levels.
        TreeNode root = new TreeNode(0), tail = root;
        for (int i = 1; i < 100_000; i++) { tail.right = new TreeNode(i); tail = tail.right; }
        if (!isValidBSTIterative(root)) throw new AssertionError("deep chain");
        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| Approach | Time | Space | Note |
|---|---|---|---|
| Brute force (scan subtrees per node) | O(n^2) worst case | O(h) | Correct but slow |
| Recursive with bounds | O(n) | O(h) | Clean, but deep skew can overflow the stack |
| Iterative in-order | O(n) | O(h) | Safe on deep trees, slightly more code |

- **Common mistake 1:** comparing only a node with its direct children, which misses violations deeper in a subtree.
- **Common mistake 2:** using `int` bounds with `Integer.MIN_VALUE` or `MAX_VALUE` as sentinels. A legitimate node holding that value is then rejected or accepted wrongly. Use `long` or null-able `Integer` bounds.
- **Common mistake 3:** using `<` instead of `<=` in the rejection check, which silently accepts duplicates. Always confirm the duplicate policy.
- **Common mistake 4:** in-order with a global `Integer prev` initialised to `Integer.MIN_VALUE` fails when the first value equals it.
- **Production note:** on a very deep tree, recursion in a request thread may overflow the stack, so prefer the iterative version there.

**Test cases I'd walk through**
- **Typical valid** `[2,1,3]` returns true.
- **Empty tree (null)** returns true. There is nothing to violate.
- **Single node** returns true.
- **Typical invalid** `[5,1,4,null,null,3,6]` returns false, because 4 is in the right subtree of 5 yet less than 5.
- **Deep violation** `[5,4,6,null,null,3,7]` returns false. A children-only check would wrongly return true.
- **Duplicates** `[2,2,2]` returns false under the strict definition.
- **Int extremes** (a node holding `Integer.MIN_VALUE` or `MAX_VALUE`) returns true when ordered correctly.
- **Large input:** a 100,000-node chain returns true with the iterative version, and the recursive one might overflow the stack.

**Follow-ups to expect**
- *What if duplicates are allowed on one side, for example left <= node?* -> Make the bound inclusive on that side only: left uses `hi` inclusive, right stays strict. State the convention before coding.
- *How do you avoid stack overflow on a skewed tree?* -> Use the iterative in-order traversal with an `ArrayDeque`, or Morris traversal for O(1) extra space, which temporarily rewires pointers.
- *How would you validate a huge tree that is stored on disk or streamed?* -> Stream the in-order sequence and keep only the previous value, so memory is O(1) beyond the traversal state.

**60-second answer**
"First I would confirm the definition: left subtree strictly smaller, right subtree strictly larger, duplicates invalid, and an empty tree valid.

### Q26 [senior] Level-order (breadth-first) traversal of a binary tree
tags: binary-tree, bfs, queue, level-order, traversal, java-collections, coding, basics

**Start here: the concepts**
- **Binary tree**: each node holds a value and up to two children (`left`, `right`). `null` means "no child".
- **Breadth-first search (BFS)**: visit nodes level by level. Visit everything at depth 0, then depth 1, then depth 2, and so on.
- **Queue**: a first-in, first-out line. Nodes discovered earlier are processed earlier, which gives the level-by-level order. In Java use `ArrayDeque` through the `Deque` or `Queue` interface.
- **Level grouping**: before processing a level, record `queue.size()`. That number is exactly how many nodes belong to the current level.
- **Big-O**: a way to say how work or memory grows with input size. `n` is the number of nodes, and `w` is the widest level.
- **Recursion depth**: how many method calls are stacked at once. A very deep tree can overflow the stack, which matters for the DFS alternative.

**The live scenario**
You are building an org-chart or category-menu service. Each manager or category has children, and the UI wants "all of level 1, then all of level 2" so it can render rows. The same shape appears when you walk a dependency tree breadth-first to find the nearest failing service. The interviewer usually says: "Given the root of a binary tree, return its values level by level, as a list of lists."

**What the interviewer is really checking**
Do you ask about null and empty input, and do you recognise that "level by level" means a queue rather than recursion? At senior level, can you also explain how you separate levels, state O(n) time and O(w) space, and discuss the DFS alternative and the deep-tree stack risk?

**How I answer it**
1. **Clarify and restate.**
   - Input: the root `TreeNode`. Output: `List<List<Integer>>`, one inner list per level, left to right.
   - Questions I would ask:
     - Can the root be null? (Return an empty list.)
     - Can values be duplicated or negative? (Yes, and it does not matter.)
     - Is the tree balanced? (Not guaranteed, so a skewed tree with a million nodes is possible.)
2. **Brute force.**
   - Compute the height, then for each level `d` from 0 to height run a separate traversal that collects the nodes at depth `d`.
   - That is O(n) per level. A skewed tree has n levels, so the total is O(n^2) time.
3. **Better idea.**
   - Use one pass with a queue. Put the root in. While the queue is not empty, take `size = queue.size()`. Pop exactly `size` nodes, which is one full level.
   - Add each popped value to the level's list, and push its non-null children.
   - Those children form the next level, and they sit behind the current level's nodes in the queue, so levels never mix.
   - Every node enters and leaves the queue once, which is why this is linear.
4. **Complexity.**
   - Time: O(n), because each node is visited once.
   - Space: O(w) for the queue, up to about n/2 for a complete tree's last level. The result itself is O(n).
5. **Code.**

```java
import java.util.*;

class TreeNode {
    int val;
    TreeNode left, right;
    TreeNode(int val) { this.val = val; }
    TreeNode(int val, TreeNode left, TreeNode right) {
        this.val = val; this.left = left; this.right = right;
    }
}

class Solution {
    static List<List<Integer>> levelOrder(TreeNode root) {
        List<List<Integer>> result = new ArrayList<>();
        if (root == null) return result;
        Deque<TreeNode> queue = new ArrayDeque<>(); // ArrayDeque rejects null, so only add non-null nodes
        queue.add(root);
        while (!queue.isEmpty()) {
            int size = queue.size(); // snapshot = number of nodes in this level
            List<Integer> level = new ArrayList<>(size);
            for (int i = 0; i < size; i++) {
                TreeNode node = queue.poll();
                level.add(node.val);
                if (node.left != null) queue.add(node.left);
                if (node.right != null) queue.add(node.right);
            }
            result.add(level);
        }
        return result;
    }

    static void check(boolean cond, String msg) {
        if (!(cond)) throw new AssertionError(msg);
    }

    static void eq(Object actual, Object expected, String name) {
        if (!(actual.equals(expected)))
            throw new AssertionError(name + ": expected " + expected + " but got " + actual);
    }

    public static void main(String[] args) {
        eq(levelOrder(null), List.of(), "null root");
        eq(levelOrder(new TreeNode(1)), List.of(List.of(1)), "single node");

        TreeNode t = new TreeNode(3, new TreeNode(9),
                new TreeNode(20, new TreeNode(15), new TreeNode(7)));
        eq(levelOrder(t), List.of(List.of(3), List.of(9, 20), List.of(15, 7)), "typical");

        TreeNode d = new TreeNode(2,
                new TreeNode(2, new TreeNode(-1), null),
                new TreeNode(2, null, new TreeNode(-1)));
        eq(levelOrder(d), List.of(List.of(2), List.of(2, 2), List.of(-1, -1)),
                "duplicates, negatives, missing children");

        TreeNode left = new TreeNode(1, new TreeNode(2, new TreeNode(3), null), null);
        eq(levelOrder(left), List.of(List.of(1), List.of(2), List.of(3)), "left skewed");

        // 100_000 levels deep: BFS must not overflow the stack
        TreeNode root = new TreeNode(0), cur = root;
        for (int i = 1; i < 100_000; i++) { cur.right = new TreeNode(i); cur = cur.right; }
        List<List<Integer>> deep = levelOrder(root);
        check(deep.size() == 100_000 && deep.get(99_999).get(0) == 99_999, "deep skewed tree");

        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| Approach | Time | Space | Notes |
|---|---|---|---|
| Brute force (one traversal per level) | O(n^2) worst case | O(h) recursion | Simple but repeats work |
| Queue BFS (final) | O(n) | O(w) | Iterative, so no stack overflow |
| Recursive DFS with a depth parameter | O(n) | O(h) stack | Fine for balanced trees, risky for skewed ones |

- **Common mistakes**
  - Reading `queue.size()` inside the loop condition. The size changes as children are added, so levels get mixed.
  - Adding null children to an `ArrayDeque`, which throws `NullPointerException`.
  - Forgetting the null-root check.
  - Using `LinkedList` as the queue. It works but allocates more per element than `ArrayDeque`.
- **Memory**: a very wide tree makes the queue large. On huge trees, stream each level out instead of holding the whole result.
- **Monitoring**: in a service, log the node count and the elapsed time per traversal. Alert on unusually deep or wide trees, since the input shape drives the cost.

**Test cases I'd walk through**
- **Typical** `3 / (9, 20 / (15, 7))`: returns `[[3],[9,20],[15,7]]`.
- **Null root**: returns `[]`, not null and not `[[]]`.
- **Single node**: returns `[[1]]`.
- **Duplicates and negatives with missing children**: values are never used as keys, so the result is `[[2],[2,2],[-1,-1]]`.
- **Skewed tree**: one node per level, so `[[1],[2],[3]]`. Queue size stays at 1.
- **Large input (100,000 levels)**: runs in linear time with no stack overflow. A recursive DFS could fail here.

**Follow-ups to expect**
- *Return the levels in zigzag order.* -> Same BFS, but reverse every other level's list, or use `addFirst` on a `LinkedList` for odd levels. Still O(n).
- *Return only the right-side view.* -> Same BFS, keep only the last node of each level (`i == size - 1`).
- *Can you do it with recursion?* -> Yes. Pass `depth` down, and when `depth == result.size()` add a new list, then append the value to `result.get(depth)`. It is O(n) time and O(h) stack, which is risky for skewed trees.
- *What about an n-ary tree?* -> Loop over `node.children` instead of left and right. Nothing else changes.

**60-second answer**
"First I'd confirm that a null root returns an empty list and that the output is a list of lists, one per level. The brute force finds the height and runs a separate traversal for each depth, which is O(n^2) on a skewed tree. Instead I use a queue, because BFS naturally visits nodes level by level. At the start of each round I record the queue size, which is exactly the number of nodes in that level. I pop that many nodes, record their values, and push their non-null children for the next round. Each node is enqueued and dequeued once, so time is O(n). Space is O(w) for the queue, where w is the widest level, plus the output. I'd use `ArrayDeque` because it is faster than `LinkedList` and does not accept nulls, so I only add non-null children. Being iterative, it also avoids stack overflow

### Q27 [senior] Implement an LRU cache
tags: lru-cache, hashmap, doubly-linked-list, linkedhashmap, o1, coding, basics

**Start here: the concepts**
- **Cache**: a small, fast store that keeps recent results so we avoid a slow call (database, REST service).
- **LRU (Least Recently Used)**: when the cache is full, evict the entry that has gone unused the longest. Both `get` and `put` count as "use".
- **Hash map**: key to value lookup in O(1) on average.
- **Doubly linked list**: each node points to its previous and next node. If you hold a reference to a node, you can remove it or move it in O(1), with no scanning.
- **Sentinel nodes**: dummy `head` and `tail` nodes that remove all the "is this the first or last node?" null checks.
- **Big-O**: how work grows with input size. O(1) means the cost does not grow with the number of cached entries. O(n) means it grows in proportion.
- **The trick**: the map finds a node in O(1), and the list orders nodes by recency in O(1). Together they give O(1) for everything.

**The live scenario**
A product-catalog service takes 3,000 requests/s, and each database lookup costs about 20 ms. About 10% of the products get 90% of the traffic, so we keep the hottest 10,000 products in memory. Memory must stay bounded, so we need an eviction rule. The interviewer usually says: *"Design and implement an LRU cache with `get` and `put`, both O(1). Don't use a library cache."*

**What the interviewer is really checking**
Whether you ask about capacity, null handling and thread safety, then reason from a naive O(n) design to the map plus linked-list combination. They also want pointer-manipulation code with no bugs (sentinels, updating an existing key, evicting from the correct end). A senior candidate should mention `LinkedHashMap` as the production shortcut and say when to use it.

**How I answer it**
1. **Clarify and restate.**
   - Input: `get(key)` and `put(key, value)` on a fixed-capacity cache.
   - Output: `get` returns the value, or `null` on a miss. Both operations mark the key as most recently used.
   - Questions to ask: What happens at capacity <= 0 (I will throw)? Are null values allowed (I will say no, because `null` means a miss)? Does it need to be thread-safe (not in the base version)? Is `put` on an existing key an update plus a refresh (yes)?
2. **Brute force.** Keep a list or array ordered by recency.
   - A lookup scans for the key, which is O(n).
   - Moving the entry to the front shifts elements, which is also O(n).
   - A map alone gives O(1) lookup but no way to find the oldest entry without scanning all of them.
3. **Better idea.**
   - A `HashMap<K, Node>` finds any entry in O(1).
   - A doubly linked list keeps entries in recency order: the node after `head` is the most recent, and the node before `tail` is the least recent.
   - On a hit, unlink the node and re-insert it after `head`. Because we hold the node reference from the map, no scan is needed.
   - On insert at capacity, remove `tail.prev` and delete its key from the map. This is why the node stores its key.
4. **Complexity.** `get` and `put` are O(1) average time. Space is O(capacity) for the map entries and nodes.
5. **Code.**

```java
import java.util.HashMap;
import java.util.Map;

class Solution {
    static final class LRUCache<K, V> {
        private final class Node {
            final K key; V val; Node prev, next;
            Node(K k, V v) { key = k; val = v; }
        }
        private final int capacity;
        private final Map<K, Node> map = new HashMap<>();
        private final Node head = new Node(null, null); // sentinel: next = most recent
        private final Node tail = new Node(null, null); // sentinel: prev = least recent

        LRUCache(int capacity) {
            if (capacity <= 0) throw new IllegalArgumentException("capacity must be > 0");
            this.capacity = capacity;
            head.next = tail;
            tail.prev = head;
        }
        V get(K key) {
            Node n = map.get(key);
            if (n == null) return null;
            unlink(n);
            addFirst(n);
            return n.val;
        }
        void put(K key, V val) {
            Node n = map.get(key);
            if (n != null) { n.val = val; unlink(n); addFirst(n); return; }
            if (map.size() == capacity) {
                Node lru = tail.prev;
                unlink(lru);
                map.remove(lru.key); // why the node stores its key
            }
            n = new Node(key, val);
            map.put(key, n);
            addFirst(n);
        }
        int size() { return map.size(); }
        private void unlink(Node n) { n.prev.next = n.next; n.next.prev = n.prev; }
        private void addFirst(Node n) {
            n.prev = head; n.next = head.next;
            head.next.prev = n; head.next = n;
        }
    }

    static void check(boolean cond, String msg) {
        if (!(cond)) throw new AssertionError(msg);
    }

    public static void main(String[] args) {
        LRUCache<Integer, String> c = new LRUCache<>(2);
        check(c.get(1) == null, "miss on empty cache");
        c.put(1, "a"); c.put(2, "b");
        check("a".equals(c.get(1)), "hit refreshes key 1");
        c.put(3, "c"); // evicts 2, the least recently used
        check(c.get(2) == null, "key 2 evicted");
        check("c".equals(c.get(3)) && "a".equals(c.get(1)), "3 and 1 remain");

        LRUCache<Integer, String> u = new LRUCache<>(2);
        u.put(1, "x"); u.put(1, "y");
        check(u.size() == 1 && "y".equals(u.get(1)), "update does not grow cache");

        LRUCache<Integer, String> r = new LRUCache<>(2);
        r.put(1, "a"); r.put(2, "b"); r.put(1, "a2"); r.put(3, "c");
        check(r.get(2) == null && "a2".equals(r.get(1)), "update refreshes recency");

        LRUCache<Integer, String> one = new LRUCache<>(1);
        one.put(1, "a"); one.put(2, "b");
        check(one.get(1) == null && "b".equals(one.get(2)), "capacity 1");

        boolean threw = false;
        try { new LRUCache<Integer, String>(0); } catch (IllegalArgumentException e) { threw = true; }
        check(threw, "capacity 0 rejected");

        LRUCache<Integer, Integer> big = new LRUCache<>(1000);
        for (int i = 0; i < 100_000; i++) big.put(i, i);
        check(big.size() == 1000 && big.get(0) == null && big.get(99_999) == 99_999, "large input");
        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| Approach | get / put | Space | Note |
|---|---|---|---|
| List or array ordered by recency | O(n) | O(n) | Scan and shift on every access |
| HashMap + doubly linked list (above) | O(1) avg | O(capacity) | More code, easy to get pointers wrong |
| `LinkedHashMap(cap, 0.75f, true)` + `removeEldestEntry` | O(1) avg | O(capacity) | About 5 lines, same idea built into the JDK |

- **Common mistakes:**
  - Forgetting to remove the evicted key from the map, which leaks memory.
  - Not storing the key in the node, so you cannot remove it from the map on eviction.
  - Treating `put` on an existing key as a new insert, which grows the cache past capacity or breaks the order.
  - Skipping sentinels and getting null-pointer bugs at the ends of the list.
  - Using `null` as both a miss and a valid value.
- **Concurrency:** `get` mutates the list, so even reads are writes. A plain `HashMap` and list are not thread-safe. This version is single-threaded only.
- **Monitoring in production:** expose hit rate, miss rate, eviction count and size. A falling hit rate means the cache is too small or the access pattern has changed. In Splunk, log cache misses with a sampling rate and alert when hit ratio drops below an agreed threshold.

**Test cases I'd walk through**
- **Typical:** cap 2, `put(1)`, `put(2)`, `get(1)`, `put(3)`. Key 2 is evicted, and keys 1 and 3 remain.
- **Empty:** `get` on an empty cache returns `null`.
- **Single element:** capacity 1. Each `put` evicts the previous key.
- **Duplicates:** `put` on the same key twice gives size 1 and the latest value. It also marks the key most recent, so another key is evicted next.
- **Invalid:** capacity 0 or negative throws `IllegalArgumentException`.
- **Large input:** 100,000 puts into capacity 1,000 leave size 1,000, with only the newest keys present.

**Follow-ups to expect**
- *How would you do this with `LinkedHashMap`?* -> Subclass it with `super(cap, 0.75f, true)` for access order and override `removeEldestEntry(e)` to return `size() > cap`. It is the same algorithm, maintained by the JDK.
- *Make it thread-safe.* -> The simplest option is to make `get` and `put` `synchronized` (or use a `ReentrantLock`). `get` writes, so a read-write lock does not help. For high contention, shard into N segments by key hash, or use Caffeine, which buffers recency updates.
- *Add TTL expiry.* -> Store an expiry timestamp in each node. Check it on `get` and treat an expired entry as a miss. For proactive cleanup, add a scheduled sweep or a delay queue.
- *Why not a `TreeMap` keyed by timestamp?* -> It gives O(log n), not O(1), and needs a unique timestamp per access.

**60-second answer**
"An LRU cache needs two things fast: finding an entry by key, and finding or reordering the least recently used one. A list ordered by recency is O(n) per operation. So I combine a HashMap from key to node with a doubly linked list. The head side holds the most recent entry and the tail side the oldest, with sentinel nodes so there are no null edge cases. On `get` I look up the node, unlink it, and re-insert it after the head. On `put` I update and move an existing key, or evict the node before the tail and remove its key from the map when full, then insert the new node. Both operations are O(1) average time with O(capacity) space. In production I would usually use `LinkedHashMap` with access order, or Caffeine if I need thread safety and TTL, and I would monitor hit rate and evictions."

### Q28 [senior] Implement a thread-safe singleton
tags: singleton, thread-safety, volatile, double-checked-locking, class-initialization, enum, coding, basics

**Start here: the concepts**
- **Singleton**: a class that allows exactly one instance per JVM (strictly, per classloader), with one global access point.
- **Thread-safe**: if 64 threads call `get()` at the same moment, they all receive the same object and the constructor runs once.
- **Eager vs lazy**: eager creates the object when the class loads. Lazy creates it on first use, which only matters if construction is expensive.
- **`synchronized`**: only one thread at a time may enter the block. It is correct but costs contention if every call takes the lock.
- **`volatile`**: a write to the field becomes visible to all threads, and the JVM may not reorder it with the writes that built the object. Without it, another thread can see a non-null reference to a half-built object.
- **Double-checked locking (DCL)**: check without a lock, lock only if null, check again inside the lock, then create.
- **Holder idiom**: a private static nested class holds the instance. The JVM initialises a class lazily and under a lock, exactly once, so you get lazy loading and thread safety with no explicit locking.
- **Enum singleton**: `enum X { INSTANCE }`. The JVM guarantees a single instance, and it also resists reflection and serialization attacks.
- **Big-O**: O(1) means the cost does not grow with the number of callers or calls. Here every `get()` is O(1), and the only question is the constant cost (lock or no lock).

**The live scenario**
Your payment service has a `PricingRuleEngine` that loads 40 MB of rules from a database at startup. It is used by 200 request threads at about 3,000 requests/second. If two threads each build their own engine, you pay double the memory and the two copies drift apart after a refresh. The interviewer usually says: "Implement a thread-safe singleton. Now make it lazy. Now tell me why `volatile` is needed. Now tell me how someone could still break it."

**What the interviewer is really checking**
Whether you know that a naive lazy singleton is racy and can explain why (instruction reordering and visibility), not just recite DCL. A senior candidate should also pick the simplest correct option (holder or enum), name how singletons get broken, and mention that in Spring you would let the container manage the scope.

**How I answer it**
1. **Clarify and restate.** Input: none. Output: the same instance on every call, from any thread. Questions I ask:
   - Does it need to be lazy, or is eager fine?
   - Is serialization involved?
   - Do we need to defend against reflection?
   - Is it one per JVM, or per classloader (app servers)?
   - Could dependency injection do this instead?
2. **Brute force.**
   - (a) A plain lazy `if (instance == null) instance = new X();` is not thread-safe. Two threads can both see null and create two objects.
   - (b) Making `getInstance()` `synchronized` is correct and O(1), but every call, even long after initialisation, takes the lock. At 3,000 requests/second that is needless contention.
3. **Better idea.** Only the first creation needs mutual exclusion.
   - **DCL with `volatile`:** the fast path is one volatile read and no lock. Inside the lock we re-check, because another thread may have won the race while we waited. `volatile` stops `instance` from being published before the constructor finishes. This is correct since Java 5 (JSR-133 memory model).
   - **Holder idiom:** the JVM's class-initialisation lock does the work, so the code is shorter and has nothing to get wrong.
   - **Enum:** the safest choice if you do not need a superclass or lazy loading.
   - My default is the holder or enum. I use DCL when the instance needs constructor arguments or other state that a static initialiser cannot supply.
4. **Complexity.** `get()` is O(1) time and O(1) space (one object, one reference). The DCL fast path is a single volatile read. The holder fast path is a plain static field read.
5. **Code.**

```java
import java.io.*;
import java.lang.reflect.Constructor;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Supplier;

final class DclSingleton {
    static final AtomicInteger CREATED = new AtomicInteger();
    private static volatile DclSingleton instance;
    private DclSingleton() { CREATED.incrementAndGet(); }
    static DclSingleton get() {
        DclSingleton local = instance;              // single volatile read on fast path
        if (local == null) {
            synchronized (DclSingleton.class) {
                local = instance;                   // re-check under the lock
                if (local == null) instance = local = new DclSingleton();
            }
        }
        return local;
    }
}

final class HolderSingleton {
    static final AtomicInteger CREATED = new AtomicInteger();
    private HolderSingleton() { CREATED.incrementAndGet(); }
    private static class Holder { static final HolderSingleton INSTANCE = new HolderSingleton(); }
    static HolderSingleton get() { return Holder.INSTANCE; }   // lazy: Holder loads on first call
}

enum EnumSingleton { INSTANCE }

class Solution {
    // Calls the supplier from n threads released at the same instant; returns distinct objects seen.
    static Set<Object> grab(Supplier<Object> s, int n) throws Exception {
        Set<Object> seen = ConcurrentHashMap.newKeySet();
        CountDownLatch go = new CountDownLatch(1);
        try (ExecutorService ex = Executors.newFixedThreadPool(n)) {
            List<Future<?>> fs = new ArrayList<>();
            for (int i = 0; i < n; i++) fs.add(ex.submit(() -> { go.await(); seen.add(s.get()); return null; }));
            go.countDown();
            for (Future<?> f : fs) f.get();
        }
        return seen;
    }

    public static void main(String[] args) throws Exception {
        if (!(grab(DclSingleton::get, 64).size() == 1)) throw new AssertionError("DCL returned >1 instance");
        if (!(DclSingleton.CREATED.get() == 1)) throw new AssertionError("DCL constructor ran " + DclSingleton.CREATED.get());
        if (!(grab(HolderSingleton::get, 64).size() == 1)) throw new AssertionError("Holder returned >1 instance");
        if (!(HolderSingleton.CREATED.get() == 1)) throw new AssertionError("Holder constructor ran more than once");
        if (!(grab(() -> EnumSingleton.INSTANCE, 64).size() == 1)) throw new AssertionError("Enum differs");
        if (!(DclSingleton.get() == DclSingleton.get())) throw new AssertionError("sequential calls differ");

        try {   // reflection cannot create a second enum constant
            Constructor<EnumSingleton> c = EnumSingleton.class.getDeclaredConstructor(String.class, int.class);
            c.setAccessible(true);
            c.newInstance("X", 1);
            throw new AssertionError("reflection should have failed");
        } catch (IllegalArgumentException expected) { }

        ByteArrayOutputStream bos = new ByteArrayOutputStream();   // serialization keeps identity for enums
        try (ObjectOutputStream out = new ObjectOutputStream(bos)) { out.writeObject(EnumSingleton.INSTANCE); }
        try (ObjectInputStream in = new ObjectInputStream(new ByteArrayInputStream(bos.toByteArray()))) {
            if (!(in.readObject() == EnumSingleton.INSTANCE)) throw new AssertionError("deserialized copy differs");
        }
        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| Approach | Lazy | Lock on hot path | Reflection/serialization safe | Notes |
|---|---|---|---|---|
| Unsynchronised lazy | yes | no | no | Racy: two instances, or a half-built one |
| `synchronized getInstance()` | yes | yes (every call) | no | Correct but contended |
| DCL + `volatile` | yes | no | no | Needs `volatile`; most error-prone |
| Holder idiom | yes | no | no | Simple and correct; cannot take runtime arguments |
| Enum | on first use | no | yes | Cannot extend a class |

All options are O(1) time and O(1) space. The differences are contention and safety.

Common mistakes:
- Forgetting `volatile` on a DCL field. On weak memory models (ARM) another thread can see a partly built object.
- Dropping the second null check, which allows two instances.
- Locking on `this` or a public object instead of the class.
- Expecting a singleton to be "one per application". It is one per classloader, so app servers and OSGi can produce several.
- Hiding global mutable state in a singleton, which makes unit tests order-dependent.
- Letting a constructor throw inside a holder: the class is then permanently broken (`NoClassDefFoundError` on later calls).

**Test cases I'd walk through**
- **Typical:** 64 threads released together by a latch all get the same object, and the constructor counter is 1.
- **Sequential:** two calls on the same thread return the same reference (`==`).
- **Single thread:** works with no contention, and the first call creates the instance.
- **Large concurrency:** raise the thread count and repeat the run, because race bugs are probabilistic. A passing test does not prove DCL is correct without `volatile`; the memory model argument does.
- **Reflection on enum:** `newInstance` throws `IllegalArgumentException`.
- **Serialization of enum:** the round trip returns the same constant. A class-based singleton would need `readResolve()`.
- **Null/empty:** not applicable, because there is no input. Say so explicitly.

**Follow-ups to expect**
- *Why is `volatile` needed in DCL?* -> `new X()` is allocate, construct, then assign the reference, and without `volatile` the assignment can be reordered before construction. Another thread's unlocked read could then see a non-null but unconstructed object. `volatile` forbids that reordering and gives visibility.
- *How can a singleton still be broken?* -> By reflection (`setAccessible` on the private constructor), by serialization (a new object on deserialization unless you add `readResolve`), by `clone()`, and by multiple classloaders. An enum closes the first three.
- *Is a Spring singleton bean the same thing?* -> No. It is one instance per `ApplicationContext`, not per JVM, and the container manages creation, so you get testability and can inject a mock. In Spring code I would use a bean, not a hand-written singleton.

**60-second answer**
"First I clarify: lazy or eager, any serialization or reflection concerns, and whether DI could own this. The naive lazy version is racy because two threads can both see null, and a `synchronized` getter is correct but locks on every call. My default is the holder idiom: a private static nested class holds the instance, and the JVM's class-initialisation lock makes it lazy and thread-safe with no explicit locking. If I need constructor arguments I use double-checked locking: read a `volatile` field, lock only if it is null, re-check inside the lock, then create. `volatile` is essential because without it the reference can be published before the constructor finishes. If the interviewer cares about reflection or serialization attacks, I use an enum singleton. All of these are O(1) time and space per call, and I test them by releasing 64 threads from a latch and checking one distinct instance and one constructor run."

### Q29 [senior] Implement producer-consumer with BlockingQueue
tags: blockingqueue, producer-consumer, concurrency, poison-pill, backpressure, executorservice, coding, basics

**Start here: the concepts**
- **Producer-consumer**: some threads create work (producers), others process it (consumers). A shared queue decouples their speeds.
- **BlockingQueue**: a thread-safe queue. `put` waits when the queue is full and `take` waits when it is empty, so no manual `wait/notify` is needed.
- **Bounded queue**: a fixed capacity (`ArrayBlockingQueue`). When consumers fall behind, producers block. This is **backpressure**, and it protects memory. An unbounded queue just hides the problem until an OutOfMemoryError.
- **Poison pill**: a special sentinel object a producer puts on the queue. A consumer that takes it stops. You need one pill per consumer, because each consumer swallows exactly one.
- **Big-O here**: n is the number of items. Each `put` or `take` is O(1) amortised work, so the total is O(n). Extra memory is O(capacity), not O(n).

**The live scenario**
An order service accepts 5,000 requests/s, and each one must be written to a slow audit store at about 800/s per writer. Request threads (producers) push events onto a queue and a small pool of writers (consumers) drains it. The interviewer usually says: "Implement producer-consumer with a BlockingQueue. How does it shut down cleanly? How do you test it without sleeps?"

**What the interviewer is really checking**
Whether you pick a bounded queue and can explain why, and whether you shut down without hanging or losing items (one pill per consumer, sent only after all producers finish). A senior is also expected to handle interrupts and failures, and to write a deterministic test that checks counts and sums instead of timing.

**How I answer it**
1. **Clarify.** How many producers and consumers? Is ordering required (across producers it is not)? Is the queue bounded? Is shutdown graceful (drain everything) or immediate? Edge cases: zero items, capacity 0, no consumers.
2. **Brute force.** A shared `LinkedList` with `synchronized` and `wait/notifyAll`. It works, but it is easy to get wrong (lost signals, `if` instead of `while`, and notifying the wrong side). Complexity is the same, O(n), but the code is riskier.
3. **Better idea.** Use `ArrayBlockingQueue` with `put` and `take`, which handle the locking and waiting. Producers run first. When they have all finished, main enqueues one pill per consumer. Because the queue is FIFO, every real item sits ahead of the pills and is processed before any consumer exits. That is why the pills must come after the producers finish.
4. **Complexity.** Time O(n) for n items in total. Space O(capacity) for the queue. Lock contention is the real cost at scale, not the Big-O.
5. **Code:**

```java
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.LongAdder;

class Solution {
    static final Object POISON = new Object();

    // returns {itemsConsumed, sumOfConsumed}
    static long[] run(int producers, int consumers, int perProducer, int capacity) throws Exception {
        if (producers < 1 || consumers < 1 || perProducer < 0)
            throw new IllegalArgumentException("bad sizes");
        BlockingQueue<Object> q = new ArrayBlockingQueue<>(capacity); // throws if capacity < 1
        LongAdder count = new LongAdder(), sum = new LongAdder();
        ExecutorService pool = Executors.newFixedThreadPool(producers + consumers);
        try {
            List<Future<?>> prod = new ArrayList<>(), cons = new ArrayList<>();
            for (int c = 0; c < consumers; c++) {
                cons.add(pool.submit(() -> {
                    while (true) {
                        Object o = q.take();
                        if (o == POISON) return null; // identity check on purpose
                        count.increment();
                        sum.add((Integer) o);
                    }
                }));
            }
            for (int p = 0; p < producers; p++) {
                prod.add(pool.submit(() -> {
                    for (int i = 1; i <= perProducer; i++) q.put(i);
                    return null;
                }));
            }
            for (Future<?> f : prod) f.get();             // all real items are queued
            for (int c = 0; c < consumers; c++) q.put(POISON); // one pill per consumer
            for (Future<?> f : cons) f.get();             // wait for drain
        } finally {
            pool.shutdownNow(); // on any failure, interrupt blocked threads
        }
        return new long[] {count.sum(), sum.sum()};
    }

    static void check(boolean cond, String msg) {
        if (!cond) throw new AssertionError(msg);
    }

    public static void main(String[] args) throws Exception {
        long[] r = run(1, 1, 1000, 1);
        check(r[0] == 1000 && r[1] == 500500L, "1P/1C cap 1");
        r = run(4, 3, 5000, 2);
        check(r[0] == 20000 && r[1] == 4L * 5000 * 5001 / 2, "4P/3C");
        r = run(2, 5, 0, 4);
        check(r[0] == 0 && r[1] == 0, "no items still terminates");
        r = run(1, 8, 3, 100);
        check(r[0] == 3 && r[1] == 6, "more consumers than items");
        try { run(1, 1, 1, 0); throw new AssertionError("cap 0 accepted"); }
        catch (IllegalArgumentException expected) { }
        try { run(1, 0, 1, 1); throw new AssertionError("0 consumers accepted"); }
        catch (IllegalArgumentException expected) { }
        BlockingQueue<Object> full = new ArrayBlockingQueue<>(1); // backpressure, no sleeps
        check(full.offer(1), "first offer fits");
        check(!full.offer(2, 50, TimeUnit.MILLISECONDS), "second offer must time out");
        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**
| Choice | Pros | Cons |
|---|---|---|
| `synchronized` + `wait/notify` | No library needed | Lost wake-ups, spurious wake-ups, easy to deadlock |
| `ArrayBlockingQueue` (bounded) | Backpressure, one lock, fixed memory | Producers stall when consumers are slow (usually what you want) |
| `LinkedBlockingQueue` (unbounded by default) | Higher throughput, separate put/take locks | Can grow until OutOfMemoryError if you forget a capacity |

- **Pill sent too early.** Items behind the pill are lost. Send pills only after all producers are done.
- **Too few pills.** Some consumers block forever on `take`. Send one per consumer.
- **Swallowing `InterruptedException`.** Restore the interrupt flag or let it propagate. Never loop on it silently.
- **A producer throws.** Consumers wait forever. That is why `finally` calls `shutdownNow()`.
- **Pool smaller than producers plus consumers.** Consumers may never start, and producers then block on a full queue (a deadlock).
- **Pill compared with `equals`.** Use identity (`==`) against a private sentinel object.

**Test cases I'd walk through**
- **Typical:** 4 producers, 3 consumers, 5,000 items each, capacity 2. Consumed count is 20,000 and the sum is 50,010,000. A tiny capacity forces heavy blocking.
- **Empty:** 0 items per producer. Consumers receive only pills and exit, with count 0 and no hang.
- **Single:** 1 producer, 1 consumer, capacity 1. All 1,000 items arrive and the sum is 500,500.
- **More consumers than items:** 8 consumers, 3 items. The count is 3 and every consumer still terminates.
- **Invalid input:** capacity 0 or zero consumers throws `IllegalArgumentException`.
- **Backpressure:** a full queue's `offer` with a timeout returns false. This is deterministic and needs no `sleep` to simulate a slow consumer.
- **Large:** raise `perProducer` to millions. Memory stays flat because of the bound.

**Follow-ups to expect**
- *How do you stop if a consumer fails midway?* -> Catch the failure per item and log or dead-letter it so the thread survives. If the failure is fatal, cancel the pool with `shutdownNow()` and propagate the exception through the `Future`.
- *Why not rely on `isEmpty()` to detect the end?* -> It is racy: a producer may be about to enqueue. A poison pill gives an in-band, ordered "no more data" signal.
- *Would you use virtual threads (Java 21)?* -> Yes for blocking I/O consumers. `put` and `take` park the virtual thread cheaply. The bounded queue is still what provides backpressure.
- *How is this different from Kafka?* -> Same idea across processes. The queue is a partition, consumers are a group, and lag is queue depth. Backpressure there is `max.poll.records` and pausing the consumer.

**60-second answer**
"I'd first clarify that it's multiple producers and consumers, that I want backpressure, and that shutdown must drain everything. I'd use a bounded `ArrayBlockingQueue`: `put` blocks when full, `take` blocks when empty, so no `wait/notify` and memory stays bounded. For shutdown I use poison pills. I wait for every producer to finish, then enqueue one sentinel per consumer, so FIFO order guarantees all real items are consumed first. I compare the sentinel by identity. The pool must have at least producers plus consumers threads, and a `finally` with `shutdownNow()` prevents hangs if something fails. Time is O(n) overall and extra space is O(capacity). My test checks count and sum for several thread mixes, the empty case, invalid arguments, and uses `offer` with a timeout on a full queue to prove backpressure without relying on sleeps."

### Q30 [senior] Implement a simple rate limiter (token bucket)
tags: rate-limiter, token-bucket, injectable-clock, concurrency, refill-math, coding, basics

**Start here: the concepts**
- **Token bucket**: a bucket holds up to `capacity` tokens. Each request spends tokens. Tokens come back at a steady `refillPerSecond`. A full bucket allows a burst of `capacity` requests. After that, the sustained rate is `refillPerSecond`.
- **Lazy refill**: no background thread adds tokens. On each call we compute `elapsed * rate` and add that many tokens (capped at capacity). This is cheap and needs no timers.
- **Injectable clock**: the limiter takes a time source (`LongSupplier` returning nanoseconds) instead of calling `System.nanoTime()` directly. Tests pass a fake clock, so no `Thread.sleep` and no flaky tests.
- **Big-O**: it describes how work or memory grows with input size. O(1) means the cost per call does not depend on how many requests came before.
- **Monotonic time**: `System.nanoTime()` never jumps with NTP or wall-clock changes, so use it for elapsed time, not `System.currentTimeMillis()`.

**The live scenario**
Your payment service calls a partner API that allows 100 requests/second with bursts up to 200. Beyond that the partner returns 429s and may ban you. The interviewer says: "Implement a simple rate limiter. `tryAcquire()` returns true if the call may go ahead. How would you unit-test it without sleeping?"

**What the interviewer is really checking**
Whether you ask clarifying questions (burst allowed? thread-safe? one limiter or one per key?) and mention the sliding-log brute force before the O(1) bucket. They also want to see you avoid `Thread.sleep` in tests by injecting a clock, and get the refill math right: cap at capacity, handle fractional tokens, and handle a clock that goes backwards.

**How I answer it**
1. **Clarify and restate.** Input: `capacity`, `refillPerSecond`, and a call to `tryAcquire(permits)`. Output: a boolean, non-blocking. I ask: is it thread-safe (yes, assume many threads), per-key or global (global here), and should the bucket start full (yes)? Edge cases: capacity or rate <= 0, permits <= 0, permits > capacity (can never succeed), a long idle period (must not exceed capacity), and a clock that moves backwards.
2. **Brute force.** Keep a queue of timestamps for every accepted request. On each call, drop the entries older than 1 second and allow the call if the size is below the limit. Time is O(k) per call for cleanup (amortized O(1)). Space is O(limit) per key, and it allows no controlled bursts.
3. **Better idea.** Store only two numbers: the current `tokens` and `lastRefillTime`. On each call, add `elapsedSeconds * rate` tokens and cap the total at `capacity`. If `tokens >= permits`, subtract and return true; otherwise return false. This works because the bucket state depends only on the last update time and the token count, so no history is needed.
4. **Complexity.** Time O(1) per call, space O(1) per limiter. A `synchronized` method keeps the read-refill-spend sequence atomic.
5. **Code.**

```java
import java.util.function.LongSupplier;

class TokenBucket {
    private final long capacity;
    private final double ratePerSec;
    private final LongSupplier nanoClock;
    private double tokens;
    private long lastNanos;

    TokenBucket(long capacity, double ratePerSec, LongSupplier nanoClock) {
        if (capacity <= 0 || ratePerSec <= 0) throw new IllegalArgumentException("capacity and rate must be > 0");
        this.capacity = capacity;
        this.ratePerSec = ratePerSec;
        this.nanoClock = nanoClock;
        this.tokens = capacity;                 // start full
        this.lastNanos = nanoClock.getAsLong();
    }

    synchronized boolean tryAcquire(int permits) {
        if (permits <= 0) throw new IllegalArgumentException("permits must be > 0");
        long now = nanoClock.getAsLong();
        long elapsed = Math.max(0L, now - lastNanos);   // ignore a clock that goes backwards
        // multiply before dividing to keep exact results for whole numbers
        tokens = Math.min(capacity, tokens + elapsed * ratePerSec / 1_000_000_000.0);
        lastNanos = Math.max(lastNanos, now);
        if (tokens >= permits) { tokens -= permits; return true; }
        return false;
    }
}

class Solution {
    static void check(boolean cond, String msg) {
        if (!(cond)) throw new AssertionError(msg);
    }

    public static void main(String[] args) {
        long[] now = {1_000L};                       // fake clock in nanos
        TokenBucket b = new TokenBucket(5, 2.0, () -> now[0]);

        for (int i = 0; i < 5; i++) check(b.tryAcquire(1), "burst " + i);
        check(!b.tryAcquire(1), "6th request must be rejected");

        now[0] += 250_000_000L;                      // 0.25s -> 0.5 token
        check(!b.tryAcquire(1), "half a token is not enough");
        now[0] += 250_000_000L;                      // 0.5s total -> 1 token
        check(b.tryAcquire(1), "one token refilled");
        check(!b.tryAcquire(1), "bucket empty again");

        now[0] += 3_600_000_000_000L;                // 1 hour idle: capped at capacity
        for (int i = 0; i < 5; i++) check(b.tryAcquire(1), "after idle " + i);
        check(!b.tryAcquire(1), "cap must hold after long idle");

        now[0] -= 5_000_000_000L;                    // clock goes backwards: no refill
        check(!b.tryAcquire(1), "no tokens from a backwards clock");

        check(!new TokenBucket(5, 2.0, () -> 0L).tryAcquire(6), "permits > capacity");
        try { new TokenBucket(0, 1.0, () -> 0L); throw new AssertionError("expected IAE"); }
        catch (IllegalArgumentException expected) { }
        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| | Sliding log (brute force) | Token bucket (final) |
|---|---|---|
| Time per call | O(k) cleanup, amortized O(1) | O(1) |
| Space per key | O(limit) timestamps | O(1) |
| Bursts | Hard to control | Explicit via `capacity` |
| Accuracy | Exact in the window | Approximate by design |

- **Using `System.currentTimeMillis()`**: NTP corrections can cause negative elapsed time or huge refills. Use `nanoTime`.
- **Forgetting the cap**: after an idle hour the bucket would hold 7200 tokens and allow a giant burst.
- **Integer division in refill**: `elapsed / 1e9 * rate` with ints or longs loses fractions, so slow rates never refill.
- **Race conditions**: an unsynchronized read-modify-write lets two threads spend the same token.
- **Background refill thread**: needless complexity and timer drift. Lazy refill is simpler.
- **Floating-point drift**: `double` is fine for a limiter. For exact accounting, use integer "nano-tokens".
- **Monitoring**: count allowed and rejected calls per limiter, and alert when the reject ratio rises. In Splunk, a search like `index=app "rate_limited" | timechart count by client` shows who is being throttled.

**Test cases I'd walk through**
- **Typical**: capacity 5, rate 2/s. Five calls succeed, the sixth fails.
- **Partial refill**: at +0.25s there are 0.5 tokens, so the call fails. At +0.5s there is 1 token, so it succeeds.
- **Long idle**: 1 hour later only 5 calls succeed (capped), not 7200.
- **Single or boundary**: `permits == capacity` succeeds on a full bucket. `permits > capacity` always returns false.
- **Invalid input**: capacity 0 or a negative rate throws `IllegalArgumentException`. permits <= 0 does too.
- **Clock goes backwards**: no tokens are added and nothing crashes.
- **Large input / concurrency**: 1M calls from many threads should never allow more than `capacity + rate * elapsed` total.

**Follow-ups to expect**
- *How do you make it lock-free?* -> Keep `(tokens, lastNanos)` in an immutable object inside an `AtomicReference` and retry with compare-and-set. Under heavy contention, `synchronized` is often just as fast and simpler.
- *How would you do it across many service instances?* -> Keep the state in Redis and do refill and spend in one Lua script so it is atomic. Alternatively, give each node a local share of the quota and sync periodically.
- *One limiter per user or API key?* -> Use a `ConcurrentHashMap<String, TokenBucket>` with `computeIfAbsent`, and evict idle keys (Caffeine `expireAfterAccess`) so memory is bounded.
- *Token bucket vs leaky bucket vs fixed window?* -> A fixed window allows 2x bursts at window edges. A leaky bucket smooths output to a constant rate. A token bucket allows controlled bursts while keeping the average rate.
- *What do you return to the client?* -> HTTP 429 with a `Retry-After` header, computed from `(permits - tokens) / rate`.

**60-second answer**
"I would first clarify whether bursts are allowed and whether it must be thread-safe. The brute force is a sliding log of timestamps, which costs memory proportional to the limit. Instead I keep two values, the token count and the last refill time. On each call I add `elapsed * rate` tokens, cap at capacity, and spend if enough remain. That is O(1) time and space, with no background thread. I inject a `LongSupplier` nanosecond clock so tests can advance time deterministically instead of sleeping. I use `nanoTime` for monotonic time, clamp negative elapsed to zero, and make `tryAcquire` synchronized so refill and spend are atomic. Edge cases I handle are permits larger than capacity, invalid arguments, and long idle periods. For scale-out I would move the state to Redis with a Lua script."

### Q31 [senior] Implement retry with exponential backoff
tags: retry, exponential-backoff, resilience, jitter, dependency-injection, coding, basics

**Start here: the concepts**
- **Retry**: call an operation again if it failed, because many failures (timeouts, HTTP 503, deadlock victim) disappear on their own.
- **Transient vs permanent error**: a transient error may succeed next time (timeout, 429, 503). A permanent error never will (400, validation failure, NPE). Retrying a permanent error only wastes time and load.
- **Exponential backoff**: the wait doubles after each failure (100 ms, 200 ms, 400 ms, ...). This gives a struggling dependency room to recover.
- **Cap**: an upper limit on a single wait, so the delay does not grow without bound.
- **Jitter**: a random fraction of the delay. Without it, 1,000 clients that failed together all retry at the same instant (a "retry storm" or thundering herd).
- **Injectable sleeper**: a tiny interface wrapping `Thread.sleep`. Tests pass a fake that records the delays, so they run in microseconds and are deterministic.
- **Big-O here**: time is O(maxAttempts) calls plus the waiting time. Space is O(1). The total wait is bounded by `maxAttempts * cap`.

**The live scenario**
Your order service calls a payment gateway at 800 requests/s. During a 20-second gateway blip about 5% of calls time out. Without retries, 40 orders/s fail and customers see errors. With naive instant retries, you triple the load on a gateway that is already struggling. The interviewer says: *"Write a generic retry helper with exponential backoff. How would you unit test it without waiting?"*

**What the interviewer is really checking**
Whether you ask which errors are retryable and what happens when attempts run out, and whether you design for testability (the injectable sleeper). A senior candidate also mentions the cap, jitter, overflow on `2^n`, interrupt handling and idempotency, without being prompted.

**How I answer it**
1. **Clarify and restate.** Input: a task (`Callable<T>`), max attempts, base delay, cap, a predicate for "is this retryable", and a sleeper. Output: the task's result, or the last exception once attempts are exhausted or the error is permanent. Questions I ask: Is `maxAttempts` the total number of calls, including the first? (I assume yes.) Is the operation idempotent? What if `maxAttempts < 1`? Do we sleep after the final failure? (No, it is pointless.)
2. **Brute force.** Wrap the call in a loop with a fixed `Thread.sleep(1000)`. It is O(attempts) and simple, but it retries every exception, uses a hard-wired sleep that makes tests slow, and does not back off, so it hammers the dependency at a constant rate.
3. **Better idea.**
   - Loop `attempt = 1..maxAttempts`.
   - On failure, rethrow immediately if this was the last attempt or the predicate says the error is not retryable.
   - Otherwise sleep for `min(cap, base * 2^(attempt-1))`, passed through a jitter function.
   - Compute the delay by doubling in a loop that stops at the cap, so large attempt numbers cannot overflow.
   - Inject both the `Sleeper` and the jitter function. Production uses real sleep and full jitter (`random(0..delay)`). Tests use a recorder and identity jitter.
4. **Complexity.** Time is O(maxAttempts) task invocations plus bounded sleep. Space is O(1). The delay calculation is O(log(cap/base)) per retry, which is effectively constant.
5. **Code.**

```java
import java.util.*;
import java.util.concurrent.Callable;
import java.util.function.LongUnaryOperator;
import java.util.function.Predicate;

class Solution {
    interface Sleeper { void sleep(long ms) throws InterruptedException; }

    static class TransientException extends Exception {
        TransientException(String m) { super(m); }
    }

    // delay before retry number retryNo (1-based); doubling stops at the cap, so no overflow
    static long delay(int retryNo, long baseMs, long capMs) {
        long d = Math.min(baseMs, capMs);
        for (int i = 1; i < retryNo && d < capMs; i++) d = Math.min(capMs, d * 2);
        return d;
    }

    static <T> T retry(Callable<T> task, int maxAttempts, long baseMs, long capMs,
                       Predicate<Exception> retryable, LongUnaryOperator jitter,
                       Sleeper sleeper) throws Exception {
        if (maxAttempts < 1) throw new IllegalArgumentException("maxAttempts < 1");
        for (int attempt = 1; ; attempt++) {
            try {
                return task.call();
            } catch (Exception e) {
                if (attempt >= maxAttempts || !retryable.test(e)) throw e;
                sleeper.sleep(jitter.applyAsLong(delay(attempt, baseMs, capMs)));
            }
        }
    }

    static void check(boolean c, String m) { if (!c) throw new AssertionError(m); }

    public static void main(String[] args) throws Exception {
        List<Long> sleeps = new ArrayList<>();
        Sleeper rec = sleeps::add;
        LongUnaryOperator none = d -> d; // prod: d -> ThreadLocalRandom.current().nextLong(d + 1)
        Predicate<Exception> transientOnly = e -> e instanceof TransientException;
        int[] calls = {0};

        String r = retry(() -> { calls[0]++; return "ok"; }, 3, 100, 1000, transientOnly, none, rec);
        check(r.equals("ok") && calls[0] == 1 && sleeps.isEmpty(), "first try");

        calls[0] = 0;
        r = retry(() -> { if (++calls[0] < 3) throw new TransientException("t"); return "done"; },
                  5, 100, 1000, transientOnly, none, rec);
        check(r.equals("done") && calls[0] == 3 && sleeps.equals(List.of(100L, 200L)), "recovers");

        calls[0] = 0; sleeps.clear();
        try {
            retry(() -> { calls[0]++; throw new IllegalArgumentException("bad"); },
                  5, 100, 1000, transientOnly, none, rec);
            throw new AssertionError("expected IAE");
        } catch (IllegalArgumentException expected) { }
        check(calls[0] == 1 && sleeps.isEmpty(), "permanent error not retried");

        calls[0] = 0; sleeps.clear();
        try {
            retry(() -> { calls[0]++; throw new TransientException("x"); },
                  6, 100, 500, transientOnly, none, rec);
            throw new AssertionError("expected failure");
        } catch (TransientException expected) { }
        check(calls[0] == 6, "all attempts used");
        check(sleeps.equals(List.of(100L, 200L, 400L, 500L, 500L)), "capped, no sleep after last");

        try {
            retry(() -> "x", 0, 100, 500, transientOnly, none, rec);
            throw new AssertionError("expected IAE");
        } catch (IllegalArgumentException expected) { }
        check(delay(100000, 100, 5000) == 5000, "no overflow for huge attempt numbers");
        System.out.println("OK");
    }
}
```

**Trade-offs and what can go wrong**

| Aspect | Brute force (fixed sleep, catch all) | Final (backoff, cap, jitter, predicate) |
|---|---|---|
| Time | O(attempts), constant pressure on dependency | O(attempts), pressure falls over time |
| Space | O(1) | O(1) |
| Testability | Slow, real sleeps | Instant, deterministic |
| Safety | Retries bugs and 400s | Retries only transient errors |

- **No jitter**: synchronized retry storms. Use full jitter in production.
- **Non-idempotent operation**: retrying a "charge card" call can double-charge. Use an idempotency key.
- **Retrying at every layer**: 3 layers with 3 attempts each means 27 calls. Retry at one layer only.
- **Blocking threads**: the worst-case total wait is about `attempts * cap`, so make sure it fits inside the caller's timeout. Add an overall deadline.
- **Swallowing `InterruptedException`**: either rethrow it or restore the interrupt flag with `Thread.currentThread().interrupt()`.
- **Overflow**: `base << attempt` goes negative after about 63 doublings. Cap the delay as you double it.
- **Monitoring**:
  - Metrics: `retry_attempts_total{op,outcome}`, `retry_exhausted_total` and a latency histogram.
  - Splunk: `index=app "retry exhausted" | timechart count by dependency`.
  - Alert when the exhausted rate rises above its baseline.

**Test cases I'd walk through**
- **Succeeds on the first call**: returns the result, 1 call, no sleep.
- **Fails twice, then succeeds** (base 100): sleeps are `[100, 200]`, 3 calls.
- **Permanent error** (`IllegalArgumentException`): thrown immediately, 1 call, no sleep.
- **All attempts fail** (`maxAttempts` = 6): the last `TransientException` is rethrown, 6 calls, 5 sleeps and none after the last.
- **Cap** (base 100, cap 500): sleeps are `100, 200, 400, 500, 500`.
- **`maxAttempts` of 0 or less**: `IllegalArgumentException`.
- **Huge attempt number** (100000): the delay equals the cap, with no overflow.

**Follow-ups to expect**
- *Why add jitter, and which kind?* -> It spreads out clients that failed together. Full jitter (`random(0..delay)`) gives the best spread. "Equal jitter" keeps half the delay fixed and randomizes the other half.
- *How do you do this in Spring or Java 21 in production?* -> Use Resilience4j `Retry` or Spring Retry (`@Retryable` with `@Backoff(multiplier=2)`), combined with a circuit breaker. I would still be able to write the core loop myself.
- *How do you make it non-blocking?* -> Use a `ScheduledExecutorService` or `CompletableFuture` with `delayedExecutor` instead of sleeping, or run on virtual threads (Java 21) where blocking sleep is cheap.

**60-second answer**
"I'd confirm that `maxAttempts` counts the total calls and ask which errors are retryable. A naive version loops with a fixed sleep and catches everything, which retries bugs and hammers the dependency. My version loops up to `maxAttempts` and rethrows immediately if it's the last attempt or the predicate says the error is permanent. Otherwise it sleeps `min(cap, base * 2^(n-1))` plus jitter, so clients don't retry in lockstep. The delay is computed by doubling up to the cap, so it can't overflow. The sleeper and jitter are injected, so tests record the delays and finish instantly. Time is O(maxAttempts) calls and space is O(1), with the worst-case wait bounded by attempts times cap. In production I'd also require idempotency, set an overall deadline, retry at only one layer, and track the exhausted-retry rate."
