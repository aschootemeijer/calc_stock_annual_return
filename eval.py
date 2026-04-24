import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests
import datetime
import time
from scipy.optimize import newton
start   = time.time()


class AnnualReturnInvestigation:

    """
    This class calculates annual returns of an investment portfolio.
    It requires a date file with: stock name, ticker, change in number of stocks, transaction amount in euro
    Output: Annual returns in percentage
    """

    def __init__( self ):
        self.vandaag = pd.Timestamp.now().date() #.normalize()

    def load_stocks( self ):
        d = pd.read_csv( '/mnt/c/Users/hp/Desktop/dinges/fin/resultaten_evalueren/gekochte_stox.csv', delimiter=',' )
        #d = pd.read_csv( 'stock_transactions_normalized.csv', delimiter=',' )
        return d

    def add_currency_column( self, ticker ):   # THIS WORKS well but is very slow; half a second per ticker
        try:
            curr = yf.Ticker( ticker ).info.get( 'currency','EUR' )
            return curr
        except Exception:
            return 'NOT found'

    def add_currency_column_quickly( self, d ):   # this has been tested - it gives the same currencies as the get_currency() method 
        d['currency'] = np.where( (d['ticker'].str.contains(r'\.') & (d['ticker']!='XNID.L')), 'EUR', 'USD' )
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
        dp = dp.drop( columns=['broker'] )
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
        # Newton-Raphson method to find rate at which XNPV is 0
        try:
            return np.round(newton(lambda r: xnpv(r, cashflows, dates), 0.1) * 100, 1)
        except RuntimeError:
            return 0.0

    def run_investigation( self ):
        d_raw = self.load_stocks()

        # PRE-PROCESSING
        dividend_in_eur = 32.88
        d = self.add_cashflow_column( d_raw, dividend_in_eur )
        d = self.add_currency_column_quickly( d )
        d['current_value_per_stock'] = d['ticker'].apply( self.add_column_with_current_value_per_stock )
        d = self.add_column_with_current_value_total(d)

        # CASHFLOW OF CURRENT HOLDINGS. Where delta_n_stock=0 (rows reserved for current holdings), assign currently held stock value
        d.loc[ d['delta_n_stock']==0, 'cashflow' ] = d['current_total_eur']

        avg_ylry_returns = self.calc_xirr( d['cashflow'], d['date'])
        print( f'\nOur investments. Annual return: {avg_ylry_returns}%' ) 
        print( f"Total profit: {np.round( sum(d['cashflow']),2 )} EUR" )


class BenchmarkWithSP500( AnnualReturnInvestigation ):

     """
     We use inheritance. This gives this class the methods from its parent class AnnualReturnInvestigation
     This child class can calculate the annual returns had we invested in the S&P500 instead of the stocks we chose, at the times we bought them.
     """
    
    def add_sp500_columns( self, d ):
        d['date']          = pd.to_datetime( d['date'] )
        sp500              = yf.download( '^GSPC',start=d['date'].min(), end=self.vandaag)
        sp500.columns      = sp500.columns.get_level_values(0)
        sp500              = sp500.reset_index()
        sp500_now          = sp500.Close.iloc[-1]
        d                  = d.merge( sp500[['Date','Close']], how='left', left_on='date', right_on='Date' )
        d                  = d.rename( columns={'Close':'SP500'} )
        d['delta_n_sp500'] = [ t/s for t,s in zip(d['transaction_total_eur'],d['SP500']) ] 
        d = d.drop( columns=['Date','broker'] )

        d['cashflow']      = [-t if dn>= 0 else t for dn,t in zip(d['delta_n_stock'],d['transaction_total_eur'])]

        # add important row with TODAY's VALUE 
        current_value                  = sum( d['delta_n_sp500'] ) * d['SP500'].iloc[-1]
        d.loc[ len(d),'name']          = 'current_value'
        d.at[ d.index[-1],'cashflow' ] = current_value
        d.at[ d.index[-1], 'date' ]    = pd.Timestamp.now().normalize()  # self.vandaag
        return d

    def run_benchmark( self ):
        d_raw = self.load_stocks()
        d     = self.add_sp500_columns( d_raw )
        avg_ylry_returns = self.calc_xirr( d['cashflow'], d['date'])
        print( f'\nBenchmarking with S&P500. Annual return: {avg_ylry_returns}%' ) 
        print( f"Total profit: {np.round( sum(d['cashflow']),2 )} EUR" )


if __name__ == "__main__":
    investigation = AnnualReturnInvestigation( )
    investigation.run_investigation( )

    benchmark = BenchmarkWithSP500( )
    benchmark.run_benchmark( )
