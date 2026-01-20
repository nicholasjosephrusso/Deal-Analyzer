import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as nf
import altair as alt

st.set_page_config(page_title="Real Estate Deal Analyzer v9", layout="wide")
st.title("🏠 Real Estate Deal Analyzer – Rental Strategy Edition (v9)")

# --- 1. Global Assumptions -----------------------------------------
with st.sidebar:
    st.header("Global Assumptions")
    closing_pct   = st.slider("Closing Cost % (buy & sell)", 0.00, 0.10, 0.06, 0.005)
    show_debug    = st.checkbox("Show Debug Data in Net-Sheet", value=False)

    st.subheader("Long-Term Rental (LTR)")
    ltr_rent      = st.number_input("LTR Monthly Rent ($)", 0.0, 1e6, 2000.0, 50.0)
    ltr_growth    = st.slider("LTR Annual Rent Growth %", 0.00, 0.10, 0.02, 0.005)
    ltr_expense   = st.slider("LTR Expense Ratio", 0.00, 1.00, 0.35, 0.01)
    ltr_vacancy   = st.slider("LTR Vacancy Rate %", 0.00, 0.20, 0.05, 0.01)

    st.subheader("Short-Term Rental (STR)")
    str_nightly   = st.number_input("STR Nightly Rate ($)", 0.0, 2000.0, 150.0, 10.0)
    str_occupancy = st.slider("STR Occupancy Rate %", 0.00, 1.00, 0.65, 0.01)
    str_growth    = st.slider("STR Annual Rate Growth %", 0.00, 0.15, 0.03, 0.005)
    str_expense   = st.slider("STR Expense Ratio", 0.00, 1.00, 0.50, 0.01)

# Backward compatibility
market_rent = ltr_rent
rent_growth = ltr_growth
oper_exp = ltr_rent * ltr_expense

# --- 2. Deal Inputs ------------------------------------------------
DEAL_TYPES = ["Subject-To","Conventional","Seller Financing","BRRRR"]
RENTAL_STRATEGIES = ["LTR", "STR", "Hybrid"]
num_deals = st.sidebar.number_input("# Deals to Compare", 1, 4, 2)

deal_configs = []
for i in range(int(num_deals)):
    with st.sidebar:
        st.markdown("---")
        name  = st.text_input(f"Deal {i+1} Name", value=f"Deal {i+1}", key=f"name{i}")
        dtype = st.selectbox("Financing Type", DEAL_TYPES, key=f"type{i}")
        rental_strategy = st.selectbox("Rental Strategy", RENTAL_STRATEGIES, key=f"rental{i}")
        pp    = st.number_input("Purchase Price", 0.0, 1e7, 300000.0, 10000.0, key=f"pp{i}")
        hold  = st.slider("Holding Period (yrs)", 1, 30, 10, key=f"hold{i}")
        gr    = st.slider("Annual Appreciation %", 0.00, 0.10, 0.04, 0.005, key=f"gr{i}")
        dr    = st.slider("Discount Rate %", 0.00, 0.20, 0.08, 0.005, key=f"dr{i}")

        # Hybrid-specific parameters
        if rental_strategy == "Hybrid":
            str_months = st.slider("STR Months per Year", 1, 11, 4, key=f"strmo{i}",
                                   help="Number of months operated as STR (peak season)")
        else:
            str_months = 0

        params = {"name": name, "type": dtype, "pp": pp, "hold": hold, "gr": gr, "dr": dr,
                  "rental_strategy": rental_strategy, "str_months": str_months}
        if dtype == "Subject-To":
            eb_default = min(pp, 200000.0)
            params.update({
                "eb":      st.number_input("Existing Loan Balance", 0.0, pp, eb_default, 10000.0, key=f"eb{i}"),
                "rate":    st.slider("Subject Loan Rate", 0.01, 0.08, 0.035, 0.001, key=f"sr{i}"),
                "term":    st.slider("Loan Term Remaining (yrs)", 1, 30, 25, key=f"tr{i}"),
                "premium": st.number_input("Premium to Seller", 0.0, 1e6, 10000.0, 1000.0, key=f"prem{i}")
            })
        elif dtype == "Conventional":
            params.update({
                "dp_pct": st.slider("Down Payment %", 0.05, 0.50, 0.20, 0.01, key=f"dp{i}"),
                "rate":   st.slider("Mortgage Rate",   0.02, 0.10, 0.05, 0.001, key=f"cr{i}"),
                "term":   st.slider("Loan Term (yrs)", 10, 30, 30, key=f"ct{i}")
            })
        elif dtype == "Seller Financing":
            params.update({
                "fin_pct": st.slider("Seller-Financed %", 0.00, 1.00, 0.80, 0.01, key=f"fp{i}"),
                "rate":    st.slider("Note Rate",     0.01, 0.10, 0.06, 0.001, key=f"nr{i}"),
                "term":    st.slider("Note Term (yrs)", 1, 30, 5, key=f"nt{i}")
            })
        else:  # BRRRR
            params.update({
                "rehab": st.number_input("Rehab Cost", 0.0, 1e6, 50000.0, 5000.0, key=f"rc{i}"),
                "arv":   st.number_input("After-Repair Value", 0.0, 1e7, 350000.0, 10000.0, key=f"arv{i}"),
                "rr":    st.slider("Refi Rate",    0.02, 0.10, 0.05, 0.001, key=f"rr{i}"),
                "rlv":   st.slider("Refi LTV",    0.50, 0.80, 0.75, 0.01, key=f"rl{i}")
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
        st.subheader(cfg['name'])
        st.metric("IRR", f"{irr:.2%}")
        st.metric("Total ROI", f"{total_roi:.2%}")
        st.metric("NPV", f"${npv:,.0f}")
        with st.expander("Net-Sheet Details", expanded=False):
            if show_debug:
                st.json(sheet)
            df_sheet = pd.DataFrame(sheet.items(), columns=["Line Item","Amount"]).set_index("Line Item")
            # Format numeric amounts, leave strings intact
            st.table(
                df_sheet.style.format(lambda v: f"${v:,.0f}" if isinstance(v, (int, float)) else v)
            )

# --- 6. Cumulative Cash Flow Comparison ---------------------------
st.header("📈 Cumulative Cash Flow Comparison")
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
