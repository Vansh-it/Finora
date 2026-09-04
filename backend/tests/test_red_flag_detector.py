"""Tests for red flag detection engine."""

import pytest
from lib.red_flag_detector import detect_red_flags


def _make_stmts(**overrides):
    """Build financial statements using period-keyed format (how _get_fact expects)."""
    base = {
        "income_statement": {
            "revenue": {
                "FY2023": {"value": 100e9, "period": "FY2023"},
                "FY2022": {"value": 90e9, "period": "FY2022"},
            },
            "gross_profit": {
                "FY2023": {"value": 40e9, "period": "FY2023"},
                "FY2022": {"value": 38e9, "period": "FY2022"},
            },
            "operating_income": {
                "FY2023": {"value": 25e9, "period": "FY2023"},
                "FY2022": {"value": 24e9, "period": "FY2022"},
            },
            "net_income": {
                "FY2023": {"value": 20e9, "period": "FY2023"},
                "FY2022": {"value": 18e9, "period": "FY2022"},
            },
            "cost_of_revenue": {
                "FY2023": {"value": 60e9, "period": "FY2023"},
                "FY2022": {"value": 52e9, "period": "FY2022"},
            },
        },
        "balance_sheet": {
            "accounts_receivable": {
                "FY2023": {"value": 15e9, "period": "FY2023"},
                "FY2022": {"value": 14e9, "period": "FY2022"},
            },
            "inventory": {
                "FY2023": {"value": 5e9, "period": "FY2023"},
                "FY2022": {"value": 4.5e9, "period": "FY2022"},
            },
            "total_assets": {
                "FY2023": {"value": 200e9, "period": "FY2023"},
                "FY2022": {"value": 180e9, "period": "FY2022"},
            },
            "current_assets": {
                "FY2023": {"value": 80e9, "period": "FY2023"},
                "FY2022": {"value": 75e9, "period": "FY2022"},
            },
            "current_liabilities": {
                "FY2023": {"value": 50e9, "period": "FY2023"},
                "FY2022": {"value": 48e9, "period": "FY2022"},
            },
            "long_term_debt": {
                "FY2023": {"value": 40e9, "period": "FY2023"},
                "FY2022": {"value": 38e9, "period": "FY2022"},
            },
        },
        "cash_flow": {
            "operating_cash_flow": {
                "FY2023": {"value": 30e9, "period": "FY2023"},
                "FY2022": {"value": 28e9, "period": "FY2022"},
            },
            "capital_expenditures": {
                "FY2023": {"value": 8e9, "period": "FY2023"},
                "FY2022": {"value": 7e9, "period": "FY2022"},
            },
        },
        "additional": {
            "diluted_shares": {
                "FY2023": {"value": 5e9, "period": "FY2023"},
                "FY2022": {"value": 4.8e9, "period": "FY2022"},
            },
        },
    }
    base.update(overrides)
    return base


class TestRedFlags:
    def test_no_flags_on_stable_data(self):
        """Stable, improving data should produce few/no high-severity flags."""
        stmts = _make_stmts()
        flags = detect_red_flags(stmts, "FY2023")
        high_flags = [f for f in flags if f.get("severity") == "high"]
        assert len(high_flags) == 0

    def test_receivables_growth_flag(self):
        """AR growing much faster than revenue should trigger flag."""
        stmts = _make_stmts()
        # Set AR to grow much faster than revenue (11% vs 42%)
        stmts["balance_sheet"]["accounts_receivable"]["FY2023"] = {"value": 25e9, "period": "FY2023"}
        flags = detect_red_flags(stmts, "FY2023")
        flag_ids = [f["id"] for f in flags]
        assert "receivables_growth_exceeds_revenue" in flag_ids

    def test_inventory_growth_flag(self):
        """Inventory growing much faster than revenue should trigger flag."""
        stmts = _make_stmts()
        # Set inventory to grow much faster than revenue (11% vs 122%)
        stmts["balance_sheet"]["inventory"]["FY2023"] = {"value": 15e9, "period": "FY2023"}
        flags = detect_red_flags(stmts, "FY2023")
        flag_ids = [f["id"] for f in flags]
        assert "inventory_growth_exceeds_revenue" in flag_ids

    def test_gross_margin_deterioration(self):
        """Declining gross margin should trigger flag."""
        stmts = _make_stmts()
        # Current GM: 30/100 = 30%, Prior GM: 38/90 = 42.2%
        stmts["income_statement"]["gross_profit"]["FY2023"] = {"value": 30e9, "period": "FY2023"}
        flags = detect_red_flags(stmts, "FY2023")
        flag_ids = [f["id"] for f in flags]
        assert "gross_margin_deterioration" in flag_ids

    def test_operating_margin_deterioration(self):
        """Declining operating margin should trigger flag."""
        stmts = _make_stmts()
        # Current OM: 10/100 = 10%, Prior OM: 24/90 = 26.7%
        stmts["income_statement"]["operating_income"]["FY2023"] = {"value": 10e9, "period": "FY2023"}
        flags = detect_red_flags(stmts, "FY2023")
        flag_ids = [f["id"] for f in flags]
        assert "operating_margin_deterioration" in flag_ids

    def test_share_dilution_flag(self):
        """Shares increasing >3% should trigger flag."""
        stmts = _make_stmts()
        # Current: 6e9, Prior: 4.8e9 → 25% dilution
        stmts["additional"]["diluted_shares"]["FY2023"] = {"value": 6e9, "period": "FY2023"}
        flags = detect_red_flags(stmts, "FY2023")
        flag_ids = [f["id"] for f in flags]
        assert "share_dilution" in flag_ids

    def test_leverage_increase(self):
        """LTD increasing relative to assets should trigger flag."""
        stmts = _make_stmts()
        # Current LTD/TA: 70/200 = 35%, Prior: 38/180 = 21.1% → +13.9pp
        stmts["balance_sheet"]["long_term_debt"]["FY2023"] = {"value": 70e9, "period": "FY2023"}
        flags = detect_red_flags(stmts, "FY2023")
        flag_ids = [f["id"] for f in flags]
        assert "leverage_increase" in flag_ids

    def test_piotroski_weak_flag(self):
        """Weak Piotroski score should be flagged."""
        forensic_scores = {"piotroski": {"score": 2, "status": "WEAK"}}
        stmts = _make_stmts()
        flags = detect_red_flags(stmts, "FY2023", forensic_scores)
        flag_ids = [f["id"] for f in flags]
        assert "weak_piotroski" in flag_ids

    def test_altman_distress_flag(self):
        """Low Altman Z should be flagged."""
        forensic_scores = {"altman": {"score": 1.2, "status": "DISTRESS ZONE"}}
        stmts = _make_stmts()
        flags = detect_red_flags(stmts, "FY2023", forensic_scores)
        flag_ids = [f["id"] for f in flags]
        assert "altman_distress_signal" in flag_ids

    def test_missing_data_graceful(self):
        """Missing data should not crash."""
        stmts = {"income_statement": {}, "balance_sheet": {}, "cash_flow": {}, "additional": {}}
        flags = detect_red_flags(stmts, "FY2023")
        assert isinstance(flags, list)

    def test_flag_structure(self):
        """Each flag should have required fields."""
        stmts = _make_stmts()
        stmts["additional"]["diluted_shares"]["FY2023"] = {"value": 6e9, "period": "FY2023"}
        flags = detect_red_flags(stmts, "FY2023")
        for flag in flags:
            assert "id" in flag
            assert "category" in flag
            assert "severity" in flag
            assert "headline" in flag
            assert "description" in flag
            assert "period" in flag
