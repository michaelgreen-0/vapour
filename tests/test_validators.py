import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.services.validators import is_valid_fingerprint


class TestValidators(unittest.TestCase):
    valid = "497472E4EADD6B41F735D437F8FC9A8BDC9CF796"

    def test_accepts_real_fingerprint(self):
        self.assertTrue(is_valid_fingerprint(self.valid))

    def test_rejects_lowercase(self):
        self.assertFalse(is_valid_fingerprint(self.valid.lower()))

    def test_rejects_wrong_length(self):
        self.assertFalse(is_valid_fingerprint(self.valid[:39]))
        self.assertFalse(is_valid_fingerprint(self.valid + "A"))

    def test_rejects_spaces_and_non_hex(self):
        self.assertFalse(is_valid_fingerprint("497472E4 EADD6B41"))
        self.assertFalse(is_valid_fingerprint("G" * 40))

    def test_rejects_non_strings(self):
        for value in (None, 123, ["A" * 40], {"fp": self.valid}):
            self.assertFalse(is_valid_fingerprint(value), value)


if __name__ == "__main__":
    unittest.main()
