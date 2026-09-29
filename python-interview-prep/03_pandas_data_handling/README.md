# 03 — Pandas for Data Handling

Needs `pandas` installed (`pip install -r ../requirements.txt`). Run with `py <file>.py`.

## Crib sheet

- **Series** = labelled 1-D array, single dtype. **DataFrame** = dict-like collection of Series
  (columns) sharing a row index; each column can have its own dtype.
- **`loc` vs `iloc`**: `loc` is label-based and slice-*inclusive*; `iloc` is position-based and
  slice-*exclusive* (like normal Python lists). This trips people up constantly — memorize it.
- **Missing data**: detect with `isna().sum()`; fix with `dropna`, `fillna`, `ffill`/`bfill`, or
  `interpolate()` — pick based on what the missingness *means*, never blindly fill with 0.
- **`merge`/`join`/`concat`**: `merge` is SQL-style joins on columns; `join` is a convenience for
  joining on the index; `concat` stacks frames without key matching. Use `indicator=True` on
  `merge` to see which rows matched from which side.
- **`apply` vs vectorized ops**: vectorized ops (`np.where`, `.str`, `.dt`, arithmetic on columns)
  run in C and are fastest; `apply` runs a Python function per row/element and is slow;
  `iterrows()` is slowest of all. Always try to rewrite `apply` as a vectorized expression.
- **`groupby`**: split-apply-combine. `agg` reduces each group to one row; `transform` returns a
  result the same shape as the input (e.g. "this row's value / this group's total").
- **Large data**: `chunksize` for streaming reads, `usecols` to skip unneeded columns, `category`
  dtype for low-cardinality strings, Parquet instead of CSV for repeated reads.

## Files

| File | Topic |
|---|---|
| `01_series_dataframe_basics.py` | Series/DataFrame construction, `loc` vs `iloc`, dtypes |
| `02_missing_data_groupby_merge.py` | `isna`/`fillna`, `groupby().agg()`, `merge` with `indicator` |
| `03_performance_large_data.py` | `apply` vs vectorized (timed), chunked CSV reads, memory reduction |
| `sample_data/orders.csv` | small dataset the examples read from |
