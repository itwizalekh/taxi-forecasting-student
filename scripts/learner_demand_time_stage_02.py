"""Stage 2: carved from learner cumulative code; assistant-prepared snapshot.
Stages are cumulative: stage 2 also executes preceding stages.
Comment clarifications preserve calculations; stage 3 adds reviewed checks.
"""
from pathlib import Path

import pandas as pd

# Resolve paths from this script's location rather than the shell's current
# directory; module invocation still normally starts at the repository root.
REPO_ROOT = Path(__file__).resolve().parents[1]
FEATURES_DIR = REPO_ROOT / "data" / "features"
# Keep column names in constants so the selections below use the same keys.
TIME_COL = "pickup_hour"
ZONE_COL = "PULocationID"

# Load each already-created split into a dictionary keyed by its split name.
# The names are later used both for readable output and to label combined rows.
splits = {}

for split_name in ("train", "val", "test"):
    # Build the expected Parquet path for this split, then read it into pandas.
    file_path = FEATURES_DIR / f"demand_{split_name}.parquet"
    splits[split_name] = pd.read_parquet(file_path)

# Show the available training columns as a quick schema check before auditing.
print("Training columns:")
# Convert the Index of column names into a regular list for straightforward display.
print(splits["train"].columns.tolist())
print()

# Summarize row counts and coverage for every split. Rows are zone-hour records,
# while nunique() counts distinct timestamp or zone values across those records.
for split_name, frame in splits.items():
    print(
        # len(frame) counts records; nunique() counts distinct values in a column.
        # min()/max() on the pickup_hour series give the time coverage endpoints.
        f"{split_name}: rows={len(frame)}, "
        f"hours={frame[TIME_COL].nunique()}, "
        f"zones={frame[ZONE_COL].nunique()}, "
        f"first={frame[TIME_COL].min()}, "
        f"last={frame[TIME_COL].max()}"
    )

# Print the adjacent splits' endpoint timestamps. Equality between endpoints is
# timestamp overlap; strict "<" is false when the endpoint hour is shared.
print("\nSplit boundaries:")
print(f"Last training hour: {splits['train'][TIME_COL].max()}")
print(f"First validation hour: {splits['val'][TIME_COL].min()}")
print(f"Last validation hour: {splits['val'][TIME_COL].max()}")
print(f"First test hour: {splits['test'][TIME_COL].min()}")
# Compare scalar timestamps returned by min/max; each expression prints a bool.
print(
    "Last training hour < First validation hour: "
    f"{splits['train'][TIME_COL].max() < splits['val'][TIME_COL].min()}"
)
print(
    "Last validation hour < First test hour: "
    f"{splits['val'][TIME_COL].max() < splits['test'][TIME_COL].min()}"
)

# Build copies so adding a split label cannot mutate the original DataFrames in
# `splits`. The label records where each row came from after concatenation.
labelled_frames = []

for split_name, frame in splits.items():
    # copy() protects the loaded frame; assigning a scalar string broadcasts
    # that split name into a new column for every row in this copy.
    labelled = frame.copy()
    labelled["split"] = split_name
    # Append each labelled DataFrame so concat can combine all rows below.
    labelled_frames.append(labelled)

# Stack the split DataFrames row-wise. ignore_index=True creates one fresh
# sequential index instead of retaining duplicate indices from the source files.
combined = pd.concat(labelled_frames, ignore_index=True)

# duplicated() tests whether each (zone, hour) pair appears more than once.
# keep=False marks every occurrence of a repeated key, not just later copies.
# The split label is intentionally excluded: same-key records in different
# splits must still be detected as a duplicate zone-hour key.
duplicate_mask = combined.duplicated(subset=[ZONE_COL, TIME_COL], keep=False)
# Boolean DataFrame indexing keeps only rows whose duplicate_mask value is True.
duplicate_rows = combined[duplicate_mask]


def report(text=""):
    # Centralize report output so every section uses consistent print behavior.
    print(text)


# A duplicate key requires both the same zone and the same timestamp; sharing
# an hour alone is not enough. sum() counts True values because bool is numeric
# in Python, while ~ flips each mask value so the second count is False values.
report("\nA. Duplicate zone-hour keys")
report(f"True values in duplicate mask: {duplicate_mask.sum()}")
report(f"False values in duplicate mask: {(~duplicate_mask).sum()}")
report("Matching rows:")
# to_string() prints all matching rows and avoids the display truncation pandas
# may apply to a DataFrame; index=False omits the generated row index.
report(duplicate_rows.to_string(index=False))

# Inspect the earlier split's final hour; the comparisons above establish that it is
# shared in this dataset. The row selection below
# checks each timestamp across the combined data, not only one source split.
boundary_hours = (
    ("train/val", splits["train"][TIME_COL].max()),
    ("val/test", splits["val"][TIME_COL].max()),
)
# Limit boundary output to provenance, zone, timestamp, and observed demand.
boundary_columns = ["split", ZONE_COL, TIME_COL, "pickup_count"]

report("\nB. Shared boundary hours")
for boundary_name, boundary_hour in boundary_hours:
    # Series.eq() compares every combined timestamp to this boundary and
    # produces a Boolean mask with one True/False value per row.
    boundary_mask = combined[TIME_COL].eq(boundary_hour)
    # .loc[mask, columns] selects matching rows and only the requested fields.
    rows = combined.loc[boundary_mask, boundary_columns]
    # groupby().size() counts records per split; reindex() adds any absent split
    # with a zero count and orders the result like the splits dictionary.
    rows_per_split = rows.groupby("split").size().reindex(splits, fill_value=0)

    # Print all rows at this hour, counts for each split, and the number of
    # distinct zones. The zone count is across selected rows from all splits.
    report(f"\n{boundary_name} boundary hour: {boundary_hour}")
    report(rows.to_string(index=False))
    report("Rows per split:")
    report(rows_per_split.to_string())
    report(f"Distinct zones: {rows[ZONE_COL].nunique()}")
