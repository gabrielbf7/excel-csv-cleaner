"""Basic tests for cleaner.py, using the sample data in samples/."""
import shutil
from pathlib import Path

import pandas as pd
import pytest

import cleaner

SAMPLE = Path(__file__).resolve().parent.parent / "samples" / "messy_customers.csv"


@pytest.fixture
def sample_df():
    return cleaner.read_file(SAMPLE)


@pytest.fixture
def result(sample_df):
    return cleaner.clean(sample_df)


def test_summary_numbers(result):
    _, stats = result
    assert stats["processed"] == 196
    assert stats["valid"] == 156
    assert stats["invalid"] == 14
    assert stats["duplicates"] == 20
    assert stats["empty_rows"] == 6


def test_numbers_add_up(result):
    _, stats = result
    total = (
        stats["valid"] + stats["invalid"] + stats["duplicates"] + stats["empty_rows"]
    )
    assert total == stats["processed"]


def test_no_duplicates_left(result):
    df, _ = result
    assert not df.duplicated().any()


def test_whitespace_is_trimmed(result):
    df, _ = result
    for col in ["name", "city"]:
        assert (df[col] == df[col].str.strip()).all()


def test_invalid_rows_are_kept_and_flagged(result):
    df, _ = result
    flagged = df[df["issue"] != ""]
    assert len(flagged) == 14
    assert flagged["issue"].str.startswith("invalid").all()


def test_empty_values_are_filled(result):
    df, _ = result
    assert not (df.drop(columns="issue") == "").any().any()
    assert (df == "N/A").any().any()


def test_drop_empty_removes_rows(sample_df):
    df, stats = cleaner.clean(sample_df, drop_empty=True)
    assert stats["dropped_empty"] == 18
    assert not (df == "N/A").any().any()


def test_filter_and_sort(sample_df):
    df, _ = cleaner.clean(sample_df, sort_by="name", filter_spec="city=Austin")
    assert set(df["city"]) == {"Austin"}
    assert len(df) == 28
    names = df["name"].str.lower().tolist()
    assert names == sorted(names)


def test_email_validation():
    assert cleaner.is_valid_email("a@example.com")
    assert not cleaner.is_valid_email("a@@example.com")
    assert not cleaner.is_valid_email("a@example")


def test_date_normalization():
    assert cleaner.normalize_date("2024-03-15") == "2024-03-15"
    assert cleaner.normalize_date("03/15/2024") == "2024-03-15"
    assert cleaner.normalize_date("2024-02-31") is None
    assert cleaner.normalize_date("not a date") is None


def test_unknown_column_raises(sample_df):
    with pytest.raises(cleaner.CleanerError):
        cleaner.clean(sample_df, sort_by="country")


def test_missing_file_raises(tmp_path):
    with pytest.raises(cleaner.CleanerError):
        cleaner.read_file(tmp_path / "missing.csv")


def test_cli_writes_csv_outputs(tmp_path):
    work = tmp_path / "customers.csv"
    shutil.copy(SAMPLE, work)
    assert cleaner.main([str(work)]) == 0
    assert (tmp_path / "customers_clean.csv").exists()
    assert (tmp_path / "customers_summary.txt").exists()


def test_cli_xlsx_roundtrip(tmp_path, sample_df):
    work = tmp_path / "customers.xlsx"
    sample_df.to_excel(work, index=False)
    assert cleaner.main([str(work)]) == 0
    out = pd.read_excel(
        tmp_path / "customers_clean.xlsx", dtype=str, keep_default_na=False
    )
    assert "issue" in out.columns


def test_cli_returns_error_code_for_missing_file(tmp_path, capsys):
    assert cleaner.main([str(tmp_path / "nope.csv")]) == 1
    assert "Error:" in capsys.readouterr().err