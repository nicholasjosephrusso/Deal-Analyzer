import numpy_financial as nf
import pytest
from subject_to_analyzer import build_metrics


def test_build_metrics_simple_case():
    irr, roi = build_metrics(1000, [1100])
    expected_monthly = nf.irr([-1000, 1100])
    expected_annual = (1 + expected_monthly) ** 12 - 1
    expected_roi = 1100 / 1000
    assert irr == pytest.approx(expected_annual, rel=1e-6)
    assert roi == pytest.approx(expected_roi, rel=1e-6)
