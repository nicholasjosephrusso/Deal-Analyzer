import numpy_financial as nf
import pytest
from unittest.mock import patch


class TestBuildMetrics:
    """Tests for the build_metrics function."""

    def test_simple_case(self):
        """Test basic IRR and ROI calculation."""
        from subject_to_analyzer import build_metrics

        irr, roi, npv = build_metrics(1000, [1100])
        expected_monthly = nf.irr([-1000, 1100])
        expected_annual = (1 + expected_monthly) ** 12 - 1
        expected_roi = 1100 / 1000

        assert irr == pytest.approx(expected_annual, rel=1e-6)
        assert roi == pytest.approx(expected_roi, rel=1e-6)

    def test_multiple_cashflows(self):
        """Test with multiple monthly cash flows."""
        from subject_to_analyzer import build_metrics

        initial = 10000
        cf = [500] * 12  # 12 months of $500/month
        irr, roi, npv = build_metrics(initial, cf)

        assert irr > 0  # Should be positive return
        assert roi == pytest.approx(sum(cf) / initial, rel=1e-6)

    def test_zero_equity_returns_zero_roi(self):
        """Test that zero equity doesn't cause division by zero."""
        from subject_to_analyzer import build_metrics

        irr, roi, npv = build_metrics(0, [100, 100])
        assert roi == 0

    def test_npv_calculation(self):
        """Test NPV calculation with discount rate."""
        from subject_to_analyzer import build_metrics

        initial = 10000
        cf = [1000] * 12
        discount_rate = 0.10

        irr, roi, npv = build_metrics(initial, cf, discount_rate)

        # NPV should be positive since cash flows exceed initial investment
        assert npv > 0

    def test_different_discount_rates(self):
        """Test that higher discount rates result in lower NPV."""
        from subject_to_analyzer import build_metrics

        initial = 10000
        cf = [1000] * 24

        _, _, npv_low = build_metrics(initial, cf, 0.05)
        _, _, npv_high = build_metrics(initial, cf, 0.15)

        assert npv_low > npv_high


class TestValidateDeal:
    """Tests for the validate_deal function."""

    @pytest.fixture
    def mock_closing_pct(self):
        """Mock the closing_pct global variable."""
        with patch('subject_to_analyzer.closing_pct', 0.06):
            yield

    def test_subject_to_valid(self, mock_closing_pct):
        """Test valid Subject-To deal passes validation."""
        from subject_to_analyzer import validate_deal

        deal = {
            'name': 'Test Deal',
            'type': 'Subject-To',
            'pp': 300000,
            'eb': 200000,
            'premium': 10000,
        }
        warnings = validate_deal(deal)
        assert len(warnings) == 0

    def test_subject_to_zero_balance(self, mock_closing_pct):
        """Test Subject-To with zero balance fails."""
        from subject_to_analyzer import validate_deal

        deal = {
            'name': 'Test Deal',
            'type': 'Subject-To',
            'pp': 300000,
            'eb': 0,
            'premium': 10000,
        }
        warnings = validate_deal(deal)
        assert any('Existing balance' in w for w in warnings)

    def test_conventional_valid(self, mock_closing_pct):
        """Test valid Conventional deal passes validation."""
        from subject_to_analyzer import validate_deal

        deal = {
            'name': 'Test Deal',
            'type': 'Conventional',
            'pp': 300000,
            'dp_pct': 0.20,
        }
        warnings = validate_deal(deal)
        assert len(warnings) == 0

    def test_conventional_zero_down_payment(self, mock_closing_pct):
        """Test Conventional with zero down payment fails."""
        from subject_to_analyzer import validate_deal

        deal = {
            'name': 'Test Deal',
            'type': 'Conventional',
            'pp': 300000,
            'dp_pct': 0,
        }
        warnings = validate_deal(deal)
        assert any('Down payment' in w for w in warnings)

    def test_seller_financing_valid(self, mock_closing_pct):
        """Test valid Seller Financing deal passes validation."""
        from subject_to_analyzer import validate_deal

        deal = {
            'name': 'Test Deal',
            'type': 'Seller Financing',
            'pp': 300000,
            'fin_pct': 0.80,
        }
        warnings = validate_deal(deal)
        assert len(warnings) == 0

    def test_seller_financing_invalid_percentage(self, mock_closing_pct):
        """Test Seller Financing with invalid percentage fails."""
        from subject_to_analyzer import validate_deal

        deal = {
            'name': 'Test Deal',
            'type': 'Seller Financing',
            'pp': 300000,
            'fin_pct': 1.5,  # Invalid: > 100%
        }
        warnings = validate_deal(deal)
        assert any('Financed percentage' in w for w in warnings)

    def test_brrrr_valid(self, mock_closing_pct):
        """Test valid BRRRR deal passes validation."""
        from subject_to_analyzer import validate_deal

        deal = {
            'name': 'Test Deal',
            'type': 'BRRRR',
            'pp': 200000,
            'rehab': 50000,
            'arv': 350000,
            'rlv': 0.75,
        }
        warnings = validate_deal(deal)
        assert len(warnings) == 0

    def test_brrrr_arv_below_pp(self, mock_closing_pct):
        """Test BRRRR with ARV below purchase price warns."""
        from subject_to_analyzer import validate_deal

        deal = {
            'name': 'Test Deal',
            'type': 'BRRRR',
            'pp': 300000,
            'rehab': 50000,
            'arv': 250000,  # Below purchase price
            'rlv': 0.75,
        }
        warnings = validate_deal(deal)
        assert any('After-repair value' in w for w in warnings)


class TestCashflowFunctions:
    """Integration tests for cashflow calculation functions."""

    @pytest.fixture
    def mock_globals(self):
        """Mock all global variables used by cashflow functions."""
        with patch.multiple(
            'subject_to_analyzer',
            market_rent=2000.0,
            rent_growth=0.02,
            oper_exp=700.0,
            closing_pct=0.06
        ):
            yield

    def test_subject_cf_returns_correct_structure(self, mock_globals):
        """Test Subject-To cashflow function returns expected structure."""
        from subject_to_analyzer import subject_cf

        params = {
            'name': 'Test',
            'type': 'Subject-To',
            'pp': 300000,
            'eb': 200000,
            'rate': 0.035,
            'term': 25,
            'premium': 10000,
            'hold': 5,
            'gr': 0.04,
        }
        cf, sheet = subject_cf(params)

        # Check cashflow length
        assert len(cf) == 5 * 12  # 5 years * 12 months

        # Check sheet contains required keys
        required_keys = [
            'Purchase Price', 'Existing Balance', 'Premium Paid',
            'Initial Equity', 'Sale Price', 'Net Sale Proceeds'
        ]
        for key in required_keys:
            assert key in sheet

    def test_conventional_cf_returns_correct_structure(self, mock_globals):
        """Test Conventional cashflow function returns expected structure."""
        from subject_to_analyzer import conventional_cf

        params = {
            'name': 'Test',
            'type': 'Conventional',
            'pp': 300000,
            'dp_pct': 0.20,
            'rate': 0.05,
            'term': 30,
            'hold': 10,
            'gr': 0.04,
        }
        cf, sheet = conventional_cf(params)

        assert len(cf) == 10 * 12
        assert 'Down Payment' in sheet
        assert 'Loan Amount' in sheet

    def test_seller_fin_cf_returns_correct_structure(self, mock_globals):
        """Test Seller Financing cashflow function returns expected structure."""
        from subject_to_analyzer import seller_fin_cf

        params = {
            'name': 'Test',
            'type': 'Seller Financing',
            'pp': 300000,
            'fin_pct': 0.80,
            'rate': 0.06,
            'term': 5,
            'hold': 7,
            'gr': 0.04,
        }
        cf, sheet = seller_fin_cf(params)

        assert len(cf) == 7 * 12
        assert 'Financed Amount' in sheet

    def test_brrrr_cf_returns_correct_structure(self, mock_globals):
        """Test BRRRR cashflow function returns expected structure."""
        from subject_to_analyzer import brrrr_cf

        params = {
            'name': 'Test',
            'type': 'BRRRR',
            'pp': 200000,
            'rehab': 50000,
            'arv': 350000,
            'rr': 0.05,
            'rlv': 0.75,
            'hold': 10,
            'gr': 0.04,
        }
        cf, sheet = brrrr_cf(params)

        assert len(cf) == 10 * 12
        assert 'Rehab Cost' in sheet
        assert 'Refi Loan Amount' in sheet
        assert 'Cash-Out Proceeds' in sheet

    def test_cashflow_sale_included_in_last_month(self, mock_globals):
        """Test that sale proceeds are included in the final month's cashflow."""
        from subject_to_analyzer import conventional_cf

        params = {
            'name': 'Test',
            'type': 'Conventional',
            'pp': 300000,
            'dp_pct': 0.20,
            'rate': 0.05,
            'term': 30,
            'hold': 5,
            'gr': 0.04,
        }
        cf, sheet = conventional_cf(params)

        # Last month should include sale proceeds (much larger than normal month)
        assert cf[-1] > cf[0] * 10  # Sale should be much larger than monthly CF

    def test_rent_growth_increases_cashflow(self, mock_globals):
        """Test that rent growth results in increasing cashflows over time."""
        from subject_to_analyzer import conventional_cf

        params = {
            'name': 'Test',
            'type': 'Conventional',
            'pp': 300000,
            'dp_pct': 0.20,
            'rate': 0.05,
            'term': 30,
            'hold': 5,
            'gr': 0.04,
        }
        cf, sheet = conventional_cf(params)

        # Compare year 1 vs year 5 (excluding last month with sale)
        year1_avg = sum(cf[0:12]) / 12
        year5_avg = sum(cf[48:59]) / 11  # 11 months, excluding sale month

        assert year5_avg > year1_avg
