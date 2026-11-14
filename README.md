# csv-unpivot

Turn a wide CSV into a long (tidy) one. Identifier columns stay as they are; the named measure columns are melted into a variable/value pair, one row per measure. Python 3 standard library only.

Use it to reshape month-by-month or otherwise-pivoted extracts before loading a fact table or charting by period.

## Usage

```bash
python3 csv_unpivot.py samples/sales_wide.csv \
  --id product_id,region --cols jan,feb,mar --var month --value amount --drop-null
```

The long CSV is written to stdout. A JSON summary is written to stderr. Use `--write out.csv` to write the CSV to a file instead.

Options:

- `--id product_id,region` identifier columns to keep on every output row.
- `--cols jan,feb,mar` measure columns to unpivot. If omitted, every non-id column is used, in file order.
- `--var month` and `--value amount` name the new columns (defaults: `variable`, `value`).
- `--drop-null` omits rows whose unpivoted value is empty.
- `--write out.csv` (or `--write -` for stdout).

Exit codes: `0` success, `2` bad input (missing columns or a name collision).

## Example output (real run on the samples)

Stdout:

```csv
product_id,region,month,amount
P1,DXB,jan,100
P1,DXB,feb,120
P1,DXB,mar,90
P1,AUH,jan,80
P1,AUH,feb,80
P2,DXB,jan,50
P2,DXB,feb,60
P2,DXB,mar,70
```

Stderr:

```json
{
  "input_rows": 3,
  "id_columns": ["product_id", "region"],
  "unpivoted_columns": ["jan", "feb", "mar"],
  "var_column": "month",
  "value_column": "amount",
  "output_rows": 8,
  "dropped_nulls": 1,
  "written": "-"
}
```

(The stderr JSON was reformatted for width; the tool prints it with one field per line. Exit code was 0.)

Three wide rows become eight long rows. P1 in AUH had a blank March cell, so `--drop-null` dropped that one.

## Tests

```bash
python3 -m unittest -v
```
