import streamlit as st
import pandas as pd
import numpy_financial as nf

st.set_page_config(page_title="Real Estate Deal Analyzer", layout="wide")
st.title("🏠 Real Estate Deal Analyzer – Net‑Sheet Edition (v7)")

# ───────────────────────────────────────────────────────────
# 1 ▸ GLOBAL ASSUMPTIONS
# ───────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Global Assumptions")
    market_rent   = st.number_input("Market Rent ($/mo)",  value=2000.0, step=50.0)
    expense_ratio = st.slider("Operating Expense Ratio", 0.00, 1.00, 0.35, 0.01)
    closing_pct   = st.slider("Closing Cost % (buy & sell)", 0.00, 0.10, 0.06, 0.005)

oper_exp = market_rent * expense_ratio  # monthly opex

# ───────────────────────────────────────────────────────────
# 2 ▸ DEAL INPUTS
# ───────────────────────────────────────────────────────────
DEAL_TYPES = ["Subject-To", "Conventional", "Seller Financing", "BRRRR"]
num_deals  = st.sidebar.number_input("Number of Deals", 1, 4, 2)

deal_configs = []
for i in range(int(num_deals)):
    with st.sidebar:
        st.markdown("---")
        name = st.text_input("Deal Display Name", value=f"Deal {i+1}", key=f"name{i}")
        dtype = st.selectbox("Type", DEAL_TYPES, key=f"dtype{i}")
        pp    = st.number_input("Purchase Price", 0.0, 1e7, 300000.0, 10000.0, key=f"pp{i}")
        hold  = st.slider("Holding Period (yrs)", 1, 30, 10, key=f"hold{i}")
        gr    = st.slider("Annual Appreciation %", 0.00, 0.10, 0.04, 0.005, key=f"gr{i}")
        dr    = st.slider("Discount Rate %",       0.00, 0.20, 0.08, 0.005, key=f"dr{i}")
        cfg   = dict(name=name, type=dtype, pp=pp, hold=hold, gr=gr, dr=dr)

        if dtype == "Subject-To":
            cfg.update({
                "eb":      st.number_input("Existing Loan Balance", 0.0, pp, 200000.0, 10000.0, key=f"eb{i}"),
                "rate":    st.slider("Subject Loan Rate", 0.01, 0.08, 0.035, 0.001, key=f"sr{i}"),
                "term":    st.slider("Loan Term Remaining (yrs)", 1, 30, 25, key=f"tr{i}"),
                "premium": st.number_input("Premium to Seller", 0.0, 1e6, 10000.0, 1000.0, key=f"prem{i}")
            })
        elif dtype == "Conventional":
            cfg.update({
                "dp_pct": st.slider("Down Payment %", 0.05, 0.50, 0.20, 0.01, key=f"dp{i}"),
                "rate":   st.slider("Loan Rate", 0.02, 0.10, 0.05, 0.001, key=f"cr{i}"),
                "term":   st.slider("Loan Term (yrs)", 10, 30, 30, key=f"ct{i}")
            })
        elif dtype == "Seller Financing":
            cfg.update({
                "fin_pct": st.slider("Seller‑Financed %", 0.00, 1.00, 0.80, 0.01, key=f"fp{i}"),
                "rate":    st.slider("Note Rate", 0.01, 0.10, 0.06, 0.001, key=f"nr{i}"),
                "term":    st.slider("Note Term (yrs)", 1, 30, 5, key=f"nt{i}")
            })
        else:  # BRRRR
            cfg.update({
                "rehab": st.number_input("Rehab Cost", 0.0, 1e6, 50000.0, 5000.0, key=f"rc{i}"),
                "arv":   st.number_input("After‑Repair Value", 0.0, 1e7, 350000.0, 10000.0, key=f"arv{i}"),
                "rr":    st.slider("Refi Rate", 0.02, 0.10, 0.05, 0.001, key=f"rr{i}"),
                "rlv":   st.slider("Refi LTV", 0.50, 0.80, 0.75, 0.01, key=f"rlv{i}")
            })
        deal_configs.append(cfg)

# ───────────────────────────────────────────────────────────
# 3 ▸ HELPER FUNCTIONS
# ───────────────────────────────────────────────────────────

def amortize(balance, rate_mo, payment, n):
    bal=balance
    for _ in range(n):
        interest=bal*rate_mo
        bal-=payment-interest
    return bal


def monthly_cf(payment):
    return market_rent - oper_exp - payment


def build_metrics(sheet, cf, hold):
    annual_cash_flow = sheet["Total Rental CF"] / hold
    coc = annual_cash_flow / sheet["Initial Investment"] if sheet["Initial Investment"] else 0
    ending_equity = sheet["Profit"] + sheet["Initial Investment"]
    ann_roi = (ending_equity / sheet["Initial Investment"]) ** (1/hold) - 1 if sheet["Initial Investment"] else 0
    irr = nf.irr(cf) if cf else 0
    return coc, ann_roi, irr

# ───────────────────────────────────────────────────────────
# 4 ▸ DEAL MODELS
# ───────────────────────────────────────────────────────────

def subject_cf(p):
    pp, eb, rate, term, prem, hold = p['pp'], p['eb'], p['rate'], p['term'], p['premium'], p['hold']
    # Calculate payment and cash flows
    pay = nf.pmt(rate / 12, term * 12, -eb)
    rent = market_rent
    exp = oper_exp
    mon = rent - exp - pay
    init = (pp - eb) + prem + pp * closing_pct
    total_rent = mon * hold * 12
    bal = amortize(eb, rate / 12, pay, hold * 12)
    sale = pp * (1 + p['gr']) ** hold
    sale_net = sale - sale * closing_pct - bal
    cf = [-init] + [mon] * (hold * 12)
    cf[-1] += sale_net
    # Build net-sheet including breakdown
    sheet = {
        "Purchase Price":        pp,
        "Existing Loan Balance": eb,
        "Premium Paid":          prem,
        "Closing Costs (buy)":   pp * closing_pct,
        "Initial Investment":    init,
        "Monthly Rent":          rent,
        "Operating Expenses":    exp,
        "Debt Service (mo)":     pay,
        "Monthly Net Cash":      mon,
        "Total Rental CF":       total_rent,
        "Sale Price":            sale,
        "Net Sale Proceeds":     sale_net,
        "Profit":                total_rent + sale_net,
    }
    coc, ann_roi, irr = build_metrics(sheet, cf, hold)
    return cf, sheet, coc, ann_roi, irr

def conventional_cf(p):
    pp, dp, rate, term, hold = p['pp'], p['dp_pct'], p['rate'], p['term'], p['hold']
    down = pp * dp
    loan = pp - down
    pay = nf.pmt(rate / 12, term * 12, -loan)
    rent = market_rent
    exp = oper_exp
    mon = rent - exp - pay
    init = down + pp * closing_pct
    total_rent = mon * hold * 12
    bal = amortize(loan, rate / 12, pay, hold * 12)
    sale = pp * (1 + p['gr']) ** hold
    sale_net = sale - sale * closing_pct - bal
    cf = [-init] + [mon] * (hold * 12)
    cf[-1] += sale_net
    sheet = {
        "Purchase Price":        pp,
        "Down Payment":          down,
        "Loan Amount":           loan,
        "Closing Costs (buy)":   pp * closing_pct,
        "Initial Investment":    init,
        "Monthly Rent":          rent,
        "Operating Expenses":    exp,
        "Debt Service (mo)":     pay,
        "Monthly Net Cash":      mon,
        "Total Rental CF":       total_rent,
        "Sale Price":            sale,
        "Net Sale Proceeds":     sale_net,
        "Profit":                total_rent + sale_net,
    }
    coc, ann_roi, irr = build_metrics(sheet, cf, hold)
    return cf, sheet, coc, ann_roi, irr

def seller_fin_cf(p):
    pp, fp, rate, term, hold = p['pp'], p['fin_pct'], p['rate'], p['term'], p['hold']
    financed = pp * fp
    pay = nf.pmt(rate / 12, term * 12, -financed)
    rent = market_rent
    exp = oper_exp
    mon = rent - exp - pay
    init = (pp - financed) + pp * closing_pct
    total_rent = mon * hold * 12
    bal = amortize(financed, rate / 12, pay, hold * 12)
    sale = pp * (1 + p['gr']) ** hold
    sale_net = sale - sale * closing_pct - bal
    cf = [-init] + [mon] * (hold * 12)
    cf[-1] += sale_net
    sheet = {
        "Purchase Price":        pp,
        "Seller-Financed %":     fp,
        "Closing Costs (buy)":   pp * closing_pct,
        "Initial Investment":    init,
        "Monthly Rent":          rent,
        "Operating Expenses":    exp,
        "Debt Service (mo)":     pay,
        "Monthly Net Cash":      mon,
        "Total Rental CF":       total_rent,
        "Sale Price":            sale,
        "Net Sale Proceeds":     sale_net,
        "Profit":                total_rent + sale_net,
    }
    coc, ann_roi, irr = build_metrics(sheet, cf, hold)
    return cf, sheet, coc, ann_roi, irr

def brrrr_cf(p):
    pp, rehab, arv, rr, rlv, hold = (
        p['pp'], p['rehab'], p['arv'], p['rr'], p['rlv'], p['hold']
    )
    cost = pp + rehab + pp * closing_pct
    loan = arv * rlv
    pay = nf.pmt(rr / 12, hold * 12, -loan)
    rent = market_rent
    exp = oper_exp
    mon = rent - exp - pay
    init = cost - loan
    total_rent = mon * hold * 12
    bal = amortize(loan, rr / 12, pay, hold * 12)
    sale = arv * (1 + p['gr']) ** hold
    sale_net = sale - sale * closing_pct - bal
    cf = [-init] + [mon] * (hold * 12)
    cf[-1] += sale_net
    sheet = {
        "Purchase Price":        pp,
        "Rehab Cost":            rehab,
        "Closing Costs (buy)":   pp * closing_pct,
        "Initial Investment":    init,
        "Monthly Rent":          rent,
        "Operating Expenses":    exp,
        "Debt Service (mo)":     pay,
        "Monthly Net Cash":      mon,
        "Total Rental CF":       total_rent,
        "Sale Price":            sale,
        "Net Sale Proceeds":     sale_net,
        "Profit":                total_rent + sale_net,
    }
    coc, ann_roi, irr = build_metrics(sheet, cf, hold)
    return cf, sheet, coc, ann_roi, irr

# mapping
# ───────────────────────────────────────────────────────────
# 5 ▸ CALCULATE RESULTS
# ───────────────────────────────────────────────────────────
calc_map = {
    "Subject-To": subject_cf,
    "Conventional": conventional_cf,
    "Seller Financing": seller_fin_cf,
    "BRRRR": brrrr_cf,
}

summary_rows = []
net_sheets   = []

for idx, cfg in enumerate(deal_configs, 1):
    cf, sheet, coc, ann_roi, irr = calc_map[cfg["type"]](cfg)
    # use custom name
    deal_label = cfg.get("name", f"Deal {idx}")
    total_roi = sheet["Profit"] / sheet["Initial Investment"] if sheet["Initial Investment"] else 0
    summary_rows.append({
        "Deal":               deal_label,
        "Type":               cfg["type"],
        "Initial Investment": sheet["Initial Investment"],
        "IRR":                irr,
        "Annual ROI":         ann_roi,
        "Total ROI":          total_roi,
        "Cash Profit":        sheet["Profit"],
    })
    net_sheets.append((deal_label, sheet))

# ───────────────────────────────────────────────────────────
# 6 ▸ DISPLAY SUMMARY & NET‑SHEETS
# ───────────────────────────────────────────────────────────
summary_df = pd.DataFrame(summary_rows).set_index("Deal")

st.subheader("📊 Summary Metrics")
st.dataframe(
    summary_df.style.format({
        "Initial Investment": "${:,.0f}",
        "IRR":                "{:.2%}",
        "Annual ROI":         "{:.2%}",
        "Total ROI":          "{:.2%}",
        "Cash Profit":        "${:,.0f}",
    })
)

st.subheader("Charts")
col1, col2 = st.columns(2)
with col1:
    st.bar_chart(summary_df["IRR"])
with col2:
    st.bar_chart(summary_df["Cash Profit"])

st.subheader("🧾 Net‑Sheet Details")
for title, sheet in net_sheets:
    with st.expander(title):
        # Debug: show raw sheet values
        st.markdown("**Debug: Net-Sheet Data**")
        st.json(sheet)
        # Display formatted table
        st.table(
            pd.DataFrame(sheet.items(), columns=["Line Item", "Amount"])  
              .set_index("Line Item")  
              .style.format("${:,.0f}")
        )
