import unittest
from decimal import Decimal

from services.excel_price_service import clean_product_name
from services.variant_detection_service import (
    extract_base_name_and_size,
    detect_variant_groups,
)


class TestCleanProductName(unittest.TestCase):
    def test_clean_patterns(self):
        cases = [
            ("+7910 product name", "product name"),
            ("A-G product name", "product name"),
            ("A One product name", "product name"),
            ("A -1 product name", "product name"),
            ("A product name", "product name"),
            ("A11 product name", "product name"),
            ("A8068 product name", "product name"),
            ("001 candle light", "candle light"),
            ("12 BABY GLASS", "BABY GLASS"),
            ("005 - Lipton Tea", "Lipton Tea"),
            ("Just A Normal Product", "Just A Normal Product"),
            ("Apple Juice 1L", "Apple Juice 1L"),
            ("ABC Product", "ABC Product"),
            ("Lipton Tea 200g", "Lipton Tea 200g"),
            ("Nestle Milk Pack", "Nestle Milk Pack"),
            ("", ""),
            (None, ""),
        ]
        for input_val, expected in cases:
            with self.subTest(input_val=input_val):
                self.assertEqual(clean_product_name(input_val), expected)


class TestVariantDetection(unittest.TestCase):
    def test_extract_base_name_and_size(self):
        cases = [
            ("Lipton Tea 200g", "Lipton Tea", "200g"),
            ("Lipton Tea 500g", "Lipton Tea", "500g"),
            ("Nestle Pure Life 1.5 Litre", "Nestle Pure Life", "1.5 Litre"),
            ("Olpers Milk 1000ml", "Olpers Milk", "1000ml"),
            ("Surf Excel 1kg", "Surf Excel", "1kg"),
            ("A11 Lipton Tea 200g", "Lipton Tea", "200g"),
            ("001 Shan Biryani 50g", "Shan Biryani", "50g"),
            ("Simple Product Without Size", "Simple Product Without Size", None),
        ]
        for name, expected_base, expected_size in cases:
            with self.subTest(name=name):
                base, size = extract_base_name_and_size(name)
                self.assertEqual(base, expected_base)
                self.assertEqual(size, expected_size)

    def test_detect_variant_groups(self):
        rows = [
            {"id": 1, "item_name": "Lipton Yellow Label 100g", "uploaded_price": Decimal("150.00")},
            {"id": 2, "item_name": "Lipton Yellow Label 200g", "uploaded_price": Decimal("280.00")},
            {"id": 3, "item_name": "Lipton Yellow Label 500g", "uploaded_price": Decimal("650.00")},
            {"id": 4, "item_name": "Nestle Milk 1L", "uploaded_price": Decimal("260.00")},
            {"id": 5, "item_name": "Nestle Milk 1.5L", "uploaded_price": Decimal("380.00")},
            {"id": 6, "item_name": "Standalone Soap Bar", "uploaded_price": Decimal("100.00")},
        ]

        groups = detect_variant_groups(rows)

        self.assertIn("lipton yellow label", groups)
        self.assertEqual(len(groups["lipton yellow label"]), 3)
        self.assertEqual(
            [m["size_label"] for m in groups["lipton yellow label"]],
            ["100g", "200g", "500g"]
        )

        self.assertIn("nestle milk", groups)
        self.assertEqual(len(groups["nestle milk"]), 2)

        self.assertNotIn("standalone soap bar", groups)


if __name__ == "__main__":
    unittest.main()
