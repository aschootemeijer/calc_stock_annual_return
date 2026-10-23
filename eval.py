import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests
import datetime
import time
from scipy.optimize import newton
start_time = time.time()

benchmark  = 'SP500'   # choose from the keys of BENCHMARKS
BENCHMARKS = { 'SP500': {'ticker': '^GSPC',  'currency': 'USD'},
               'DAX':   {'ticker': '^GDAXI', 'currency': 'EUR'} }

csv_file      = 'stock_transactions_normalized.csv'   # choose from the keys of DIVIDENDS_EUR
DIVIDENDS_EUR = { 'stock_transactions_normalized.csv': 3,      # total dividend received so far
                  'stock_transactions.csv':            1100 }

class AnnualReturnInvestigation:

    """
    This class calculates annual returns of an investment portfolio.
    It requires a date file with: stock name, ticker, change in number of stocks, transaction amount in euro (always positive)
    Output: Annual returns in percentage
    """

    def __init__( self ):
        self.vandaag = pd.Timestamp.now().date() 

    def load_stocks( self ):
        #d = pd.read_csv( '/mnt/c/Users/hp/Desktop/dinges/fin/resultaten_evalueren/stock_transactions.csv', delimiter=',' )
        d = pd.read_csv( csv_file, delimiter=',' )
        #d = d[ d['mom25']=='y' ]
        return d

    def add_currency_column( self, ticker ):  # Works well, but very slow; half a second per ticker. So use only to test if add_currency_column_quickly works
        try:
            curr = yf.Ticker( ticker ).info.get( 'currency','EUR' )
            return curr
        except Exception:
            return 'NOT found'

    def add_currency_column_quickly( self, d ):
        """
        Rule of thumb, checked against the slow add_currency_column method for the stocks purchased so far:
        tickers without an exchange suffix (US) and London tickers (*.L) are in USD, other European tickers (e.g. *.DE) in EUR.
        The dividend row has no ticker; it is already in EUR.
        """
        is_european   = d['ticker'].str.contains( r'\.', na=False )
        is_london     = d['ticker'].str.endswith( '.L', na=False )
        d['currency'] = np.where( is_european & ~is_london, 'EUR', 'USD' )
        d.loc[ d['ticker'].isna(), 'currency' ] = 'EUR'
        return d

    def add_cashflow_column( self, d, dividend_in_eur ):
        """
        This method adds the cashflow column, which is crucial for calculating annual return.
        Bough stocks are negative cashflow, sold stocks, dividend and current holdings are positive cashflow.
        The method organizes the data per stock to calculate currently held number of stocks, taking into account sold or additionally bought stocks.
        """
        dts = []
        d['total_n_stock'] = d['delta_n_stock'] # we overwrite all but the first entry per stock below
        for t in d['ticker'].unique():
            dt = d[ d['ticker'] == t ].copy()
            dt = dt.sort_values( by='date', ascending=True )
            dt['total_n_stock'] = dt['delta_n_stock'].cumsum()
            # make copy of last row as starting point for today's value cashflow. We do this later, not in this function (need to calc today's value first)
            dt = pd.concat( [dt,dt.iloc[[-1]]], ignore_index=True )
            last_ind = dt.index[-1]
            dt.at[ last_ind, 'date']                  = self.vandaag
            dt.at[ last_ind, 'delta_n_stock']         = 0
            dt.at[ last_ind, 'transaction_total_eur'] = 0
            dt['cashflow'] = [ -1*tot if dns>0 else tot if dns<0 else 0 for dns, tot in zip( dt['delta_n_stock'],dt['transaction_total_eur'] ) ]
            dts.append(dt)
        dp = pd.concat( dts ).reset_index( drop=True )
        # ADD DIVIDEND in a final row 
        dp.loc[len(dp)]              = {'cashflow': dividend_in_eur}
        dp.at[ dp.index[-1], 'date'] = self.vandaag
        dp.at[ dp.index[-1], 'name'] = 'dividend'
        return dp

    def add_column_with_current_value_per_stock( self, ticker ):
        """ Gets the current stock value using Yahoo Finance """
        try:
            t = yf.Ticker(ticker)
            price = t.fast_info['last_price']
            if price is None or pd.isna(price):
                price = t.basic_info['last_price']
            return price
        except:
            try:
                return yf.Ticker(ticker).info.get('regularMarketPrice')
            except:
                return None

    def add_column_with_current_value_total( self, d ):
        usd_to_eur = yf.Ticker('EUR=X').fast_info['last_price']
        d['current_total_eur'] = [ n*value if currency=='EUR' else n*value*usd_to_eur 
                                   for currency, n, value in zip( d['currency'], d['total_n_stock'], d['current_value_per_stock'] ) ]
        d['current_total_eur'] = np.round( d['current_total_eur'], 2 )
        return d

    def calc_xirr(self, cashflows, dates):
        """
        (X)IRR: Internal Rate of Return (or annual return)
        XNPV:   eXtended Net Present Value. Essentially uses time difference between cashflows.
        The correct rate (annual return) is the one for which the sum of the XNPV is zero
        """
        dates = pd.to_datetime( dates )
        def xnpv(rate, cashflows, dates):
            start_date = min(dates)
            return sum([cf / (1 + rate)**((d - start_date).days / 365.25) for cf, d in zip(cashflows, dates)])
        if pd.isna( cashflows ).any():
            raise ValueError( 'Cannot calculate XIRR: some cashflows are missing (NaN).' )
        # Newton-Raphson method to find rate at which XNPV is 0. Raises RuntimeError if it does not converge
        return np.round(newton(lambda r: xnpv(r, cashflows, dates), 0.1) * 100, 1)

    def run_investigation( self ):
        d_raw = self.load_stocks()

        # PRE-PROCESSING
        d = self.add_cashflow_column( d_raw, DIVIDENDS_EUR[ csv_file ] )
        d = self.add_currency_column_quickly( d )
        d['current_value_per_stock'] = d['ticker'].apply( self.add_column_with_current_value_per_stock )
        missing = d.loc[ d['ticker'].notna() & d['current_value_per_stock'].isna(), 'ticker' ].unique()
        if len( missing ) > 0:
            raise ValueError( f'Could not get a current price for: {", ".join(missing)}' )
        d = self.add_column_with_current_value_total(d)


        # CASHFLOW OF CURRENT HOLDINGS. Where delta_n_stock=0 (rows reserved for current holdings), assign currently held stock value
        d.loc[ d['delta_n_stock']==0, 'cashflow' ] = d['current_total_eur']
        print( 'PORTFOLIO DATAFRAME:\n', d )
        avg_ylry_returns = self.calc_xirr( d['cashflow'], d['date'])
        print( f'\nOur investments. Annual return: {avg_ylry_returns}%' ) 
        print( f"Total profit: {np.round( sum(d['cashflow']),2 )} EUR" )


class BenchmarkComparison( AnnualReturnInvestigation ):

    """
    We use inheritance. This gives this class the methods from its parent class AnnualReturnInvestigation
    This child class calculates the annual returns had we invested in the benchmark index instead of the stocks we chose,
    with the same euro amounts at the same dates (buys and sales).
    """

    def download_daily( self, ticker, start ):
        """ Daily Open prices from Yahoo Finance, forward-filled over weekends and holidays """
        data         = yf.download( ticker, start=start, end=self.vandaag, auto_adjust=True )
        data.columns = data.columns.get_level_values(0)
        return data['Open'].asfreq('D').ffill()

    def add_benchmark_columns( self, d ):
        bench         = BENCHMARKS[ benchmark ]
        d['date']     = pd.to_datetime( d['date'] )
        d_bench       = self.download_daily( bench['ticker'], start=d['date'].min() )
        if bench['currency'] == 'USD':   # convert the index to EUR at each day's exchange rate
            usd_to_eur = self.download_daily( 'EUR=X', start=d['date'].min() )
            d_bench    = ( d_bench * usd_to_eur ).ffill()
        d_bench       = d_bench.rename( 'bench_price_eur' ).rename_axis( 'date' ).reset_index()
        bench_now_eur = d_bench['bench_price_eur'].iloc[-1]
        d             = d.merge( d_bench, how='left', on='date' )

        # Buys (delta_n_stock > 0) add benchmark units and are negative cashflow; sales remove units and are positive cashflow
        direction          = np.sign( d['delta_n_stock'] )
        d['delta_n_bench'] = direction * d['transaction_total_eur'] / d['bench_price_eur']
        d['cashflow']      = -direction * d['transaction_total_eur']

        # add important row with TODAY's VALUE of the benchmark units still held
        current_value                         = d['delta_n_bench'].sum() * bench_now_eur
        d.loc[ len(d), 'name' ]               = 'current_value'
        d.at[ d.index[-1], 'cashflow' ]        = current_value
        d.at[ d.index[-1], 'bench_price_eur' ] = bench_now_eur
        d.at[ d.index[-1], 'date' ]            = pd.Timestamp( self.vandaag )
        return d

    def run_benchmark( self ):
        d_raw = self.load_stocks()
        d     = self.add_benchmark_columns( d_raw )
        print( 'BENCHMARK DATAFRAME:\n', d )
        avg_ylry_returns = self.calc_xirr( d['cashflow'], d['date'])
        print( f'\nBenchmarking with {benchmark}. Annual return: {avg_ylry_returns}%' )
        print( f"Total profit: {np.round( sum(d['cashflow']),2 )} EUR" )


if __name__ == "__main__":
    investigation = AnnualReturnInvestigation( )
    investigation.run_investigation( )

    comparison = BenchmarkComparison( )
    comparison.run_benchmark( )
    print( f"That took { int(time.time()-start_time+0.5) } seconds.")

