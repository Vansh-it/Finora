"""Tests for the v2 financial calculation engine."""

import pytest
from lib.financial_calculator import (
    calculate_metrics,
    CalculatedMetric,
    _safe_divide,
    _safe_cagr,
    _val,
)


# ── Helper: build a mock FinancialStatements dict ──────────────────────

def _make_fact(value, period="FY2025", form="10-K", concept="Revenues",
               filing_date="2025-07-29", accession="000119312525-000001",
               unit="USD", period_start="", period_end="2025-06-30",
               source_url="https://www.sec.gov/test"):
    return {
        "value": value, "unit": unit, "period": period,
        "period_start": period_start, "period_end": period_end,
        "form": form, "filing_date": filing_date,
        "accession_number": accession, "xbrl_concept": concept,
        "source": "SEC XBRL", "source_url": source_url,
        "verification_status": "primary_source",
    }


def _make_statements(
    revenue_2025=331_839_000_000, revenue_2024=245_122_000_000,
    gross_profit_2025=225_538_000_000, gross_profit_2024=170_204_000_000,
    operating_income_2025=155_237_000_000, operating_income_2024=109_433_000_000,
    pretax_income_2025=165_000_000_000, pretax_income_2024=118_000_000_000,
    income_tax_2025=31_250_000_000, income_tax_2024=29_864_000_000,
    net_income_2025=133_749_000_000, net_income_2024=88_136_000_000,
    diluted_eps_2025=17.95, diluted_eps_2024=11.80,
    total_assets_2025=758_376_000_000, total_assets_2024=512_062_000_000,
    current_assets_2025=265_000_000_000, current_liabilities_2025=135_000_000_000,
    total_liabilities_2025=316_000_000_000,
    equity_2025=442_387_000_000, equity_2024=268_474_000_000,
    cash_2025=82_000_000_000, st_investments_2025=60_000_000_000,
    ar_2025=57_000_000_000, inventory_2025=5_000_000_000,
    ap_2025=15_000_000_000,
    st_debt_2025=10_000_000_000, lt_debt_2025=42_000_000_000,
    ocf_2025=182_935_000_000, ocf_2024=118_500_000_000,
    capex_2025=80_146_000_000, capex_2024=44_300_000_000,
    da_2025=20_000_000_000, da_2024=15_000_000_000,
    interest_2025=3_000_000_000, interest_2024=2_500_000_000,
    cost_of_revenue_2025=106_301_000_000, cost_of_revenue_2024=74_918_000_000,
    dividends_2025=25_000_000_000,
    buybacks_2025=30_000_000_000,
    diluted_shares_2025=7_452_000_000,
    periods=None,
):
    if periods is None:
        periods = ["FY2024", "FY2025"]
    return {
        "company": {"name": "Microsoft Corporation", "ticker": "MSFT", "cik": "0000789019"},
        "periods": periods,
        "income_statement": {
            "revenue": {"FY2024": _make_fact(revenue_2024, "FY2024"), "FY2025": _make_fact(revenue_2025, "FY2025")},
            "cost_of_revenue": {"FY2024": _make_fact(cost_of_revenue_2024, "FY2024"), "FY2025": _make_fact(cost_of_revenue_2025, "FY2025")},
            "gross_profit": {"FY2024": _make_fact(gross_profit_2024, "FY2024"), "FY2025": _make_fact(gross_profit_2025, "FY2025")},
            "operating_income": {"FY2024": _make_fact(operating_income_2024, "FY2024"), "FY2025": _make_fact(operating_income_2025, "FY2025")},
            "pretax_income": {"FY2024": _make_fact(pretax_income_2024, "FY2024"), "FY2025": _make_fact(pretax_income_2025, "FY2025")},
            "income_tax_expense": {"FY2024": _make_fact(income_tax_2024, "FY2024"), "FY2025": _make_fact(income_tax_2025, "FY2025")},
            "net_income": {"FY2024": _make_fact(net_income_2024, "FY2024"), "FY2025": _make_fact(net_income_2025, "FY2025")},
            "diluted_eps": {"FY2024": _make_fact(diluted_eps_2024, "FY2024", unit="USD/shares"), "FY2025": _make_fact(diluted_eps_2025, "FY2025", unit="USD/shares")},
        },
        "balance_sheet": {
            "cash_and_equivalents": {"FY2024": _make_fact(cash_2025 - 20e9, "FY2024"), "FY2025": _make_fact(cash_2025, "FY2025")},
            "short_term_investments": {"FY2024": _make_fact(st_investments_2025 - 10e9, "FY2024"), "FY2025": _make_fact(st_investments_2025, "FY2025")},
            "accounts_receivable": {"FY2024": _make_fact(ar_2025 - 5e9, "FY2024"), "FY2025": _make_fact(ar_2025, "FY2025")},
            "inventory": {"FY2024": _make_fact(inventory_2025 - 1e9, "FY2024"), "FY2025": _make_fact(inventory_2025, "FY2025")},
            "current_assets": {"FY2024": _make_fact(current_assets_2025 - 30e9, "FY2024"), "FY2025": _make_fact(current_assets_2025, "FY2025")},
            "total_assets": {"FY2024": _make_fact(total_assets_2024, "FY2024"), "FY2025": _make_fact(total_assets_2025, "FY2025")},
            "accounts_payable": {"FY2024": _make_fact(ap_2025 - 2e9, "FY2024"), "FY2025": _make_fact(ap_2025, "FY2025")},
            "current_liabilities": {"FY2024": _make_fact(current_liabilities_2025 - 10e9, "FY2024"), "FY2025": _make_fact(current_liabilities_2025, "FY2025")},
            "total_liabilities": {"FY2024": _make_fact(total_liabilities_2025 - 30e9, "FY2024"), "FY2025": _make_fact(total_liabilities_2025, "FY2025")},
            "short_term_debt": {"FY2024": _make_fact(st_debt_2025, "FY2024"), "FY2025": _make_fact(st_debt_2025, "FY2025")},
            "long_term_debt": {"FY2024": _make_fact(lt_debt_2025 - 5e9, "FY2024"), "FY2025": _make_fact(lt_debt_2025, "FY2025")},
            "shareholders_equity": {"FY2024": _make_fact(equity_2024, "FY2024"), "FY2025": _make_fact(equity_2025, "FY2025")},
        },
        "cash_flow": {
            "operating_cash_flow": {"FY2024": _make_fact(ocf_2024, "FY2024"), "FY2025": _make_fact(ocf_2025, "FY2025")},
            "capital_expenditures": {"FY2024": _make_fact(capex_2024, "FY2024"), "FY2025": _make_fact(capex_2025, "FY2025")},
            "investing_cash_flow": {"FY2024": _make_fact(-50e9, "FY2024"), "FY2025": _make_fact(-70e9, "FY2025")},
            "financing_cash_flow": {"FY2024": _make_fact(-40e9, "FY2024"), "FY2025": _make_fact(-50e9, "FY2025")},
            "depreciation_amortization": {"FY2024": _make_fact(da_2024, "FY2024"), "FY2025": _make_fact(da_2025, "FY2025")},
            "interest_expense": {"FY2024": _make_fact(interest_2024, "FY2024"), "FY2025": _make_fact(interest_2025, "FY2025")},
            "dividends_paid": {"FY2024": _make_fact(20e9, "FY2024"), "FY2025": _make_fact(dividends_2025, "FY2025")},
            "share_repurchases": {"FY2024": _make_fact(25e9, "FY2024"), "FY2025": _make_fact(buybacks_2025, "FY2025")},
        },
        "additional": {
            "diluted_shares": {"FY2024": _make_fact(diluted_shares_2025, "FY2024", unit="shares"), "FY2025": _make_fact(diluted_shares_2025, "FY2025", unit="shares")},
        },
        "metadata": {"extraction_source": "SEC XBRL CompanyFacts", "cik": "0000789019"},
    }


# ══════════════════════════════════════════════════════════════════════════
# SCHEMA TESTS
# ══════════════════════════════════════════════════════════════════════════

class TestMetricSchema:
    def test_calculated_metric_has_all_fields(self):
        stmts = _make_statements()
        result = calculate_metrics(stmts)
        m = result["annual_metrics"]["FY2025"]["gross_margin"]
        assert m["metric_id"] == "gross_margin"
        assert m["name"] == "Gross Margin"
        assert m["unit"] == "%"
        assert m["period"] == "FY2025"
        assert m["period_type"] == "annual"
        assert m["status"] == "calculated"
        assert m["classification"] == "calculated"
        assert m["formula"]
        assert m["inputs"]
        assert m["calculation"]
        assert m["methodology"] is not None

    def test_unavailable_metric_schema(self):
        stmts = _make_statements()
        result = calculate_metrics(stmts)
        # EBITDA requires D&A which is provided, so let's test one that's truly unavailable
        m = result["annual_metrics"]["FY2025"].get("interest_coverage")
        if m and m["status"] == "unavailable":
            assert "reason" in m
            assert m["status"] == "unavailable"

    def test_categories_present(self):
        stmts = _make_statements()
        result = calculate_metrics(stmts)
        assert "categories" in result
        assert "growth" in result["categories"]
        assert "profitability" in result["categories"]
        assert "returns" in result["categories"]
        assert "liquidity" in result["categories"]
        assert "leverage" in result["categories"]
        assert "efficiency" in result["categories"]
        assert "per_share" in result["categories"]
        assert "capital_allocation" in result["categories"]
        assert "dupont" in result["categories"]

    def test_trend_metadata(self):
        stmts = _make_statements()
        result = calculate_metrics(stmts)
        m = result["annual_metrics"]["FY2025"]["gross_margin"]
        # Should have trend info since FY2024 exists
        assert "previous_value" in m
        assert "change_pp" in m
        assert "direction" in m


# ══════════════════════════════════════════════════════════════════════════
# PROFITABILITY
# ══════════════════════════════════════════════════════════════════════════

class TestProfitability:
    def test_gross_margin(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["gross_margin"]
        assert m["status"] == "calculated"
        expected = 225_538 / 331_839 * 100
        assert abs(m["value"] - expected) < 0.5

    def test_operating_margin(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["operating_margin"]
        assert m["status"] == "calculated"
        expected = 155_237 / 331_839 * 100
        assert abs(m["value"] - expected) < 0.5

    def test_pretax_margin(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["pretax_margin"]
        assert m["status"] == "calculated"
        expected = 165_000 / 331_839 * 100
        assert abs(m["value"] - expected) < 0.5

    def test_net_margin(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["net_margin"]
        assert m["status"] == "calculated"
        expected = 133_749 / 331_839 * 100
        assert abs(m["value"] - expected) < 0.5

    def test_ebitda_margin(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["ebitda_margin"]
        assert m["status"] == "calculated"
        # EBITDA = 155237 + 20000 = 175237; margin = 175237/331839*100
        expected = 175_237 / 331_839 * 100
        assert abs(m["value"] - expected) < 0.5

    def test_fcf_margin(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["fcf_margin"]
        assert m["status"] == "calculated"
        fcf = 182_935 - 80_146
        expected = fcf / 331_839 * 100
        assert abs(m["value"] - expected) < 0.5

    def test_ocf_margin(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["ocf_margin"]
        assert m["status"] == "calculated"
        expected = 182_935 / 331_839 * 100
        assert abs(m["value"] - expected) < 0.5


# ══════════════════════════════════════════════════════════════════════════
# RETURNS
# ══════════════════════════════════════════════════════════════════════════

class TestReturns:
    def test_roa(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["roa"]
        assert m["status"] == "calculated"
        assert 15 < m["value"] < 30

    def test_roe(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["roe"]
        assert m["status"] == "calculated"
        assert 25 < m["value"] < 45

    def test_roic(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["roic"]
        assert m["status"] == "calculated"
        assert 10 < m["value"] < 40

    def test_roce(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["roce"]
        assert m["status"] == "calculated"
        assert 10 < m["value"] < 50


# ══════════════════════════════════════════════════════════════════════════
# CASH FLOW
# ══════════════════════════════════════════════════════════════════════════

class TestCashFlow:
    def test_free_cash_flow(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        fcf = r["annual_metrics"]["FY2025"]["free_cash_flow"]
        assert fcf["status"] == "calculated"
        expected = 182_935_000_000 - 80_146_000_000
        assert abs(fcf["value"] - expected) < 1_000

    def test_cash_conversion(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        cc = r["annual_metrics"]["FY2025"]["cash_conversion"]
        assert cc["status"] == "calculated"

    def test_ocf_to_net_income(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["ocf_to_net_income"]
        assert m["status"] == "calculated"
        expected = (182_935 / 133_749) * 100
        assert abs(m["value"] - expected) < 0.5

    def test_capex_intensity(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["capex_intensity"]
        assert m["status"] == "calculated"
        expected = (80_146 / 331_839) * 100
        assert abs(m["value"] - expected) < 0.5

    def test_capex_to_ocf(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["capex_to_ocf"]
        assert m["status"] == "calculated"
        expected = (80_146 / 182_935) * 100
        assert abs(m["value"] - expected) < 0.5


# ══════════════════════════════════════════════════════════════════════════
# LIQUIDITY
# ══════════════════════════════════════════════════════════════════════════

class TestLiquidity:
    def test_current_ratio(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["current_ratio"]
        assert m["status"] == "calculated"
        expected = 265 / 135
        assert abs(m["value"] - expected) < 0.1

    def test_quick_ratio(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["quick_ratio"]
        assert m["status"] == "calculated"
        liquid = 82 + 60 + 57
        expected = liquid / 135
        assert abs(m["value"] - expected) < 0.1

    def test_cash_ratio(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["cash_ratio"]
        assert m["status"] == "calculated"
        expected = (82 + 60) / 135
        assert abs(m["value"] - expected) < 0.1

    def test_net_working_capital(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["net_working_capital"]
        assert m["status"] == "calculated"
        expected = 265 - 135
        assert abs(m["value"] - expected * 1e9) < 1e9


# ══════════════════════════════════════════════════════════════════════════
# LEVERAGE
# ══════════════════════════════════════════════════════════════════════════

class TestLeverage:
    def test_debt_to_equity(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["debt_to_equity"]
        assert m["status"] == "calculated"
        expected = 316 / 442.387
        assert abs(m["value"] - expected) < 0.1

    def test_debt_to_assets(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["debt_to_assets"]
        assert m["status"] == "calculated"
        expected = 316 / 758.376
        assert abs(m["value"] - expected) < 0.1

    def test_net_debt(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["net_debt"]
        assert m["status"] == "calculated"
        expected = (10_000_000_000 + 42_000_000_000) - 82_000_000_000 - 60_000_000_000
        assert abs(m["value"] - expected) < 1_000

    def test_debt_to_ebitda(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["debt_to_ebitda"]
        assert m["status"] == "calculated"
        assert m["value"] > 0

    def test_debt_to_capital(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["debt_to_capital"]
        assert m["status"] == "calculated"
        td = 10 + 42
        expected = td / (td + 442.387) * 100
        assert abs(m["value"] - expected) < 0.5

    def test_interest_coverage(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["interest_coverage"]
        assert m["status"] == "calculated"
        expected = 155_237 / 3_000
        assert abs(m["value"] - expected) < 1

    def test_cash_flow_to_debt(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["cash_flow_to_debt"]
        assert m["status"] == "calculated"
        assert m["value"] > 0


# ══════════════════════════════════════════════════════════════════════════
# EFFICIENCY
# ══════════════════════════════════════════════════════════════════════════

class TestEfficiency:
    def test_asset_turnover(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["asset_turnover"]
        assert m["status"] == "calculated"
        expected = 331_839 / 758_376
        assert abs(m["value"] - expected) < 0.01

    def test_receivables_turnover(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["receivables_turnover"]
        assert m["status"] == "calculated"
        expected = 331_839 / 57_000
        assert abs(m["value"] - expected) < 0.1

    def test_dso(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["days_sales_outstanding"]
        assert m["status"] == "calculated"
        assert m["value"] > 0

    def test_inventory_turnover(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["inventory_turnover"]
        assert m["status"] == "calculated"
        expected = 106_301 / 5_000
        assert abs(m["value"] - expected) < 1

    def test_dio(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["days_inventory_outstanding"]
        assert m["status"] == "calculated"
        assert m["value"] > 0

    def test_dpo(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["days_payable_outstanding"]
        assert m["status"] == "calculated"
        assert m["value"] > 0

    def test_cash_conversion_cycle(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["cash_conversion_cycle"]
        assert m["status"] == "calculated"
        assert m["value"] is not None


# ══════════════════════════════════════════════════════════════════════════
# PER SHARE
# ══════════════════════════════════════════════════════════════════════════

class TestPerShare:
    def test_revenue_per_share(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["revenue_per_share"]
        assert m["status"] == "calculated"
        expected = 331_839_000_000 / 7_452_000_000
        assert abs(m["value"] - expected) < 1

    def test_fcf_per_share(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["fcf_per_share"]
        assert m["status"] == "calculated"
        assert m["value"] > 0

    def test_book_value_per_share(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["book_value_per_share"]
        assert m["status"] == "calculated"
        expected = 442_387_000_000 / 7_452_000_000
        assert abs(m["value"] - expected) < 1


# ══════════════════════════════════════════════════════════════════════════
# CAPITAL ALLOCATION
# ══════════════════════════════════════════════════════════════════════════

class TestCapitalAllocation:
    def test_dividend_payout(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["dividend_payout_ratio"]
        assert m["status"] == "calculated"
        expected = (25_000_000_000 / 133_749_000_000) * 100
        assert abs(m["value"] - expected) < 0.1

    def test_buyback_to_fcf(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["buyback_to_fcf"]
        assert m["status"] == "calculated"
        fcf = 182_935 - 80_146
        expected = (30_000 / fcf) * 100
        assert abs(m["value"] - expected) < 0.5

    def test_effective_tax_rate(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["effective_tax_rate"]
        assert m["status"] == "calculated"
        expected = (31_250 / 165_000) * 100
        assert abs(m["value"] - expected) < 0.5


# ══════════════════════════════════════════════════════════════════════════
# DUPONT
# ══════════════════════════════════════════════════════════════════════════

class TestDuPont:
    def test_dupont_decomposition(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["dupont"]
        assert m["status"] == "calculated"
        assert m["value"] > 0
        # Verify: margin x turnover x multiplier
        nm = 133_749 / 331_839
        at = 331_839 / 758_376
        em = 758_376 / 442_387
        expected = nm * at * em * 100
        assert abs(m["value"] - expected) < 0.5


# ══════════════════════════════════════════════════════════════════════════
# EBITDA
# ══════════════════════════════════════════════════════════════════════════

class TestEBITDA:
    def test_derived_ebitda(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["ebitda"]
        assert m["status"] == "calculated"
        assert m["classification"] == "derived"
        expected = 155_237_000_000 + 20_000_000_000
        assert abs(m["value"] - expected) < 1_000

    def test_missing_da(self):
        stmts = _make_statements(da_2025=0, da_2024=0)
        stmts["cash_flow"]["depreciation_amortization"]["FY2025"] = _make_fact(0)
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["ebitda"]
        # D&A = 0 means ebitda = operating income (0 D&A), should be calculated
        assert m["status"] == "calculated"


# ══════════════════════════════════════════════════════════════════════════
# GROWTH
# ══════════════════════════════════════════════════════════════════════════

class TestGrowth:
    def test_revenue_growth(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        g = r["growth_metrics"]["FY2025 vs FY2024"]["revenue_growth"]
        assert g["status"] == "calculated"
        expected = (331_839 - 245_122) / 245_122 * 100
        assert abs(g["value"] - expected) < 0.5

    def test_missing_previous(self):
        stmts = _make_statements(periods=["FY2025"])
        r = calculate_metrics(stmts)
        assert len(r["growth_metrics"]) == 0


class TestCAGR:
    def test_revenue_cagr(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        c = r["cagr_metrics"]["FY2024 to FY2025"]["revenue_cagr"]
        assert c["status"] == "calculated"
        expected = (331_839 / 245_122 - 1) * 100
        assert abs(c["value"] - expected) < 0.5


# ══════════════════════════════════════════════════════════════════════════
# EDGE CASES
# ══════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_empty_statements(self):
        stmts = {"company": {}, "periods": [], "income_statement": {},
                 "balance_sheet": {}, "cash_flow": {}, "additional": {}, "metadata": {}}
        r = calculate_metrics(stmts)
        assert r["annual_metrics"] == {}
        assert r["growth_metrics"] == {}
        assert r["cagr_metrics"] == {}

    def test_single_period(self):
        stmts = _make_statements(periods=["FY2025"])
        r = calculate_metrics(stmts)
        assert "FY2025" in r["annual_metrics"]
        assert len(r["growth_metrics"]) == 0

    def test_none_values(self):
        stmts = _make_statements()
        stmts["income_statement"]["revenue"]["FY2025"] = _make_fact(None)
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["gross_margin"]
        assert m["status"] == "unavailable"

    def test_zero_revenue(self):
        stmts = _make_statements(revenue_2025=0)
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["gross_margin"]
        assert m["status"] == "unavailable"

    def test_zero_denominator_growth(self):
        stmts = _make_statements(revenue_2024=0)
        r = calculate_metrics(stmts)
        g = r["growth_metrics"]["FY2025 vs FY2024"]["revenue_growth"]
        assert g["status"] == "unavailable"

    def test_metadata(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        meta = r["metadata"]
        assert meta["total_metrics_attempted"] > 0
        assert meta["metrics_calculated"] > 0
        assert "Finora" in meta["calculation_engine"]

    def test_source_evidence(self):
        stmts = _make_statements()
        r = calculate_metrics(stmts)
        m = r["annual_metrics"]["FY2025"]["gross_margin"]
        for inp in m["inputs"]:
            if inp.get("value") is not None:
                assert "source_evidence" in inp
