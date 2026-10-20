"""Clean messy Excel/CSV files.

Removes empty rows and duplicates, trims whitespace, handles empty values,
flags invalid emails/dates in an `issue` column, and writes a clean file
plus a short summary.

Usage:
    python cleaner.py data.csv
    python cleaner.py data.xlsx --drop-empty --sort-by name --filter "city=Austin"
"""
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

SUPPORTED_EXTENSIONS = {".csv", ".xlsx"}
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y")


class CleanerError(Exception):
    """A problem the user can fix (bad path, bad column, ...)."""


def read_file(path):
    """Read a CSV/XLSX file as text so no value is silently converted."""
    if not path.exists():
        raise CleanerError(f"File not found: {path}")
    extension = path.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise CleanerError(
            f"Unsupported file type '{path.suffix}'. Use a .csv or .xlsx file."
        )
    try:
        if extension == ".csv":
            df = pd.read_csv(
                path, dtype=str, keep_default_na=False, encoding="utf-8-sig"
            )
        else:
            df = pd.read_excel(path, dtype=str, keep_default_na=False)
    except pd.errors.EmptyDataError:
        raise CleanerError("The file is empty.") from None
    except Exception:
        raise CleanerError(
            "Could not read the file. Is it a valid CSV/XLSX file?"
        ) from None
    if df.empty:
        raise CleanerError("The file has no data rows.")
    return df.fillna("")


def find_column(df, name, option):
    """Find a column by name (case-insensitive) or raise a clear error."""
    matches = [c for c in df.columns if c.lower() == name.strip().lower()]
    if not matches:
        available = ", ".join(df.columns)
        raise CleanerError(
            f"Column '{name}' (from {option}) not found. "
            f"Available columns: {available}"
        )
    return matches[0]


def parse_filter(text):
    if "=" not in text:
        raise CleanerError(
            'Invalid --filter. Use the form "column=value", '
            'for example --filter "city=Austin".'
        )
    column, value = text.split("=", 1)
    return column.strip(), value.strip()


def is_valid_email(value):
    return bool(EMAIL_PATTERN.match(value))


def normalize_date(value):
    """Return the date as YYYY-MM-DD, or None if it is not a valid date."""
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def find_issues(df):
    """Return one text per row describing invalid emails/dates ('' if none)."""
    if df.empty:
        return []
    email_cols = [c for c in df.columns if "email" in c.lower()]
    date_cols = [c for c in df.columns if "date" in c.lower()]
    parts = []
    for col in email_cols:
        bad = (df[col] != "") & ~df[col].map(is_valid_email)
        parts.append(bad.map({True: f"invalid {col}", False: ""}))
    for col in date_cols:
        bad = (df[col] != "") & df[col].map(lambda v: normalize_date(v) is None)
        parts.append(bad.map({True: f"invalid {col}", False: ""}))
    if not parts:
        return [""] * len(df)
    joined = pd.concat(parts, axis=1)
    return joined.apply(lambda row: "; ".join(x for x in row if x), axis=1).tolist()


def normalize_dates(df):
    df = df.copy()
    for col in [c for c in df.columns if "date" in c.lower()]:
        df[col] = df[col].map(lambda v: normalize_date(v) or v)
    return df


def clean(df, drop_empty=False, fill_value="N/A", sort_by=None, filter_spec=None):
    """Clean the data. Returns (clean_df, stats)."""
    stats = {"processed": len(df)}
    df = df.copy()
    df.columns = df.columns.str.strip()

    # Check the options first, so we fail before doing any work
    sort_col = find_column(df, sort_by, "--sort-by") if sort_by else None
    filter_col = filter_value = None
    if filter_spec:
        name, filter_value = parse_filter(filter_spec)
        filter_col = find_column(df, name, "--filter")

    df = df.apply(lambda col: col.str.strip())

    blank = (df == "").all(axis=1)
    stats["empty_rows"] = int(blank.sum())
    df = df[~blank]

    duplicated = df.duplicated()
    stats["duplicates"] = int(duplicated.sum())
    df = df[~duplicated]

    if drop_empty:
        has_empty = (df == "").any(axis=1)
        stats["dropped_empty"] = int(has_empty.sum())
        df = df[~has_empty]

    issues = find_issues(df)
    df = normalize_dates(df)
    if not drop_empty:
        df = df.mask(df == "", fill_value)
    df["issue"] = issues

    if filter_col:
        keep = df[filter_col].str.lower() == filter_value.lower()
        stats["filtered_out"] = int((~keep).sum())
        df = df[keep]

    if sort_col:
        df = df.sort_values(by=sort_col, kind="stable", key=lambda s: s.str.lower())

    stats["invalid"] = int((df["issue"] != "").sum())
    stats["valid"] = len(df) - stats["invalid"]
    return df.reset_index(drop=True), stats


def write_output(df, path):
    try:
        if path.suffix.lower() == ".csv":
            df.to_csv(path, index=False, encoding="utf-8")
        else:
            df.to_excel(path, index=False)
    except PermissionError:
        raise CleanerError(
            f"Could not write {path.name}. Is it open in another program?"
        ) from None


def build_summary(input_name, stats):
    lines = [
        f"Cleaning summary for {input_name}",
        "-" * 40,
        f"Processed:  {stats['processed']}",
        f"Valid:      {stats['valid']}",
        f"Invalid:    {stats['invalid']}",
        f"Duplicates: {stats['duplicates']}",
        "",
        f"Empty rows removed: {stats['empty_rows']}",
    ]
    if "dropped_empty" in stats:
        lines.append(f"Rows dropped (empty values): {stats['dropped_empty']}")
    if "filtered_out" in stats:
        lines.append(f"Rows filtered out: {stats['filtered_out']}")
    return "\n".join(lines)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Clean a messy CSV/XLSX file: remove duplicates, handle "
        "empty and invalid values, and write a clean file plus a summary."
    )
    parser.add_argument("input_file", help="path to a .csv or .xlsx file")
    parser.add_argument(
        "--drop-empty",
        action="store_true",
        help="remove rows that have any empty value (default: fill them)",
    )
    parser.add_argument(
        "--fill-value",
        default="N/A",
        help='value used for empty cells (default: "N/A")',
    )
    parser.add_argument("--sort-by", metavar="COLUMN", help="sort the output by a column")
    parser.add_argument(
        "--filter",
        metavar="COLUMN=VALUE",
        help='keep only matching rows, e.g. --filter "city=Austin"',
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    path = Path(args.input_file)
    try:
        df = read_file(path)
        clean_df, stats = clean(
            df, args.drop_empty, args.fill_value, args.sort_by, args.filter
        )
        out_path = path.with_name(f"{path.stem}_clean{path.suffix.lower()}")
        summary_path = path.with_name(f"{path.stem}_summary.txt")
        write_output(clean_df, out_path)
        summary = build_summary(path.name, stats)
        summary_path.write_text(summary + "\n", encoding="utf-8")
    except CleanerError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(summary)
    print()
    print(f"Clean file:   {out_path}")
    print(f"Summary file: {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())