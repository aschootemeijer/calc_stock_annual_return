"""
Tests for the XIRR calculation and the cashflow signs, with cashflows whose annual return is known.
They need no internet connection. Run with: python3 -m unittest
"""
import unittest

import pandas as pd

from eval import Investment, calc_xirr


def two_cashflows(invested, returned, start, end):
    """ Cashflows of a single investment; its annual return is (returned / invested) ** (1 / years) - 1 """
    dates = pd.Series(pd.to_datetime([start, end]))
    years = (dates[1] - dates[0]).days / 365.25
    expected = (returned / invested) ** (1 / years) - 1
    return pd.Series([-invested, returned]), dates, expected


class TestCalcXirr(unittest.TestCase):

    def test_ten_percent_in_one_year(self):
        cashflows, dates, expected = two_cashflows(100.0, 110.0, '2025-01-01', '2026-01-01')
        self.assertAlmostEqual(calc_xirr(cashflows, dates), expected, places=6)
        self.assertAlmostEqual(calc_xirr(cashflows, dates), 0.10, places=3)  # 365 days, so very close to 10%

    def test_doubling_in_two_years(self):
        cashflows, dates, expected = two_cashflows(100.0, 200.0, '2024-01-01', '2026-01-01')
        self.assertAlmostEqual(calc_xirr(cashflows, dates), expected, places=6)

    def test_loss(self):
        cashflows, dates, expected = two_cashflows(100.0, 80.0, '2025-01-01', '2026-01-01')
        self.assertAlmostEqual(calc_xirr(cashflows, dates), expected, places=6)

    def test_two_buys(self):
        """ Two buys of 100, one year apart, each growing 10% per year: worth 110 * 1.1 + 110 = 231 after two years """
        cashflows = pd.Series([-100.0, -100.0, 231.0])
        dates = pd.Series(pd.to_datetime(['2024-01-01', '2024-12-31', '2025-12-31']))  # 365 and 365 days apart
        self.assertAlmostEqual(calc_xirr(cashflows, dates), 0.10, places=3)

    def test_missing_cashflow_raises(self):
        cashflows = pd.Series([-100.0, None])
        dates = pd.Series(pd.to_datetime(['2024-01-01', '2025-01-01']))
        with self.assertRaises(ValueError):
            calc_xirr(cashflows, dates)


class FixedValue(Investment):
    """ Minimal subclass, so the shared Investment logic can be tested without downloading prices """

    def value_today(self) -> list[float]:
        return [125.0]


class TestInvestment(unittest.TestCase):

    def setUp(self):
        transactions = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01', '2024-07-01']),
            'delta_n_stock': [10, -4],               # a buy and a sale
            'transaction_total_eur': [100.0, 50.0],  # always positive
        })
        self.investment = FixedValue('test', transactions, usd_to_eur=1.0, today=pd.Timestamp('2025-01-01'))

    def test_buy_negative_sale_positive(self):
        self.assertEqual(self.investment.transaction_cashflows()['cashflow'].tolist(), [-100.0, 50.0])

    def test_value_today_added_on_today(self):
        cashflows = self.investment.cashflows()
        self.assertEqual(cashflows['cashflow'].iloc[-1], 125.0)
        self.assertEqual(cashflows['date'].iloc[-1], pd.Timestamp('2025-01-01'))

    def test_base_class_cannot_be_used_directly(self):
        with self.assertRaises(TypeError):
            Investment('test', self.investment.transactions, 1.0, pd.Timestamp('2025-01-01'))


if __name__ == '__main__':
    unittest.main()
