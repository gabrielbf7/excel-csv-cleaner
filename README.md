# Excel/CSV Cleaner

Python command-line tool that cleans messy `.csv` and `.xlsx` files: removes empty rows and duplicates, handles empty and invalid values, and writes a clean file plus a short summary.

> All data in `samples/` is **fictional**. No real personal data is used.

## What it does

- Reads `.csv` or `.xlsx` and writes the clean file in the same format.
- Removes fully empty rows and exact duplicates; trims extra spaces.
- Fills empty values with `N/A` (or drops those rows with `--drop-empty`).
- Validates emails and dates (dates become `YYYY-MM-DD`). Invalid rows are kept and marked in an `issue` column.
- Optional sort and filter.
- Prints a summary and saves it to `<file>_summary.txt`.
- Clear error messages instead of tracebacks.

## Setup

Requires Python 3. Windows (PowerShell):

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

macOS / Linux:

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

```
python cleaner.py samples/messy_customers.csv
```

Output:

```
Cleaning summary for messy_customers.csv
----------------------------------------
Processed: 196
Valid: 156
Invalid: 14
Duplicates: 20

Empty rows removed: 6

Clean file: samples/messy_customers_clean.csv
Summary file: samples/messy_customers_summary.txt
```

The clean file and the summary are saved next to the input file.

## Options

| Option | What it does |
| --- | --- |
| `--drop-empty` | Remove rows that have any empty value (default: fill them) |
| `--fill-value TEXT` | Text used for empty cells (default: `N/A`) |
| `--sort-by COLUMN` | Sort the output by a column |
| `--filter COLUMN=VALUE` | Keep only rows where the column equals the value |

Example:

```
python cleaner.py data.csv --filter "city=Austin" --sort-by name
```

## Sample files

- `samples/messy_customers.csv`: 196 fictional rows with blank rows, duplicates, extra spaces, missing values and invalid emails/dates.
- `samples/messy_customers_clean.csv` and `samples/messy_customers_summary.txt`: the result of the command above.
- `samples/make_sample_data.py`: regenerates the sample input.

## Tests

```
pytest
```

## Limitations

- Only columns whose name contains `email` or `date` are validated; phone numbers are not.
- Dates are accepted as `YYYY-MM-DD` or `MM/DD/YYYY`; other formats are flagged as invalid.
- For `.xlsx`, only the first sheet is read.

## Author

Gabriel Fantin - [GitHub](https://github.com/gabrielbf7)