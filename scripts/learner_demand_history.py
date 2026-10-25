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
print(f"Number of sparse rows: {len(sparse)}")
print(f"Number of dense rows: {len(dense)}")
print(f"Number of zero-count dense rows: {dense[TARGET].eq(0).sum()}")
print(f"Total pickups before expansion: {sparse[TARGET].sum()}")
print(f"Total pickups after expansion: {dense[TARGET].sum()}")

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
sparse_source_hour = sparse_demo.loc[
    (sparse_demo[ZONE] == 101) & (sparse_demo[TIME] < target_time), TIME
].max()
print(
    f"Sparse: count={sparse_result['previous_row_count']}, "
    f"source hour={sparse_source_hour}"
)
print(
    f"Dense: count={dense_result['previous_hour_count']}, "
    f"source hour={target_time - pd.Timedelta(hours=1)}"
)

history = (
    dense.sort_values([ZONE, TIME])
    .reset_index(drop=True)
    .copy()
)

history["lag_1"] = history.groupby(ZONE)[TARGET].shift(1)
history["lag_2"] = history.groupby(ZONE)[TARGET].shift(2)

"""
Do not fill missing lag values with zero.
These represent different situations:
Value	Meaning
0	An available hourly count containing no accepted pickups
NaN in a lag	The required earlier observation is unavailable


For the first hour in this example, there is no earlier history. Inventing a zero would conceal that limitation.
"""

history["past_mean_3"] = (
    history.groupby(ZONE)["lag_1"]
    .transform(
        lambda series: series.rolling(
            window=3,
            min_periods=1,
        ).mean()
    )
)

history["past_std_3"] = (
    history.groupby(ZONE)["lag_1"]
    .transform(
        lambda series: series.rolling(
            window=3,
            min_periods=1,
        ).std(ddof=1)
    )
)

# Sample standard deviation (for n > 1): s = sqrt(sum((x_i - x̄) ** 2) / (n - 1))

"""
With only one available observation, sample standard deviation is undefined, so pandas returns NaN. Leave it visible for now. The repository later fills rolling-standard-deviation NaN values with zero as an explicit implementation convention.
"""

print("\nShort history features:")
print(
    history[
        [
            ZONE,
            TIME,
            TARGET,
            "lag_1",
            "lag_2",
            "past_mean_3",
            "past_std_3",
        ]
    ].to_string(index=False)
)

required_lags = ["lag_1", "lag_2"]

# Inspect missing historical inputs separately.
print("\nMissing required lags:")
print(history[required_lags].isna().to_string(index=False))

# True when at least one required lag is missing in that row.
warmup_mask = history[required_lags].isna().any(axis=1)

excluded = history.loc[warmup_mask].copy()
eligible = history.loc[~warmup_mask].copy()

print(f"\nTotal rows before warm-up exclusion: {len(history)}")

display_columns = [ZONE, TIME, TARGET, *required_lags]

print("\nExcluded rows:")
print(excluded[display_columns].to_string(index=False))

print("\nEligible rows:")
print(eligible[display_columns].to_string(index=False))

excluded_counts = excluded.groupby(ZONE).size().reindex(zones, fill_value=0)
print("\nExcluded-row counts by zone:")
print(excluded_counts.rename("excluded_rows").to_string())

first_eligible_hours = eligible.groupby(ZONE)[TIME].min().reindex(zones)
print("\nFirst eligible hour by zone:")
print(first_eligible_hours.rename("first_eligible_hour").to_string())

assert len(excluded) + len(eligible) == len(history)
assert not eligible[required_lags].isna().any().any()

zone_101 = (
    dense.loc[dense[ZONE].eq(101)]
    .sort_values(TIME)
    .set_index(TIME)[TARGET]
)

origin = pd.Timestamp("2024-01-01 02:00")

# At the forecast origin, only earlier counts are available as model inputs.
observed = zone_101.loc[zone_101.index < origin].tolist()
# Keep later actuals separate: they are answers for evaluation, not inputs that
# a fixed-origin forecast is allowed to see.
future_actuals = zone_101.loc[zone_101.index >= origin]

print("\nObserved before origin:", observed)
print("Evaluation actuals:")
print(future_actuals)

"""
Keeping future_actuals separately lets us evaluate predictions afterward. Their availability in the file does not authorize using them as inputs at the origin.
"""

"""
defining shared forecasting rule
"""
def predict_last_two(values):
    assert len(values) >= 2
    return sum(values[-2:]) / 2

one_step_history = observed.copy()
recursive_history = observed.copy()

one_step_predictions = []
recursive_predictions = []

for _timestamp, actual in future_actuals.items():
    # Rolling one-step evaluation predicts this hour using only data available
    # before it. After the hour has passed, its actual is observed and can
    # legitimately become history for predicting the next hour.
    one_step_prediction = predict_last_two(one_step_history)
    one_step_predictions.append(one_step_prediction)
    one_step_history.append(actual)

    # A fixed-origin forecast must not use any future actuals. Extend its
    # history with the prior prediction instead, so every horizon remains based
    # only on information available at the original `origin`.
    recursive_prediction = predict_last_two(recursive_history)
    recursive_predictions.append(recursive_prediction)
    recursive_history.append(recursive_prediction)

forecast_table = pd.DataFrame(
    {
        "hour": future_actuals.index,
        "actual": future_actuals.to_numpy(),
        "one_step_prediction": one_step_predictions,
        "recursive_prediction": recursive_predictions,
    }
)
print("\nForecast comparison:")
print(forecast_table)

assert one_step_predictions == [1.0, 2.0]
assert recursive_predictions == [1.0, 0.5]
