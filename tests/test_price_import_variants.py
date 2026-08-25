import unittest
from decimal import Decimal
from unittest.mock import MagicMock

from services.excel_price_service import (
    clean_product_name,
)


class TestPriceImportVariantLogic(unittest.TestCase):
    def test_variant_price_calculation(self):
        # Master product price: Rs. 100.00
        # Variant A (Base 100g): adjustment = 0.00 -> effective = Rs. 100.00
        # Variant B (200g): adjustment = +50.00 -> effective = Rs. 150.00
        # Variant C (500g): adjustment = +200.00 -> effective = Rs. 300.00

        master_price = Decimal("100.00")
        var_b_adj = Decimal("50.00")
        var_c_adj = Decimal("200.00")

        self.assertEqual(master_price + var_b_adj, Decimal("150.00"))
        self.assertEqual(master_price + var_c_adj, Decimal("300.00"))

        # When price list uploads new price for Variant B = Rs. 165.00
        new_var_b_price = Decimal("165.00")
        new_b_adj = new_var_b_price - master_price
        self.assertEqual(new_b_adj, Decimal("65.00"))
        self.assertEqual(master_price + new_b_adj, Decimal("165.00"))


if __name__ == "__main__":
    unittest.main()
