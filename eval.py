"""
Calculates the annual return (XIRR) of a stock portfolio, and compares it with a benchmark index
in which the same euro amounts were invested (and withdrawn) at the same dates.

Input: a csv file with per transaction: name, ticker, date, delta_n_stock
(positive for a buy, negative for a sale) and transaction_total_eur (always positive).

How it works:
  1. Every buy is money out (negative cashflow), every sale money in (positive).
  2. What we still hold is counted as if sold today (positive cashflow), plus dividends.
  3. XIRR: the yearly rate at which all these cashflows, discounted to the first date, sum to zero.
The benchmark does the same, but with every euro going into an index instead.
"""
import time
from abc import ABC, abstractmethod

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


# ---------- Investments ----------

class Investment(ABC):
    """
    Base class: an investment made with the transactions from the csv file.
    Subclasses only define what the investment is worth today, in value_today.
    """

    def __init__(self, label: str, transactions: pd.DataFrame, usd_to_eur: float, today: pd.Timestamp):
        self.label = label
        self.transactions = transactions
        self.usd_to_eur = usd_to_eur
        self.today = today

    def transaction_cashflows(self) -> pd.DataFrame:
        """ Buys (delta_n_stock > 0) are negative cashflow, sales (delta_n_stock < 0) positive """
        direction = np.sign(self.transactions['delta_n_stock'])
        return pd.DataFrame({
            'date': self.transactions['date'],
            'cashflow': -direction * self.transactions['transaction_total_eur'],
        })

    @abstractmethod
    def value_today(self) -> list[float]:
        """ What we would get if we sold everything today: a list of amounts in EUR """

    def cashflows(self) -> pd.DataFrame:
        today_rows = pd.DataFrame({'date': self.today, 'cashflow': self.value_today()})
        return pd.concat([self.transaction_cashflows(), today_rows], ignore_index=True)

    def report(self) -> None:
        cashflows = self.cashflows()
        annual_return = calc_xirr(cashflows['cashflow'], cashflows['date'])
        profit = cashflows['cashflow'].sum()
        print(f'{self.label:<20} Annual return: {annual_return:6.1%}   Total profit: {profit:10.2f} EUR')


class Portfolio(Investment):
    """ The stocks we actually bought: the current value of the holdings plus the dividend received so far """

    def __init__(self, transactions: pd.DataFrame, usd_to_eur: float, today: pd.Timestamp, dividend_eur: float):
        super().__init__('Our investments', transactions, usd_to_eur, today)
        self.dividend_eur = dividend_eur
        self.holdings = self.get_holdings()

    def get_holdings(self) -> pd.DataFrame:
        """ Stocks currently held, with their current value in EUR """
        holdings = (self.transactions.groupby('ticker', as_index=False)
                    .agg(name=('name', 'first'), n_stock=('delta_n_stock', 'sum')))
        holdings = holdings[~np.isclose(holdings['n_stock'], 0)].reset_index(drop=True)
        holdings['currency'] = currency_from_ticker(holdings['ticker'])
        holdings['price'] = holdings['ticker'].map(get_current_price)

        missing = holdings.loc[holdings['price'].isna(), 'ticker']
        if len(missing) > 0:
            raise ValueError(f'Could not get a current price for: {", ".join(missing)}')

        to_eur = np.where(holdings['currency'] == 'USD', self.usd_to_eur, 1.0)
        holdings['value_eur'] = (holdings['n_stock'] * holdings['price'] * to_eur).round(2)
        return holdings

    def value_today(self) -> list[float]:
        return [self.holdings['value_eur'].sum(), self.dividend_eur]


class Benchmark(Investment):
    """
    The same euro amounts invested in a benchmark index: each buy adds index units at that day's price,
    each sale removes them. Today's value is that of the index units still held.
    """

    def __init__(self, transactions: pd.DataFrame, usd_to_eur: float, today: pd.Timestamp, benchmark: str):
        super().__init__(f'Benchmark ({benchmark})', transactions, usd_to_eur, today)
        self.benchmark = benchmark
        daily_price_eur, self.price_now_eur = self.index_prices_eur()
        self.units_held = self.get_units_held(daily_price_eur)

    def index_prices_eur(self) -> tuple[pd.Series, float]:
        """ Daily index prices since the first transaction, and the current index price, both in EUR """
        bench = BENCHMARKS[self.benchmark]
        daily_price = download_daily_open(bench['ticker'], start=self.transactions['date'].min(), end=self.today)
        price_now = get_current_price(bench['ticker'])
        if bench['currency'] == 'USD':  # convert to EUR at each day's exchange rate
            daily_usd_to_eur = download_daily_open('EUR=X', start=daily_price.index[0], end=self.today)
            daily_price = (daily_price * daily_usd_to_eur).ffill()
            price_now *= self.usd_to_eur
        return daily_price, price_now

    def get_units_held(self, daily_price_eur: pd.Series) -> float:
        """ Index units bought minus index units sold, at the index price on each transaction date """
        price_on_date = self.transactions['date'].map(daily_price_eur)
        if price_on_date.isna().any():
            missing_dates = self.transactions.loc[price_on_date.isna(), 'date'].dt.date.tolist()
            raise ValueError(f'No {self.benchmark} price for: {missing_dates}')

        direction = np.sign(self.transactions['delta_n_stock'])
        return (direction * self.transactions['transaction_total_eur'] / price_on_date).sum()

    def value_today(self) -> list[float]:
        return [self.units_held * self.price_now_eur]


# ---------- Annual return ----------

def calc_xirr(cashflows: pd.Series, dates: pd.Series) -> float:
    """
    (X)IRR: Internal Rate of Return (or annual return)
    XNPV:   eXtended Net Present Value. Essentially uses time difference between cashflows.
    The correct rate (annual return) is the one for which the XNPV is zero
    """
    if cashflows.isna().any():
        raise ValueError('Cannot calculate XIRR: some cashflows are missing (NaN).')
    cashflows = cashflows.to_numpy()
    years = ((dates - dates.min()).dt.days / 365.25).to_numpy()

    def xnpv(rate: float) -> float:
        return np.sum(cashflows / (1 + rate)**years)

    # Newton-Raphson method to find the rate at which XNPV is 0. Raises RuntimeError if it does not converge
    return newton(xnpv, 0.1)


def main() -> None:
    start_time = time.time()
    today = pd.Timestamp.today().normalize()
    transactions = pd.read_csv(CSV_FILE, parse_dates=['date'])
    usd_to_eur = get_current_price('EUR=X')

    portfolio = Portfolio(transactions, usd_to_eur, today, DIVIDENDS_EUR[CSV_FILE])
    print('CURRENT HOLDINGS:\n', portfolio.holdings.to_string(index=False), '\n')

    for investment in [portfolio, Benchmark(transactions, usd_to_eur, today, BENCHMARK)]:
        investment.report()
    print(f'\nThat took {round(time.time() - start_time)} seconds.')


# ---------- Market data (Yahoo Finance) ----------

def get_current_price(ticker: str) -> float | None:
    """ Latest price from Yahoo Finance, in the ticker's own currency. None if not found """
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


def download_daily_open(ticker: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    """ Daily Open prices from start up to and including end, forward-filled over weekends and holidays """
    data = yf.download(ticker, start=start, end=end + pd.Timedelta(days=1), auto_adjust=True, progress=False)
    data.columns = data.columns.get_level_values(0)
    return data['Open'].asfreq('D').ffill()


def currency_from_ticker(tickers: pd.Series) -> np.ndarray:
    """
    Rule of thumb, checked against lookup_currency for the stocks purchased so far:
    tickers without an exchange suffix (US) and London tickers (*.L) are in USD,
    other European tickers (e.g. *.DE) in EUR.
    """
    is_european = tickers.str.contains(r'\.')
    is_london = tickers.str.endswith('.L')
    return np.where(is_european & ~is_london, 'EUR', 'USD')


def lookup_currency(ticker: str) -> str:
    """
    Slow (about half a second per ticker), so not used in the calculation.
    Use it to check that currency_from_ticker assigns the right currencies.
    """
    try:
        return yf.Ticker(ticker).info.get('currency', 'EUR')
    except Exception:
        return 'NOT found'


if __name__ == '__main__':
    main()
