# Deep Dive 09 — Pandas for Data Handling

> Runnable companion: [`03_pandas_data_handling/`](../03_pandas_data_handling/) — Series/DataFrame
> basics, missing data + groupby + merge, performance on large data.
> Related deep dives: [Comprehensions](02_comprehensions_map_filter_reduce.md) ·
> [Generators](04_generators_iterators.md) · [Kafka pipelines](14_kafka_pipelines_delivery_semantics.md)

## What interviewers are actually probing

Pandas rounds are **practical**. Expect a small DataFrame on a screen and "transform this." What's
being assessed: do you reach for **vectorised operations** or write `iterrows()`; do you know
`loc` vs `iloc` cold; can you `groupby().agg()` with named aggregations; do you understand
`merge` semantics well enough to catch a fan-out join; and — the senior differentiator — **can you
process a file larger than memory**.

The `SettingWithCopyWarning` question comes up constantly because almost everyone has seen it and
almost nobody can explain it.

---

## Must-know points

- **Series** = labelled 1-D array, single dtype. **DataFrame** = dict-like collection of Series
  (columns) sharing one row index; each column has its own dtype.
- **`loc` = label-based, slice end-INCLUSIVE. `iloc` = position-based, slice end-EXCLUSIVE.**
- **Vectorised >> `.map` >> `.apply` >> `iterrows`.** Often 100× between the ends of that chain.
- **`groupby` is split-apply-combine.** `agg` reduces each group to one row; `transform` returns the
  original shape.
- **For large data**: `chunksize`, `usecols`, `dtype`/`category`, `engine="pyarrow"`, Parquet.
- **Chained indexing (`df[mask]['col'] = x`) is the source of `SettingWithCopyWarning`.** Use a
  single `.loc[mask, 'col'] = x`.

---

## Interview questions and full answers

### Q1. What is the difference between a Series and a DataFrame?

A **Series** is a one-dimensional labelled array with a **single dtype**, backed by a NumPy array (or
an Arrow array with the pyarrow backend) plus an `Index`.

A **DataFrame** is two-dimensional: a collection of Series sharing a common row `Index`, where each
**column** can have a different dtype. Selecting one column returns a Series; selecting a list of
columns returns a DataFrame.

```python
import pandas as pd

s = pd.Series([10, 20], index=["a", "b"], name="sales")
print(s.dtype, s.index.tolist())          # int64 ['a', 'b']

df = pd.DataFrame({"name": ["Ravi", "Asha"], "salary": [100, 120], "active": [True, False]})
print(df.dtypes)
# name      object
# salary     int64
# active      bool

print(type(df["salary"]))                 # <class 'pandas.core.series.Series'>
print(type(df[["salary"]]))               # <class 'pandas.core.frame.DataFrame'>  — note [[ ]]
```

**Why the index matters** (and why it's more than a row number): operations **align on the index**
automatically. That's powerful and it's a common source of surprise:

```python
a = pd.Series([1, 2, 3], index=[0, 1, 2])
b = pd.Series([10, 20, 30], index=[1, 2, 3])
print(a + b)
# 0     NaN     <- index 0 exists only in a
# 1    11.0
# 2    22.0
# 3     NaN     <- index 3 exists only in b
```

After filtering or concatenating, indexes get holes or duplicates — `reset_index(drop=True)` is the
fix when you want clean positional labels.

---

### Q2. Difference between `loc` and `iloc`?

- **`.loc[]` selects by LABEL.** Slices are **end-inclusive**. Accepts boolean masks and callables.
- **`.iloc[]` selects by INTEGER POSITION.** Slices are **end-exclusive**, like normal Python.

The inclusive/exclusive asymmetry trips people up constantly. The reason: with labels there's no
"one past the end" to name, so pandas includes the endpoint you asked for.

```python
import pandas as pd

df = pd.DataFrame({"x": [1, 2, 3]}, index=["a", "b", "c"])

print(df.loc["a":"b"])      # rows a AND b     — 2 rows, END-INCLUSIVE
print(df.iloc[0:2])         # rows 0 and 1     — 2 rows, END-EXCLUSIVE

print(df.loc[df.x > 1, "x"])          # boolean mask + column, in one call
print(df.loc[:, ["x"]])               # all rows, selected columns
print(df.iloc[-1])                    # last row by position
print(df.loc[lambda d: d.x > 1])      # callable — chainable, avoids naming an intermediate
```

**The confusing case: an integer index.** `df.loc[0]` means *the row labelled 0*; `df.iloc[0]` means
*the first row*. With a default `RangeIndex` these coincide; after sorting or filtering they don't:

```python
df = pd.DataFrame({"x": [10, 20, 30]})
df = df.sort_values("x", ascending=False)   # index is now [2, 1, 0]
print(df.loc[0])    # x = 10 — the row LABELLED 0, which is now last
print(df.iloc[0])   # x = 30 — the FIRST row
```

Also worth knowing: **`.at` / `.iat`** are the scalar-only fast paths — noticeably quicker than
`.loc`/`.iloc` when you're reading one cell in a loop (though a loop reading cells is itself a smell).

---

### Q3. How do you handle missing data?

**Detect** first, decide second:

```python
df.isna().sum()                    # count of NaN per column — always start here
df.isna().mean()                   # fraction missing per column
df[df.isna().any(axis=1)]          # the actual offending rows
```

**Then choose based on what the missingness MEANS.** This is the part interviewers listen for —
blindly `fillna(0)` on a salary column invents data and corrupts every downstream average.

| Technique | When |
|---|---|
| `dropna(subset=["ts"])` | The row is unusable without that field |
| `dropna(thresh=3)` | Keep rows with at least 3 non-null values |
| `fillna(0)` | Zero is the genuine semantic default (e.g. a count of events) |
| `fillna(df.col.median())` | Numeric imputation; median beats mean with outliers |
| `fillna("UNKNOWN")` | Categorical; makes the gap explicit rather than silent |
| `ffill()` / `bfill()` | **Time series** — carry the last known reading forward |
| `interpolate()` | Continuous numeric series with a meaningful trend |
| Leave as `NaN` | Aggregations skip NaN by default — often the correct choice |

```python
df = pd.DataFrame({"city": ["A", None, "B"], "sales": [100.0, None, 50.0]})

df["sales"] = df["sales"].fillna(df["sales"].median())   # numeric -> median
df["city"] = df["city"].fillna("UNKNOWN")                # categorical -> explicit sentinel
```

**Three details worth volunteering:**

1. **`NaN` is a float**, so an integer column containing missing values is upcast to `float64`. Use
   the **nullable** dtypes (`Int64` with a capital I, `boolean`, `string`) to keep integers integral:
   `df["n"] = df["n"].astype("Int64")`.
2. **`np.nan != np.nan`.** Never compare with `==`; use `.isna()`.
3. **`inplace=True` is being phased out** and never saved meaningful memory anyway. Prefer
   reassignment — it also chains better.

---

### Q4. Explain `groupby` with multiple aggregations.

`groupby` is **split-apply-combine**: split rows into groups by key, apply a function to each group,
combine the results.

**Named aggregation** is the modern form and gives you clean output column names instead of a
MultiIndex you then have to flatten:

```python
import pandas as pd

df = pd.DataFrame({
    "dept":   ["IT", "IT", "HR", "HR"],
    "emp":    ["a", "b", "c", "d"],
    "salary": [100, 150, 90, 95],
})

out = (df.groupby("dept", as_index=False)
         .agg(headcount=("emp", "count"),
              avg_salary=("salary", "mean"),
              max_salary=("salary", "max"),
              spread=("salary", lambda s: s.max() - s.min())))
print(out)
#   dept  headcount  avg_salary  max_salary  spread
# 0   HR          2        92.5          95       5
# 1   IT          2       125.0         150      50
```

**Details that matter in practice:**

- **`as_index=False`** (or `.reset_index()`) keeps the group key as a column rather than an index.
- **`dropna=False`** includes NaN keys, which are **dropped by default** — a silent data-loss trap.
- **`observed=True`** is essential with `category` dtypes; otherwise pandas produces a row for every
  unobserved category combination, which can explode a grouped result into millions of empty rows.
- **`count` excludes NaN; `size` includes it.** Choosing the wrong one silently changes your answer.
- Grouping by multiple keys: `df.groupby(["dept", "region"])`.
- A **lambda in `agg` is slow** (Python per group). Prefer built-in string names (`"mean"`, `"sum"`)
  which run in C.

---

### Q5. What is the difference between `merge`, `join` and `concat`?

- **`merge`** — SQL-style join on **columns** (or indexes), with `how="inner"|"left"|"right"|
  "outer"|"cross"`. The workhorse.
- **`join`** — a convenience method for joining on the **index**. `df.join(other)` is
  `df.merge(other, left_index=True, right_index=True, how="left")`.
- **`concat`** — stacks frames **without key matching**: `axis=0` vertically (append rows),
  `axis=1` side-by-side (aligning on index).

```python
orders = pd.DataFrame({"oid": [1, 2, 3], "cid": [10, 20, 30]})
cust   = pd.DataFrame({"cid": [10, 20], "name": ["Ravi", "Asha"]})

m = orders.merge(cust, on="cid", how="left", indicator=True, validate="many_to_one")
print(m)
#    oid  cid  name     _merge
# 0    1   10  Ravi       both
# 1    2   20  Asha       both
# 2    3   30   NaN  left_only    <- cid 30 has no customer
```

**The two arguments that catch real bugs, and which you should mention unprompted:**

1. **`indicator=True`** adds a `_merge` column showing `left_only` / `right_only` / `both`. It's the
   fastest way to answer "why did my row count change?"
2. **`validate=`** asserts the join cardinality — `"one_to_one"`, `"one_to_many"`, `"many_to_one"`,
   `"many_to_many"` — and **raises** if it's violated. This catches the classic silent disaster: a
   duplicated key on the right side **fans out** your left rows and inflates every subsequent sum.

```python
# Without validate, a duplicate 'cid' in cust silently doubles matching order rows,
# and your revenue total is now wrong with no error anywhere.
cust_dupe = pd.DataFrame({"cid": [10, 10], "name": ["Ravi", "Ravi Dup"]})
# orders.merge(cust_dupe, on="cid", validate="many_to_one")
# -> MergeError: Merge keys are not unique in right dataset
```

**Always check `len(df)` before and after a merge.** If the row count changed on a left join, you
have a fan-out.

`suffixes=("_l", "_r")` controls the renaming of overlapping non-key columns — set it explicitly, as
the default `_x`/`_y` is unreadable three merges later.

---

### Q6. `apply` vs `map` vs vectorisation — which is fastest?

The performance ladder, best to worst:

1. **Vectorised operations** — column arithmetic, `.str`, `.dt`, `np.where`, `np.select`. These run
   in **C over the whole array** with no Python-level loop.
2. **`Series.map(dict)`** — fast for dictionary lookups.
3. **`Series.apply(func)`** — a Python function call **per element**.
4. **`DataFrame.apply(func, axis=1)`** — constructs a **Series object per row**. Very slow.
5. **`iterrows()`** — constructs a Series per row *and* iterates in Python. The slowest possible way.

The gap between 1 and 5 is routinely **100–1000×** on a million rows.

```python
import pandas as pd, numpy as np

df = pd.DataFrame({"amt": np.random.randint(0, 1000, 1_000_000)})

# SLOW — a Python function call per element
# df["tier"] = df["amt"].apply(lambda a: "high" if a > 500 else "low")

# FAST — vectorised, runs in C
df["tier"] = np.where(df["amt"] > 500, "high", "low")

# Multiple conditions: np.select instead of nested np.where
df["band"] = np.select(
    [df.amt < 100, df.amt < 500],      # conditions, in order
    ["S", "M"],                         # results
    default="L",
)

# String and datetime operations are vectorised too
df["code"] = df["tier"].str.upper().str.slice(0, 2)
```

**How to rewrite an `apply` as vectorised code** — the pattern to describe:

| `apply` shape | Vectorised replacement |
|---|---|
| `if/else` on one column | `np.where(cond, a, b)` |
| Multi-branch `if/elif/else` | `np.select([c1, c2], [r1, r2], default=)` |
| Dict lookup | `.map(mapping)` |
| String manipulation | `.str.*` accessors |
| Date parts | `.dt.year`, `.dt.dayofweek`, … |
| Row-wise arithmetic on columns | Direct column arithmetic: `df.a * df.b` |
| Binning | `pd.cut` / `pd.qcut` |

**When `apply` is genuinely unavoidable:** calling an external API per row, complex logic that can't
be expressed with array ops, or a group-wise operation needing the whole sub-frame. Even then,
consider `df.itertuples()` — it's roughly 10× faster than `iterrows()` because it yields lightweight
namedtuples rather than constructing a Series per row.

---

### Q7. How do you process a CSV larger than memory?

This is the senior question in a Pandas round. Layered answer:

**1. Don't load what you don't need.**

```python
pd.read_csv("sales.csv", usecols=["region", "amount", "ts"])   # skip 40 other columns
```

**2. Use compact dtypes.** Reading with the right dtypes can cut memory 5–10×:

```python
pd.read_csv("sales.csv",
            dtype={"region": "category",      # 1000s of repeated strings -> tiny integer codes
                   "amount": "float32",       # half of float64
                   "qty": "int32"},
            parse_dates=["ts"])
```

**3. Stream in chunks and aggregate incrementally.** This is the core technique — memory stays flat
regardless of file size:

```python
import pandas as pd

totals = {}
for chunk in pd.read_csv("sales.csv",
                         usecols=["region", "amount"],
                         dtype={"region": "category"},
                         chunksize=500_000):
    grouped = chunk.groupby("region", observed=True)["amount"].sum()
    for region, amt in grouped.items():
        totals[region] = totals.get(region, 0) + amt

result = pd.Series(totals).sort_values(ascending=False)
```

`read_csv(..., chunksize=N)` returns a **`TextFileReader`, which is a generator** of DataFrames —
the same laziness principle as [Deep Dive 04](04_generators_iterators.md).

**Caveat to state:** chunking works cleanly for **associative** aggregations (sum, count, min, max)
and for per-chunk filtering. It does **not** work naively for median, exact distinct counts, or
global sorts — those need either a two-pass algorithm, an approximate structure (HyperLogLog,
t-digest), or a real engine.

**4. Convert to Parquet for repeated reads.** Columnar, compressed, typed, and supports predicate/
column pushdown — typically 5–10× smaller and far faster than CSV:

```python
df.to_parquet("sales.parquet", compression="zstd")
pd.read_parquet("sales.parquet", columns=["region", "amount"],
                filters=[("region", "==", "APAC")])       # pushed down — never read
```

**5. Use the pyarrow backend** (`dtype_backend="pyarrow"`) for better memory and native nullability.

**6. Know when to leave Pandas.** Say this explicitly — it shows judgement rather than tool loyalty:

| Tool | When |
|---|---|
| **Polars** | Single machine, multi-core, lazy query optimiser. Often 5–30× faster. |
| **DuckDB** | You want SQL over Parquet/CSV without a server. Excellent for ad-hoc analytics. |
| **Dask** | You want the Pandas API across a cluster or out-of-core. |
| **PySpark** | Genuinely distributed, TB-scale, already on Databricks/EMR. |

---

### Q8. How do you reduce DataFrame memory usage?

**Measure first** — `deep=True` is essential, because without it object columns report only the
pointer array, not the strings themselves:

```python
df.memory_usage(deep=True).sort_values(ascending=False)
df.info(memory_usage="deep")
```

Then, in order of payoff:

```python
# 1. Low-cardinality strings -> category. Usually the single biggest win.
df["region"] = df["region"].astype("category")     # can be 100x smaller

# 2. Downcast numerics to the smallest type that fits
df["qty"] = pd.to_numeric(df["qty"], downcast="integer")     # int64 -> int8 if it fits
df["amt"] = pd.to_numeric(df["amt"], downcast="float")       # float64 -> float32

# 3. Parse dates properly — a datetime64 is 8 bytes; the string "2026-09-30" is ~60
df["ts"] = pd.to_datetime(df["ts"])

# 4. Arrow-backed strings instead of Python objects
df["name"] = df["name"].astype("string[pyarrow]")

# 5. Drop columns you don't need, as early as possible
df = df.drop(columns=["unused_blob"])
```

**The `category` rule of thumb:** worth it when unique values are **less than ~50%** of the rows. A
column of 1,000,000 rows with 50 distinct regions becomes a `int8` code array plus a 50-entry
dictionary. Above that ratio it can *cost* memory.

**Caveat to mention:** `category` makes some operations slower (string ops need decoding), and
`groupby` on a category **without `observed=True`** produces every unobserved combination — a common
memory explosion.

---

### Q9. What is `SettingWithCopyWarning` and how do you avoid it?

It warns that you may be modifying a **copy** rather than the original, so your assignment might
silently do nothing.

The cause is **chained indexing** — two indexing operations in sequence:

```python
df[df.a > 0]["b"] = 1
#  ^^^^^^^^^^^^^ operation 1: returns a NEW frame (possibly a copy)
#                ^^^^^^^^^^ operation 2: assigns into THAT temporary
# The temporary is discarded. df is unchanged. Warning, no error, wrong result.
```

Pandas cannot always tell whether the intermediate is a view or a copy — it depends on dtypes and
memory layout — so it warns rather than guessing.

**The fix: one single indexing operation with `.loc`:**

```python
df.loc[df.a > 0, "b"] = 1          # unambiguous, always modifies df
```

**When you genuinely want a separate frame, say so explicitly:**

```python
subset = df[df.a > 0].copy()       # explicit copy — no warning, no ambiguity
subset["b"] = 1                    # modifies subset only, as intended
```

**The modern resolution: Copy-on-Write.** Pandas 2.x offers it via
`pd.options.mode.copy_on_write = True`, and **Pandas 3.0 makes it the default**. Under CoW every
indexing operation behaves as if it returned a copy, so chained assignment *never* propagates —
the ambiguity is gone, the warning becomes an error, and the rule is simply "always use a single
`.loc`". Mentioning this shows you're current.

---

### Q10. Explain `pivot_table` vs `pivot` vs `melt`.

- **`pivot`** — reshapes **long → wide**. Purely a reshape: it **raises** on duplicate
  index/column pairs because it has no way to combine them.
- **`pivot_table`** — the same reshape but **aggregates** duplicates via `aggfunc`, plus
  `fill_value` and `margins` (grand totals). The one you'll actually use.
- **`melt`** — the inverse: **wide → long**, collapsing columns into key/value rows. Also called
  unpivot.

```python
df = pd.DataFrame({"month":  ["Jan", "Jan", "Feb"],
                   "region": ["N", "S", "N"],
                   "sales":  [100, 80, 120]})

wide = df.pivot_table(index="month", columns="region", values="sales",
                      aggfunc="sum", fill_value=0, margins=True, margins_name="Total")
print(wide)
# region   N   S  Total
# month
# Feb    120   0    120
# Jan    100  80    180
# Total  220  80    300

long = (wide.drop(index="Total", columns="Total")
            .reset_index()
            .melt(id_vars="month", var_name="region", value_name="sales"))
```

**Where each belongs:** wide for human-readable reports and spreadsheets; long ("tidy") for storage,
plotting libraries, and further aggregation. Most pipelines keep data long and pivot only at the
final presentation step.

Related: **`stack`/`unstack`** do the same thing between columns and a MultiIndex level, and
`crosstab` is a frequency-focused shortcut over `pivot_table`.

---

### Q11. How do you work with dates and time series?

```python
df = pd.DataFrame({"ts": pd.date_range("2026-09-01", periods=10, freq="D"),
                   "sales": range(10)})

# .dt accessor for components — vectorised
df["year"]  = df.ts.dt.year
df["dow"]   = df.ts.dt.dayofweek          # Monday = 0
df["is_eom"] = df.ts.dt.is_month_end

# DatetimeIndex unlocks resample / rolling / slicing by date string
df = df.set_index("ts")
print(df.resample("W").sum())             # downsample to weekly
print(df.resample("h").ffill())           # upsample, carrying values forward

df["ma3"]   = df["sales"].rolling(3).mean()              # trailing 3-period average
df["ma3c"]  = df["sales"].rolling(3, center=True).mean() # centred
df["cum"]   = df["sales"].expanding().sum()              # cumulative

df["delta"] = df["sales"].diff()                         # period over period
df["growth"] = df["sales"].pct_change()
df["yoy"]   = df["sales"] / df["sales"].shift(365) - 1   # year over year

print(df.loc["2026-09-03":"2026-09-05"])  # slice a DatetimeIndex by string
```

**Parsing** — always be explicit, because inference is slow and ambiguous:

```python
pd.to_datetime(df.ts, format="%Y-%m-%d")        # explicit format: much faster, no ambiguity
pd.to_datetime(df.ts, errors="coerce")          # bad values -> NaT instead of raising
pd.read_csv(f, parse_dates=["ts"])              # parse at read time
```

**Timezones** — the detail that causes production bugs. A naive timestamp has no zone; comparing it
with an aware one raises. Store **UTC**, convert at the display boundary:

```python
df.ts = df.ts.dt.tz_localize("UTC").dt.tz_convert("Asia/Kolkata")
```

`Timedelta` arithmetic works naturally: `df.ts + pd.Timedelta(days=7)`, and
`(df.end - df.start).dt.total_seconds()`.

---

### Q12. How do you find and remove duplicates?

```python
df.duplicated(subset=["id"], keep="first").sum()    # how many dupes
df[df.duplicated(subset=["id"], keep=False)]        # ALL rows involved — for inspection
df = df.drop_duplicates(subset=["id"], keep="last")
```

`keep` takes `"first"` (default), `"last"`, or `False` (mark every duplicate, keeping none) — and
`keep=False` is what you want when *investigating*, since it shows both sides of each pair.

**The pattern that matters in an event pipeline — "keep the latest record per key":**

```python
latest = (events
          .sort_values("ts")                          # order by time first
          .drop_duplicates("id", keep="last"))        # then keep the final one per id
```

This is **idempotent deduplication**, and it's exactly what you do to a Kafka-exported topic where
at-least-once delivery guarantees duplicates. Sorting first is mandatory — `keep="last"` means *last
in current row order*, not *latest timestamp*. See
[Kafka failure handling](15_kafka_failure_handling.md#q8-what-is-consumer-idempotency-and-why-is-it-essential).

A common alternative using `groupby`:

```python
latest = events.loc[events.groupby("id")["ts"].idxmax()]     # index of max ts per group
```

---

### Q13. What is the difference between `transform` and `agg` in `groupby`?

- **`agg`** reduces each group to **one row**. Output has one row per group.
- **`transform`** returns a result with the **same shape as the input**, aligned back to the original
  rows. Output has the same number of rows as the input.

`transform` is how you add **group-level features to individual rows** — "this row's share of its
department's total" — without a merge:

```python
df = pd.DataFrame({"dept": ["IT", "IT", "HR"], "sal": [100, 300, 50]})

print(df.groupby("dept")["sal"].agg("sum"))
# dept
# HR     50
# IT    400          <- 2 rows (one per group)

df["dept_total"] = df.groupby("dept")["sal"].transform("sum")
df["share"] = df["sal"] / df["dept_total"]
print(df)
#   dept  sal  dept_total  share
# 0   IT  100         400   0.25   <- 3 rows (same as input)
# 1   IT  300         400   0.75
# 2   HR   50          50   1.00
```

Without `transform` you'd `agg` then `merge` back — two steps, a join, and a chance of fan-out.

`transform` also does **group-wise imputation** elegantly:

```python
df["sal"] = df.groupby("dept")["sal"].transform(lambda s: s.fillna(s.median()))
```

The third member of the family is **`filter`**, which keeps or drops **whole groups**:

```python
df.groupby("dept").filter(lambda g: len(g) >= 2)     # only departments with 2+ employees
```

So: `agg` = reduce, `transform` = broadcast back, `filter` = select groups, `apply` = anything else
(and slowest).

---

### Q14. How would you rank or get top-N per group?

Three approaches, each with a reason:

```python
df = pd.DataFrame({"dept": ["IT", "IT", "IT", "HR"],
                   "emp":  list("abcd"),
                   "sal":  [100, 300, 200, 50]})

# 1. Sort then head — simplest, and the usual answer
top2 = df.sort_values("sal", ascending=False).groupby("dept").head(2)

# 2. Rank as a column — when you need the rank itself, not just a filter
df["rank"] = df.groupby("dept")["sal"].rank(ascending=False, method="dense")
top2 = df[df["rank"] <= 2]

# 3. nlargest inside the group — expressive for exactly this job
top2 = df.groupby("dept", group_keys=False).apply(lambda g: g.nlargest(2, "sal"))
```

**`method=` on `rank` is the detail to know** — it's the SQL window-function distinction:

| method | Ties 100, 100, 90 get | SQL equivalent |
|---|---|---|
| `"min"` | 1, 1, 3 | `RANK()` |
| `"dense"` | 1, 1, 2 | `DENSE_RANK()` |
| `"first"` | 1, 2, 3 | `ROW_NUMBER()` |
| `"average"` (default) | 1.5, 1.5, 3 | — |

Approach 1 is fastest for large frames; approach 3 uses `apply` and is slowest. Mention that
trade-off.

---

## Worked example — clean, enrich and summarise Kafka-exported order events

The realistic end-to-end shape: messy export, duplicates from at-least-once delivery, mixed types,
missing values. Written as a single method chain, which is the idiomatic style — each step is
readable and no intermediate variables leak.

```python
import pandas as pd

raw = pd.DataFrame({
    "order_id": [1, 2, 2, 3, 4],
    "ts": ["2026-09-01 10:00", "2026-09-01 11:00", "2026-09-01 11:05",
           "2026-09-02 09:30", None],
    "customer": ["c1", "c2", "c2", "c1", "c3"],
    "amount": ["100", "250", "250", None, "80"],      # strings from JSON!
    "status": ["PAID", "PAID", "PAID", "FAILED", "PAID"],
})

df = (raw
      .dropna(subset=["ts"])                                   # unusable without a timestamp
      .assign(
          ts=lambda d: pd.to_datetime(d.ts),                   # strings -> datetime64
          amount=lambda d: pd.to_numeric(d.amount, errors="coerce").fillna(0),
          customer=lambda d: d.customer.astype("category"),    # low cardinality -> compact
      )
      .sort_values("ts")                                       # order BEFORE deduping
      .drop_duplicates("order_id", keep="last"))               # idempotent dedupe

daily = (df[df.status == "PAID"]
         .groupby([df.ts.dt.date.rename("day"), "customer"], observed=True)
         .agg(orders=("order_id", "nunique"),
              revenue=("amount", "sum"))
         .reset_index())

print(daily)
```

**Why each step is there** — be ready to justify all of them:

- **`dropna(subset=["ts"])`** — an event with no timestamp can't be placed in a daily aggregate.
  Dropping is a *decision*; say so rather than doing it silently.
- **`assign` with lambdas** — each lambda receives the frame *as it is at that point in the chain*,
  so you can reference columns created earlier in the same `assign`.
- **`errors="coerce"`** — turns unparseable amounts into `NaN` instead of raising, then `fillna(0)`
  makes the choice explicit.
- **`sort_values` before `drop_duplicates`** — `keep="last"` is positional, so ordering first is what
  makes "latest wins" true. Order 2 appears twice (at-least-once redelivery); we keep the later.
- **`observed=True`** — mandatory with a `category` key, or you get a row for every
  (day, customer) combination that never happened.
- **`nunique` not `count`** — counts distinct orders, immune to any residual duplication.

---

## Hands-on drills

1. Build a DataFrame with a non-default index, sort it, then call `.loc[0]` and `.iloc[0]` and
   explain why they differ.
2. Time `apply`, `np.where`, and `iterrows` for the same conditional on 1,000,000 rows. Report the
   three numbers as ratios.
3. Merge two frames where the right has a duplicated key. Check `len()` before and after. Then add
   `validate="many_to_one"` and read the error.
4. Reproduce `SettingWithCopyWarning` with chained assignment, confirm the original is unchanged,
   then fix it with `.loc`. Turn on `pd.options.mode.copy_on_write = True` and rerun.
5. Generate a 2 GB CSV. Read it whole (watch memory), then read it with `chunksize` + `usecols` +
   `dtype` and compute the same aggregate. Compare peak RSS.
6. Take a string column with 20 distinct values in 1,000,000 rows. Convert to `category` and compare
   `memory_usage(deep=True)`.
7. Group by a `category` column *without* `observed=True` and watch the row count explode.
8. Use `transform("sum")` to add a group-total column, then achieve the same with `agg` + `merge`.
   Compare line count and think about which fails more dangerously.
9. Deduplicate an event export "latest per key" — once correctly (sort first) and once without
   sorting. Show that the answers differ.

---

## The 60-second spoken answer

> "A Series is a one-dimensional labelled array with one dtype; a DataFrame is a set of Series
> sharing a row index, so operations align on that index. `loc` is label-based and slice-inclusive,
> `iloc` is positional and exclusive — and with an integer index after a sort they diverge. For
> missing data I always start with `isna().sum()` and then choose based on meaning: drop when the row
> is unusable, median for numerics, an explicit UNKNOWN for categoricals, and `ffill` for time
> series — never a blind `fillna(0)`. For performance the ladder is vectorised, then `map`, then
> `apply`, then `iterrows`, and the gap is often a hundredfold, so I rewrite `apply` as `np.where` or
> `np.select`. On merges I use `indicator=True` and `validate=` to catch fan-out, and I check the row
> count before and after. `agg` reduces each group to a row; `transform` broadcasts the group result
> back to the original rows, which is how I add 'share of department total' without a join. For files
> bigger than memory I stream with `chunksize`, restrict with `usecols`, use `category` and downcast
> dtypes, and convert to Parquet for repeated reads — and past a certain point I'd move to Polars,
> DuckDB or Spark rather than fight Pandas."
