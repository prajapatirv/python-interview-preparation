"""
Series/DataFrame basics: construction, dtypes, and the loc-vs-iloc trap.
Run me: python 01_series_dataframe_basics.py
"""
import pandas as pd


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ---------------------------------------------------------------- Series vs DataFrame
section("Series (1-D, labelled) vs DataFrame (2-D, columns of Series)")
s = pd.Series([10, 20, 30], index=["a", "b", "c"])
print("Series:\n", s, sep="")

df = pd.DataFrame({"name": ["Ravi", "Asha", "Kiran"], "salary": [100, 120, 90]})
print("\nDataFrame:\n", df, sep="")
print("\ndtypes:\n", df.dtypes, sep="")


# ---------------------------------------------------------------- loc vs iloc
section("loc (label-based, slice INCLUSIVE) vs iloc (position-based, slice EXCLUSIVE)")
df2 = pd.DataFrame({"x": [1, 2, 3]}, index=["a", "b", "c"])
print("df2.loc['a':'b']  (labels 'a' through 'b', INCLUSIVE of 'b'):")
print(df2.loc["a":"b"])
print("\ndf2.iloc[0:2]  (positions 0 through 2, EXCLUSIVE of 2):")
print(df2.iloc[0:2])
# Both happen to return the same two rows here, but for a different index (e.g. non-sequential
# labels) or a different slice, they diverge -- that's exactly why interviewers ask this.

print("\nboolean mask with .loc:")
print(df2.loc[df2.x > 1, "x"])


# ---------------------------------------------------------------- reading real data
section("reading the sample CSV")
orders = pd.read_csv("sample_data/orders.csv", parse_dates=["ts"])
print(orders.head())
print("\nshape:", orders.shape)
print("\ncolumn dtypes:\n", orders.dtypes, sep="")

# EXPERIMENT: change df2.loc["a":"b"] to df2.loc["a":"c"] and confirm it includes ALL THREE rows
# -- label slicing is inclusive on both ends, unlike Python list slicing.
