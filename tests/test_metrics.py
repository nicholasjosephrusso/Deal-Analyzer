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


class TestRentalIncomeCalculation:
    """Tests for rental income calculation functions."""

    @pytest.fixture
    def mock_rental_globals(self):
        """Mock all rental-related global variables."""
        with patch.multiple(
            'subject_to_analyzer',
            ltr_rent=2000.0,
            ltr_growth=0.02,
            ltr_expense=0.35,
            ltr_vacancy=0.05,
            str_nightly=150.0,
            str_occupancy=0.65,
            str_growth=0.03,
            str_expense=0.50
        ):
            yield

    def test_ltr_income_calculation(self, mock_rental_globals):
        """Test LTR income calculation."""
        from subject_to_analyzer import calculate_rental_income

        gross, exp = calculate_rental_income("LTR", 1, 0)

        # LTR: base_rent * (1 - vacancy) for gross
        expected_gross = 2000.0 * (1 - 0.05)  # 1900
        expected_exp = 2000.0 * 0.35  # 700

        assert gross == pytest.approx(expected_gross, rel=1e-6)
        assert exp == pytest.approx(expected_exp, rel=1e-6)

    def test_ltr_income_with_growth(self, mock_rental_globals):
        """Test LTR income increases with year."""
        from subject_to_analyzer import calculate_rental_income

        gross_y0, _ = calculate_rental_income("LTR", 1, 0)
        gross_y1, _ = calculate_rental_income("LTR", 1, 1)

        # Year 1 should be 2% higher than year 0
        assert gross_y1 == pytest.approx(gross_y0 * 1.02, rel=1e-6)

    def test_str_income_calculation(self, mock_rental_globals):
        """Test STR income calculation."""
        from subject_to_analyzer import calculate_rental_income

        gross, exp = calculate_rental_income("STR", 1, 0)

        # STR: nightly * 30 days * occupancy
        expected_gross = 150.0 * 30 * 0.65  # 2925
        expected_exp = expected_gross * 0.50  # 1462.50

        assert gross == pytest.approx(expected_gross, rel=1e-6)
        assert exp == pytest.approx(expected_exp, rel=1e-6)

    def test_str_income_higher_than_ltr(self, mock_rental_globals):
        """Test that STR gross income exceeds LTR gross income."""
        from subject_to_analyzer import calculate_rental_income

        ltr_gross, _ = calculate_rental_income("LTR", 1, 0)
        str_gross, _ = calculate_rental_income("STR", 1, 0)

        assert str_gross > ltr_gross

    def test_hybrid_uses_str_for_peak_months(self, mock_rental_globals):
        """Test Hybrid uses STR income for designated STR months."""
        from subject_to_analyzer import calculate_rental_income

        # Month 1 should be STR (within str_months=4)
        hybrid_m1, _ = calculate_rental_income("Hybrid", 1, 0, str_months=4)
        str_m1, _ = calculate_rental_income("STR", 1, 0)

        assert hybrid_m1 == pytest.approx(str_m1, rel=1e-6)

    def test_hybrid_uses_ltr_for_off_peak_months(self, mock_rental_globals):
        """Test Hybrid uses LTR income for non-STR months."""
        from subject_to_analyzer import calculate_rental_income

        # Month 5 should be LTR (outside str_months=4)
        hybrid_m5, _ = calculate_rental_income("Hybrid", 5, 0, str_months=4)
        ltr_m5, _ = calculate_rental_income("LTR", 5, 0)

        assert hybrid_m5 == pytest.approx(ltr_m5, rel=1e-6)


class TestValidateDeal:
    """Tests for the validate_deal function."""

    @pytest.fixture
    def mock_validation_globals(self):
        """Mock globals needed for validation."""
        with patch.multiple(
            'subject_to_analyzer',
            closing_pct=0.06,
            str_nightly=150.0,
            str_occupancy=0.65,
            str_expense=0.50
        ):
            yield

    def test_subject_to_valid(self, mock_validation_globals):
        """Test valid Subject-To deal passes validation."""
        from subject_to_analyzer import validate_deal

        deal = {
            'name': 'Test Deal',
            'type': 'Subject-To',
            'pp': 300000,
            'eb': 200000,
            'premium': 10000,
            'rental_strategy': 'LTR',
            'str_months': 0,
        }
        warnings = validate_deal(deal)
        assert len(warnings) == 0

    def test_subject_to_zero_balance(self, mock_validation_globals):
        """Test Subject-To with zero balance fails."""
        from subject_to_analyzer import validate_deal

        deal = {
            'name': 'Test Deal',
            'type': 'Subject-To',
            'pp': 300000,
            'eb': 0,
            'premium': 10000,
            'rental_strategy': 'LTR',
            'str_months': 0,
        }
        warnings = validate_deal(deal)
        assert any('Existing balance' in w for w in warnings)

    def test_conventional_valid(self, mock_validation_globals):
        """Test valid Conventional deal passes validation."""
        from subject_to_analyzer import validate_deal

        deal = {
            'name': 'Test Deal',
            'type': 'Conventional',
            'pp': 300000,
            'dp_pct': 0.20,
            'rental_strategy': 'LTR',
            'str_months': 0,
        }
        warnings = validate_deal(deal)
        assert len(warnings) == 0

    def test_str_deal_validation(self, mock_validation_globals):
        """Test STR deal validation."""
        from subject_to_analyzer import validate_deal

        deal = {
            'name': 'Test Deal',
            'type': 'Conventional',
            'pp': 300000,
            'dp_pct': 0.20,
            'rental_strategy': 'STR',
            'str_months': 0,
        }
        warnings = validate_deal(deal)
        # Should pass with valid STR globals
        assert len(warnings) == 0

    def test_hybrid_invalid_months(self, mock_validation_globals):
        """Test Hybrid with invalid STR months fails."""
        from subject_to_analyzer import validate_deal

        deal = {
            'name': 'Test Deal',
            'type': 'Conventional',
            'pp': 300000,
            'dp_pct': 0.20,
            'rental_strategy': 'Hybrid',
            'str_months': 0,  # Invalid: must be 1-11
        }
        warnings = validate_deal(deal)
        assert any('Hybrid STR months' in w for w in warnings)


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
            closing_pct=0.06,
            ltr_rent=2000.0,
            ltr_growth=0.02,
            ltr_expense=0.35,
            ltr_vacancy=0.05,
            str_nightly=150.0,
            str_occupancy=0.65,
            str_growth=0.03,
            str_expense=0.50
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
            'rental_strategy': 'LTR',
            'str_months': 0,
        }
        cf, sheet = subject_cf(params)

        # Check cashflow length
        assert len(cf) == 5 * 12  # 5 years * 12 months

        # Check sheet contains required keys
        required_keys = [
            'Purchase Price', 'Existing Balance', 'Premium Paid',
            'Initial Equity', 'Sale Price', 'Net Sale Proceeds',
            'Rental Strategy'  # New key
        ]
        for key in required_keys:
            assert key in sheet

    def test_conventional_cf_with_str(self, mock_globals):
        """Test Conventional cashflow with STR strategy."""
        from subject_to_analyzer import conventional_cf

        params_ltr = {
            'name': 'Test LTR',
            'type': 'Conventional',
            'pp': 300000,
            'dp_pct': 0.20,
            'rate': 0.05,
            'term': 30,
            'hold': 5,
            'gr': 0.04,
            'rental_strategy': 'LTR',
            'str_months': 0,
        }
        params_str = {
            **params_ltr,
            'name': 'Test STR',
            'rental_strategy': 'STR',
        }

        cf_ltr, _ = conventional_cf(params_ltr)
        cf_str, _ = conventional_cf(params_str)

        # STR should generate higher cash flows (before sale month)
        assert sum(cf_str[:-1]) > sum(cf_ltr[:-1])

    def test_conventional_cf_with_hybrid(self, mock_globals):
        """Test Conventional cashflow with Hybrid strategy."""
        from subject_to_analyzer import conventional_cf

        params = {
            'name': 'Test Hybrid',
            'type': 'Conventional',
            'pp': 300000,
            'dp_pct': 0.20,
            'rate': 0.05,
            'term': 30,
            'hold': 1,  # 1 year to see seasonal variation
            'gr': 0.04,
            'rental_strategy': 'Hybrid',
            'str_months': 4,
        }
        cf, sheet = conventional_cf(params)

        assert len(cf) == 12
        assert 'Hybrid' in sheet['Rental Strategy']

    def test_brrrr_cf_with_str(self, mock_globals):
        """Test BRRRR cashflow with STR strategy."""
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
            'rental_strategy': 'STR',
            'str_months': 0,
        }
        cf, sheet = brrrr_cf(params)

        assert len(cf) == 10 * 12
        assert 'Short-Term Rental' in sheet['Rental Strategy']

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
            'rental_strategy': 'LTR',
            'str_months': 0,
        }
        cf, sheet = seller_fin_cf(params)

        assert len(cf) == 7 * 12
        assert 'Financed Amount' in sheet
        assert 'Rental Strategy' in sheet

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
            'rental_strategy': 'LTR',
            'str_months': 0,
        }
        cf, sheet = conventional_cf(params)

        # Last month should include sale proceeds (much larger than normal month)
        assert cf[-1] > cf[0] * 10  # Sale should be much larger than monthly CF


class TestGetRentalDescription:
    """Tests for rental description generation."""

    @pytest.fixture
    def mock_rental_globals(self):
        """Mock rental globals for description tests."""
        with patch.multiple(
            'subject_to_analyzer',
            ltr_rent=2000.0,
            ltr_growth=0.02,
            ltr_expense=0.35,
            ltr_vacancy=0.05,
            str_nightly=150.0,
            str_occupancy=0.65,
            str_growth=0.03,
            str_expense=0.50
        ):
            yield

    def test_ltr_description(self, mock_rental_globals):
        """Test LTR description contains correct info."""
        from subject_to_analyzer import get_rental_description

        desc = get_rental_description("LTR")

        assert desc["Rental Strategy"] == "Long-Term Rental (LTR)"
        assert "$2,000" in desc["Monthly Income"]
        assert "5%" in desc["Vacancy Rate"]

    def test_str_description(self, mock_rental_globals):
        """Test STR description contains correct info."""
        from subject_to_analyzer import get_rental_description

        desc = get_rental_description("STR")

        assert desc["Rental Strategy"] == "Short-Term Rental (STR)"
        assert "$150" in desc["Nightly Rate"]
        assert "65%" in desc["Occupancy Rate"]

    def test_hybrid_description(self, mock_rental_globals):
        """Test Hybrid description shows month split."""
        from subject_to_analyzer import get_rental_description

        desc = get_rental_description("Hybrid", str_months=4)

        assert "4mo STR" in desc["Rental Strategy"]
        assert "8mo LTR" in desc["Rental Strategy"]
