# Real Estate Deal Analyzer

A Streamlit-based web application for analyzing and comparing real estate investment deals across multiple financing structures.

## Features

- **Compare up to 4 deals** side-by-side with different financing structures
- **4 deal types supported**:
  - **Subject-To**: Assume existing mortgage with premium to seller
  - **Conventional**: Traditional financing with down payment
  - **Seller Financing**: Seller-financed portion with custom terms
  - **BRRRR**: Buy, Rehab, Rent, Refinance, Repeat strategy
- **Financial metrics**: IRR (annualized), Total ROI, and NPV
- **Interactive visualization**: Cumulative cash flow comparison chart
- **Detailed net-sheets**: Expandable breakdowns for each deal

## Installation

1. Clone the repository:
```bash
git clone https://github.com/nicholasjosephrusso/Deal-Analyzer.git
cd Deal-Analyzer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run subject_to_analyzer.py
```

## Usage

### Global Assumptions (Sidebar)
Configure market-wide assumptions that apply to all deals:
- **Market Rent**: Expected monthly rental income
- **Annual Rent Growth %**: Year-over-year rent increase rate
- **Operating Expense Ratio**: Percentage of rent allocated to expenses
- **Closing Cost %**: Combined buy and sell closing costs

### Deal Configuration
For each deal, specify:
- **Deal Name**: Identifier for the deal
- **Deal Type**: Subject-To, Conventional, Seller Financing, or BRRRR
- **Purchase Price**: Acquisition cost
- **Holding Period**: Years before sale
- **Annual Appreciation %**: Property value growth rate
- **Discount Rate %**: Rate used for NPV calculation

Additional parameters vary by deal type.

### Interpreting Results

| Metric | Description |
|--------|-------------|
| **IRR** | Annualized Internal Rate of Return - measures profitability considering time value of money |
| **Total ROI** | Total Return on Investment - total cash returned divided by initial equity |
| **NPV** | Net Present Value - present value of all cash flows at your discount rate |

## Testing

Run the test suite:
```bash
pytest tests/ -v
```

## Project Structure

```
Deal-Analyzer/
├── subject_to_analyzer.py  # Main application
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── .gitignore             # Git ignore rules
└── tests/
    ├── __init__.py
    └── test_metrics.py    # Test suite
```

## Dependencies

- streamlit - Web application framework
- pandas - Data manipulation
- numpy - Numerical computations
- numpy-financial - Financial calculations (IRR, PMT, NPV)
- altair - Interactive visualizations
- pytest - Testing framework

## License

MIT
