import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from envdiff import parse_env_file, diff_env, mask, format_report, main  # noqa: E402


class TestParseEnvFile(unittest.TestCase):
    def test_basic_parse(self, tmp_path=Path("/tmp/envdiff_test_basic.env")):
        tmp_path.write_text(
            "\n".join(
                [
                    "# comment",
                    "",
                    "FOO=bar",
                    "export BAZ=qux",
                    'QUOTED="hello world"',
                    "SINGLE='it is fine'",
                    "EMPTY=",
                    "DUPLICATE=first",
                    "DUPLICATE=second",
                    "NOT_A_VAR_LINE_WITHOUT_EQUALS",
                ]
            )
        )
        result = parse_env_file(tmp_path)
        self.assertEqual(result["FOO"], "bar")
        self.assertEqual(result["BAZ"], "qux")
        self.assertEqual(result["QUOTED"], "hello world")
        self.assertEqual(result["SINGLE"], "it is fine")
        self.assertEqual(result["EMPTY"], "")
        self.assertEqual(result["DUPLICATE"], "second")
        self.assertNotIn("NOT_A_VAR_LINE_WITHOUT_EQUALS", result)
        tmp_path.unlink()


class TestDiffEnv(unittest.TestCase):
    def test_only_in_a(self):
        a = {"A": "1", "B": "2"}
        b = {"A": "1"}
        result = diff_env(a, b)
        self.assertEqual(result.only_in_a, ["B"])
        self.assertEqual(result.only_in_b, [])
        self.assertEqual(result.differing, [])
        self.assertEqual(result.identical, ["A"])
        self.assertTrue(result.has_differences())

    def test_only_in_b(self):
        a = {"A": "1"}
        b = {"A": "1", "C": "3"}
        result = diff_env(a, b)
        self.assertEqual(result.only_in_b, ["C"])
        self.assertTrue(result.has_differences())

    def test_differing_values(self):
        a = {"A": "1"}
        b = {"A": "2"}
        result = diff_env(a, b)
        self.assertEqual(result.differing, ["A"])
        self.assertTrue(result.has_differences())

    def test_no_differences(self):
        a = {"A": "1", "B": "2"}
        b = {"A": "1", "B": "2"}
        result = diff_env(a, b)
        self.assertFalse(result.has_differences())
        self.assertEqual(result.identical, ["A", "B"])


class TestMask(unittest.TestCase):
    def test_mask_nonempty(self):
        self.assertEqual(mask("secret123"), "<set, 9 chars>")

    def test_mask_empty(self):
        self.assertEqual(mask(""), "<empty>")

    def test_mask_never_leaks(self):
        value = "super-secret-token-xyz"
        masked = mask(value)
        self.assertNotIn(value, masked)


class TestFormatReport(unittest.TestCase):
    def test_masked_by_default(self):
        a = {"TOKEN": "abc123"}
        b = {"TOKEN": "def456"}
        result = diff_env(a, b)
        report = format_report(result, "a.env", "b.env", a, b, show_values=False)
        self.assertNotIn("abc123", report)
        self.assertNotIn("def456", report)
        self.assertIn("<set, 6 chars>", report)

    def test_show_values_flag(self):
        a = {"TOKEN": "abc123"}
        b = {"TOKEN": "def456"}
        result = diff_env(a, b)
        report = format_report(result, "a.env", "b.env", a, b, show_values=True)
        self.assertIn("abc123", report)
        self.assertIn("def456", report)


class TestMainCLI(unittest.TestCase):
    def setUp(self):
        self.file_a = Path("/tmp/envdiff_cli_a.env")
        self.file_b = Path("/tmp/envdiff_cli_b.env")

    def tearDown(self):
        for f in (self.file_a, self.file_b):
            if f.exists():
                f.unlink()

    def test_exit_code_zero_when_identical(self):
        self.file_a.write_text("A=1\nB=2\n")
        self.file_b.write_text("A=1\nB=2\n")
        code = main([str(self.file_a), str(self.file_b)])
        self.assertEqual(code, 0)

    def test_exit_code_one_when_different(self):
        self.file_a.write_text("A=1\nB=2\n")
        self.file_b.write_text("A=1\n")
        code = main([str(self.file_a), str(self.file_b)])
        self.assertEqual(code, 1)

    def test_exit_code_two_when_file_missing(self):
        code = main(["/tmp/does_not_exist_a.env", "/tmp/does_not_exist_b.env"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
