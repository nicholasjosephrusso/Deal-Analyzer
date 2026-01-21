import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as nf
import altair as alt

st.set_page_config(page_title="Real Estate Deal Analyzer v10", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS for better styling
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 10px;
    }
    .deal-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    div[data-testid="stExpander"] {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏠 Real Estate Deal Analyzer v10")
st.caption("Compare financing strategies and rental income scenarios for real estate investments")

# --- Session State Initialization ---
if 'num_deals' not in st.session_state:
    st.session_state.num_deals = 2

# --- Constants ---
DEAL_TYPES = ["Subject-To", "Conventional", "Seller Financing", "BRRRR"]
RENTAL_STRATEGIES = ["LTR", "STR", "Hybrid"]

# ============================================================================
# SIDEBAR - Global Assumptions Only (Simplified)
# ============================================================================
with st.sidebar:
    st.header("⚙️ Global Settings")

    with st.expander("🏷️ Transaction Costs", expanded=True):
        closing_pct = st.slider(
            "Closing Cost % (buy & sell)",
            0.00, 0.10, 0.06, 0.005,
            help="Total closing costs as percentage of property value"
        )

    with st.expander("📊 Analysis Options", expanded=True):
        show_debug = st.checkbox("Show Debug Data", value=False)
        show_monthly_breakdown = st.checkbox("Show Monthly Cash Flow Table", value=False)

    st.divider()

    with st.expander("🏠 Long-Term Rental (LTR) Defaults", expanded=True):
        ltr_rent = st.number_input("Monthly Rent ($)", 0.0, 1e6, 2000.0, 50.0)
        ltr_growth = st.slider("Annual Rent Growth %", 0.00, 0.10, 0.02, 0.005)
        ltr_expense = st.slider("Expense Ratio", 0.00, 1.00, 0.35, 0.01)
        ltr_vacancy = st.slider("Vacancy Rate %", 0.00, 0.20, 0.05, 0.01)

    with st.expander("🏨 Short-Term Rental (STR) Defaults", expanded=False):
        str_nightly = st.number_input("Nightly Rate ($)", 0.0, 2000.0, 150.0, 10.0)
        str_occupancy = st.slider("Occupancy Rate %", 0.00, 1.00, 0.65, 0.01)
        str_growth = st.slider("Annual Rate Growth %", 0.00, 0.15, 0.03, 0.005)
        str_expense = st.slider("STR Expense Ratio", 0.00, 1.00, 0.50, 0.01)

    st.divider()
    st.caption("Real Estate Deal Analyzer v10")
    st.caption("Built with Streamlit")

# Backward compatibility
market_rent = ltr_rent
rent_growth = ltr_growth
oper_exp = ltr_rent * ltr_expense

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_rental_income(strategy: str, month: int, year: int, str_months: int = 0) -> tuple[float, float]:
    """Calculate monthly gross rental income and expenses based on rental strategy."""
    if strategy == "LTR":
        base_rent = ltr_rent * (1 + ltr_growth) ** year
        gross = base_rent * (1 - ltr_vacancy)
        expenses = base_rent * ltr_expense
        return gross, expenses
    elif strategy == "STR":
        base_rate = str_nightly * (1 + str_growth) ** year
        days_in_month = 30
        gross = base_rate * days_in_month * str_occupancy
        expenses = gross * str_expense
        return gross, expenses
    else:  # Hybrid
        month_in_year = ((month - 1) % 12) + 1
        if month_in_year <= str_months:
            base_rate = str_nightly * (1 + str_growth) ** year
            days_in_month = 30
            gross = base_rate * days_in_month * str_occupancy
            expenses = gross * str_expense
        else:
            base_rent = ltr_rent * (1 + ltr_growth) ** year
            gross = base_rent * (1 - ltr_vacancy)
            expenses = base_rent * ltr_expense
        return gross, expenses


def get_rental_description(strategy: str, str_months: int = 0) -> dict:
    """Generate description strings for rental income display."""
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

    if strategy == "STR":
        if str_nightly <= 0:
            warnings.append(f"{p['name']}: STR nightly rate must be positive")
        if str_occupancy <= 0:
            warnings.append(f"{p['name']}: STR occupancy rate must be positive")
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
            warnings.append(f"{p['name']}: Refi loan exceeds total cost")

    return warnings


def build_cashflow_and_sheet(p: dict) -> tuple[list[float], dict]:
    """Route deal parameters to the appropriate cashflow calculation function."""
    tp = p['type']
    if tp == "Subject-To":
        return subject_cf(p)
    if tp == "Conventional":
        return conventional_cf(p)
    if tp == "Seller Financing":
        return seller_fin_cf(p)
    return brrrr_cf(p)


def build_metrics(initial_equity: float, cf: list[float], discount_rate: float = 0.08) -> tuple[float, float, float]:
    """Calculate investment metrics from cash flows."""
    monthly_irr = nf.irr([-initial_equity] + cf)
    irr = (1 + monthly_irr) ** 12 - 1
    total_roi = sum(cf) / initial_equity if initial_equity else 0
    monthly_dr = (1 + discount_rate) ** (1/12) - 1
    npv = nf.npv(monthly_dr, [-initial_equity] + cf)
    return irr, total_roi, npv


# ============================================================================
# DEAL CALCULATION MODELS
# ============================================================================

def subject_cf(p: dict) -> tuple[list[float], dict]:
    """Calculate cashflows for a Subject-To deal."""
    pp, eb, rate, term, prem, hold = p['pp'], p['eb'], p['rate'], p['term'], p['premium'], p['hold']
    strategy, str_months = p['rental_strategy'], p['str_months']
    mrate = rate/12
    periods = term*12
    payment = nf.pmt(mrate, periods, -eb)
    bal = eb
    interest_total = 0
    cf = []
    for m in range(1, hold*12+1):
        year = (m-1)//12
        gross, exp = calculate_rental_income(strategy, m, year, str_months)
        interest = bal * mrate
        principal = payment - interest
        bal -= principal
        interest_total += interest
        cf.append(gross - exp - payment)
    sale_price = pp * (1 + p['gr'])**hold
    sale_net = sale_price - sale_price * closing_pct - bal
    cf[-1] += sale_net
    total_rent = sum(cf[:-1])

    rental_info = get_rental_description(strategy, str_months)
    sheet = {
        "Purchase Price": pp,
        "Existing Balance": eb,
        "Premium Paid": prem,
        "Closing Costs": pp * closing_pct,
        "Initial Equity": prem + pp * closing_pct,
        **rental_info,
        "Debt Service (mo)": payment,
        "Total Interest Paid": interest_total,
        "Monthly Net Cash (M1)": cf[0],
        "Total Rental CF": total_rent,
        "Sale Price": sale_price,
        "Net Sale Proceeds": sale_net,
        "Cash Profit": total_rent + sale_net,
    }
    return cf, sheet


def conventional_cf(p: dict) -> tuple[list[float], dict]:
    """Calculate cashflows for a Conventional financing deal."""
    pp, dp, rate, term, hold = p['pp'], p['dp_pct'], p['rate'], p['term'], p['hold']
    strategy, str_months = p['rental_strategy'], p['str_months']
    down = pp*dp
    loan = pp-down
    payment = nf.pmt(rate/12, term*12, -loan)
    bal = loan
    interest_total = 0
    cf = []
    for m in range(1, hold*12+1):
        year = (m-1)//12
        gross, exp = calculate_rental_income(strategy, m, year, str_months)
        interest = bal * (rate/12)
        principal = payment - interest
        bal -= principal
        interest_total += interest
        cf.append(gross - exp - payment)
    sale_price = pp * (1 + p['gr'])**hold
    sale_net = sale_price - sale_price * closing_pct - bal
    cf[-1] += sale_net
    total_rent = sum(cf[:-1])

    rental_info = get_rental_description(strategy, str_months)
    sheet = {
        "Purchase Price": pp,
        "Down Payment": down,
        "Loan Amount": loan,
        "Closing Costs": pp * closing_pct,
        "Initial Equity": down + pp * closing_pct,
        **rental_info,
        "Debt Service (mo)": payment,
        "Total Interest Paid": interest_total,
        "Monthly Net Cash (M1)": cf[0],
        "Total Rental CF": total_rent,
        "Sale Price": sale_price,
        "Net Sale Proceeds": sale_net,
        "Cash Profit": total_rent + sale_net,
    }
    return cf, sheet


def seller_fin_cf(p: dict) -> tuple[list[float], dict]:
    """Calculate cashflows for a Seller Financing deal."""
    pp, fp, rate, term, hold = p['pp'], p['fin_pct'], p['rate'], p['term'], p['hold']
    strategy, str_months = p['rental_strategy'], p['str_months']
    financed = pp*fp
    payment = nf.pmt(rate/12, term*12, -financed)
    bal = financed
    interest_total = 0
    cf = []
    for m in range(1, hold*12+1):
        year = (m-1)//12
        gross, exp = calculate_rental_income(strategy, m, year, str_months)
        interest = bal*(rate/12)
        principal = payment-interest
        bal -= principal
        interest_total += interest
        cf.append(gross - exp - payment)
    sale_price = pp * (1 + p['gr'])**hold
    sale_net = sale_price - sale_price * closing_pct - bal
    cf[-1] += sale_net
    total_rent = sum(cf[:-1])

    rental_info = get_rental_description(strategy, str_months)
    sheet = {
        "Purchase Price": pp,
        "Financed Amount": financed,
        "Closing Costs": pp * closing_pct,
        "Initial Equity": pp - financed + pp * closing_pct,
        **rental_info,
        "Debt Service (mo)": payment,
        "Total Interest Paid": interest_total,
        "Monthly Net Cash (M1)": cf[0],
        "Total Rental CF": total_rent,
        "Sale Price": sale_price,
        "Net Sale Proceeds": sale_net,
        "Cash Profit": total_rent + sale_net,
    }
    return cf, sheet


def brrrr_cf(p: dict) -> tuple[list[float], dict]:
    """Calculate cashflows for a BRRRR deal."""
    pp, rehab, arv, rr, rlv, hold = p['pp'], p['rehab'], p['arv'], p['rr'], p['rlv'], p['hold']
    strategy, str_months = p['rental_strategy'], p['str_months']
    cost = pp+rehab+pp*closing_pct
    loan = arv*rlv
    payment = nf.pmt(rr/12, hold*12, -loan)
    bal = loan
    interest_total = 0
    cf = []
    for m in range(1, hold*12+1):
        year = (m-1)//12
        gross, exp = calculate_rental_income(strategy, m, year, str_months)
        interest = bal*(rr/12)
        principal = payment-interest
        bal -= principal
        interest_total += interest
        val = gross-exp-payment
        if m == 12:
            val += loan  # cash-out proceeds at refinance
        cf.append(val)
    sale_price = arv*(1+p['gr'])**hold
    sale_net = sale_price - sale_price*closing_pct - bal
    cf[-1] += sale_net
    total_rent = sum(cf[:-1])

    rental_info = get_rental_description(strategy, str_months)
    sheet = {
        "Purchase Price": pp,
        "Rehab Cost": rehab,
        "Refi Loan Amount": loan,
        "Cash-Out Proceeds": loan,
        "Closing Costs": pp * closing_pct,
        "Initial Equity": cost - loan,
        **rental_info,
        "Debt Service (mo)": payment,
        "Total Interest Paid": interest_total,
        "Monthly Net Cash (M1)": cf[0],
        "Total Rental CF": total_rent,
        "Sale Price": sale_price,
        "Net Sale Proceeds": sale_net,
        "Cash Profit": total_rent + sale_net,
    }
    return cf, sheet


# ============================================================================
# MAIN APPLICATION - TABBED INTERFACE
# ============================================================================

# Main tabs for the application
tab_dashboard, tab_deals, tab_analysis, tab_cashflow = st.tabs([
    "📊 Dashboard",
    "🏷️ Deal Configuration",
    "📋 Detailed Analysis",
    "📈 Cash Flow Charts"
])

# ============================================================================
# TAB 2: DEAL CONFIGURATION
# ============================================================================
with tab_deals:
    st.header("Configure Your Deals")

    col_num, col_spacer = st.columns([1, 3])
    with col_num:
        num_deals = st.number_input(
            "Number of Deals to Compare",
            min_value=1,
            max_value=4,
            value=st.session_state.num_deals,
            key="num_deals_input"
        )
        st.session_state.num_deals = num_deals

    st.divider()

    # Create deal configuration containers
    deal_configs = []
    deal_columns = st.columns(int(num_deals))

    for i, col in enumerate(deal_columns):
        with col:
            with st.container(border=True):
                st.subheader(f"Deal {i+1}")

                # Basic Info
                name = st.text_input("Deal Name", value=f"Deal {i+1}", key=f"name{i}")

                # Deal Type Selection with popover for info
                col_type, col_info = st.columns([4, 1])
                with col_type:
                    dtype = st.selectbox(
                        "Financing Type",
                        DEAL_TYPES,
                        key=f"type{i}"
                    )
                with col_info:
                    with st.popover("ℹ️"):
                        if dtype == "Subject-To":
                            st.write("**Subject-To**: Take over seller's existing mortgage payments")
                        elif dtype == "Conventional":
                            st.write("**Conventional**: Traditional bank financing with down payment")
                        elif dtype == "Seller Financing":
                            st.write("**Seller Financing**: Seller acts as the lender")
                        else:
                            st.write("**BRRRR**: Buy, Rehab, Rent, Refinance, Repeat")

                # Rental Strategy
                rental_strategy = st.selectbox(
                    "Rental Strategy",
                    RENTAL_STRATEGIES,
                    key=f"rental{i}"
                )

                # Core Deal Parameters in expander
                with st.expander("💰 Purchase Details", expanded=True):
                    pp = st.number_input(
                        "Purchase Price ($)",
                        0.0, 1e7, 300000.0, 10000.0,
                        key=f"pp{i}"
                    )
                    hold = st.slider(
                        "Holding Period (years)",
                        1, 30, 10,
                        key=f"hold{i}"
                    )
                    gr = st.slider(
                        "Annual Appreciation %",
                        0.00, 0.10, 0.04, 0.005,
                        key=f"gr{i}",
                        format="%.1f%%"
                    )
                    dr = st.slider(
                        "Discount Rate %",
                        0.00, 0.20, 0.08, 0.005,
                        key=f"dr{i}",
                        format="%.1f%%"
                    )

                # Hybrid-specific parameters
                if rental_strategy == "Hybrid":
                    with st.expander("🔄 Hybrid Strategy Settings", expanded=True):
                        str_months = st.slider(
                            "STR Months per Year",
                            1, 11, 4,
                            key=f"strmo{i}",
                            help="Number of months operated as STR (peak season)"
                        )
                        ltr_months = 12 - str_months
                        st.caption(f"📅 {str_months} months STR + {ltr_months} months LTR")
                else:
                    str_months = 0

                # Financing-specific parameters
                params = {
                    "name": name, "type": dtype, "pp": pp, "hold": hold,
                    "gr": gr, "dr": dr, "rental_strategy": rental_strategy,
                    "str_months": str_months
                }

                with st.expander("🏦 Financing Details", expanded=True):
                    if dtype == "Subject-To":
                        eb_default = min(pp, 200000.0)
                        params["eb"] = st.number_input(
                            "Existing Loan Balance ($)",
                            0.0, pp, eb_default, 10000.0,
                            key=f"eb{i}"
                        )
                        params["rate"] = st.slider(
                            "Subject Loan Rate",
                            0.01, 0.08, 0.035, 0.001,
                            key=f"sr{i}",
                            format="%.2f%%"
                        )
                        params["term"] = st.slider(
                            "Loan Term Remaining (years)",
                            1, 30, 25,
                            key=f"tr{i}"
                        )
                        params["premium"] = st.number_input(
                            "Premium to Seller ($)",
                            0.0, 1e6, 10000.0, 1000.0,
                            key=f"prem{i}"
                        )

                    elif dtype == "Conventional":
                        params["dp_pct"] = st.slider(
                            "Down Payment %",
                            0.05, 0.50, 0.20, 0.01,
                            key=f"dp{i}",
                            format="%.0f%%"
                        )
                        params["rate"] = st.slider(
                            "Mortgage Rate",
                            0.02, 0.10, 0.05, 0.001,
                            key=f"cr{i}",
                            format="%.2f%%"
                        )
                        params["term"] = st.slider(
                            "Loan Term (years)",
                            10, 30, 30,
                            key=f"ct{i}"
                        )

                    elif dtype == "Seller Financing":
                        params["fin_pct"] = st.slider(
                            "Seller-Financed %",
                            0.00, 1.00, 0.80, 0.01,
                            key=f"fp{i}",
                            format="%.0f%%"
                        )
                        params["rate"] = st.slider(
                            "Note Rate",
                            0.01, 0.10, 0.06, 0.001,
                            key=f"nr{i}",
                            format="%.2f%%"
                        )
                        params["term"] = st.slider(
                            "Note Term (years)",
                            1, 30, 5,
                            key=f"nt{i}"
                        )

                    else:  # BRRRR
                        params["rehab"] = st.number_input(
                            "Rehab Cost ($)",
                            0.0, 1e6, 50000.0, 5000.0,
                            key=f"rc{i}"
                        )
                        params["arv"] = st.number_input(
                            "After-Repair Value ($)",
                            0.0, 1e7, 350000.0, 10000.0,
                            key=f"arv{i}"
                        )
                        params["rr"] = st.slider(
                            "Refi Rate",
                            0.02, 0.10, 0.05, 0.001,
                            key=f"rr{i}",
                            format="%.2f%%"
                        )
                        params["rlv"] = st.slider(
                            "Refi LTV",
                            0.50, 0.80, 0.75, 0.01,
                            key=f"rl{i}",
                            format="%.0f%%"
                        )

                deal_configs.append(params)

# ============================================================================
# TAB 1: DASHBOARD (Summary View)
# ============================================================================
with tab_dashboard:
    st.header("Investment Summary Dashboard")

    # Validation warnings at the top
    all_warnings = []
    for cfg in deal_configs:
        all_warnings.extend(validate_deal(cfg))

    if all_warnings:
        with st.expander("⚠️ Validation Warnings", expanded=True):
            for warning in all_warnings:
                st.warning(warning)

    # Calculate metrics for all deals
    deal_results = []
    for cfg in deal_configs:
        cf, sheet = build_cashflow_and_sheet(cfg)
        initial_equity = sheet["Initial Equity"]
        irr, total_roi, npv = build_metrics(initial_equity, cf, cfg['dr'])
        deal_results.append({
            "config": cfg,
            "cf": cf,
            "sheet": sheet,
            "irr": irr,
            "roi": total_roi,
            "npv": npv,
            "initial_equity": initial_equity
        })

    # Summary metrics in cards
    st.subheader("Key Metrics Comparison")
    metric_cols = st.columns(int(num_deals))

    # Find best deal for comparison indicators
    best_irr_idx = max(range(len(deal_results)), key=lambda i: deal_results[i]['irr'])
    best_npv_idx = max(range(len(deal_results)), key=lambda i: deal_results[i]['npv'])

    for i, (col, result) in enumerate(zip(metric_cols, deal_results)):
        with col:
            with st.container(border=True):
                st.markdown(f"### {result['config']['name']}")
                st.caption(f"{result['config']['type']} | {result['config']['rental_strategy']}")

                # IRR with indicator
                irr_delta = None
                if len(deal_results) > 1 and i == best_irr_idx:
                    irr_delta = "Best IRR"
                st.metric(
                    "IRR (Annualized)",
                    f"{result['irr']:.2%}",
                    delta=irr_delta
                )

                # Total ROI
                st.metric("Total ROI", f"{result['roi']:.2%}")

                # NPV with indicator
                npv_delta = None
                if len(deal_results) > 1 and i == best_npv_idx:
                    npv_delta = "Best NPV"
                st.metric(
                    "Net Present Value",
                    f"${result['npv']:,.0f}",
                    delta=npv_delta
                )

                st.divider()

                # Quick stats
                st.caption("Quick Stats")
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Cash In", f"${result['initial_equity']:,.0f}", label_visibility="visible")
                with c2:
                    cash_profit = result['sheet'].get('Cash Profit', 0)
                    st.metric("Cash Profit", f"${cash_profit:,.0f}", label_visibility="visible")

    # Comparison table
    st.divider()
    st.subheader("Side-by-Side Comparison")

    comparison_data = {
        "Metric": ["IRR", "Total ROI", "NPV", "Initial Equity", "Cash Profit", "Monthly Net (M1)", "Holding Period"],
    }
    for result in deal_results:
        comparison_data[result['config']['name']] = [
            f"{result['irr']:.2%}",
            f"{result['roi']:.2%}",
            f"${result['npv']:,.0f}",
            f"${result['initial_equity']:,.0f}",
            f"${result['sheet'].get('Cash Profit', 0):,.0f}",
            f"${result['sheet'].get('Monthly Net Cash (M1)', 0):,.0f}",
            f"{result['config']['hold']} years"
        ]

    comparison_df = pd.DataFrame(comparison_data)
    st.dataframe(comparison_df, use_container_width=True, hide_index=True)

    # Mini cash flow chart
    st.divider()
    st.subheader("Cash Flow Overview")

    cum_df = pd.DataFrame()
    for result in deal_results:
        cum_series = pd.Series(np.cumsum(result['cf']), name=result['config']['name'])
        cum_df = pd.concat([cum_df, cum_series], axis=1)

    cum_df = cum_df.reset_index().rename(columns={'index': 'Month'})
    melt_df = cum_df.melt(id_vars=['Month'], var_name='Deal', value_name='Cumulative CF')

    chart = alt.Chart(melt_df).mark_line(strokeWidth=2).encode(
        x=alt.X('Month:Q', title='Month'),
        y=alt.Y('Cumulative CF:Q', title='Cumulative Cash Flow ($)'),
        color=alt.Color('Deal:N', legend=alt.Legend(orient='bottom')),
        tooltip=['Deal', 'Month', alt.Tooltip('Cumulative CF:Q', format='$,.0f')]
    ).properties(height=300)

    st.altair_chart(chart, use_container_width=True)

# ============================================================================
# TAB 3: DETAILED ANALYSIS
# ============================================================================
with tab_analysis:
    st.header("Detailed Deal Analysis")

    # Deal selector for detailed view
    selected_deal = st.selectbox(
        "Select a deal for detailed analysis",
        options=range(len(deal_results)),
        format_func=lambda i: deal_results[i]['config']['name']
    )

    result = deal_results[selected_deal]
    cfg = result['config']
    sheet = result['sheet']
    cf = result['cf']

    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.subheader("📊 Investment Metrics")

            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("IRR", f"{result['irr']:.2%}")
            with m2:
                st.metric("ROI", f"{result['roi']:.2%}")
            with m3:
                st.metric("NPV", f"${result['npv']:,.0f}")

        with st.container(border=True):
            st.subheader("🏠 Property Details")

            details_df = pd.DataFrame({
                "Item": ["Purchase Price", "Financing Type", "Rental Strategy", "Holding Period", "Appreciation Rate"],
                "Value": [
                    f"${cfg['pp']:,.0f}",
                    cfg['type'],
                    cfg['rental_strategy'],
                    f"{cfg['hold']} years",
                    f"{cfg['gr']:.1%}"
                ]
            })
            st.dataframe(details_df, use_container_width=True, hide_index=True)

    with col2:
        with st.container(border=True):
            st.subheader("💰 Financial Summary")

            # Filter numeric values for display
            financial_items = [
                ("Initial Equity", sheet.get("Initial Equity", 0)),
                ("Monthly Debt Service", sheet.get("Debt Service (mo)", 0)),
                ("Total Interest Paid", sheet.get("Total Interest Paid", 0)),
                ("Total Rental CF", sheet.get("Total Rental CF", 0)),
                ("Sale Price", sheet.get("Sale Price", 0)),
                ("Net Sale Proceeds", sheet.get("Net Sale Proceeds", 0)),
                ("Cash Profit", sheet.get("Cash Profit", 0)),
            ]

            fin_df = pd.DataFrame(financial_items, columns=["Item", "Amount"])
            fin_df["Amount"] = fin_df["Amount"].apply(lambda x: f"${x:,.0f}" if isinstance(x, (int, float)) else x)
            st.dataframe(fin_df, use_container_width=True, hide_index=True)

    # Full Net Sheet
    with st.expander("📋 Complete Net Sheet", expanded=False):
        if show_debug:
            st.json(sheet)

        df_sheet = pd.DataFrame(sheet.items(), columns=["Line Item", "Amount"]).set_index("Line Item")
        st.table(
            df_sheet.style.format(lambda v: f"${v:,.0f}" if isinstance(v, (int, float)) else v)
        )

    # Monthly Cash Flow Table
    if show_monthly_breakdown:
        with st.expander("📅 Monthly Cash Flow Breakdown", expanded=False):
            monthly_df = pd.DataFrame({
                "Month": list(range(1, len(cf) + 1)),
                "Cash Flow": cf,
                "Cumulative": np.cumsum(cf)
            })
            monthly_df["Cash Flow"] = monthly_df["Cash Flow"].apply(lambda x: f"${x:,.0f}")
            monthly_df["Cumulative"] = monthly_df["Cumulative"].apply(lambda x: f"${x:,.0f}")
            st.dataframe(monthly_df, use_container_width=True, hide_index=True)

# ============================================================================
# TAB 4: CASH FLOW CHARTS
# ============================================================================
with tab_cashflow:
    st.header("Cash Flow Analysis")

    # Chart type selector
    chart_type = st.radio(
        "Chart View",
        ["Cumulative Cash Flow", "Monthly Cash Flow", "Year-over-Year"],
        horizontal=True
    )

    if chart_type == "Cumulative Cash Flow":
        st.subheader("📈 Cumulative Cash Flow Comparison")

        cum_df = pd.DataFrame()
        for result in deal_results:
            cum_series = pd.Series(np.cumsum(result['cf']), name=result['config']['name'])
            cum_df = pd.concat([cum_df, cum_series], axis=1)

        cum_df = cum_df.reset_index().rename(columns={'index': 'Month'})
        melt_df = cum_df.melt(id_vars=['Month'], var_name='Deal', value_name='Cumulative CF')

        # Base line chart with points
        base = alt.Chart(melt_df).mark_line(point=True, strokeWidth=2).encode(
            x=alt.X('Month:Q', title='Month'),
            y=alt.Y('Cumulative CF:Q', title='Cumulative Cash Flow ($)'),
            color='Deal:N',
            tooltip=['Deal', 'Month', alt.Tooltip('Cumulative CF:Q', format='$,.0f')]
        ).properties(height=400)

        # Build label data
        labels = []
        for result in deal_results:
            name = result['config']['name']
            hold_mo = result['config']['hold'] * 12
            sale_month = hold_mo - 1
            end_rent_month = max(0, hold_mo - 2)

            rent_rows = cum_df.loc[cum_df['Month'] == end_rent_month, name]
            sale_rows = cum_df.loc[cum_df['Month'] == sale_month, name]

            if not rent_rows.empty and not pd.isna(rent_rows.iloc[0]):
                val_rent = rent_rows.iloc[0]
                labels.append({'Deal': name, 'Month': end_rent_month, 'Cumulative CF': val_rent, 'Label': 'End Rent'})

            if not sale_rows.empty and not pd.isna(sale_rows.iloc[0]):
                val_sale = sale_rows.iloc[0]
                labels.append({'Deal': name, 'Month': sale_month, 'Cumulative CF': val_sale, 'Label': 'With Sale'})

        labels_df = pd.DataFrame(labels)

        if not labels_df.empty:
            text = alt.Chart(labels_df).mark_text(dx=10, dy=-10, fontSize=11).encode(
                x='Month:Q',
                y='Cumulative CF:Q',
                text='Label:N',
                color='Deal:N'
            )
            st.altair_chart(base + text, use_container_width=True)
        else:
            st.altair_chart(base, use_container_width=True)

    elif chart_type == "Monthly Cash Flow":
        st.subheader("📊 Monthly Cash Flow by Deal")

        # Select which deal to show
        selected_cf_deal = st.selectbox(
            "Select Deal",
            options=range(len(deal_results)),
            format_func=lambda i: deal_results[i]['config']['name'],
            key="monthly_cf_select"
        )

        result = deal_results[selected_cf_deal]
        monthly_df = pd.DataFrame({
            'Month': list(range(1, len(result['cf']) + 1)),
            'Cash Flow': result['cf']
        })

        bar_chart = alt.Chart(monthly_df).mark_bar().encode(
            x=alt.X('Month:Q', title='Month'),
            y=alt.Y('Cash Flow:Q', title='Monthly Cash Flow ($)'),
            color=alt.condition(
                alt.datum['Cash Flow'] > 0,
                alt.value('#2ecc71'),
                alt.value('#e74c3c')
            ),
            tooltip=['Month', alt.Tooltip('Cash Flow:Q', format='$,.0f')]
        ).properties(height=400)

        st.altair_chart(bar_chart, use_container_width=True)

        # Summary stats
        positive_months = sum(1 for x in result['cf'] if x > 0)
        negative_months = sum(1 for x in result['cf'] if x < 0)
        avg_monthly = np.mean(result['cf'][:-1])  # Exclude final month with sale

        s1, s2, s3 = st.columns(3)
        with s1:
            st.metric("Positive Cash Flow Months", f"{positive_months}")
        with s2:
            st.metric("Negative Cash Flow Months", f"{negative_months}")
        with s3:
            st.metric("Avg Monthly CF (excl. sale)", f"${avg_monthly:,.0f}")

    else:  # Year-over-Year
        st.subheader("📅 Year-over-Year Cash Flow")

        yearly_data = []
        for result in deal_results:
            cf = result['cf']
            hold = result['config']['hold']
            for year in range(hold):
                start_month = year * 12
                end_month = min((year + 1) * 12, len(cf))
                yearly_cf = sum(cf[start_month:end_month])
                yearly_data.append({
                    'Deal': result['config']['name'],
                    'Year': year + 1,
                    'Annual CF': yearly_cf
                })

        yearly_df = pd.DataFrame(yearly_data)

        yearly_chart = alt.Chart(yearly_df).mark_bar().encode(
            x=alt.X('Year:O', title='Year'),
            y=alt.Y('Annual CF:Q', title='Annual Cash Flow ($)'),
            color='Deal:N',
            xOffset='Deal:N',
            tooltip=['Deal', 'Year', alt.Tooltip('Annual CF:Q', format='$,.0f')]
        ).properties(height=400)

        st.altair_chart(yearly_chart, use_container_width=True)

        # Yearly comparison table
        with st.expander("📋 Yearly Cash Flow Table", expanded=False):
            pivot_df = yearly_df.pivot(index='Year', columns='Deal', values='Annual CF')
            pivot_df = pivot_df.applymap(lambda x: f"${x:,.0f}" if pd.notna(x) else "-")
            st.dataframe(pivot_df, use_container_width=True)

# Footer
st.divider()
st.caption("Real Estate Deal Analyzer v10 | Built with Streamlit | Use the tabs above to navigate between views")
