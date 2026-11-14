#!/usr/bin/env python3
import csv
import io
import json
import os
import tempfile
import unittest

import csv_unpivot as cu


SAMPLES = os.path.join(os.path.dirname(__file__), "samples")
WIDE = os.path.join(SAMPLES, "sales_wide.csv")


def run_main(argv):
    stdout = io.StringIO()
    stderr = io.StringIO()
    old_out, old_err = cu.sys.stdout, cu.sys.stderr
    cu.sys.stdout, cu.sys.stderr = stdout, stderr
    try:
        code = cu.main(argv)
    finally:
        cu.sys.stdout, cu.sys.stderr = old_out, old_err
    err = stderr.getvalue()
    summary = json.loads(err) if err.strip().startswith("{") else None
    return code, stdout.getvalue(), summary, err


class UnpivotTests(unittest.TestCase):
    def test_sample_keeps_empty_values(self):
        with open(WIDE, newline="", encoding="utf-8") as handle:
            fields, rows = cu.read_rows(handle)
        long_rows, dropped = cu.unpivot(
            rows, fields, ["product_id", "region"], ["jan", "feb", "mar"],
            "month", "amount", drop_null=False,
        )
        self.assertEqual(dropped, 0)
        self.assertEqual(len(long_rows), 9)
        self.assertEqual(long_rows[0], {"product_id": "P1", "region": "DXB", "month": "jan", "amount": "100"})
        self.assertEqual(long_rows[2], {"product_id": "P1", "region": "DXB", "month": "mar", "amount": "90"})
        self.assertEqual(long_rows[5], {"product_id": "P1", "region": "AUH", "month": "mar", "amount": ""})

    def test_drop_null(self):
        with open(WIDE, newline="", encoding="utf-8") as handle:
            fields, rows = cu.read_rows(handle)
        long_rows, dropped = cu.unpivot(
            rows, fields, ["product_id", "region"], ["jan", "feb", "mar"],
            "month", "amount", drop_null=True,
        )
        self.assertEqual(dropped, 1)
        self.assertEqual(len(long_rows), 8)
        self.assertFalse(any(r["product_id"] == "P1" and r["region"] == "AUH" and r["month"] == "mar" for r in long_rows))

    def test_preserves_row_and_column_order(self):
        rows = [
            {"id": "A", "feb": "2", "jan": "1"},
            {"id": "B", "feb": "4", "jan": "3"},
        ]
        long_rows, _ = cu.unpivot(
            rows, ["id", "feb", "jan"], ["id"], ["jan", "feb"], "month", "n"
        )
        self.assertEqual([r["id"] for r in long_rows], ["A", "A", "B", "B"])
        self.assertEqual([r["month"] for r in long_rows], ["jan", "feb", "jan", "feb"])
        self.assertEqual([r["n"] for r in long_rows], ["1", "2", "3", "4"])


class CliTests(unittest.TestCase):
    def test_sample_run_stdout(self):
        code, out, summary, _err = run_main(
            [WIDE, "--id", "product_id,region", "--cols", "jan,feb,mar",
             "--var", "month", "--value", "amount"]
        )
        self.assertEqual(code, 0)
        self.assertEqual(summary["input_rows"], 3)
        self.assertEqual(summary["output_rows"], 9)
        self.assertEqual(summary["dropped_nulls"], 0)
        self.assertEqual(summary["unpivoted_columns"], ["jan", "feb", "mar"])
        self.assertEqual(summary["written"], "-")
        rows = list(csv.DictReader(io.StringIO(out)))
        self.assertEqual(list(rows[0].keys()), ["product_id", "region", "month", "amount"])
        self.assertEqual(len(rows), 9)
        self.assertEqual(rows[0]["amount"], "100")

    def test_default_cols_and_drop_null_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = os.path.join(tmp, "long.csv")
            code, out, summary, _err = run_main(
                [WIDE, "--id", "product_id,region", "--var", "month",
                 "--value", "amount", "--drop-null", "--write", dest]
            )
            self.assertEqual(code, 0)
            self.assertEqual(out, "")
            self.assertEqual(summary["output_rows"], 8)
            self.assertEqual(summary["dropped_nulls"], 1)
            self.assertEqual(summary["written"], dest)
            with open(dest, newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 8)

    def test_missing_id_exits_two(self):
        code, _out, summary, err = run_main(
            [WIDE, "--id", "nope", "--cols", "jan"]
        )
        self.assertEqual(code, 2)
        self.assertIsNone(summary)
        self.assertIn("missing id column", err)

    def test_missing_measure_exits_two(self):
        code, _out, summary, err = run_main(
            [WIDE, "--id", "product_id", "--cols", "apr"]
        )
        self.assertEqual(code, 2)
        self.assertIsNone(summary)
        self.assertIn("missing measure column", err)

    def test_id_value_name_collision_exits_two(self):
        code, _out, summary, err = run_main(
            [WIDE, "--id", "product_id,region", "--var", "region"]
        )
        self.assertEqual(code, 2)
        self.assertIsNone(summary)
        self.assertIn("must not collide", err)


if __name__ == "__main__":
    unittest.main()
