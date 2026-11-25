# Coding problems and algorithm reasoning

Questions 1–51 from the [Product Java Backend Expanded Question Bank](../../InterviewTopic/Product_Java_Backend_Expanded_Question_Bank.pdf), documented by @lowkey.unhandled. Question numbers follow the source PDF.

### Trace a prefix-sum count

For [1, −1, 1] and target 1 the running sums are 1, 0 and 1. The matching earlier-prefix counts are 1, 0 and 2. The third step counts both the final element and the entire array.

```java
static long countSubarrays(int[] values, long target) {
    Map<Long, Long> frequencies = new HashMap<>();
    frequencies.put(0L, 1L);
    long sum = 0;
    long count = 0;
    for (int value : values) {
        sum += value;
        count += frequencies.getOrDefault(sum - target, 0L);
        frequencies.merge(sum, 1L, Long::sum);
    }
    return count;
}
```

Practice by replacing frequency with earliest index for Q6. Explain why overwriting the earliest index can shorten the answer.

## Interview questions and answers

### Q1. Two Sum; 3Sum; 4Sum; pair with target sum.

For unsorted Two Sum, scan left to right. Look up target minus the current value before storing its index, so [3,3] can use two different positions. Expected time and space are O(n). For unique triples or quadruples, sort, fix one or two leading positions, then move the ends of the remaining range according to the sum. Skip equal values at each choice and use long arithmetic. Time is O(n²) or O(n³), respectively.

### Q2. Maximum subarray sum; maximum product subarray; best time to buy and sell stock.

For maximum sum, keep the best sum ending here by choosing between x and previous+x. Initialize from the first element so an all-negative input works. For maximum product, carry both previous extremes because a negative multiplier swaps their roles. For one stock transaction, record the cheapest earlier price and maximize today's price minus that minimum. Each scan takes O(n) time and constant space.

### Q3. Move zeroes; rotate array; product of array except self.

Compact nonzero values to a write index, then fill the remaining slots with zeros. This preserves relative order. Rotate right by reversing the whole array and then the first k and remaining n−k elements, reducing k modulo n after checking for an empty array. For products, write prefix products into the output and multiply by a running suffix on the reverse pass. This handles zeros without division. Each takes O(n) time.

### Q4. Merge sorted arrays; remove duplicates in-place; sort 0s, 1s and 2s.

With spare capacity at the end of the first sorted array, merge backward from the two largest unread values so writes cannot overwrite unread input. Deduplicate sorted data by writing only values different from the last accepted value. For three colors maintain low, current and high boundaries. After swapping a 2 to high, examine the incoming value before advancing. All three run in linear time.

### Q5. Find missing number; find duplicate number; find all disappeared numbers.

For distinct values drawn from 0..n, XOR all indices, n, and values to cancel matched pairs. For n+1 entries in 1..n with one repeated value, treat values as next indices and use Floyd's cycle entrance algorithm. For all missing values in 1..n, negate the slot at abs(value)−1 and return positive slots plus one. The last method mutates input. All take O(n) time.

### Q6. Subarray sum equals K; longest subarray with given sum; maximum sum of fixed-size window.

Seed prefix sum zero with frequency one. At running sum s, add freq[s−k] to the count before recording s. To maximize length, store only the earliest index for each sum, seeded with index −1. Negative values work because the argument uses prefix differences. For a fixed width, roll the sum by subtracting the outgoing value and adding the incoming one. Reject widths outside 1..n.

### Q7. Set matrix zeroes; rotate matrix by 90 degrees; spiral matrix traversal.

Record whether the first row and column originally contain zeros, then use those borders as markers for interior cells. Apply the markers before clearing the borders. Rotate a square matrix clockwise by transposing across its diagonal and reversing each row. Traverse a rectangle in spirals by shrinking top, right, bottom and left boundaries, checking for an exhausted dimension before each return sweep. Each visits O(rows × columns) cells.

### Q8. Merge intervals; insert interval; non-overlapping intervals.

Sort intervals by start and extend the current end while intervals overlap. For insertion into an already sorted disjoint list, copy intervals before the new one, absorb overlaps, then append the suffix, in O(n). To minimize removals, sort by finish time and keep each compatible interval. Finishing earliest leaves maximal room for future choices. Agree whether touching endpoints overlap before choosing the comparison.

### Q9. Reverse words in a string; reverse vowels; valid palindrome.

Split on whitespace and emit words in reverse order if whitespace normalization is allowed. To reverse vowels, move two indices inward to the next vowels and swap them. For a normalized palindrome, skip non-alphanumeric characters and compare case-normalized ends. All take linear time under a stated character model. Java char indexes UTF-16 units, so clarify Unicode requirements.

### Q10. Longest substring without repeating characters.

Maintain a window of unique characters and a map of last-seen positions. For each character at right, set left=max(left,lastSeen+1), record right, and maximize right−left+1. The max prevents moving backward on “abba”. Each index advances once for O(n) time with space bounded by alphabet size.

### Q11. Longest repeating character replacement; minimum window substring.

For replacement, a window is feasible when length minus its largest character frequency is at most k. Grow right and shrink left if over budget. A historical maximum frequency suffices for computing the best length. For minimum cover, track required multiplicities and a missing-character count. Once all are covered, shrink while recording the shortest valid window. Repeated characters in the target must each be satisfied.

### Q12. Group anagrams; valid anagram; find all anagram indices.

Anagrams share a canonical key. For lowercase letters use a fixed frequency vector with unambiguous separators as a map key, or sort each word for a general alphabet. To validate two words subtract their counts and check all zeros. To find matching starts slide a pattern-length frequency window, removing the outgoing character. A fixed alphabet makes the scan linear.

### Q13. Longest palindromic substring; palindromic substrings count.

Expand from each character and each gap for odd and even palindromes. Every successful expansion represents one distinct occurrence by position. Count all expansions for the count problem or remember the widest endpoints for the longest substring. On “aaa” the count is six and the longest has length three. Worst case O(n²) time and O(1) auxiliary space.

### Q14. String compression; implement atoi; longest common prefix.

Compress runs with separate read and write indices, emitting the character and decimal count when the count exceeds one. For atoi, skip leading whitespace, accept one sign, consume digits and check the bound before multiplying by ten. For longest common prefix compare each column until any string ends or differs. Empty input needs an explicit return convention.

### Q15. Minimum characters to add to make a string palindrome; check string rotation.

If additions are allowed only at the front, find the longest palindromic prefix via the KMP prefix table on s + unique separator + reverse(s). Subtract the final match length from n. For insertion anywhere, interval DP uses dp[i+1][j−1] for equal ends and one plus the cheaper trimmed interval otherwise. A rotation has equal length and occurs in s+s. Define empty strings as rotations of each other.

### Q16. Two Sum using HashMap; first unique character; frequency of elements.

Hash each previously visited number to its index for Two Sum, testing its complement first. For frequencies increment a counter per key. For the first unique character, scan the original sequence a second time and return the first with count one. Iterating an ordinary HashMap cannot recover encounter order. Expected O(n) time.

### Q17. Find duplicates; intersection of two arrays; longest consecutive sequence.

A failed insertion into a set identifies a duplicate. For a distinct intersection, build a set of the smaller input and remove matches as you scan the larger. For longest consecutive sequence, start walking only at values without a predecessor, so each run is traversed once. Guard predecessor/successor arithmetic at integer bounds. Expected O(n) time overall.

### Q18. Subarray sum equals K; count zero-sum subarrays; prefix sum range queries.

Let prefix[0]=0 and prefix[i+1]=prefix[i]+a[i]. Inclusive range [l,r] sums to prefix[r+1]−prefix[l] in O(1) after O(n) preprocessing. Counting target sums needs frequencies of earlier prefixes. For k=0 equal prefixes form a zero-sum interval. With [0,0], counts grow by one then two, yielding three. Use long for totals and counts.

### Q19. Find majority element; elements appearing more than n/3 times.

Boyer–Moore cancels mismatched pairs and retains a possible majority. Verify its count if existence is unspecified. For the n/3 threshold, keep two candidates and counters, decrementing both when a third distinct value arrives. At most two values can exceed that threshold. Verify both with a second pass. Time O(n), extra space O(1).

### Q20. Design LRU cache; design LFU cache; explain HashMap-based implementation.

LRU maps keys to doubly linked nodes. Move each hit to the most-recent end and evict from the other end. An access-ordered LinkedHashMap supplies this behavior. LFU also maps each frequency to an ordered bucket and tracks the minimum frequency. Promotion moves a node between buckets, with LRU breaking frequency ties. Handle capacity zero and coordinate list and map mutations under concurrent access.

### Q21. Container with most water; trapping rain water; 3Sum.

For the container, compute width × shorter height and move the shorter end inward since retaining it cannot improve the area at a narrower width. For trapped water maintain maxima from both sides and settle the side with the smaller maximum, adding its deficit. Both run in O(n). For 3Sum sort, fix a value and scan the remaining pair from opposite ends, skipping repeats in O(n²).

### Q22. Remove duplicates from sorted array; pair with target in sorted array.

On sorted input, keep a write pointer after the unique prefix and overwrite it when the next distinct value arrives. Return the prefix length. For a target pair start at opposite ends, increment left when the sum is too small and decrement right when too large. Sorted order rules out the discarded index. Each uses O(n) time and O(1) extra space.

### Q23. Binary search; first and last position; search in rotated sorted array.

Use a half-open interval [lo,hi) and midpoint lo+(hi−lo)/2. Lower bound returns the first element ≥ target, upper bound the first > target. Check equality before returning first and last indices. In a rotated distinct array at least one half is sorted, so test whether the target belongs there. Ambiguous duplicate boundaries can force linear time.

### Q24. Find minimum in rotated sorted array; find peak element.

For a rotated distinct array, compare mid with right. If mid is larger, the minimum lies strictly to its right, otherwise retain mid in the left search interval. For a local peak compare mid with mid+1 and move uphill. A peak exists with virtual negative-infinity boundaries and unequal neighbors. Both halve the search range.

### Q25. Search a 2D matrix; median of two sorted arrays.

If rows form one globally sorted sequence, binary-search flattened indices using quotient and remainder by column count. If only rows and columns are independently sorted, walk from top right in O(rows+cols). For the median, binary-search a partition of the shorter array, deriving the other cut to balance lengths. Require both left maxima ≤ opposite right minima. For odd length return the larger left value, for even average the two middle values safely. O(log min(m,n)).

### Q26. Allocate books / ship packages within D days; square root using binary search.

For contiguous book allocations or shipping, search capacities from the largest item to the total sum. Greedily fill each day or student up to the candidate limit. Feasibility is monotonic, so keep the smallest feasible limit. Exact nonempty book allocations require at least as many books as students. For floor square root of nonnegative x, binary-search the largest positive m with m ≤ x/m, handling zero separately.

### Q27. Reverse linked list iteratively and recursively; reverse in groups of K.

Reverse iteratively with previous, current and saved next pointers, or recursively reverse the tail and link the old second node back to the head, clearing the old forward link. Recursion uses O(n) stack. For k-groups check k nodes exist before rewiring, reverse to the saved next-group boundary and reconnect through a dummy predecessor. Leave a short final group intact.

### Q28. Detect cycle; find cycle starting node; find middle node.

Advance slow by one and fast by two, guarding fast and fast.next. A meeting implies a cycle. Reset one pointer to head and advance both one step until they meet at the entrance, since the distance difference at the first meeting is a multiple of cycle length. On an acyclic list the same speed ratio locates the middle. State which middle you return for even length.

### Q29. Merge two sorted lists; remove Nth node from end.

Merge sorted lists behind a dummy tail by detaching the smaller head, then attach the remaining suffix. This reuses nodes in O(m+n) time. To delete the nth from the end, start two pointers at a dummy, advance fast n steps and slide both until fast reaches the last node. Slow then precedes the target, including when deleting the head. Validate n.

### Q30. Add two numbers represented by linked lists; check palindrome linked list.

For reverse-order digits sum the current digits and carry, emit sum modulo ten, and propagate integer division by ten. Continue while either list or carry remains. Forward-order digits need stacks or reversed inputs. For palindrome checking, find the midpoint, reverse the second half, compare corresponding nodes and restore the links. Both approaches are linear.

### Q31. Intersection of two linked lists; sort a linked list; flatten a multilevel list.

For intersection by node identity, switch each pointer to the other head at its list end. They traverse equal combined lengths and meet at the shared node or null. Sort by linked-list merge sort in O(n log n). For a doubly linked child list flatten depth-first with a stack of deferred next nodes, repairing prev and clearing child. For sorted bottom-linked chains, merge ordered heads with a heap instead.

### Q32. Valid parentheses; implement min stack; implement queue using stacks.

Validate nested brackets by matching each closer to the most recent opener and requiring an empty final stack. A min stack stores the minimum so far alongside each value, preserving duplicate minima. For a FIFO queue push onto an input stack and transfer to an output stack only when output empties. Each item transfers once, giving amortized O(1) operations.

### Q33. Next greater element; next smaller element; daily temperatures.

Keep indices of unresolved elements on a monotonic stack. On a strictly larger current value, pop smaller entries and record the current value as their next greater. Reverse the inequality for next smaller. Daily temperatures records the index distance and leaves zero for unresolved days. Equal temperatures do not resolve each other. Each index enters and leaves at most once.

### Q34. Largest rectangle in histogram; maximal rectangle in binary matrix.

Maintain increasing bar indices and append a virtual zero height to flush pending bars. When popping a taller bar, its width runs from one after the new top through the preceding index, using −1 for an empty stack. For a binary matrix maintain consecutive-one heights by column, resetting at zeros, and solve one histogram per row. O(rows × cols) time and O(cols) space.

### Q35. Sliding window maximum; stock span problem.

Sliding maximum uses a deque of candidate indices with decreasing values. Expire indices outside the window and remove smaller trailing candidates before appending. The front is the maximum. For stock span, pop earlier prices ≤ today's price and take the distance to the nearest remaining greater price, or the entire prefix. Both are amortized linear.

### Q36. Evaluate Reverse Polish Notation; simplify Unix path.

For RPN push operands, then for each binary operator pop the right operand before the left. Check division and require exactly one final result. For a canonical absolute Unix path split on slashes, ignore empty segments and dots, pop on double dot when possible and join remaining segments with a leading slash. This is lexical normalization and does not resolve symlinks.

### Q37. Inorder, preorder and postorder traversal; level-order traversal.

A depth-first traversal visits the root before, between or after its subtrees for preorder, inorder and postorder respectively. Use recursion or a stack with explicit visit state. Level order uses a queue, taking the queue size before each level. All visit n nodes, with depth-first space O(height) and breadth-first space O(maximum width).

### Q38. Maximum depth; diameter; balanced binary tree; invert binary tree.

Compute height bottom-up as one plus the larger child height, with null height zero. The longest path through a node spans leftHeight+rightHeight edges, so accumulate the maximum for diameter. Return a sentinel on imbalance to detect a height difference above one in the same pass. Invert by swapping children at every node. All run in O(n).

### Q39. Lowest common ancestor; validate BST; kth smallest in BST.

In a general tree propagate each target upward. A node receiving matches from both subtrees is their LCA. Verify presence separately if targets may be absent. Validate a strict BST by passing exclusive lower and upper bounds to each subtree. Inorder traversal yields sorted keys, so stop at the kth visit. For frequent queries, maintain subtree sizes to select in O(height).

### Q40. Path sum; maximum path sum; serialize and deserialize a binary tree.

For root-to-leaf sum subtract each value on descent and test the remainder at leaves. For maximum path sum return the best single positive branch upward and score each node with both positive branches. Initialize the best to a real node for negative trees. Serialize preorder values with explicit null markers. Deserialization consumes one token per slot, preserving shape even with duplicate values.

### Q41. Top K frequent elements; Kth largest element; merge K sorted lists.

Count frequencies then keep a size-k min-heap of the most frequent keys, costing O(n+u log k) for u distinct values. For kth largest retain the k largest inputs, including duplicates if ranks count occurrences. Merge k sorted lists by polling the smallest current head and inserting its successor. Total O(N log k) time and O(k) heap space.

### Q42. Find median from data stream; connect nodes at the same level.

Maintain a max-heap for the lower half and min-heap for the upper half. Restore ordered boundaries and size difference at most one after insertion. Median is the larger heap's root or the average of roots. Insert O(log n), query O(1). To connect level neighbors, process a queue level at a time, wiring successive nodes and terminating each level with null.

### Q43. Generate subsets; permutations; combination sum.

Subsets branch on inclusion or exclusion, yielding 2ⁿ outputs. Permutations select each unused position for the next slot, yielding n! leaves for distinct values. Combination sum on positive reusable candidates keeps a nondecreasing start index and reduces the remaining target until zero. Sort and skip equal sibling choices where duplicate results are disallowed. Copy the path at each output.

### Q44. Generate balanced parentheses; letter combinations of phone number.

For n pairs, append an opener while opens<n and a closer only while closes<opens. This prefix invariant prevents invalid strings before they are built. For phone digits expand each prefix by the letters mapped to the next digit. Output count is the product of mapping sizes. Define behavior for empty input and digits without letter mappings.

### Q45. Word search; N-Queens; palindrome partitioning.

Word search explores adjacent cells matching the next character, temporarily marking and restoring visited cells on each path. N-Queens places one queen per row and tracks occupied columns and both diagonal indices. Palindrome partitioning chooses each palindromic next segment and recurses on the suffix. Precomputing palindrome intervals in O(n²) avoids repeated checks. All can have exponential search or output.

### Q46. Activity selection; jump game; gas station; minimum number of platforms.

Select compatible activities by earliest end time. For jump reachability track the farthest reachable position and fail if the next index exceeds it. For a circular gas route require nonnegative total surplus, resetting the candidate start after any negative running balance. For platforms sort arrivals and departures separately and sweep simultaneous occupancy. Decide whether equal-time arrival needs another platform.

### Q47. Meeting rooms; job sequencing; fractional knapsack.

Meeting-room feasibility follows from checking adjacent start-sorted intervals. To count rooms sweep starts and ends or reuse the earliest free end in a heap. For unit-duration profitable jobs with deadlines, process jobs by decreasing profit and place each in its latest free feasible slot. Fractional knapsack takes highest value/weight first, including a partial final item. The ratio argument depends on divisibility.

### Q48. BFS and DFS; number of islands; clone graph; course schedule / cycle detection.

BFS queues discovered vertices while DFS uses recursion or a stack. Mark on discovery to avoid rework. Count islands by starting a flood fill at each unseen land cell. Clone a graph using an original-to-copy map populated before following neighbors, which handles cycles. For course prerequisites use indegrees and remove zero-indegree nodes. Fewer than V removals indicates a directed cycle. Graph traversals cost O(V+E) with adjacency lists.

### Q49. Shortest path in an unweighted graph; Dijkstra basics; topological sorting.

BFS gives minimum hop count because each frontier is one edge farther from the source. Save a parent to reconstruct the route. For nonnegative weighted edges run Dijkstra, relaxing neighbors from the smallest tentative distance and skipping obsolete heap entries. Negative edges invalidate finalization. For topological order repeatedly remove zero-indegree vertices of a DAG, decrementing their neighbors.

### Q50. Climbing stairs; house robber; coin change; longest increasing subsequence.

Stairs with 1- or 2-step moves uses ways[i]=ways[i−1]+ways[i−2], seeded with one empty path. House robber chooses max(skip, previousNonAdjacent+value). Minimum coin change uses dp[0]=0 and one plus the best reachable predecessor over valid coins, with unreachable amounts marked. For strict LIS replace the first tail ≥ the current value or append. Tail count is the LIS length in O(n log n).

### Q51. Longest common subsequence; edit distance; 0/1 knapsack basics.

LCS takes one plus diagonal for equal characters, otherwise max of dropping one character from either side. Edit distance takes the cheapest insert, delete or replace, initializing empty-prefix distances to prefix lengths. Both cost O(mn). For 0/1 knapsack update capacities downward per item using max(old,value+dp[c−weight]) so each item is used once. O(items × capacity) is pseudo-polynomial.
