import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as nf
import altair as alt

st.set_page_config(page_title="Real Estate Deal Analyzer", layout="wide")
st.title("🏠 Real Estate Deal Analyzer")
st.markdown("""
**Compare different investment properties side-by-side** to find the best deal for you.

This tool helps you analyze rental property investments by calculating returns, cash flow, and profit potential.
*New to real estate investing? Hover over the ℹ️ icons for helpful explanations!*
""")

# --- 1. Global Assumptions -----------------------------------------
with st.sidebar:
    st.header("⚙️ Settings")
    st.caption("These settings apply to all deals you compare.")

    closing_pct = st.slider(
        "Closing Costs",
        0.00, 0.10, 0.06, 0.005,
        format="%.1f%%",
        help="Fees paid when buying and selling a property (title insurance, attorney fees, agent commissions, etc.). Typically 5-7% of the property price."
    )
    show_debug = st.checkbox("Show technical details", value=False, help="Display raw data for advanced users")

    st.subheader("🏡 Long-Term Rental")
    st.caption("Traditional 12+ month tenant leases")

    ltr_rent = st.number_input(
        "Monthly Rent",
        0.0, 1e6, 2000.0, 50.0,
        help="How much rent you'll charge per month. Check local listings for comparable properties."
    )
    ltr_growth = st.slider(
        "Annual Rent Increase",
        0.00, 0.10, 0.02, 0.005,
        format="%.1f%%",
        help="How much you expect to raise rent each year. Typically 2-3% in most markets."
    )
    ltr_expense = st.slider(
        "Expense Ratio",
        0.00, 1.00, 0.35, 0.01,
        format="%.0f%%",
        help="Percentage of rent that goes to operating expenses (repairs, maintenance, property management, insurance, taxes, etc.). Typically 30-40% for long-term rentals."
    )
    ltr_vacancy = st.slider(
        "Vacancy Rate",
        0.00, 0.20, 0.05, 0.01,
        format="%.0f%%",
        help="Expected percentage of time the property sits empty between tenants. Typically 5-8% for desirable areas."
    )

    st.subheader("🏨 Short-Term Rental")
    st.caption("Vacation rentals like Airbnb or VRBO")

    str_nightly = st.number_input(
        "Nightly Rate",
        0.0, 2000.0, 150.0, 10.0,
        help="How much you'll charge per night. Research similar listings in your area on Airbnb/VRBO."
    )
    str_occupancy = st.slider(
        "Occupancy Rate",
        0.00, 1.00, 0.65, 0.01,
        format="%.0f%%",
        help="Percentage of nights the property will be booked. Typically 50-70% depending on location and seasonality."
    )
    str_growth = st.slider(
        "Annual Rate Increase",
        0.00, 0.15, 0.03, 0.005,
        format="%.1f%%",
        help="How much you expect to raise nightly rates each year."
    )
    str_expense = st.slider(
        "Expense Ratio",
        0.00, 1.00, 0.50, 0.01,
        format="%.0f%%",
        help="Percentage of income for expenses (cleaning, supplies, platform fees, utilities, management, etc.). Typically 40-60% for short-term rentals."
    )

# Backward compatibility
market_rent = ltr_rent
rent_growth = ltr_growth
oper_exp = ltr_rent * ltr_expense

# --- 2. Deal Inputs ------------------------------------------------
DEAL_TYPES = ["Conventional", "Subject-To", "Seller Financing", "BRRRR"]
DEAL_TYPE_HELP = {
    "Conventional": "Traditional bank mortgage with down payment",
    "Subject-To": "Take over seller's existing mortgage payments",
    "Seller Financing": "Seller acts as the bank and finances the purchase",
    "BRRRR": "Buy, Rehab, Rent, Refinance, Repeat strategy"
}
RENTAL_STRATEGIES = ["LTR", "STR", "Hybrid"]
RENTAL_STRATEGY_HELP = {
    "LTR": "Long-Term Rental: Traditional 12+ month leases",
    "STR": "Short-Term Rental: Vacation rentals (Airbnb/VRBO)",
    "Hybrid": "Mix of both: STR during peak season, LTR rest of year"
}

with st.sidebar:
    st.markdown("---")
    st.header("📊 Your Deals")
    st.caption("Add properties to compare their investment potential.")

num_deals = st.sidebar.number_input(
    "Number of Properties to Compare",
    1, 4, 2,
    help="Compare up to 4 different deals side-by-side"
)

deal_configs = []
for i in range(int(num_deals)):
    with st.sidebar:
        st.markdown("---")
        st.subheader(f"Property #{i+1}")

        name = st.text_input(
            "Property Name",
            value=f"Property {i+1}",
            key=f"name{i}",
            help="Give this property a memorable name (e.g., '123 Main St' or 'Downtown Duplex')"
        )

        dtype = st.selectbox(
            "How Will You Finance It?",
            DEAL_TYPES,
            key=f"type{i}",
            help="Choose how you'll pay for this property"
        )
        st.caption(f"ℹ️ {DEAL_TYPE_HELP[dtype]}")

        rental_strategy = st.selectbox(
            "Rental Strategy",
            RENTAL_STRATEGIES,
            key=f"rental{i}",
            help="How will you rent out this property?"
        )
        st.caption(f"ℹ️ {RENTAL_STRATEGY_HELP[rental_strategy]}")

        pp = st.number_input(
            "Purchase Price ($)",
            0.0, 1e7, 300000.0, 10000.0,
            key=f"pp{i}",
            help="The total price you'll pay for this property"
        )

        hold = st.slider(
            "How Long Will You Own It? (Years)",
            1, 30, 10,
            key=f"hold{i}",
            help="How many years you plan to hold the property before selling"
        )

        gr = st.slider(
            "Expected Property Value Growth",
            0.00, 0.10, 0.04, 0.005,
            format="%.1f%%",
            key=f"gr{i}",
            help="How much the property's value will increase each year. Historically 3-5% in most markets."
        )

        dr = st.slider(
            "Your Target Return Rate",
            0.00, 0.20, 0.08, 0.005,
            format="%.1f%%",
            key=f"dr{i}",
            help="The minimum annual return you want on your money. Used to calculate if this deal is worth it compared to other investments. 8% is a common benchmark."
        )

        # Hybrid-specific parameters
        if rental_strategy == "Hybrid":
            str_months = st.slider(
                "Months as Short-Term Rental",
                1, 11, 4,
                key=f"strmo{i}",
                help="How many months per year will you rent as a vacation rental? The rest will be long-term rental."
            )
        else:
            str_months = 0

        params = {"name": name, "type": dtype, "pp": pp, "hold": hold, "gr": gr, "dr": dr,
                  "rental_strategy": rental_strategy, "str_months": str_months}

        # Financing-specific inputs
        st.markdown("**Financing Details:**")

        if dtype == "Subject-To":
            eb_default = min(pp, 200000.0)
            params.update({
                "eb": st.number_input(
                    "Seller's Remaining Loan Balance ($)",
                    0.0, pp, eb_default, 10000.0,
                    key=f"eb{i}",
                    help="How much the seller still owes on their mortgage. You'll take over these payments."
                ),
                "rate": st.slider(
                    "Seller's Loan Interest Rate",
                    0.01, 0.08, 0.035, 0.001,
                    format="%.2f%%",
                    key=f"sr{i}",
                    help="The interest rate on the seller's existing mortgage."
                ),
                "term": st.slider(
                    "Years Left on Seller's Loan",
                    1, 30, 25,
                    key=f"tr{i}",
                    help="How many years remain on the seller's mortgage."
                ),
                "premium": st.number_input(
                    "Cash to Seller ($)",
                    0.0, 1e6, 10000.0, 1000.0,
                    key=f"prem{i}",
                    help="Extra cash you'll pay the seller at closing (their equity profit)."
                )
            })

        elif dtype == "Conventional":
            params.update({
                "dp_pct": st.slider(
                    "Down Payment",
                    0.05, 0.50, 0.20, 0.01,
                    format="%.0f%%",
                    key=f"dp{i}",
                    help="Percentage of purchase price you'll pay upfront. Typically 20-25% for investment properties."
                ),
                "rate": st.slider(
                    "Mortgage Interest Rate",
                    0.02, 0.10, 0.05, 0.001,
                    format="%.2f%%",
                    key=f"cr{i}",
                    help="Annual interest rate on your mortgage. Investment property rates are typically 0.5-1% higher than primary residence rates."
                ),
                "term": st.slider(
                    "Loan Length (Years)",
                    10, 30, 30,
                    key=f"ct{i}",
                    help="How long to pay off the mortgage. 30 years = lower monthly payment, 15 years = faster payoff."
                )
            })

        elif dtype == "Seller Financing":
            params.update({
                "fin_pct": st.slider(
                    "Amount Financed by Seller",
                    0.00, 1.00, 0.80, 0.01,
                    format="%.0f%%",
                    key=f"fp{i}",
                    help="What percentage of the price will the seller finance? You pay the rest as a down payment."
                ),
                "rate": st.slider(
                    "Seller's Interest Rate",
                    0.01, 0.10, 0.06, 0.001,
                    format="%.2f%%",
                    key=f"nr{i}",
                    help="Interest rate the seller will charge you. Often negotiable."
                ),
                "term": st.slider(
                    "Loan Length (Years)",
                    1, 30, 5,
                    key=f"nt{i}",
                    help="How long you have to pay off the seller. Seller financing terms are often shorter (3-7 years)."
                )
            })

        else:  # BRRRR
            params.update({
                "rehab": st.number_input(
                    "Renovation Budget ($)",
                    0.0, 1e6, 50000.0, 5000.0,
                    key=f"rc{i}",
                    help="How much you'll spend fixing up the property. Get contractor quotes to estimate."
                ),
                "arv": st.number_input(
                    "Value After Renovation ($)",
                    0.0, 1e7, 350000.0, 10000.0,
                    key=f"arv{i}",
                    help="What the property will be worth after renovations. Check comparable recently sold homes."
                ),
                "rr": st.slider(
                    "Refinance Interest Rate",
                    0.02, 0.10, 0.05, 0.001,
                    format="%.2f%%",
                    key=f"rr{i}",
                    help="Expected interest rate when you refinance after renovation."
                ),
                "rlv": st.slider(
                    "Refinance Loan-to-Value",
                    0.50, 0.80, 0.75, 0.01,
                    format="%.0f%%",
                    key=f"rl{i}",
                    help="How much of the new value banks will lend you. Typically 70-75% for investment properties."
                )
            })

        deal_configs.append(params)

# --- 3. Helpers -----------------------------------------------------

def calculate_rental_income(strategy: str, month: int, year: int, str_months: int = 0) -> tuple[float, float]:
    """
    Calculate monthly gross rental income and expenses based on rental strategy.

    Args:
        strategy: 'LTR', 'STR', or 'Hybrid'
        month: Month number (1-12 within the year, for seasonal calculations)
        year: Year number (0-indexed) for growth calculations
        str_months: For Hybrid strategy, number of months operated as STR

    Returns:
        Tuple of (gross_income, expenses) for the month
    """
    if strategy == "LTR":
        # Long-term rental: stable monthly rent with vacancy factor
        base_rent = ltr_rent * (1 + ltr_growth) ** year
        gross = base_rent * (1 - ltr_vacancy)
        expenses = base_rent * ltr_expense
        return gross, expenses

    elif strategy == "STR":
        # Short-term rental: nightly rate × days × occupancy
        base_rate = str_nightly * (1 + str_growth) ** year
        days_in_month = 30  # Simplified
        gross = base_rate * days_in_month * str_occupancy
        expenses = gross * str_expense
        return gross, expenses

    else:  # Hybrid
        # Operate as STR for str_months, LTR for remaining months
        # Assume STR months are months 1-str_months (e.g., peak season)
        month_in_year = ((month - 1) % 12) + 1  # 1-12

        if month_in_year <= str_months:
            # STR month
            base_rate = str_nightly * (1 + str_growth) ** year
            days_in_month = 30
            gross = base_rate * days_in_month * str_occupancy
            expenses = gross * str_expense
        else:
            # LTR month
            base_rent = ltr_rent * (1 + ltr_growth) ** year
            gross = base_rent * (1 - ltr_vacancy)
            expenses = base_rent * ltr_expense

        return gross, expenses


def get_rental_description(strategy: str, str_months: int = 0) -> dict:
    """
    Generate description strings for rental income display in net-sheet.

    Args:
        strategy: 'LTR', 'STR', or 'Hybrid'
        str_months: For Hybrid, number of STR months

    Returns:
        Dictionary with description strings for the net-sheet
    """
    if strategy == "LTR":
        return {
            "Rental Strategy": "Long-Term Rental (LTR)",
            "Monthly Income": f"${ltr_rent:,.0f}/mo (grows {ltr_growth:.1%}/yr)",
            "Vacancy Rate": f"{ltr_vacancy:.0%}",
            "Expense Ratio": f"{ltr_expense:.0%}",
        }
    elif strategy == "STR":
        monthly_gross = str_nightly * 30 * str_occupancy
        return {
            "Rental Strategy": "Short-Term Rental (STR)",
            "Nightly Rate": f"${str_nightly:,.0f} (grows {str_growth:.1%}/yr)",
            "Occupancy Rate": f"{str_occupancy:.0%}",
            "Est. Monthly Gross": f"${monthly_gross:,.0f}",
            "Expense Ratio": f"{str_expense:.0%}",
        }
    else:  # Hybrid
        ltr_months = 12 - str_months
        str_monthly = str_nightly * 30 * str_occupancy
        return {
            "Rental Strategy": f"Hybrid ({str_months}mo STR / {ltr_months}mo LTR)",
            "STR Nightly Rate": f"${str_nightly:,.0f}",
            "STR Occupancy": f"{str_occupancy:.0%}",
            "LTR Monthly Rent": f"${ltr_rent:,.0f}",
            "LTR Vacancy": f"{ltr_vacancy:.0%}",
        }


def validate_deal(p: dict) -> list[str]:
    """Validate deal parameters and return list of warning messages."""
    warnings = []
    dtype = p['type']
    strategy = p.get('rental_strategy', 'LTR')

    # Validate rental strategy parameters
    if strategy == "STR":
        if str_nightly <= 0:
            warnings.append(f"{p['name']}: STR nightly rate must be positive")
        if str_occupancy <= 0:
            warnings.append(f"{p['name']}: STR occupancy rate must be positive")
        # Check if STR income covers typical mortgage
        estimated_monthly = str_nightly * 30 * str_occupancy * (1 - str_expense)
        if estimated_monthly < 500:
            warnings.append(f"{p['name']}: STR net income (${estimated_monthly:.0f}/mo) may be too low")
    elif strategy == "Hybrid":
        if p['str_months'] < 1 or p['str_months'] > 11:
            warnings.append(f"{p['name']}: Hybrid STR months must be between 1 and 11")

    if dtype == "Subject-To":
        if p['eb'] <= 0:
            warnings.append(f"{p['name']}: Existing balance must be positive")
        if p['premium'] < 0:
            warnings.append(f"{p['name']}: Premium cannot be negative")
        initial_equity = p['premium'] + p['pp'] * closing_pct
        if initial_equity <= 0:
            warnings.append(f"{p['name']}: Initial equity must be positive")

    elif dtype == "Conventional":
        if p['dp_pct'] <= 0:
            warnings.append(f"{p['name']}: Down payment must be positive")
        initial_equity = p['pp'] * p['dp_pct'] + p['pp'] * closing_pct
        if initial_equity <= 0:
            warnings.append(f"{p['name']}: Initial equity must be positive")

    elif dtype == "Seller Financing":
        if p['fin_pct'] < 0 or p['fin_pct'] > 1:
            warnings.append(f"{p['name']}: Financed percentage must be between 0 and 100%")
        initial_equity = p['pp'] * (1 - p['fin_pct']) + p['pp'] * closing_pct
        if initial_equity <= 0:
            warnings.append(f"{p['name']}: Initial equity must be positive")

    elif dtype == "BRRRR":
        if p['arv'] <= p['pp']:
            warnings.append(f"{p['name']}: After-repair value should exceed purchase price")
        cost = p['pp'] + p['rehab'] + p['pp'] * closing_pct
        loan = p['arv'] * p['rlv']
        if cost - loan <= 0:
            warnings.append(f"{p['name']}: Refi loan exceeds total cost - may result in infinite/negative equity")

    return warnings

# Dispatch and metrics

def build_cashflow_and_sheet(p: dict) -> tuple[list[float], dict]:
    """
    Route deal parameters to the appropriate cashflow calculation function.

    Args:
        p: Deal parameters dictionary containing 'type' and type-specific params

    Returns:
        Tuple of (monthly cashflows list, net-sheet dictionary)
    """
    tp = p['type']
    if tp == "Subject-To": return subject_cf(p)
    if tp == "Conventional": return conventional_cf(p)
    if tp == "Seller Financing": return seller_fin_cf(p)
    return brrrr_cf(p)

def build_metrics(initial_equity: float, cf: list[float], discount_rate: float = 0.08) -> tuple[float, float, float]:
    """
    Calculate investment metrics from cash flows.

    Args:
        initial_equity: Initial cash investment
        cf: List of monthly cash flows
        discount_rate: Annual discount rate for NPV calculation

    Returns:
        Tuple of (annualized IRR, total ROI, NPV)
    """
    monthly_irr = nf.irr([-initial_equity] + cf)
    irr = (1 + monthly_irr) ** 12 - 1
    total_roi = sum(cf) / initial_equity if initial_equity else 0
    # Calculate NPV using monthly discount rate
    monthly_dr = (1 + discount_rate) ** (1/12) - 1
    npv = nf.npv(monthly_dr, [-initial_equity] + cf)
    return irr, total_roi, npv

# --- 4. Deal Models with Interest Tracking -------------------------

def subject_cf(p: dict) -> tuple[list[float], dict]:
    """
    Calculate cashflows for a Subject-To deal.

    In a Subject-To deal, the buyer takes over payments on the seller's
    existing mortgage without formally assuming the loan.

    Args:
        p: Deal parameters including pp, eb, rate, term, premium, hold, gr, rental_strategy

    Returns:
        Tuple of (monthly cashflows, net-sheet dictionary)
    """
    pp, eb, rate, term, prem, hold = p['pp'], p['eb'], p['rate'], p['term'], p['premium'], p['hold']
    strategy, str_months = p['rental_strategy'], p['str_months']
    mrate = rate/12; periods = term*12
    payment = nf.pmt(mrate, periods, -eb)
    bal = eb; interest_total = 0; cf = []
    for m in range(1, hold*12+1):
        year = (m-1)//12
        gross, exp = calculate_rental_income(strategy, m, year, str_months)
        interest = bal * mrate; principal = payment - interest; bal -= principal
        interest_total += interest
        cf.append(gross - exp - payment)
    sale_price = pp * (1 + p['gr'])**hold
    sale_net = sale_price - sale_price * closing_pct - bal; cf[-1] += sale_net
    total_rent = sum(cf[:-1])

    # Build net-sheet with rental strategy info
    rental_info = get_rental_description(strategy, str_months)
    sheet = {
        "Purchase Price":      pp,
        "Existing Balance":    eb,
        "Premium Paid":        prem,
        "Closing Costs":       pp * closing_pct,
        "Initial Equity":      prem + pp * closing_pct,
        **rental_info,
        "Debt Service (mo)":   payment,
        "Total Interest Paid": interest_total,
        "Monthly Net Cash (M1)": cf[0],
        "Total Rental CF":     total_rent,
        "Sale Price":          sale_price,
        "Net Sale Proceeds":   sale_net,
        "Cash Profit":         total_rent + sale_net,
    }
    return cf, sheet

def conventional_cf(p: dict) -> tuple[list[float], dict]:
    """
    Calculate cashflows for a Conventional financing deal.

    Standard mortgage financing with down payment and fixed-rate loan.

    Args:
        p: Deal parameters including pp, dp_pct, rate, term, hold, gr, rental_strategy

    Returns:
        Tuple of (monthly cashflows, net-sheet dictionary)
    """
    pp, dp, rate, term, hold = p['pp'], p['dp_pct'], p['rate'], p['term'], p['hold']
    strategy, str_months = p['rental_strategy'], p['str_months']
    down = pp*dp; loan = pp-down
    payment = nf.pmt(rate/12, term*12, -loan)
    bal = loan; interest_total=0; cf=[]
    for m in range(1, hold*12+1):
        year = (m-1)//12
        gross, exp = calculate_rental_income(strategy, m, year, str_months)
        interest = bal * (rate/12); principal = payment - interest; bal -= principal
        interest_total += interest
        cf.append(gross - exp - payment)
    sale_price = pp * (1 + p['gr'])**hold
    sale_net = sale_price - sale_price * closing_pct - bal; cf[-1] += sale_net
    total_rent = sum(cf[:-1])

    rental_info = get_rental_description(strategy, str_months)
    sheet = {
        "Purchase Price":      pp,
        "Down Payment":        down,
        "Loan Amount":         loan,
        "Closing Costs":       pp * closing_pct,
        "Initial Equity":      down + pp * closing_pct,
        **rental_info,
        "Debt Service (mo)":   payment,
        "Total Interest Paid": interest_total,
        "Monthly Net Cash (M1)": cf[0],
        "Total Rental CF":     total_rent,
        "Sale Price":          sale_price,
        "Net Sale Proceeds":   sale_net,
        "Cash Profit":         total_rent + sale_net,
    }
    return cf, sheet

def seller_fin_cf(p: dict) -> tuple[list[float], dict]:
    """
    Calculate cashflows for a Seller Financing deal.

    The seller acts as the lender, financing a portion of the purchase price.

    Args:
        p: Deal parameters including pp, fin_pct, rate, term, hold, gr, rental_strategy

    Returns:
        Tuple of (monthly cashflows, net-sheet dictionary)
    """
    pp, fp, rate, term, hold = p['pp'], p['fin_pct'], p['rate'], p['term'], p['hold']
    strategy, str_months = p['rental_strategy'], p['str_months']
    financed = pp*fp; payment = nf.pmt(rate/12, term*12, -financed)
    bal=financed; interest_total=0; cf=[]
    for m in range(1, hold*12+1):
        year = (m-1)//12
        gross, exp = calculate_rental_income(strategy, m, year, str_months)
        interest = bal*(rate/12); principal = payment-interest; bal-=principal
        interest_total += interest
        cf.append(gross - exp - payment)
    sale_price = pp * (1 + p['gr'])**hold
    sale_net = sale_price - sale_price * closing_pct - bal; cf[-1]+=sale_net
    total_rent = sum(cf[:-1])

    rental_info = get_rental_description(strategy, str_months)
    sheet = {
        "Purchase Price":      pp,
        "Financed Amount":     financed,
        "Closing Costs":       pp * closing_pct,
        "Initial Equity":      pp - financed + pp * closing_pct,
        **rental_info,
        "Debt Service (mo)":   payment,
        "Total Interest Paid": interest_total,
        "Monthly Net Cash (M1)": cf[0],
        "Total Rental CF":     total_rent,
        "Sale Price":          sale_price,
        "Net Sale Proceeds":   sale_net,
        "Cash Profit":         total_rent + sale_net,
    }
    return cf, sheet

def brrrr_cf(p: dict) -> tuple[list[float], dict]:
    """
    Calculate cashflows for a BRRRR (Buy, Rehab, Rent, Refinance, Repeat) deal.

    Strategy involves buying below market, rehabbing to increase value,
    then refinancing to pull out initial capital.

    Args:
        p: Deal parameters including pp, rehab, arv, rr, rlv, hold, gr, rental_strategy

    Returns:
        Tuple of (monthly cashflows, net-sheet dictionary)
    """
    pp, rehab, arv, rr, rlv, hold = p['pp'], p['rehab'], p['arv'], p['rr'], p['rlv'], p['hold']
    strategy, str_months = p['rental_strategy'], p['str_months']
    cost = pp+rehab+pp*closing_pct; loan=arv*rlv; payment=nf.pmt(rr/12,hold*12,-loan)
    bal=loan; interest_total=0; cf=[]
    for m in range(1, hold*12+1):
        year = (m-1)//12
        gross, exp = calculate_rental_income(strategy, m, year, str_months)
        interest=bal*(rr/12); principal=payment-interest; bal-=principal
        interest_total+=interest
        val = gross-exp-payment
        if m == 12:
            val += loan   # cash-out proceeds at refinance
        cf.append(val)
    sale_price = arv*(1+p['gr'])**hold; sale_net = sale_price - sale_price*closing_pct - bal; cf[-1]+=sale_net
    total_rent = sum(cf[:-1])

    rental_info = get_rental_description(strategy, str_months)
    sheet = {
        "Purchase Price":      pp,
        "Rehab Cost":          rehab,
        "Refi Loan Amount":    loan,
        "Cash-Out Proceeds":   loan,
        "Closing Costs":       pp * closing_pct,
        "Initial Equity":      cost - loan,
        **rental_info,
        "Debt Service (mo)":   payment,
        "Total Interest Paid": interest_total,
        "Monthly Net Cash (M1)": cf[0],
        "Total Rental CF":     total_rent,
        "Sale Price":          sale_price,
        "Net Sale Proceeds":   sale_net,
        "Cash Profit":         total_rent + sale_net,
    }
    return cf, sheet

# --- 5. Side-by-Side Deal Cards with Inline Net-Sheets -----------

st.header("📋 Results: How Do Your Properties Compare?")
st.markdown("""
Each property is scored on three key metrics. **Higher numbers = better investment.**
Hover over the ℹ️ icons below to learn what each metric means.
""")

# Display validation warnings
all_warnings = []
for cfg in deal_configs:
    all_warnings.extend(validate_deal(cfg))
if all_warnings:
    for warning in all_warnings:
        st.warning(warning)

cols = st.columns(int(num_deals))
for col, cfg in zip(cols, deal_configs):
    cf, sheet = build_cashflow_and_sheet(cfg)
    initial_equity = sheet["Initial Equity"]
    irr, total_roi, npv = build_metrics(initial_equity, cf, cfg['dr'])
    df_cf = pd.DataFrame({"Month": list(range(len(cf))), "Cash Flow ($)": cf})
    with col:
        st.subheader(f"🏠 {cfg['name']}")

        # IRR with explanation
        st.metric(
            "Annual Return (IRR)",
            f"{irr:.2%}",
            help="Internal Rate of Return: Your average annual return on this investment, accounting for the timing of all cash flows. Think of it like a savings account interest rate. Higher is better. A good rental property IRR is typically 12-20%."
        )

        # Total ROI with explanation
        st.metric(
            "Total Return (ROI)",
            f"{total_roi:.2%}",
            help="Return on Investment: Your total profit as a percentage of the cash you invested. For example, 150% means you got back your original investment plus 50% more. Higher is better."
        )

        # NPV with explanation
        npv_color = "normal" if npv >= 0 else "off"
        st.metric(
            "Deal Value (NPV)",
            f"${npv:,.0f}",
            help="Net Present Value: How much this deal is worth in today's dollars, compared to putting your money in a different investment earning your Target Return Rate. Positive = good deal. Negative = you'd be better off investing elsewhere."
        )

        # Quick verdict
        if npv > 0 and irr > 0.08:
            st.success("✓ This looks like a solid deal!")
        elif npv < 0:
            st.warning("⚠️ Returns may be below your target")

        with st.expander("📄 Full Financial Breakdown", expanded=False):
            if show_debug:
                st.json(sheet)
            df_sheet = pd.DataFrame(sheet.items(), columns=["Line Item","Amount"]).set_index("Line Item")
            # Format numeric amounts, leave strings intact
            st.table(
                df_sheet.style.format(lambda v: f"${v:,.0f}" if isinstance(v, (int, float)) else v)
            )

# --- 6. Cumulative Cash Flow Comparison ---------------------------
st.header("📈 Cash Flow Over Time")
st.markdown("""
This chart shows how much money you'll have made from each property over time.
The line goes up when you're making money (rent income) and jumps at the end when you sell.
**The higher the line, the more profit you've made.**
""")
# Build cumulative DataFrame for each deal
cum_df = pd.DataFrame()
for cfg in deal_configs:
    cf, _ = build_cashflow_and_sheet(cfg)
    cum_series = pd.Series(np.cumsum(cf), name=cfg['name'])
    cum_df = pd.concat([cum_df, cum_series], axis=1)

# Prepare data for Altair
cum_df = cum_df.reset_index().rename(columns={'index': 'Month'})
melt_df = cum_df.melt(id_vars=['Month'], var_name='Deal', value_name='Cumulative CF')

# Base line chart
base = alt.Chart(melt_df).mark_line(point=True).encode(
    x=alt.X('Month:Q', title='Month'),
    y=alt.Y('Cumulative CF:Q', title='Cumulative Cash Flow ($)'),
    color='Deal:N',
    tooltip=['Deal','Month','Cumulative CF']
).properties(width='container', height=300)

# Build label data: end of rent (pre-sale) and sale points
labels = []
for cfg in deal_configs:
    name = cfg['name']
    hold_mo = cfg['hold'] * 12
    # sale month is the last month (index hold_mo - 1 since 0-indexed)
    sale_month = hold_mo - 1
    # end of rental period is penultimate month, but ensure it's at least 0
    end_rent_month = max(0, hold_mo - 2)

    # Safely get values, handling potential missing data
    rent_rows = cum_df.loc[cum_df['Month'] == end_rent_month, name]
    sale_rows = cum_df.loc[cum_df['Month'] == sale_month, name]

    if not rent_rows.empty and not pd.isna(rent_rows.iloc[0]):
        val_rent = rent_rows.iloc[0]
        labels.append({'Deal': name, 'Month': end_rent_month, 'Cumulative CF': val_rent, 'Label': 'End Rent'})

    if not sale_rows.empty and not pd.isna(sale_rows.iloc[0]):
        val_sale = sale_rows.iloc[0]
        labels.append({'Deal': name, 'Month': sale_month, 'Cumulative CF': val_sale, 'Label': 'With Sale'})
labels_df = pd.DataFrame(labels)

text = alt.Chart(labels_df).mark_text(dx=5, dy=-5).encode(
    x='Month:Q',
    y='Cumulative CF:Q',
    text='Label:N',
    color='Deal:N'
)

# Render combined chart
st.altair_chart(base + text, use_container_width=True)
