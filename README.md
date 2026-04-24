![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) ![Pandas](https://img.shields.io/badge/pandas-%23150458.svg?style=for-the-badge&logo=pandas&logoColor=white) ![NumPy](https://img.shields.io/badge/numpy-%23013243.svg?style=for-the-badge&logo=numpy&logoColor=white) ![Yahoo!](https://img.shields.io/badge/Yahoo!-6001D2?style=for-the-badge&logo=Yahoo!&logoColor=white) ![SciPy](https://img.shields.io/badge/SciPy-%230C55A5.svg?style=for-the-badge&logo=scipy&logoColor=%white)

## Investment Performance Analyzer (XIRR Method)

This project calculates the annualized return (**XIRR**) of an investment portfolio based on transaction data. Making use of my astrophysics background, I developed this tool to apply numerical optimization methods to financial datasets.
For comparison, this code also provides the annualized return had the same amount at the same dates been invested in the S&P500.

## Result Highlight
Our investment strategy is picking a combination of momentum and value stocks. Starting in October 2024, 61 investments were done into 36 different stocks and etfs. The invesments are in the csv in this folder, but normalized to €100 for the first investment for privacy reasons.

At 24.04.2026, our investment strategy gave an annualized return of **30.3%**. The S&P500 benchmark gave an annualized return of **22.0%**. Conclusion: our investment strategy works well and beats the S&P 500 by large margin

### 🚀 Key Features
- **Automated Data Extraction:** Leverages the `yfinance` API for real-time market prices and currency conversion (USD/EUR).
- **Accurate Performance Metrics:** Implements the **XIRR (Extended Internal Rate of Return)** algorithm, the industry standard for portfolios with irregular cash flows and dividends.
- **Numerical Optimization:** Utilizes the **Newton-Raphson method** (`scipy.optimize`) to solve for the Net Present Value (NPV) root.
- **Data Engineering:** Robust handling of time-series data and market holiday gaps using `pandas`.

### Mathematical Background
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
- **YFinance:** Market data retrieval.


### 🛠️ Usage
1. Ensure your transactions are in a CSV file with the following columns: `ticker`, `date`, `delta_n_stock`, `transaction_total_eur`.
2. Update the CSV file path in the script.
3. Run the script: `python eval.py`
