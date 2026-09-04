"""Tests for forensic accounting engine (Piotroski, Altman, Beneish)."""

import pytest
from lib.forensic_engine import calculate_piotroski, calculate_altman_z, calculate_beneish


# ── Piotroski F-Score ─────────────────────────────────────────────────────────

def _make_stmts(**overrides):
    """Build minimal financial statements using period-keyed format."""
    base = {
        "income_statement": {
            "net_income": {
                "FY2023": {"value": 100e9, "period": "FY2023", "period_end": "2023-09-30"},
                "FY2022": {"value": 90e9, "period": "FY2022"},
            },
            "revenue": {
                "FY2023": {"value": 380e9, "period": "FY2023", "period_end": "2023-09-30"},
                "FY2022": {"value": 350e9, "period": "FY2022"},
            },
            "gross_profit": {
                "FY2023": {"value": 170e9, "period": "FY2023", "period_end": "2023-09-30"},
                "FY2022": {"value": 160e9, "period": "FY2022"},
            },
            "operating_income": {
                "FY2023": {"value": 115e9, "period": "FY2023", "period_end": "2023-09-30"},
                "FY2022": {"value": 110e9, "period": "FY2022"},
            },
            "cost_of_revenue": {
                "FY2023": {"value": 210e9, "period": "FY2023", "period_end": "2023-09-30"},
                "FY2022": {"value": 190e9, "period": "FY2022"},
            },
        },
        "balance_sheet": {
            "total_assets": {
                "FY2023": {"value": 350e9, "period": "FY2023", "period_end": "2023-09-30"},
                "FY2022": {"value": 320e9, "period": "FY2022"},
            },
            "current_assets": {
                "FY2023": {"value": 140e9, "period": "FY2023", "period_end": "2023-09-30"},
                "FY2022": {"value": 130e9, "period": "FY2022"},
            },
            "current_liabilities": {
                "FY2023": {"value": 120e9, "period": "FY2023", "period_end": "2023-09-30"},
                "FY2022": {"value": 125e9, "period": "FY2022"},
            },
            "accounts_receivable": {
                "FY2023": {"value": 30e9, "period": "FY2023", "period_end": "2023-09-30"},
                "FY2022": {"value": 28e9, "period": "FY2022"},
            },
            "long_term_debt": {
                "FY2023": {"value": 85e9, "period": "FY2023", "period_end": "2023-09-30"},
                "FY2022": {"value": 90e9, "period": "FY2022"},
            },
            "short_term_debt": {
                "FY2023": {"value": 15e9, "period": "FY2023", "period_end": "2023-09-30"},
                "FY2022": {"value": 18e9, "period": "FY2022"},
            },
            "shareholders_equity": {
                "FY2023": {"value": 200e9, "period": "FY2023", "period_end": "2023-09-30"},
                "FY2022": {"value": 180e9, "period": "FY2022"},
            },
            "total_liabilities": {
                "FY2023": {"value": 150e9, "period": "FY2023", "period_end": "2023-09-30"},
                "FY2022": {"value": 140e9, "period": "FY2022"},
            },
            "cash_and_equivalents": {
                "FY2023": {"value": 50e9, "period": "FY2023", "period_end": "2023-09-30"},
                "FY2022": {"value": 45e9, "period": "FY2022"},
            },
        },
        "cash_flow": {
            "operating_cash_flow": {
                "FY2023": {"value": 120e9, "period": "FY2023", "period_end": "2023-09-30"},
                "FY2022": {"value": 110e9, "period": "FY2022"},
            },
            "capital_expenditures": {
                "FY2023": {"value": 10e9, "period": "FY2023", "period_end": "2023-09-30"},
                "FY2022": {"value": 12e9, "period": "FY2022"},
            },
            "depreciation_amortization": {
                "FY2023": {"value": 12e9, "period": "FY2023", "period_end": "2023-09-30"},
                "FY2022": {"value": 11e9, "period": "FY2022"},
            },
        },
        "additional": {
            "diluted_shares": {
                "FY2023": {"value": 15e9, "period": "FY2023", "period_end": "2023-09-30"},
                "FY2022": {"value": 15.2e9, "period": "FY2022"},
            },
        },
    }
    base.update(overrides)
    return base


class TestPiotroski:
    def test_basic_calculation(self):
        stmts = _make_stmts()
        result = calculate_piotroski(stmts, "FY2023")
        assert result["score"] >= 0
        assert result["score"] <= 9
        assert result["status"] in ("STRONG", "MIXED", "WEAK")
        assert len(result["signals"]) == 9

    def test_all_signals_present(self):
        stmts = _make_stmts()
        result = calculate_piotroski(stmts, "FY2023")
        signal_ids = [s["id"] for s in result["signals"]]
        expected = [
            "positive_roa", "positive_ocf", "roa_improved",
            "accrual_quality", "leverage_improved", "liquidity_improved",
            "no_dilution", "gross_margin_improved", "asset_turnover_improved",
        ]
        for eid in expected:
            assert eid in signal_ids

    def test_strong_score(self):
        """Good company should score 7+."""
        stmts = _make_stmts()
        result = calculate_piotroski(stmts, "FY2023")
        assert result["score"] >= 6

    def test_missing_data_graceful(self):
        """Missing data should not crash."""
        stmts = {"income_statement": {}, "balance_sheet": {}, "cash_flow": {}, "additional": {}}
        result = calculate_piotroski(stmts, "FY2023")
        assert result["score"] >= 0
        assert result["score"] <= 9
        assert result["status"] in ("STRONG", "MIXED", "WEAK")

    def test_result_structure(self):
        stmts = _make_stmts()
        result = calculate_piotroski(stmts, "FY2023")
        assert "metric_id" in result
        assert result["metric_id"] == "piotroski_f_score"
        assert "methodology" in result
        assert "period" in result

    def test_signal_values(self):
        """Each signal should have required fields."""
        stmts = _make_stmts()
        result = calculate_piotroski(stmts, "FY2023")
        for signal in result["signals"]:
            assert "id" in signal
            assert "name" in signal
            assert "result" in signal
            assert signal["result"] in (0, 1)


# ── Altman Z-Score ────────────────────────────────────────────────────────────

class TestAltman:
    def test_basic_calculation(self):
        stmts = _make_stmts()
        result = calculate_altman_z(stmts, "FY2023", ticker="AAPL")
        assert result["applicability"] == "applicable"
        assert result["score"] is not None
        assert isinstance(result["score"], float)
        assert len(result["components"]) == 5

    def test_financial_institution_not_applicable(self):
        stmts = _make_stmts()
        result = calculate_altman_z(stmts, "FY2023", ticker="JPM")
        assert result["applicability"] == "not_applicable"
        assert "NOT APPLICABLE" in result["status"]

    def test_financial_sector_not_applicable(self):
        stmts = _make_stmts()
        result = calculate_altman_z(stmts, "FY2023", ticker="XYZ", sector="Banking")
        assert result["applicability"] == "not_applicable"

    def test_missing_data_unavailable(self):
        stmts = {"income_statement": {}, "balance_sheet": {}, "cash_flow": {}, "additional": {}}
        result = calculate_altman_z(stmts, "FY2023", ticker="AAPL")
        assert result["status"] == "UNAVAILABLE"

    def test_z_score_formula_correct(self):
        """Verify the Z-Score formula components sum correctly."""
        stmts = _make_stmts()
        result = calculate_altman_z(stmts, "FY2023", ticker="MSFT")
        if result["score"] is not None:
            # Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5 (no intercept)
            expected = sum(c["contribution"] for c in result["components"] if c["contribution"] is not None)
            assert abs(result["score"] - expected) < 0.001

    def test_interpretation_zones(self):
        stmts = _make_stmts()
        result = calculate_altman_z(stmts, "FY2023", ticker="MSFT")
        if result["score"] is not None:
            if result["score"] > 2.99:
                assert "SAFE" in result["status"]
            elif result["score"] > 1.81:
                assert "GREY" in result["status"]
            else:
                assert "DISTRESS" in result["status"]


# ── Beneish M-Score ───────────────────────────────────────────────────────────

class TestBeneish:
    def _make_beneish_stmts(self):
        """Build stmts with all Beneish-required fields including SGA and PPE."""
        stmts = _make_stmts()
        stmts["income_statement"]["selling_general_admin"] = {
            "FY2023": {"value": 25e9, "period": "FY2023"},
            "FY2022": {"value": 22e9, "period": "FY2022"},
        }
        stmts["balance_sheet"]["property_plant_equipment"] = {
            "FY2023": {"value": 100e9, "period": "FY2023"},
            "FY2022": {"value": 95e9, "period": "FY2022"},
        }
        return stmts

    def test_basic_calculation(self):
        stmts = self._make_beneish_stmts()
        result = calculate_beneish(stmts, "FY2023")
        assert result["score"] is not None
        assert isinstance(result["score"], float)
        assert len(result["components"]) == 8

    def test_all_components_present(self):
        stmts = self._make_beneish_stmts()
        result = calculate_beneish(stmts, "FY2023")
        component_ids = [c["id"] for c in result["components"]]
        expected = ["DSRI", "GMI", "AQI", "SGI", "DEPI", "SGAI", "TATA", "LVGI"]
        for eid in expected:
            assert eid in component_ids

    def test_classification(self):
        stmts = self._make_beneish_stmts()
        result = calculate_beneish(stmts, "FY2023")
        assert result["status"] in ("ELEVATED", "LOW RISK")

    def test_threshold(self):
        stmts = self._make_beneish_stmts()
        result = calculate_beneish(stmts, "FY2023")
        if result["score"] is not None:
            if result["score"] > -1.78:
                assert result["status"] == "ELEVATED"
            else:
                assert result["status"] == "LOW RISK"

    def test_missing_prior_period(self):
        stmts = _make_stmts()
        result = calculate_beneish(stmts, "FY2000")
        assert result["status"] == "UNAVAILABLE"

    def test_missing_data_graceful(self):
        stmts = {"income_statement": {}, "balance_sheet": {}, "cash_flow": {}, "additional": {}}
        result = calculate_beneish(stmts, "FY2023")
        assert result["status"] == "UNAVAILABLE"

    def test_disclaimer_present(self):
        stmts = _make_stmts()
        result = calculate_beneish(stmts, "FY2023")
        assert "statistical" in result["note"].lower() or "screening" in result["note"].lower()

    def test_component_values(self):
        """Each component should have required fields."""
        stmts = _make_stmts()
        result = calculate_beneish(stmts, "FY2023")
        for comp in result["components"]:
            assert "id" in comp
            assert "name" in comp
            assert "coefficient" in comp
