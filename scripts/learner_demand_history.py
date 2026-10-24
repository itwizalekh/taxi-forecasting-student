import pandas as pd


ZONE = "PULocationID"
TIME = "pickup_hour"
TARGET = "pickup_count"

# Teaching example, not actual TLC observations.
sparse = pd.DataFrame(
    {
        ZONE: [101, 101, 101, 202, 202, 202],
        TIME: pd.to_datetime(
            [
                "2024-01-01 00:00",
                "2024-01-01 02:00",
                "2024-01-01 03:00",
                "2024-01-01 00:00",
                "2024-01-01 01:00",
                "2024-01-01 03:00",
            ]
        ),
        TARGET: [2, 4, 1, 3, 1, 2],
    }
)

print("Sparse counts:")
print(sparse.to_string(index=False))

zones = sorted(sparse[ZONE].unique())

hours = pd.date_range(
    start=sparse[TIME].min(),
    end=sparse[TIME].max(),
    freq="h",
)

full_index = pd.MultiIndex.from_product(
    [zones, hours],
    names=[ZONE, TIME],
)

print("\nComplete zone/hour index:")
print(full_index)

# what is "indexed" below, and then what is "expanded" below? What is the difference between them?
# `indexed` contains only the observed rows from `sparse`, keyed by the
# two-level (zone, pickup hour) index rather than numbered rows.
indexed = sparse.set_index([ZONE, TIME])

# `expanded` aligns those observations to `full_index`, adding every missing
# zone/hour combination with a NaN count. Thus, `indexed` is sparse (observed
# combinations only), while `expanded` covers the complete grid; the missing
# counts are filled with zero in the next step.
expanded = indexed.reindex(full_index)

print("\nExpanded grid before filling:")
print(expanded.reset_index().to_string(index=False))

dense = expanded.fillna({TARGET: 0}).reset_index()
dense[TARGET] = dense[TARGET].astype(int)

print("\nDense grid after filling:")
print(dense.to_string(index=False))

# Print summary statistics
print("Number of sparse rows: {len(sparse)}")
print("Number of dense rows: {len(dense)}")
print("Number of zero-count dense rows: {dense[TARGET].eq(0).sum()}")
print("Total pickups before expansion: {sparse[TARGET].sum()}")
print("Total pickups after expansion: {dense[TARGET].sum()}")

assert dense[TARGET].sum() == sparse[TARGET].sum()

# Creating zero-count combinations should change the number of rows, while preserving the total pickups.
# See why this matters for lags

sparse_demo = sparse.sort_values([ZONE, TIME]).copy()
sparse_demo["previous_row_count"] = (
    sparse_demo.groupby(ZONE)[TARGET].shift(1)
)

dense_demo = dense.sort_values([ZONE, TIME]).copy()
dense_demo["previous_hour_count"] = (
    dense_demo.groupby(ZONE)[TARGET].shift(1)
)

print("\nPrevious row in sparse data:")
print(sparse_demo.to_string(index=False))

print("\nPrevious hour in dense data:")
print(dense_demo.to_string(index=False))

"""
Inspect zone 101 at 02:00:
- What count does the sparse version retrieve?
- What count does the dense version retrieve?
- Which source hour supplied each value?
"""

target_time = pd.Timestamp("2024-01-01 02:00")
sparse_result = sparse_demo.loc[
    (sparse_demo[ZONE] == 101) & (sparse_demo[TIME] == target_time)
].iloc[0]
dense_result = dense_demo.loc[
    (dense_demo[ZONE] == 101) & (dense_demo[TIME] == target_time)
].iloc[0]

print("\nPrevious-count comparison for zone 101 at 02:00:")
print(
    f"Sparse: count={sparse_result['previous_row_count']}, "
    f"source hour={sparse_demo.loc[(sparse_demo[ZONE] == 101) & "
    f"(sparse_demo[TIME] < target_time), TIME].max()}"
)
print(
    f"Dense: count={dense_result['previous_hour_count']}, "
    f"source hour={target_time - pd.Timedelta(hours=1)}"
)

