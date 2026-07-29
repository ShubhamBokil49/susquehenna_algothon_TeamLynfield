import csv
import json
import tempfile
import unittest
from pathlib import Path

from engine.result_export import flatten_result_rows, write_results_csv


class ResultExportTests(unittest.TestCase):
    def test_writes_every_nested_value_and_empty_container(self):
        results = {
            "metadata": {
                "test_id": "TEST_1234ABCD",
                "deterministic": True,
            },
            "summary": {
                "score": 12.5,
                "note": None,
            },
            "series": {
                "days": [1, 2],
                "daily_pnl": [-3.0, 7.25],
            },
            "warnings": [],
        }

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "results.csv"
            write_results_csv(results, output_path)

            with output_path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

        expected_rows = list(flatten_result_rows(results))
        self.assertEqual(len(rows), len(expected_rows))
        self.assertIn(
            {
                "section": "metadata",
                "path": "$.test_id",
                "value_type": "string",
                "value_json": json.dumps("TEST_1234ABCD"),
            },
            rows,
        )
        self.assertIn(
            {
                "section": "warnings",
                "path": "$",
                "value_type": "array",
                "value_json": "[]",
            },
            rows,
        )


if __name__ == "__main__":
    unittest.main()
