from pathlib import Path

import pandas as pd

# Resolve paths from this script's location rather than the shell's current
# directory, so the audit can be run from any working directory.
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
# Compare the endpoint Series scalars directly; each expression prints a bool.
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

# These are the two timestamps shared by adjacent splits: train's last hour is
# val's first, and val's last hour is test's first. The row selection below
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

# Remove only the audit label to get the original data columns back. This
# concatenates the saved splits; we will filter by timestamps below, so their
# current row order does not determine the illustrative whole-hour partitions.
source = combined.drop(columns="split").copy()

# Build a chronologically ordered list of unique timestamps. drop_duplicates()
# removes repeated hours caused by rows from different zones (or splits);
# sort_values() then places the remaining timestamps from earliest to latest.
hours = (
    source[TIME_COL]
    .drop_duplicates()
    .sort_values()
    .reset_index(drop=True)
)

# Show both the total record count and distinct-hour count: many zone-hour rows
# can share one timestamp, so the two quantities answer different questions.
print("\nReconstructing illustrative whole-hour boundaries")
print(f"Combined rows: {len(source)}")
print(f"Number of distinct hours: {len(hours)}")

# Convert the 80% and 90% time fractions into zero-based positions in the
# distinct-hour list. int() truncates the fractional result down to an integer.
train_end = int(len(hours) * 0.8)
val_end = int(len(hours) * 0.9)

# These positions are in `hours`, not in the full row table. Because Python
# indexing starts at zero, iloc[train_end] returns the first hour assigned to
# validation; the preceding train_end distinct hours are before it.
validation_start = hours.iloc[train_end]
test_start = hours.iloc[val_end]

print(f"80% cut position: {train_end}; validation starts at {validation_start}")
print(f"90% cut position: {val_end}; test starts at {test_start}")

# Create one Boolean mask per split. Each comparison is wrapped in parentheses
# because pandas combines element-by-element comparisons with `&`, not `and`.
training_mask = (source[TIME_COL] < validation_start)
validation_mask = (
    (source[TIME_COL] >= validation_start)
    & (source[TIME_COL] < test_start)
)
test_mask = (source[TIME_COL] >= test_start)

# Apply each mask with .loc[mask] to keep the matching source rows. copy()
# creates independent DataFrames for the new split dictionary.
strict_splits = {
    "train": source.loc[training_mask].copy(),
    "val": source.loc[validation_mask].copy(),
    "test": source.loc[test_mask].copy(),
}

# Print the same summary fields as Stage 1 for an apples-to-apples comparison.
# Every row at a timestamp is now assigned to the same split.
print("\nStrict whole-hour split summaries")
for split_name, frame in strict_splits.items():
    print(
        f"{split_name}: rows={len(frame)}, "
        f"hours={frame[TIME_COL].nunique()}, "
        f"zones={frame[ZONE_COL].nunique()}, "
        f"first={frame[TIME_COL].min()}, "
        f"last={frame[TIME_COL].max()}"
    )

# Verify strict temporal separation. The end of each earlier split must be
# strictly less than the start of the next split.
strict_train_val = (
    strict_splits["train"][TIME_COL].max()
    < strict_splits["val"][TIME_COL].min()
)
strict_val_test = (
    strict_splits["val"][TIME_COL].max()
    < strict_splits["test"][TIME_COL].min()
)
print(
    "Whole-hour train ends before validation starts: "
    f"{strict_train_val}"
)
print(
    "Whole-hour validation ends before test starts: "
    f"{strict_val_test}"
)

# Label copies before recombining. These labels let us check whether a timestamp
# appears under more than one split name; the original split frames stay intact.
strict_labelled_frames = []
for split_name, frame in strict_splits.items():
    labelled = frame.copy()
    labelled["split"] = split_name
    strict_labelled_frames.append(labelled)

strict_combined = pd.concat(strict_labelled_frames, ignore_index=True)

# Row conservation catches accidental drops or duplication during filtering.
# Check both the expected dataset size and equality with the input row count.
expected_row_count = 145_728
print(f"Strict split total rows: {len(strict_combined):,}")
print(f"Expected total rows: {expected_row_count:,}")
print(f"Row count matches expectation: {len(strict_combined) == expected_row_count}")
print(f"Row count preserved from source: {len(strict_combined) == len(source)}")

# Re-run the zone-hour duplicate test on the new splits. A key is the pair
# (PULocationID, pickup_hour); pickup_count and split name are not part of it.
strict_duplicate_mask = strict_combined.duplicated(
    subset=[ZONE_COL, TIME_COL],
    keep=False,
)
print(f"Duplicate zone-hour rows after splitting: {strict_duplicate_mask.sum()}")
print(f"No duplicate zone-hour keys: {not strict_duplicate_mask.any()}")

# Compare key sets to make sure no source zone-hour pair was lost or introduced.
# MultiIndex represents each pair as one composite key; difference() finds keys
# present on one side but absent from the other.
source_keys = pd.MultiIndex.from_frame(source[[ZONE_COL, TIME_COL]])
strict_keys = pd.MultiIndex.from_frame(strict_combined[[ZONE_COL, TIME_COL]])
missing_keys = source_keys.difference(strict_keys)
extra_keys = strict_keys.difference(source_keys)
print(f"Original zone-hour keys missing: {len(missing_keys)}")
print(f"Unexpected zone-hour keys added: {len(extra_keys)}")
print(f"Every original zone-hour key remains present: {len(missing_keys) == 0}")

# For every timestamp, count how many distinct split labels occur. The required
# result is one for each timestamp: a value above one would directly reveal
# that an hour's rows were divided across splits, which was the original issue.
timestamp_split_counts = strict_combined.groupby(TIME_COL)["split"].nunique()
timestamps_in_one_split = timestamp_split_counts.eq(1).all()
print(
    "Distinct split counts per timestamp:",
    timestamp_split_counts.value_counts().sort_index().to_dict(),
)
print(f"Every timestamp belongs to exactly one split: {timestamps_in_one_split}")
