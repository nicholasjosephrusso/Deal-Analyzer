# Real Estate Deal Analyzer

A Streamlit-based web application for analyzing and comparing real estate investment deals across multiple financing structures and rental strategies.

## Features

- **Compare up to 4 deals** side-by-side with different financing and rental configurations
- **4 financing types supported**:
  - **Subject-To**: Assume existing mortgage with premium to seller
  - **Conventional**: Traditional financing with down payment
  - **Seller Financing**: Seller-financed portion with custom terms
  - **BRRRR**: Buy, Rehab, Rent, Refinance, Repeat strategy
- **3 rental strategies**:
  - **LTR (Long-Term Rental)**: Traditional annual leases with stable income
  - **STR (Short-Term Rental)**: Nightly rentals (Airbnb/VRBO style) with higher income potential
  - **Hybrid**: Combine STR during peak season with LTR for off-peak months
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

#### General Settings
- **Closing Cost %**: Combined buy and sell closing costs

#### Long-Term Rental (LTR) Settings
- **LTR Monthly Rent**: Expected monthly rental income for long-term leases
- **LTR Annual Rent Growth %**: Year-over-year rent increase rate
- **LTR Expense Ratio**: Percentage of rent for operating expenses (maintenance, management, etc.)
- **LTR Vacancy Rate %**: Expected vacancy as percentage of income

#### Short-Term Rental (STR) Settings
- **STR Nightly Rate**: Average nightly rate for short-term rentals
- **STR Occupancy Rate %**: Expected occupancy (nights booked / nights available)
- **STR Annual Rate Growth %**: Year-over-year rate increase
- **STR Expense Ratio**: Higher expense ratio typical for STR (cleaning, supplies, utilities, management)

### Deal Configuration

For each deal, specify:
- **Deal Name**: Identifier for the deal
- **Financing Type**: Subject-To, Conventional, Seller Financing, or BRRRR
- **Rental Strategy**: LTR, STR, or Hybrid
- **Purchase Price**: Acquisition cost
- **Holding Period**: Years before sale
- **Annual Appreciation %**: Property value growth rate
- **Discount Rate %**: Rate used for NPV calculation

For **Hybrid** strategy, also specify:
- **STR Months per Year**: Number of months operated as STR (e.g., 4 for peak summer season)

Additional parameters vary by financing type.

### Rental Strategy Comparison

| Strategy | Best For | Pros | Cons |
|----------|----------|------|------|
| **LTR** | Passive investors, stable markets | Predictable income, lower management | Lower gross income |
| **STR** | Active investors, tourist markets | Higher income potential | More management, seasonal variance |
| **Hybrid** | Seasonal markets, flexibility | Balance income & stability | More complex operations |

### Interpreting Results

| Metric | Description |
|--------|-------------|
| **IRR** | Annualized Internal Rate of Return - measures profitability considering time value of money |
| **Total ROI** | Total Return on Investment - total cash returned divided by initial equity |
| **NPV** | Net Present Value - present value of all cash flows at your discount rate |

### Example Comparisons

**Compare financing strategies:**
- Deal 1: Conventional + LTR
- Deal 2: Subject-To + LTR

**Compare rental strategies:**
- Deal 1: Conventional + LTR
- Deal 2: Conventional + STR
- Deal 3: Conventional + Hybrid (4 months STR)

**Full comparison:**
- Deal 1: BRRRR + STR (aggressive growth)
- Deal 2: Conventional + LTR (stable income)
- Deal 3: Subject-To + Hybrid (balanced approach)

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
