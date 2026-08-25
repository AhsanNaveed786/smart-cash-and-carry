import unittest
from decimal import Decimal

from services.variant_detection_service import (
    extract_base_name_and_size,
    detect_variant_groups,
    SIZE_PATTERN,
)


class TestVariantSizePatterns(unittest.TestCase):
    def test_various_unit_sizes(self):
        units = [
            ("Lipton Tea 250gm", "Lipton Tea", "250gm"),
            ("National Salt 800 gram", "National Salt", "800 gram"),
            ("Rooh Afza 800ml", "Rooh Afza", "800ml"),
            ("Cooking Oil 5 Litre", "Cooking Oil", "5 Litre"),
            ("Rice 10kg", "Rice", "10kg"),
            ("Eggs 12 pcs", "Eggs", "12 pcs"),
            ("Panadol 20 tablets", "Panadol", "20 tablets"),
            ("Tissue 100 sheets", "Tissue", "100 sheets"),
            ("Toothpaste 150g", "Toothpaste", "150g"),
        ]
        for name, expected_base, expected_size in units:
            with self.subTest(name=name):
                base, size = extract_base_name_and_size(name)
                self.assertEqual(base, expected_base)
                self.assertEqual(size, expected_size)


if __name__ == "__main__":
    unittest.main()
