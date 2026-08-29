import unittest

from build_ml_benchmark import mol_features


class SmilesValidationTests(unittest.TestCase):
    def test_valid_smiles_returns_features(self):
        self.assertIsNotNone(mol_features("CCO"))

    def test_invalid_smiles_is_rejected(self):
        self.assertIsNone(mol_features("this-is-not-smiles"))


if __name__ == "__main__":
    unittest.main()
