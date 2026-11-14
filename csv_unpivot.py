#!/usr/bin/env python3
"""csv-unpivot: turn wide CSV measure columns into long (tidy) rows.

Standard library only. Keeps identifier columns as they are, and melts the
named measure columns into a pair of variable/value columns — the usual
wide-to-long reshape before loading a fact table or charting by period.
"""
import argparse
import csv
import json
import sys


def parse_columns(value):
    return [part.strip() for part in value.split(",") if part.strip()]


def read_rows(handle):
    reader = csv.DictReader(handle)
    if reader.fieldnames is None:
        return [], []
    return list(reader.fieldnames), list(reader)


def missing_columns(fieldnames, required):
    return [name for name in required if name not in fieldnames]


def is_null(value):
    return value is None or str(value).strip() == ""


def unpivot(rows, fieldnames, id_cols, value_cols, var_name, value_name, drop_null=False):
    """Return (long_rows, dropped_nulls).

    Output column order is id columns, then the variable column, then the
    value column. Input row order is preserved; value columns are walked in
    the given order.
    """
    long_rows = []
    dropped = 0
    for row in rows:
        for col in value_cols:
            raw = row.get(col, "")
            if drop_null and is_null(raw):
                dropped += 1
                continue
            out = {name: row.get(name, "") for name in id_cols}
            out[var_name] = col
            out[value_name] = "" if raw is None else raw
            long_rows.append(out)
    return long_rows, dropped


def write_csv(handle, fieldnames, rows):
    writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Unpivot wide CSV measure columns into long variable/value rows."
    )
    parser.add_argument("path", help="wide CSV file")
    parser.add_argument(
        "-i",
        "--id",
        required=True,
        help="identifier column(s) to keep, comma-separated, e.g. product_id,region",
    )
    parser.add_argument(
        "-c",
        "--cols",
        help="measure columns to unpivot, comma-separated (default: every non-id column)",
    )
    parser.add_argument(
        "--var",
        default="variable",
        help="name of the new variable column (default: variable)",
    )
    parser.add_argument(
        "--value",
        default="value",
        help="name of the new value column (default: value)",
    )
    parser.add_argument(
        "--drop-null",
        action="store_true",
        help="omit rows whose unpivoted value is empty",
    )
    parser.add_argument(
        "-o",
        "--write",
        metavar="OUT",
        help="write the long CSV to OUT ('-' for stdout). Default: stdout",
    )
    args = parser.parse_args(argv)

    id_cols = parse_columns(args.id)
    if not id_cols:
        print("csv-unpivot: --id is required", file=sys.stderr)
        return 2
    if args.var in id_cols or args.value in id_cols:
        print(
            "csv-unpivot: --var/--value names must not collide with --id columns",
            file=sys.stderr,
        )
        return 2
    if args.var == args.value:
        print("csv-unpivot: --var and --value must be different names", file=sys.stderr)
        return 2

    try:
        with open(args.path, newline="", encoding="utf-8") as handle:
            fieldnames, rows = read_rows(handle)
    except OSError as exc:
        print(f"csv-unpivot: {exc}", file=sys.stderr)
        return 2

    missing = missing_columns(fieldnames, id_cols)
    if missing:
        print("csv-unpivot: missing id column(s): " + ", ".join(missing), file=sys.stderr)
        return 2

    if args.cols:
        value_cols = parse_columns(args.cols)
        missing_vals = missing_columns(fieldnames, value_cols)
        if missing_vals:
            print(
                "csv-unpivot: missing measure column(s): " + ", ".join(missing_vals),
                file=sys.stderr,
            )
            return 2
        overlap = [name for name in value_cols if name in id_cols]
        if overlap:
            print(
                "csv-unpivot: --cols overlaps --id: " + ", ".join(overlap),
                file=sys.stderr,
            )
            return 2
    else:
        value_cols = [name for name in fieldnames if name not in id_cols]
        if not value_cols:
            print("csv-unpivot: no measure columns left after --id", file=sys.stderr)
            return 2

    long_rows, dropped = unpivot(
        rows, fieldnames, id_cols, value_cols, args.var, args.value, args.drop_null
    )
    out_fields = id_cols + [args.var, args.value]

    dest = args.write if args.write is not None else "-"
    try:
        if dest == "-":
            write_csv(sys.stdout, out_fields, long_rows)
        else:
            with open(dest, "w", newline="", encoding="utf-8") as handle:
                write_csv(handle, out_fields, long_rows)
    except OSError as exc:
        print(f"csv-unpivot: {exc}", file=sys.stderr)
        return 2

    summary = {
        "input_rows": len(rows),
        "id_columns": id_cols,
        "unpivoted_columns": value_cols,
        "var_column": args.var,
        "value_column": args.value,
        "output_rows": len(long_rows),
        "dropped_nulls": dropped,
        "written": dest,
    }
    print(json.dumps(summary, indent=2), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
