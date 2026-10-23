![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) ![Pandas](https://img.shields.io/badge/pandas-%23150458.svg?style=for-the-badge&logo=pandas&logoColor=white) ![NumPy](https://img.shields.io/badge/numpy-%23013243.svg?style=for-the-badge&logo=numpy&logoColor=white) ![Yahoo!](https://img.shields.io/badge/Yahoo!-6001D2?style=for-the-badge&logo=Yahoo!&logoColor=white) ![SciPy](https://img.shields.io/badge/SciPy-%230C55A5.svg?style=for-the-badge&logo=scipy&logoColor=white)

## Investment Performance Analyzer (XIRR Method)

This project calculates the annualized return (**XIRR**) of an investment portfolio based on transaction data. 
For comparison, the code also provides the annualized return had the same euro amounts at the same dates been invested in a benchmark index (S&P 500 or DAX).
<!-- Making use of my astrophysics background, I developed this tool to apply numerical optimization methods to financial datasets. -->
<br>

### 📈 Result Highlight
Investment strategy: we pick stocks from the momentum strategy we devised [here](https://github.com/aschootemeijer/sp500_strategy_backtesting). 
Starting in May 2026, 11 different stocks were purchased for a real portfolio (listed in stock_transactions_normalized.csv). None have been sold so far. At 23.10.2026, the result was:
- An annualized return of **72.1%** for our momentum strategy. 
- An annualized return of **18.7%** for the S&P 500 benchmark (in euros; the stronger dollar adds to this). 

Conclusion: given the low number of investments (11) and short holding periods (0-5 months), this offers less support for the momentum strategy than the backtesting. We caution that an annual return rate this high may not be sustainable.
Still, these first results are very encouraging and provide further support that our momentum strategy works.

<sub>Notes on the stock purchases: 1. to keep a sufficiently diversified portfolio, not all stocks for wich the buy signal triggered were bought. 
2. 4/11 momentum stocks are not in the buy signal list (CNC, DVA, BMPS.MI, ILMN). They are momentum stocks but found using a slightly smaller momentum_factor. 
3. For privacy reasons, all investment in the csv file are multiplied by a factor chosen such that the first entry has a value of €100.</sub>
<br>

### 🚀 Key Features
- **Automated Data Extraction:** Leverages the `yfinance` API for real-time market prices and currency conversion (USD/EUR), using the exchange rate of each transaction date for the benchmark.
- **Accurate Performance Metrics:** Implements the **XIRR (Extended Internal Rate of Return)** algorithm, the industry standard for portfolios with irregular cash flows and dividends.
- **Numerical Optimization:** Utilizes the **Newton-Raphson method** (`scipy.optimize`) to solve for the Net Present Value (NPV) root.
- **Fair Benchmark:** Every buy and sale is mirrored in the benchmark index, at that day's index price.
- **Object-Oriented Design:** An abstract `Investment` base class holds the shared cashflow, XIRR and reporting logic; `Portfolio` and `Benchmark` only define what the investment is worth today.
- **Data Engineering:** Robust handling of time-series data and market holiday gaps using `pandas`.
- **Tested:** Unit tests check the XIRR calculation against cases with a known answer.
<br>

### 🧮 Mathematical Background
The portfolio is treated as a dynamic system. The XIRR calculation is essentially a **root-finding problem**. We seek the rate $r$ such that the sum of all discounted cash flows equals zero:

$$ \sum_{i=1}^{N} \frac{P_i}{(1 + r)^{\frac{d_i - d_0}{365.25}}} = 0 $$

Where:
- $P_i$ is the cash flow on date $d_i$
- $d_0$ is the initial investment date
- $r$ is the annualized internal rate of return (XIRR)

This script solves this equation numerically, ensuring an accurate annualized return regardless of the timing or magnitude of capital injections.
<br>

### 🛠️ Tech Stack
- **Python 3.10+**
- **Pandas & NumPy:** For data transformation and vectorization.
- **SciPy:** Implementing `optimize.newton` for numerical approximations.
- **yfinance:** For current prices, historical index prices and exchange rates.
<br>

### 💻 Usage
Clone the repository, install the requirements and execute eval.py. E.g., in a Linux terminal, enter:
- `git clone https://github.com/aschootemeijer/calc_stock_annual_return`
- `cd calc_stock_annual_return`
- `pip install -r requirements.txt`
- `python3 eval.py`

The settings are at the top of eval.py: `BENCHMARK` (`'SP500'` or `'DAX'`), `CSV_FILE` and the dividend received so far (`DIVIDENDS_EUR`).

It is possible to investigate your own portfolio: then replace the entries in the csv file with your own investments. Each row is one transaction:

| column | meaning |
|---|---|
| `name` | any name for the stock |
| `ticker` | Yahoo Finance ticker, e.g. `DELL` or `BMPS.MI` |
| `date` | transaction date, `YYYY-MM-DD` |
| `delta_n_stock` | number of stocks bought (positive) or sold (negative) |
| `transaction_total_eur` | transaction amount in euros, always positive |

To run the tests (no internet connection needed): `python3 -m unittest`
