import os
import numpy as np
import numpy_financial as nf
import sys
import importlib.util

os.environ['DEAL_ANALYZER_SKIP_UI'] = '1'
spec = importlib.util.spec_from_file_location("subject_to_analyzer", os.path.join(os.path.dirname(__file__), "..", "subject_to_analyzer.py"))
sta = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = sta
spec.loader.exec_module(sta)

# Helper to recompute expected subject-to cash flows

def expected_subject_cf(p):
    mrate = p['rate']/12
    periods = p['term']*12
    payment = nf.pmt(mrate, periods, -p['eb'])
    bal = p['eb']
    cf = []
    for m in range(1, p['hold']*12+1):
        year = (m-1)//12
        rent = sta.market_rent * (1 + sta.rent_growth)**year
        exp = sta.oper_exp * (1 + sta.rent_growth)**year
        interest = bal*mrate
        principal = payment - interest
        bal -= principal
        cf.append(rent - exp - payment)
    sale_price = p['pp']*(1+p['gr'])**p['hold']
    sale_net = sale_price - sale_price*sta.closing_pct - bal
    cf[-1] += sale_net
    return cf, payment, bal

def test_subject_cf_calculations():
    sta.market_rent = 1000
    sta.rent_growth = 0.0
    sta.expense_ratio = 0.5
    sta.oper_exp = sta.market_rent * sta.expense_ratio
    sta.closing_pct = 0.05

    params = {
        'pp': 150000,
        'eb': 100000,
        'rate': 0.06,
        'term': 30,
        'premium': 10000,
        'hold': 1,
        'gr': 0.0,
        'type': 'Subject-To'
    }
    cf, sheet = sta.subject_cf(params)
    exp_cf, payment, bal = expected_subject_cf(params)
    assert np.allclose(cf, exp_cf)
    assert np.isclose(sheet['Debt Service (mo)'], payment)
    assert np.isclose(sheet['Net Sale Proceeds'], exp_cf[-1] - (sta.market_rent - sta.oper_exp - payment))

def test_conventional_cf_basic():
    sta.market_rent = 1200
    sta.rent_growth = 0
    sta.expense_ratio = 0.3
    sta.oper_exp = sta.market_rent * sta.expense_ratio
    sta.closing_pct = 0.04

    params = {
        'pp': 200000,
        'dp_pct': 0.2,
        'rate': 0.05,
        'term': 30,
        'hold': 1,
        'gr': 0.0,
        'type': 'Conventional'
    }
    cf, sheet = sta.conventional_cf(params)
    payment = nf.pmt(0.05/12, 30*12, -(200000*0.8))
    assert np.isclose(sheet['Debt Service (mo)'], payment)
    assert len(cf) == 12


def test_seller_fin_cf_basic():
    sta.market_rent = 1500
    sta.rent_growth = 0
    sta.expense_ratio = 0.4
    sta.oper_exp = sta.market_rent * sta.expense_ratio
    sta.closing_pct = 0.03

    params = {
        'pp': 250000,
        'fin_pct': 0.8,
        'rate': 0.07,
        'term': 5,
        'hold': 1,
        'gr': 0.0,
        'type': 'Seller Financing'
    }
    cf, sheet = sta.seller_fin_cf(params)
    payment = nf.pmt(0.07/12, 5*12, -(250000*0.8))
    assert np.isclose(sheet['Debt Service (mo)'], payment)
    assert len(cf) == 12


def test_brrrr_cf_basic():
    sta.market_rent = 900
    sta.rent_growth = 0
    sta.expense_ratio = 0.45
    sta.oper_exp = sta.market_rent * sta.expense_ratio
    sta.closing_pct = 0.05

    params = {
        'pp': 80000,
        'rehab': 20000,
        'arv': 120000,
        'rr': 0.05,
        'rlv': 0.75,
        'hold': 1,
        'gr': 0.0,
        'type': 'BRRRR'
    }
    cf, sheet = sta.brrrr_cf(params)
    payment = nf.pmt(0.05/12, 12, -(120000*0.75))
    assert np.isclose(sheet['Debt Service (mo)'], payment)
    assert len(cf) == 12


def test_build_metrics():
    irr, roi = sta.build_metrics(10000, [2000]*5)
    expected_irr = nf.irr([-10000] + [2000]*5)
    expected_roi = (2000*5)/10000
    assert np.isclose(irr, expected_irr)
    assert np.isclose(roi, expected_roi)
