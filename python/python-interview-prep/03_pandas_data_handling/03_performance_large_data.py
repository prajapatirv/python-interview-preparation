"""
Performance: apply vs vectorized (timed), chunked reads, and memory reduction.
Run me: python 03_performance_large_data.py
"""
import time

import numpy as np
import pandas as pd


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ---------------------------------------------------------------- apply vs vectorized: timed
section("apply() vs vectorized ops — same result, very different speed")
df = pd.DataFrame({"amt": np.random.randint(0, 1000, 500_000)})

start = time.perf_counter()
tier_apply = df["amt"].apply(lambda a: "high" if a > 500 else "low")
apply_time = time.perf_counter() - start

start = time.perf_counter()
tier_vectorized = np.where(df["amt"] > 500, "high", "low")
vector_time = time.perf_counter() - start

assert (tier_apply.values == tier_vectorized).all()
print(f"apply()     : {apply_time * 1000:8.1f}ms")
print(f"np.where()  : {vector_time * 1000:8.1f}ms")
print(f"speedup     : {apply_time / vector_time:8.1f}x")

# np.select for more than two bands
df["band"] = np.select([df.amt < 100, df.amt < 500], ["S", "M"], default="L")
print("\nband counts:\n", df["band"].value_counts(), sep="")


# ---------------------------------------------------------------- chunked reads for files bigger than RAM
section("chunksize — aggregate a CSV without loading it all into memory")
total_by_region = {}
for chunk in pd.read_csv("sample_data/orders.csv", usecols=["region", "amount"], chunksize=3):
    chunk = chunk.dropna(subset=["region"])
    for region, amt in chunk.groupby("region")["amount"].sum().items():
        total_by_region[region] = total_by_region.get(region, 0) + amt
print("totals accumulated 3-rows-at-a-time:", total_by_region)
# EXPERIMENT: this file only has 10 rows, so chunksize=3 is artificial -- but the loop shape
# (read a chunk, aggregate into a running dict, discard the chunk) is exactly what you'd use
# on a 50GB CSV with chunksize=500_000.


# ---------------------------------------------------------------- memory reduction
section("reduce memory: downcast numerics + category dtype for low-cardinality strings")
big = pd.DataFrame({
    "id": np.arange(200_000),
    "region": np.random.choice(["WEST", "EAST", "SOUTH", "NORTH"], 200_000),
    "amount": np.random.uniform(0, 1000, 200_000),
})
before = big.memory_usage(deep=True).sum()

optimized = big.copy()
optimized["id"] = pd.to_numeric(optimized["id"], downcast="unsigned")
optimized["region"] = optimized["region"].astype("category")
optimized["amount"] = pd.to_numeric(optimized["amount"], downcast="float")
after = optimized.memory_usage(deep=True).sum()

print(f"before : {before / 1024 / 1024:6.2f} MB")
print(f"after  : {after / 1024 / 1024:6.2f} MB")
print(f"saved  : {(1 - after / before) * 100:5.1f}%")

# EXERCISE: profile df["amt"].apply(...) vs np.where(...) again but with a *stateful* per-row
# calculation (e.g. a running discount that depends on the previous row) that can't be trivially
# vectorized. Explain out loud when apply() is genuinely unavoidable.
