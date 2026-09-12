"""Run: python -m unittest discover -s tests -p test_data_builders.py"""
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1]/'scripts/build_site_data.py'
spec = importlib.util.spec_from_file_location('builder', SCRIPT)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class BuilderValidation(unittest.TestCase):
    def test_duplicate_cid_rejected(self):
        with self.assertRaises(ValueError):
            builder.keyed([{'cid':'19'}, {'cid':'19'}])

    def test_non_numeric_cid_rejected(self):
        with self.assertRaises(ValueError):
            builder.keyed([{'cid':'herb_19'}])

    def test_nonfinite_rejected(self):
        for value in ['nan','inf','-inf']:
            with self.assertRaises(ValueError):
                builder.number(value,'dipole')

    def test_missing_optional_not_zero(self):
        self.assertIsNone(builder.number('','xlogp', True))

    def test_missing_required_rejected(self):
        with self.assertRaises(ValueError):
            builder.number('','dipole')

    def test_decimal_not_truncated(self):
        self.assertEqual(builder.number('19.99','frequency'),19.99)


if __name__ == '__main__':
    unittest.main()
