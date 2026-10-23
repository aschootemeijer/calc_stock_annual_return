![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) ![Pandas](https://img.shields.io/badge/pandas-%23150458.svg?style=for-the-badge&logo=pandas&logoColor=white) ![NumPy](https://img.shields.io/badge/numpy-%23013243.svg?style=for-the-badge&logo=numpy&logoColor=white) ![Yahoo!](https://img.shields.io/badge/Yahoo!-6001D2?style=for-the-badge&logo=Yahoo!&logoColor=white) ![SciPy](https://img.shields.io/badge/SciPy-%230C55A5.svg?style=for-the-badge&logo=scipy&logoColor=%white)

## Investment Performance Analyzer (XIRR Method)

This project calculates the annualized return (**XIRR**) of an investment portfolio based on transaction data. 
For comparison, this code also provides the annualized return had the same amount at the same dates been invested in the S&P500.
<!-- Making use of my astrophysics background, I developed this tool to apply numerical optimization methods to financial datasets. -->

## 📈 Result Highlight
Investment strategy: we pick stocks from the momentum strategy we devised (https://github.com/aschootemeijer/sp500_strategy_backtesting). 
Starting in May 2026, 11 different stocks were purchased (listed in stock_transactions_normalized.csv). None have been sold so far. At 23.10.2026, the result was:
- An annualized return of **64.5%** for our momentum strategy. 
- An annualized return of **9.5%** for the S&P500 benchmark. 

Conclusion: given the low number of investments (11) and short holding periods (0-5 months), this offers less support for the momentum strategy than the backtesting. We caution that an annual return rate this high may not be sustainable.
Still, these first results are very encouraging and provide further support that our momentum strategy works.

<sub>Notes on the stock selection: 1. to keep a sufficiently diversified portfolio, not all stocks for wich the buy signal triggered were bought. 2. 3/11 momentum stocks are not in the buy signal list. They are momentum stocks but with a slightly smaller momentum_factor</sub>

### 🚀 Key Features
- **Automated Data Extraction:** Leverages the `yfinance` API for real-time market prices and currency conversion (USD/EUR).
- **Accurate Performance Metrics:** Implements the **XIRR (Extended Internal Rate of Return)** algorithm, the industry standard for portfolios with irregular cash flows and dividends.
- **Numerical Optimization:** Utilizes the **Newton-Raphson method** (`scipy.optimize`) to solve for the Net Present Value (NPV) root.
- **Data Engineering:** Robust handling of time-series data and market holiday gaps using `pandas`.

### 🧮 Mathematical Background
The portfolio is treated as a dynamic system. The XIRR calculation is essentially a **root-finding problem**. We seek the rate $r$ such that the sum of all discounted cash flows equals zero:

$$ \sum_{i=1}^{N} \frac{P_i}{(1 + r)^{\frac{d_i - d_0}{365.25}}} = 0 $$

Where:
- $P_i$ is the cash flow on date $d_i$
- $d_0$ is the initial investment date
- $r$ is the annualized internal rate of return (XIRR)

This script solves this equation numerically, ensuring an accurate annualized return regardless of the timing or magnitude of capital injections.

### 🛠️ Tech Stack
- **Python 3.x**
- **Pandas & NumPy:** For data transformation and vectorization.
- **SciPy:** Implementing `optimize.newton` for numerical approximations.

### 💻 Usage
- Clone the repository, e.g., `git clone https://github.com/aschootemeijer/calc_stock_annual_return`
- Execute eval.py, .e.g., enter in a linux terminal: `python3 eval.py`
