/*
 * 01 - Coding round: strings, arrays and number problems (the classics, done properly)
 *
 * Run:  java 01_strings_and_arrays.java
 *
 * Interview angle: "reverse a string without reverse()", "palindrome", "anagram", "first
 * non-repeating character", "longest substring without repeats", "two sum", "Kadane", "missing
 * number", "Dutch national flag", "rotate", "merge sorted arrays". Every solution states its
 * time/space complexity and is checked against edge cases (null, empty, single element,
 * duplicates, negatives) because that is what interviewers actually look at.
 */
import java.util.*;

class StringsAndArrays {

    static int checks = 0;
    static void section(String t) { System.out.println("\n=== " + t + " ==="); }
    static void check(String label, Object expected, Object actual) {
        checks++;
        boolean same = expected instanceof int[] e && actual instanceof int[] a
                ? Arrays.equals(e, a) : Objects.equals(expected, actual);
        if (!same) throw new AssertionError(label + ": expected " + show(expected) + " but got " + show(actual));
        System.out.println("  ok  " + label + " -> " + show(actual));
    }
    static String show(Object o) { return o instanceof int[] a ? Arrays.toString(a) : String.valueOf(o); }

    // ---- 1. Strings ---------------------------------------------------------------------
    /** O(n) time, O(n) space. Strings are immutable, so work on a char[]. */
    static String reverse(String s) {
        if (s == null) return null;
        char[] c = s.toCharArray();
        for (int i = 0, j = c.length - 1; i < j; i++, j--) { char t = c[i]; c[i] = c[j]; c[j] = t; }
        return new String(c);
    }

    /** Two pointers, O(n)/O(1). Ignores case and non-alphanumerics (the usual follow-up). */
    static boolean isPalindrome(String s) {
        int i = 0, j = s.length() - 1;
        while (i < j) {
            while (i < j && !Character.isLetterOrDigit(s.charAt(i))) i++;
            while (i < j && !Character.isLetterOrDigit(s.charAt(j))) j--;
            if (Character.toLowerCase(s.charAt(i++)) != Character.toLowerCase(s.charAt(j--))) return false;
        }
        return true;
    }

    /** Frequency array beats sorting: O(n) vs O(n log n). Assumes lowercase a-z. */
    static boolean isAnagram(String a, String b) {
        if (a.length() != b.length()) return false;
        int[] f = new int[26];
        for (int i = 0; i < a.length(); i++) { f[a.charAt(i) - 'a']++; f[b.charAt(i) - 'a']--; }
        for (int x : f) if (x != 0) return false;
        return true;
    }

    /** LinkedHashMap keeps insertion order: count, then first with count 1. O(n). */
    static Character firstNonRepeating(String s) {
        Map<Character, Integer> m = new LinkedHashMap<>();
        for (char c : s.toCharArray()) m.merge(c, 1, Integer::sum);
        for (Map.Entry<Character, Integer> e : m.entrySet()) if (e.getValue() == 1) return e.getKey();
        return null;
    }

    /** Sliding window with last-seen index. O(n) time, O(min(n, alphabet)) space. */
    static int longestUniqueSubstring(String s) {
        Map<Character, Integer> last = new HashMap<>();
        int best = 0, start = 0;
        for (int i = 0; i < s.length(); i++) {
            Integer prev = last.put(s.charAt(i), i);
            if (prev != null && prev >= start) start = prev + 1;   // jump the window past the repeat
            best = Math.max(best, i - start + 1);
        }
        return best;
    }

    /** Group anagrams: the sorted letters are the canonical key. O(n * k log k). */
    static Collection<List<String>> groupAnagrams(String[] words) {
        Map<String, List<String>> g = new TreeMap<>();
        for (String w : words) {
            char[] c = w.toCharArray();
            Arrays.sort(c);
            g.computeIfAbsent(new String(c), k -> new ArrayList<>()).add(w);
        }
        return g.values();
    }

    /** Backtracking: n! results, so only for small n. Set de-duplicates repeated letters. */
    static Set<String> permutations(String s) {
        Set<String> out = new TreeSet<>();
        permute("", s, out);
        return out;
    }
    private static void permute(String prefix, String rest, Set<String> out) {
        if (rest.isEmpty()) { out.add(prefix); return; }
        for (int i = 0; i < rest.length(); i++)
            permute(prefix + rest.charAt(i), rest.substring(0, i) + rest.substring(i + 1), out);
    }

    /** Reverse the word order; split on one-or-more spaces so extra spaces do not create "" words. */
    static String reverseWords(String s) {
        String[] w = s.trim().split("\\s+");
        Collections.reverse(Arrays.asList(w));
        return String.join(" ", w);
    }

    // ---- 2. Arrays ----------------------------------------------------------------------
    /** One pass with a HashMap of value -> index. O(n)/O(n). Brute force is O(n^2). */
    static int[] twoSum(int[] a, int target) {
        Map<Integer, Integer> seen = new HashMap<>();
        for (int i = 0; i < a.length; i++) {
            Integer j = seen.get(target - a[i]);
            if (j != null) return new int[]{j, i};
            seen.put(a[i], i);
        }
        return new int[0];
    }

    /** Kadane: best sum ending at i = max(a[i], best ending at i-1 + a[i]). O(n)/O(1). */
    static int maxSubarray(int[] a) {
        int cur = a[0], best = a[0];
        for (int i = 1; i < a.length; i++) {
            cur = Math.max(a[i], cur + a[i]);
            best = Math.max(best, cur);
        }
        return best;
    }

    /** Sum formula. Use long: n*(n+1)/2 overflows int for n above about 65,000. */
    static int missingNumber(int[] a, int n) {
        long expected = (long) n * (n + 1) / 2, actual = 0;
        for (int x : a) actual += x;
        return (int) (expected - actual);
    }

    /** Dutch national flag: one pass, O(1) space. Sort an array of 0/1/2. */
    static void sort012(int[] a) {
        int lo = 0, mid = 0, hi = a.length - 1;
        while (mid <= hi) {
            if (a[mid] == 0) swap(a, lo++, mid++);
            else if (a[mid] == 1) mid++;
            else swap(a, mid, hi--);          // do NOT advance mid: the swapped-in value is unchecked
        }
    }
    static void swap(int[] a, int i, int j) { int t = a[i]; a[i] = a[j]; a[j] = t; }

    /** Second largest DISTINCT value without sorting. Returns null when it does not exist. */
    static Integer secondLargest(int[] a) {
        Integer first = null, second = null;
        for (int x : a) {
            if (first == null || x > first) { second = first; first = x; }
            else if (x != first && (second == null || x > second)) second = x;
        }
        return second;
    }

    /** Rotate right by k using three reversals: O(n) time, O(1) space. */
    static void rotate(int[] a, int k) {
        k %= a.length;
        reverseRange(a, 0, a.length - 1);
        reverseRange(a, 0, k - 1);
        reverseRange(a, k, a.length - 1);
    }
    static void reverseRange(int[] a, int i, int j) { while (i < j) swap(a, i++, j--); }

    /** Two pointers over two sorted arrays. O(n+m). */
    static int[] mergeSorted(int[] a, int[] b) {
        int[] r = new int[a.length + b.length];
        int i = 0, j = 0, k = 0;
        while (i < a.length && j < b.length) r[k++] = a[i] <= b[j] ? a[i++] : b[j++];   // <= keeps it stable
        while (i < a.length) r[k++] = a[i++];
        while (j < b.length) r[k++] = b[j++];
        return r;
    }

    /** Iterative binary search. mid = lo + (hi-lo)/2 avoids the (lo+hi) overflow bug. */
    static int binarySearch(int[] a, int key) {
        int lo = 0, hi = a.length - 1;
        while (lo <= hi) {
            int mid = lo + (hi - lo) / 2;
            if (a[mid] == key) return mid;
            if (a[mid] < key) lo = mid + 1; else hi = mid - 1;
        }
        return -1;
    }

    /** In-place dedupe of a SORTED array; returns the new logical length. */
    static int removeDuplicatesSorted(int[] a) {
        if (a.length == 0) return 0;
        int w = 1;
        for (int r = 1; r < a.length; r++) if (a[r] != a[w - 1]) a[w++] = a[r];
        return w;
    }

    // ---- 3. Numbers ---------------------------------------------------------------------
    /** Trial division up to sqrt(n): O(sqrt n). */
    static boolean isPrime(int n) {
        if (n < 2) return false;
        for (int i = 2; (long) i * i <= n; i++) if (n % i == 0) return false;
        return true;
    }
    static long gcd(long a, long b) { return b == 0 ? a : gcd(b, a % b); }
    static long fib(int n) { long a = 0, b = 1; for (int i = 0; i < n; i++) { long t = a + b; a = b; b = t; } return a; }
    static int sumDigits(int n) { n = Math.abs(n); int s = 0; while (n > 0) { s += n % 10; n /= 10; } return s; }
    /** Swap without a temp: XOR works, but the arithmetic form can overflow. Say so. */
    static int[] swapXor(int a, int b) { a ^= b; b ^= a; a ^= b; return new int[]{a, b}; }

    public static void main(String[] args) {
        section("1. Strings");
        check("reverse(\"interview\")", "weivretni", reverse("interview"));
        check("reverse(\"\")", "", reverse(""));
        check("reverse(null)", null, reverse(null));
        check("palindrome(\"A man, a plan, a canal: Panama\")", true, isPalindrome("A man, a plan, a canal: Panama"));
        check("palindrome(\"race a car\")", false, isPalindrome("race a car"));
        check("anagram(listen, silent)", true, isAnagram("listen", "silent"));
        check("anagram(abc, abd)", false, isAnagram("abc", "abd"));
        check("firstNonRepeating(swiss)", 'w', firstNonRepeating("swiss"));
        check("firstNonRepeating(aabb)", null, firstNonRepeating("aabb"));
        check("longestUnique(abcabcbb)", 3, longestUniqueSubstring("abcabcbb"));
        check("longestUnique(pwwkew)", 3, longestUniqueSubstring("pwwkew"));
        check("longestUnique(abba)  [stale-index trap]", 2, longestUniqueSubstring("abba"));
        check("groupAnagrams", "[[bat], [ate, eat, tea], [nat, tan]]",
                groupAnagrams(new String[]{"eat", "tea", "tan", "ate", "nat", "bat"}).stream()
                        .map(l -> { List<String> c = new ArrayList<>(l); Collections.sort(c); return c; })
                        .toList().toString());
        check("permutations(aab)", "[aab, aba, baa]", permutations("aab").toString());
        check("reverseWords", "world hello", reverseWords("  hello   world "));

        section("2. Arrays");
        check("twoSum([2,7,11,15], 9)", new int[]{0, 1}, twoSum(new int[]{2, 7, 11, 15}, 9));
        check("twoSum no answer", new int[0], twoSum(new int[]{1, 2}, 10));
        check("maxSubarray([-2,1,-3,4,-1,2,1,-5,4])", 6, maxSubarray(new int[]{-2, 1, -3, 4, -1, 2, 1, -5, 4}));
        check("maxSubarray all negative", -1, maxSubarray(new int[]{-3, -1, -2}));
        check("missingNumber 1..5", 4, missingNumber(new int[]{1, 2, 3, 5}, 5));
        int[] flag = {2, 0, 1, 2, 0, 1, 1, 0};
        sort012(flag);
        check("sort012", new int[]{0, 0, 0, 1, 1, 1, 2, 2}, flag);
        check("secondLargest([5,9,9,3])", 5, secondLargest(new int[]{5, 9, 9, 3}));
        check("secondLargest all equal", null, secondLargest(new int[]{4, 4, 4}));
        int[] rot = {1, 2, 3, 4, 5, 6, 7};
        rotate(rot, 3);
        check("rotate right by 3", new int[]{5, 6, 7, 1, 2, 3, 4}, rot);
        check("mergeSorted", new int[]{1, 2, 3, 4, 5, 6}, mergeSorted(new int[]{1, 3, 5}, new int[]{2, 4, 6}));
        check("binarySearch found", 3, binarySearch(new int[]{1, 3, 5, 7, 9}, 7));
        check("binarySearch missing", -1, binarySearch(new int[]{1, 3, 5, 7, 9}, 4));
        int[] dup = {1, 1, 2, 2, 2, 3};
        int len = removeDuplicatesSorted(dup);
        check("removeDuplicatesSorted length", 3, len);
        check("removeDuplicatesSorted prefix", new int[]{1, 2, 3}, Arrays.copyOf(dup, len));

        section("3. Numbers");
        check("isPrime(97)", true, isPrime(97));
        check("isPrime(1)", false, isPrime(1));
        check("isPrime(2147483647)  [no int overflow]", true, isPrime(2147483647));
        check("gcd(48, 18)", 6L, gcd(48, 18));
        check("fib(50)", 12586269025L, fib(50));
        check("sumDigits(-9875)", 29, sumDigits(-9875));
        check("swapXor(3, 8)", new int[]{8, 3}, swapXor(3, 8));

        System.out.println("\nAll " + checks + " checks passed.");
    }
}
