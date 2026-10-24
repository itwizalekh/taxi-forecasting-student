"""Whole-timestamp separation, including unequal timestamp-group sizes."""
import pandas as pd
import pytest

from src.data.splits import timestamp_group_split


def test_unequal_groups_stay_whole_and_rows_are_preserved():
    times = pd.date_range("2024-01-01", periods=10, freq="h")
    df = pd.DataFrame({"t": [t for i, t in enumerate(times) for _ in range(i + 1)]})
    df["id"] = range(len(df))
    parts = timestamp_group_split(df.sample(frac=1, random_state=42), "t")
    assert [p.t.nunique() for p in parts] == [8, 1, 1]
    assert [len(p) for p in parts] == [36, 9, 10]
    assert parts[0].t.max() < parts[1].t.min()
    assert parts[1].t.max() < parts[2].t.min()
    combined = pd.concat(parts)
    assert sorted(combined.id) == list(df.id)
    assert not combined.id.duplicated().any()


@pytest.mark.parametrize("train,val", [(0, .1), (.8, 0), (.9, .2), (.8, -.1)])
def test_invalid_fractions_rejected(train, val):
    with pytest.raises(ValueError):
        timestamp_group_split(pd.DataFrame({"t": range(10)}), "t",
                              train_frac=train, val_frac=val)


def test_missing_timestamps_rejected():
    with pytest.raises(ValueError, match="missing"):
        timestamp_group_split(pd.DataFrame({"t": [pd.Timestamp("2024-01-01"), pd.NaT]}), "t")


def test_insufficient_periods_rejected():
    with pytest.raises(ValueError, match="distinct"):
        timestamp_group_split(pd.DataFrame({"t": [1, 1, 2]}), "t")
