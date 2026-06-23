import io
import os
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from resolve_trace import probes
from resolve_trace.cli import main
from resolve_trace.diagnose import trace_command


def capture(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(argv)
    return code, buf.getvalue()


class CliSmoke(unittest.TestCase):
    def test_trace_known_binary(self):
        code, out = capture(["trace", "sh", "--no-log"])
        self.assertEqual(code, 0)
        self.assertIn("Command:", out)
        self.assertIn("Diagnosis:", out)

    def test_trace_shorthand(self):
        code, out = capture(["sh", "--no-log"])
        self.assertEqual(code, 0)
        self.assertIn("Diagnosis:", out)

    def test_trace_not_found_exit_code(self):
        code, out = capture(["trace", "definitely_no_such_cmd_xyz", "--no-log"])
        self.assertEqual(code, 1)
        self.assertIn("not found", out)

    def test_file_missing(self):
        code, _ = capture(["file", "/no/such/path/here"])
        self.assertEqual(code, 1)

    def test_env_and_snapshot_run(self):
        self.assertEqual(capture(["env"])[0], 0)
        self.assertEqual(capture(["snapshot"])[0], 0)

    def test_json_is_valid(self):
        import json
        _, out = capture(["trace", "sh", "--no-log", "--json"])
        json.loads(out)


class ProbeUnits(unittest.TestCase):
    def test_which_all_shape(self):
        res = probes.which_all("sh")
        self.assertIn("primary", res)
        self.assertIn("matches", res)

    def test_init_system_returns_string(self):
        self.assertIsInstance(probes.init_system(), str)

    def test_record_has_diagnosis(self):
        rec = trace_command("sh")
        self.assertIn("diagnosis", rec)
        self.assertTrue(rec["diagnosis"])


if __name__ == "__main__":
    unittest.main()
