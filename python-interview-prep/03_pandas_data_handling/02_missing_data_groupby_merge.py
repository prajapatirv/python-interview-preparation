"""
Missing data, groupby (agg vs transform), and merge with indicator.
Run me: python 02_missing_data_groupby_merge.py
"""
import pandas as pd


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


orders = pd.read_csv("sample_data/orders.csv", parse_dates=["ts"])

# ---------------------------------------------------------------- missing data
section("missing data: detect, then decide fillna vs dropna based on MEANING")
print("nulls per column:\n", orders.isna().sum(), sep="")

# `amount` missing on a FAILED order plausibly means "no charge happened" -> 0 makes sense.
# `region` missing is more like "we don't know" -> an explicit sentinel, not 0/blank.
clean = orders.copy()
clean["amount"] = clean["amount"].fillna(0)
clean["region"] = clean["region"].fillna("UNKNOWN")
print("\nafter fillna:\n", clean[["order_id", "amount", "region"]], sep="")


# ---------------------------------------------------------------- dedupe (idempotent ingestion)
section("drop_duplicates — order_id=2 appears twice (a re-delivered Kafka message, say)")
deduped = clean.sort_values("ts").drop_duplicates("order_id", keep="last")
print(f"rows before: {len(clean)}, after dedupe: {len(deduped)}")


# ---------------------------------------------------------------- groupby: agg vs transform
section("groupby().agg() reduces to one row per group; transform() keeps the original shape")
paid = deduped[deduped.status == "PAID"]

by_region = paid.groupby("region").agg(
    orders=("order_id", "nunique"),
    revenue=("amount", "sum"),
    avg_order=("amount", "mean"),
).reset_index()
print("agg (one row per region):\n", by_region, sep="")

paid = paid.copy()
paid["region_total"] = paid.groupby("region")["amount"].transform("sum")
paid["pct_of_region"] = paid["amount"] / paid["region_total"]
print("\ntransform (same shape as input, with a new per-row feature):\n",
      paid[["order_id", "region", "amount", "region_total", "pct_of_region"]], sep="")


# ---------------------------------------------------------------- merge with indicator
section("merge with indicator=True — see exactly which rows matched from which side")
customers = pd.DataFrame({
    "customer": ["c1", "c2", "c3"],
    "tier": ["gold", "silver", "gold"],
})
merged = deduped.merge(customers, on="customer", how="left", indicator=True)
print(merged[["order_id", "customer", "tier", "_merge"]])
print(
    "\nc4 and c5 have no row in `customers` -> tier is NaN and _merge == 'left_only'. "
    "This is exactly how you catch a bad join in production before it silently drops data."
)

# EXPERIMENT: change how="left" to how="inner" and see c4/c5's orders disappear entirely --
# that's the difference between "keep everything and flag the gaps" and "keep only matches."
