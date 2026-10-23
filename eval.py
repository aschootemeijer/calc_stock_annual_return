import time

import numpy as np
import pandas as pd
import yfinance as yf
from scipy.optimize import newton

BENCHMARK = 'SP500'  # choose from the keys of BENCHMARKS
BENCHMARKS = {
    'SP500': {'ticker': '^GSPC', 'currency': 'USD'},
    'DAX': {'ticker': '^GDAXI', 'currency': 'EUR'},
}

CSV_FILE = 'stock_transactions_normalized.csv'  # choose from the keys of DIVIDENDS_EUR
DIVIDENDS_EUR = {  # total dividend received so far
    'stock_transactions_normalized.csv': 3,
    'stock_transactions.csv': 1100,
}


class AnnualReturnInvestigation:
    """
    Calculates the annual return (XIRR) of an investment portfolio.
    Input: a csv file with per transaction: name, ticker, date, delta_n_stock
    (positive for a buy, negative for a sale) and transaction_total_eur (always positive).
    Output: annual return in percent and total profit in EUR.
    """

    def __init__(self):
        self.today = pd.Timestamp.now().date()

    def load_transactions(self):
        return pd.read_csv(CSV_FILE)

    def lookup_currency(self, ticker):
        """
        Slow (about half a second per ticker), so not used in the calculation.
        Use it to check that add_currency_column assigns the right currencies.
        """
        try:
            return yf.Ticker(ticker).info.get('currency', 'EUR')
        except Exception:
            return 'NOT found'

    def add_currency_column(self, d):
        """
        Rule of thumb, checked against lookup_currency for the stocks purchased so far:
        tickers without an exchange suffix (US) and London tickers (*.L) are in USD,
        other European tickers (e.g. *.DE) in EUR.
        The dividend row has no ticker; it is already in EUR.
        """
        is_european = d['ticker'].str.contains(r'\.', na=False)
        is_london = d['ticker'].str.endswith('.L', na=False)
        d['currency'] = np.where(is_european & ~is_london, 'EUR', 'USD')
        d.loc[d['ticker'].isna(), 'currency'] = 'EUR'
        return d

    def add_cashflow_column(self, d, dividend_in_eur):
        """
        Adds the cashflow column, which is what the annual return is calculated from.
        Bought stocks are negative cashflow; sold stocks, dividend and current holdings are positive cashflow.
        Per stock, it calculates the number of stocks held after each transaction, and adds a row
        for today in which the value of the current holdings is filled in later.
        """
        per_stock = []
        for ticker in d['ticker'].unique():
            dt = d[d['ticker'] == ticker].sort_values('date')
            dt['total_n_stock'] = dt['delta_n_stock'].cumsum()
            # copy the last row as today's row; its cashflow is set once today's value is known
            dt = pd.concat([dt, dt.iloc[[-1]]], ignore_index=True)
            last = dt.index[-1]
            dt.at[last, 'date'] = self.today
            dt.at[last, 'delta_n_stock'] = 0
            dt.at[last, 'transaction_total_eur'] = 0
            dt['cashflow'] = [-total if dn > 0 else total if dn < 0 else 0
                              for dn, total in zip(dt['delta_n_stock'], dt['transaction_total_eur'])]
            per_stock.append(dt)
        d = pd.concat(per_stock).reset_index(drop=True)

        # the dividend received so far is added as one final row
        d.loc[len(d)] = {'cashflow': dividend_in_eur}
        d.at[d.index[-1], 'date'] = self.today
        d.at[d.index[-1], 'name'] = 'dividend'
        return d

    def get_current_price(self, ticker):
        """ Gets the current stock price from Yahoo Finance, in the stock's own currency """
        try:
            t = yf.Ticker(ticker)
            price = t.fast_info['last_price']
            if price is None or pd.isna(price):
                price = t.basic_info['last_price']
            return price
        except Exception:
            try:
                return yf.Ticker(ticker).info.get('regularMarketPrice')
            except Exception:
                return None

    def add_current_value_column(self, d):
        usd_to_eur = yf.Ticker('EUR=X').fast_info['last_price']
        d['current_total_eur'] = [n * price if currency == 'EUR' else n * price * usd_to_eur
                                  for currency, n, price in zip(d['currency'], d['total_n_stock'], d['current_price'])]
        d['current_total_eur'] = np.round(d['current_total_eur'], 2)
        return d

    def calc_xirr(self, cashflows, dates):
        """
        (X)IRR: Internal Rate of Return (or annual return)
        XNPV:   eXtended Net Present Value. Essentially uses time difference between cashflows.
        The correct rate (annual return) is the one for which the sum of the XNPV is zero
        """
        if pd.isna(cashflows).any():
            raise ValueError('Cannot calculate XIRR: some cashflows are missing (NaN).')
        dates = pd.to_datetime(dates)

        def xnpv(rate):
            start_date = min(dates)
            return sum(cf / (1 + rate)**((d - start_date).days / 365.25) for cf, d in zip(cashflows, dates))

        # Newton-Raphson method to find the rate at which XNPV is 0. Raises RuntimeError if it does not converge
        return np.round(newton(xnpv, 0.1) * 100, 1)

    def run_investigation(self):
        d = self.load_transactions()
        d = self.add_cashflow_column(d, DIVIDENDS_EUR[CSV_FILE])
        d = self.add_currency_column(d)

        d['current_price'] = d['ticker'].apply(self.get_current_price)
        missing = d.loc[d['ticker'].notna() & d['current_price'].isna(), 'ticker'].unique()
        if len(missing) > 0:
            raise ValueError(f'Could not get a current price for: {", ".join(missing)}')
        d = self.add_current_value_column(d)

        # today's rows (delta_n_stock == 0) get the value of the current holdings as cashflow
        d.loc[d['delta_n_stock'] == 0, 'cashflow'] = d['current_total_eur']
        print('PORTFOLIO DATAFRAME:\n', d)
        annual_return = self.calc_xirr(d['cashflow'], d['date'])
        print(f'\nOur investments. Annual return: {annual_return}%')
        print(f"Total profit: {np.round(sum(d['cashflow']), 2)} EUR")


class BenchmarkComparison(AnnualReturnInvestigation):
    """
    Calculates the annual return had we invested in the benchmark index instead of the stocks we chose,
    with the same euro amounts at the same dates (buys and sales).
    Inherits load_transactions and calc_xirr from AnnualReturnInvestigation.
    """

    def download_daily(self, ticker, start):
        """ Daily Open prices from Yahoo Finance, forward-filled over weekends and holidays """
        data = yf.download(ticker, start=start, end=self.today, auto_adjust=True)
        data.columns = data.columns.get_level_values(0)
        return data['Open'].asfreq('D').ffill()

    def add_benchmark_columns(self, d):
        bench = BENCHMARKS[BENCHMARK]
        d['date'] = pd.to_datetime(d['date'])
        d_bench = self.download_daily(bench['ticker'], start=d['date'].min())
        if bench['currency'] == 'USD':  # convert the index to EUR at each day's exchange rate
            usd_to_eur = self.download_daily('EUR=X', start=d['date'].min())
            d_bench = (d_bench * usd_to_eur).ffill()
        d_bench = d_bench.rename('bench_price_eur').rename_axis('date').reset_index()
        bench_now_eur = d_bench['bench_price_eur'].iloc[-1]
        d = d.merge(d_bench, how='left', on='date')

        # buys (delta_n_stock > 0) add benchmark units and are negative cashflow; sales remove units and are positive cashflow
        direction = np.sign(d['delta_n_stock'])
        d['delta_n_bench'] = direction * d['transaction_total_eur'] / d['bench_price_eur']
        d['cashflow'] = -direction * d['transaction_total_eur']

        # final row: today's value of the benchmark units still held
        d.loc[len(d), 'name'] = 'current_value'
        d.at[d.index[-1], 'cashflow'] = d['delta_n_bench'].sum() * bench_now_eur
        d.at[d.index[-1], 'bench_price_eur'] = bench_now_eur
        d.at[d.index[-1], 'date'] = pd.Timestamp(self.today)
        return d

    def run_benchmark(self):
        d = self.load_transactions()
        d = self.add_benchmark_columns(d)
        print('BENCHMARK DATAFRAME:\n', d)
        annual_return = self.calc_xirr(d['cashflow'], d['date'])
        print(f'\nBenchmarking with {BENCHMARK}. Annual return: {annual_return}%')
        print(f"Total profit: {np.round(sum(d['cashflow']), 2)} EUR")


if __name__ == '__main__':
    start_time = time.time()

    investigation = AnnualReturnInvestigation()
    investigation.run_investigation()

    comparison = BenchmarkComparison()
    comparison.run_benchmark()
    print(f'That took {round(time.time() - start_time)} seconds.')
