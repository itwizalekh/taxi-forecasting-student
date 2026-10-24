"""Stage 1: carved from learner cumulative code; assistant-prepared snapshot.
Stages are cumulative: stage 1 also executes preceding stages.
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
