"""XBRL concept normalization layer.

Maps US-GAAP XBRL concepts to normalized Finora financial metrics.
Different companies may use different XBRL tags for the same metric.
This module provides a controlled alias system for each supported metric.
"""

from __future__ import annotations

from typing import Any, Optional


# ── XBRL concept aliases ─────────────────────────────────────────────────────
# Each Finora metric maps to a list of valid US-GAAP XBRL concepts,
# ordered by preference (most specific first).

INCOME_STATEMENT_CONCEPTS: dict[str, list[str]] = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "OperatingRevenue",
        "NetRevenues",
        "TotalRevenue",
        "SalesRevenueGoodsNet",
        "SalesRevenueServicesNet",
    ],
    "cost_of_revenue": [
        "CostOfRevenue",
        "CostOfGoodsAndServicesSold",
        "CostOfGoodsSold",
        "CostOfSales",
        "CostOfRevenueExcludingDepreciationAndAmortization",
        "CostOfGoodsSoldAndOperatingExpensesExcludingDepreciation",
    ],
    "gross_profit": [
        "GrossProfit",
    ],
    "operating_income": [
        "OperatingIncomeLoss",
    ],
    "pretax_income": [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxes",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesAndDiscontinuedOperations",
    ],
    "income_tax_expense": [
        "IncomeTaxExpenseBenefit",
        "IncomeTaxes",
        "FederalIncomeTaxExpense",
        "IncomeTaxExpenseBenefitOtherThanFederalIncomeTax",
    ],
    "net_income": [
        "NetIncomeLoss",
        "ProfitLoss",
        "NetIncomeLossAttributableToParent",
        "NetIncomeLossAttributableToNoncontrollingInterest",
    ],
    "diluted_eps": [
        "EarningsPerShareDiluted",
        "EarningsPerShareBasicAndDiluted",
    ],
    "basic_eps": [
        "EarningsPerShareBasic",
        "EarningsPerShareBasicAndDiluted",
    ],
}

BALANCE_SHEET_CONCEPTS: dict[str, list[str]] = {
    "cash_and_equivalents": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "CashAndCashEquivalents",
        "CashCashEquivalentsAndShortTermInvestments",
    ],
    "short_term_investments": [
        "ShortTermInvestments",
        "MarketableSecuritiesCurrent",
        "AvailableForSaleSecuritiesCurrent",
        "InvestmentsCurrent",
        "MarketableSecurities",
    ],
    "accounts_receivable": [
        "AccountsReceivableNetCurrent",
        "AccountsReceivableNet",
        "ReceivablesNetCurrent",
        "TradeReceivablesNetCurrent",
    ],
    "inventory": [
        "InventoryNet",
        "Inventory",
        "InventoriesNet",
    ],
    "current_assets": [
        "AssetsCurrent",
    ],
    "total_assets": [
        "Assets",
    ],
    "accounts_payable": [
        "AccountsPayableCurrent",
        "AccountsPayable",
        "AccountsPayableAccruedLiabilitiesAndOtherLiabilitiesCurrent",
        "AccountsPayableAndAccruedLiabilitiesCurrent",
    ],
    "current_liabilities": [
        "LiabilitiesCurrent",
    ],
    "total_liabilities": [
        "Liabilities",
    ],
    "short_term_debt": [
        "ShortTermBorrowings",
        "DebtCurrent",
        "LongTermDebtCurrent",
        "LongTermDebtAndCapitalLeaseObligationsCurrent",
        "DebtInstrumentCurrent",
    ],
    "long_term_debt": [
        "LongTermDebtNoncurrent",
        "LongTermDebt",
        "LongTermDebtAndCapitalLeaseObligations",
        "LongTermDebtAndCapitalLeaseObligationsNoncurrent",
        "LongTermDebtNetNoncurrent",
    ],
    "shareholders_equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        "TotalStockholdersEquity",
        "StockholdersEquityOrOwnersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
}

CASH_FLOW_CONCEPTS: dict[str, list[str]] = {
    "operating_cash_flow": [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByOperatingActivities",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecrease",
    ],
    "capital_expenditures": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "CapitalExpenditures",
        "PaymentsForCapitalImprovements",
        "PaymentsToAcquireDevelopedTechnology",
        "AcquisitionsNetOfCashAcquired",
    ],
    "investing_cash_flow": [
        "NetCashProvidedByUsedInInvestingActivities",
        "NetCashUsedForInvestingActivities",
    ],
    "financing_cash_flow": [
        "NetCashProvidedByUsedInFinancingActivities",
        "NetCashUsedForFinancingActivities",
    ],
    "dividends_paid": [
        "PaymentsOfDividends",
        "DividendsPaid",
        "Dividends",
        "DividendsCommonStock",
    ],
    "share_repurchases": [
        "PaymentsForRepurchaseOfCommonStock",
        "RepurchaseOfCapitalStock",
        "PaymentsForRepurchaseOfEquity",
        "ShareBasedCompensation",
    ],
    "depreciation_amortization": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
        "DepreciationAmortizationAndAccretionNet",
        "Depreciation",
        "DepreciationAndAmortizationExpense",
        "AmortizationOfIntangibleAssets",
        "AmortizationOfDebtIssuanceCosts",
    ],
    "interest_expense": [
        "InterestExpense",
        "InterestExpenseDebt",
        "InterestAndDebtExpense",
        "InterestExpenseNet",
    ],
}

ADDITIONAL_CONCEPTS: dict[str, list[str]] = {
    "shares_outstanding": [
        "CommonStockSharesOutstanding",
        "EntityCommonStockSharesOutstanding",
    ],
    "diluted_shares": [
        "EarningsPerShareDilutedSharesOutstanding",
        "WeightedAverageNumberOfDilutedSharesOutstanding",
        "DilutedWeightedAverageSharesOutstanding",
        "CommonStockDilutedSharesOutstanding",
    ],
    "weighted_average_shares_basic": [
        "EarningsPerShareBasicSharesOutstanding",
        "WeightedAverageNumberOfSharesOutstandingBasic",
        "WeightedAverageNumberOfShares",
    ],
}


# ── Unit validation ──────────────────────────────────────────────────────────
METRIC_UNITS: dict[str, str] = {
    "revenue": "USD",
    "cost_of_revenue": "USD",
    "gross_profit": "USD",
    "operating_income": "USD",
    "pretax_income": "USD",
    "income_tax_expense": "USD",
    "net_income": "USD",
    "diluted_eps": "USD/shares",
    "basic_eps": "USD/shares",
    "cash_and_equivalents": "USD",
    "short_term_investments": "USD",
    "accounts_receivable": "USD",
    "inventory": "USD",
    "current_assets": "USD",
    "total_assets": "USD",
    "accounts_payable": "USD",
    "current_liabilities": "USD",
    "total_liabilities": "USD",
    "short_term_debt": "USD",
    "long_term_debt": "USD",
    "shareholders_equity": "USD",
    "operating_cash_flow": "USD",
    "capital_expenditures": "USD",
    "investing_cash_flow": "USD",
    "financing_cash_flow": "USD",
    "dividends_paid": "USD",
    "share_repurchases": "USD",
    "depreciation_amortization": "USD",
    "interest_expense": "USD",
    "shares_outstanding": "shares",
    "diluted_shares": "shares",
    "weighted_average_shares_basic": "shares",
}


def get_concepts_for_metric(metric: str) -> list[str]:
    """Return the list of XBRL concepts that could represent this metric."""
    all_concepts: dict[str, list[str]] = {}
    all_concepts.update(INCOME_STATEMENT_CONCEPTS)
    all_concepts.update(BALANCE_SHEET_CONCEPTS)
    all_concepts.update(CASH_FLOW_CONCEPTS)
    all_concepts.update(ADDITIONAL_CONCEPTS)
    return all_concepts.get(metric, [])


def get_all_xbrl_concepts() -> set[str]:
    """Return the set of all known XBRL concepts across all metrics."""
    all_concepts: set[str] = set()
    for concepts in INCOME_STATEMENT_CONCEPTS.values():
        all_concepts.update(concepts)
    for concepts in BALANCE_SHEET_CONCEPTS.values():
        all_concepts.update(concepts)
    for concepts in CASH_FLOW_CONCEPTS.values():
        all_concepts.update(concepts)
    for concepts in ADDITIONAL_CONCEPTS.values():
        all_concepts.update(concepts)
    return all_concepts


def get_metric_unit(metric: str) -> str:
    """Return the expected unit for a metric."""
    return METRIC_UNITS.get(metric, "USD")


def get_income_statement_metrics() -> list[str]:
    """Return all income statement metric names."""
    return list(INCOME_STATEMENT_CONCEPTS.keys())


def get_balance_sheet_metrics() -> list[str]:
    """Return all balance sheet metric names."""
    return list(BALANCE_SHEET_CONCEPTS.keys())


def get_cash_flow_metrics() -> list[str]:
    """Return all cash flow metric names."""
    return list(CASH_FLOW_CONCEPTS.keys())


def get_additional_metrics() -> list[str]:
    """Return all additional metric names."""
    return list(ADDITIONAL_CONCEPTS.keys())
