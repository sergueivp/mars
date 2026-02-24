#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ComboHarnessSmokeTest(unittest.TestCase):
    def test_harness_creates_json_report(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        harness = repo_root / "tools" / "test_combos.py"
        self.assertTrue(harness.exists(), f"Missing harness: {harness}")

        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [
                    sys.executable,
                    str(harness),
                    "--smoke",
                    "--json-only",
                    "--out-dir",
                    tmp,
                ],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(
                proc.returncode,
                0,
                msg=f"Harness failed.\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}",
            )

            marker = "REPORT_FILE:"
            self.assertIn(marker, proc.stdout, msg=f"Missing report marker.\nstdout:\n{proc.stdout}")
            report_path = Path(proc.stdout.split(marker, 1)[1].strip())
            self.assertTrue(report_path.exists(), f"Report file does not exist: {report_path}")

            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertIn("results", payload)
            self.assertGreater(len(payload["results"]), 0)
            self.assertIn("passRateByBudget", payload)


if __name__ == "__main__":
    unittest.main()
