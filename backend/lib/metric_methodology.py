"""Metric methodology documentation.

Defines the formula, required inputs, and handling rules for every
calculated financial metric in Finora.  This serves as both the
authoritative reference for the calculation engine and the future
source for the verification modal / public methodology page.
"""

BEGINNER_EXPLANATIONS: dict[str, str] = {
    "revenue_growth": "Revenue growth shows how much a company's total sales increased or decreased compared to the previous year. Positive growth means the company is selling more.",
    "gross_profit_growth": "Gross profit growth measures how much the money left after subtracting the cost of making products increased from last year.",
    "operating_income_growth": "Operating income growth shows how the company's core business profitability changed from last year, after accounting for all operating costs.",
    "net_income_growth": "Net income growth shows how the company's bottom-line profit (what's left after all expenses, taxes, and costs) changed from last year.",
    "eps_growth": "EPS growth shows how much each share's earnings increased from last year. This is one of the most-watched metrics by investors.",
    "ocf_growth": "Operating cash flow growth shows how the cash generated from core business activities changed from last year.",
    "fcf_growth": "Free cash flow growth shows how much cash the company generated after spending on equipment and buildings, compared to last year.",
    "revenue_cagr": "Revenue CAGR is the average annual growth rate of revenue over a multi-year period, smoothing out year-to-year fluctuations.",
    "net_income_cagr": "Net income CAGR is the average annual growth rate of profit over a multi-year period.",
    "eps_cagr": "EPS CAGR is the average annual growth rate of earnings per share over a multi-year period.",
    "gross_margin": "Gross margin shows what percentage of revenue is left after subtracting the direct cost of making products or services. A higher margin means more efficient production.",
    "operating_margin": "Operating margin shows what percentage of revenue remains after paying for all costs to run the business (salaries, rent, marketing, etc.).",
    "pretax_margin": "Pretax margin shows what percentage of revenue remains before the government takes its share in taxes.",
    "net_margin": "Net margin (profit margin) shows what percentage of each dollar of revenue becomes actual profit. This is the bottom line.",
    "ebitda_margin": "EBITDA margin shows what percentage of revenue remains after operating costs but before accounting for depreciation, interest, and taxes.",
    "fcf_margin": "FCF margin shows what percentage of revenue converts to free cash — the cash actually available to shareholders and creditors.",
    "ocf_margin": "OCF margin shows what percentage of revenue converts to operating cash flow.",
    "roa": "Return on Assets (ROA) measures how efficiently a company uses its assets to generate profit. Higher ROA means the company is more effective at converting investments into earnings.",
    "roe": "Return on Equity (ROE) measures how efficiently a company generates profit from shareholders' capital. A higher ROE can indicate stronger capital efficiency, but should be interpreted alongside leverage and industry characteristics.",
    "roic": "Return on Invested Capital (ROIC) measures how well a company uses all its capital (debt and equity) to generate profits. It's considered one of the most important metrics for evaluating a company's true economic performance.",
    "roce": "Return on Capital Employed (ROCE) measures how efficiently a company uses its total capital (assets minus current liabilities) to generate operating profits.",
    "free_cash_flow": "Free Cash Flow is the cash a company generates after spending on equipment and buildings. It represents money available for dividends, debt repayment, or growth investments.",
    "cash_conversion": "Cash conversion shows what percentage of reported earnings actually turned into free cash. A ratio above 100% means the company is generating more cash than its accounting profit suggests.",
    "ocf_to_net_income": "This ratio compares operating cash flow to net income. A ratio above 100% generally indicates high-quality earnings — the company is collecting real cash, not just accounting profits.",
    "capex_intensity": "CapEx intensity shows how much of the company's revenue is spent on equipment, buildings, and infrastructure. Capital-intensive businesses (like manufacturing) have higher ratios.",
    "capex_to_ocf": "This shows what percentage of operating cash flow is reinvested in equipment and buildings. A high ratio may indicate heavy investment in growth.",
    "cash_flow_to_debt": "Cash flow to debt shows how quickly a company could pay off its total debt using one year of operating cash flow. Higher is better for creditworthiness.",
    "current_ratio": "The current ratio measures whether a company has enough short-term assets to cover its short-term bills. A ratio above 1.0 means it can cover its near-term obligations.",
    "quick_ratio": "The quick ratio is a stricter version of the current ratio — it excludes inventory, which might be hard to sell quickly. It tests whether a company can pay bills without selling inventory.",
    "cash_ratio": "The cash ratio is the most conservative liquidity measure — it tests whether a company could pay all short-term bills using only cash and short-term investments.",
    "net_working_capital": "Net working capital is the difference between short-term assets and short-term liabilities. Positive working capital means the company can fund its day-to-day operations.",
    "nwc_to_revenue": "This shows net working capital as a percentage of revenue — a measure of how much working capital is needed to support each dollar of sales.",
    "debt_to_equity": "Debt-to-equity shows how much the company relies on borrowed money versus shareholder money. Higher ratios mean more financial leverage and potentially more risk.",
    "debt_to_assets": "Debt-to-assets shows what percentage of the company's assets are financed by debt. Lower is generally safer, though some debt can boost returns.",
    "debt_to_capital": "Debt-to-capital shows what percentage of the company's total capital structure (debt + equity) comes from debt.",
    "net_debt": "Net debt is total debt minus cash. If a company has more cash than debt, net debt is negative — a very strong financial position.",
    "debt_to_ebitda": "Debt-to-EBITDA shows how many years of operating earnings it would take to pay off all debt. Lower is better; under 3.0x is generally considered healthy.",
    "net_debt_to_ebitda": "Net debt-to-EBITDA shows how many years of operating earnings it would take to pay off net debt (debt minus cash).",
    "interest_coverage": "Interest coverage shows how many times the company could pay its interest expense with operating income. Higher means safer — the company can comfortably afford its interest payments.",
    "asset_turnover": "Asset turnover measures how efficiently a company uses its assets to generate revenue. A higher ratio means the company generates more sales per dollar of assets.",
    "receivables_turnover": "Receivables turnover measures how quickly a company collects money from its customers. Higher turnover means faster collection.",
    "inventory_turnover": "Inventory turnover measures how many times a company sold and replaced its inventory during the year. Higher turnover generally means efficient inventory management.",
    "days_sales_outstanding": "DSO shows the average number of days it takes to collect payment after a sale. Lower is better — it means the company collects cash faster.",
    "days_inventory_outstanding": "DIO shows the average number of days inventory sits before being sold. Lower generally means more efficient operations.",
    "days_payable_outstanding": "DPO shows how many days the company takes to pay its suppliers. Taking longer to pay preserves cash, but too long could strain supplier relationships.",
    "cash_conversion_cycle": "The cash conversion cycle measures how many days it takes to convert investments in inventory back into cash from sales. A shorter cycle means faster cash generation.",
    "revenue_per_share": "Revenue per share shows how much revenue is attributable to each outstanding share.",
    "fcf_per_share": "Free cash flow per share shows how much free cash flow each share generates.",
    "book_value_per_share": "Book value per share shows the net asset value attributable to each share — essentially what shareholders would theoretically receive if the company liquidated at book value.",
    "dividend_payout_ratio": "The dividend payout ratio shows what percentage of net income is paid out as dividends. A very high ratio may be unsustainable; a low ratio may indicate reinvestment for growth.",
    "buyback_to_fcf": "This shows what percentage of free cash flow is spent on buying back the company's own shares. High buybacks can boost earnings per share.",
    "effective_tax_rate": "The effective tax rate is the actual percentage of pretax income that goes to taxes. This often differs from the statutory rate due to deductions, credits, and international operations.",
    "ebitda": "EBITDA (Earnings Before Interest, Taxes, Depreciation, and Amortization) is a measure of operating profitability that removes the effects of financing and accounting decisions.",
    "dupont": "DuPont analysis breaks ROE into three components: profit margin (how much of each sale becomes profit), asset turnover (how efficiently assets generate sales), and equity multiplier (how much leverage the company uses).",
}

METODOLOGY: dict[str, dict] = {
    # ── Growth ────────────────────────────────────────────────────────────
    "revenue_growth": {"name": "Revenue Growth (YoY)", "unit": "%", "classification": "calculated",
        "formula": "(Revenue_current - Revenue_previous) / Revenue_previous * 100",
        "notes": "Compares two consecutive annual periods.",
        "beginner": BEGINNER_EXPLANATIONS.get("revenue_growth", "")},
    "gross_profit_growth": {"name": "Gross Profit Growth (YoY)", "unit": "%", "classification": "calculated",
        "formula": "(GrossProfit_current - GrossProfit_previous) / GrossProfit_previous * 100",
        "notes": "Year-over-year change in gross profit."},
    "operating_income_growth": {"name": "Operating Income Growth (YoY)", "unit": "%", "classification": "calculated",
        "formula": "(OpIncome_current - OpIncome_previous) / OpIncome_previous * 100",
        "notes": "Year-over-year change in operating income."},
    "net_income_growth": {"name": "Net Income Growth (YoY)", "unit": "%", "classification": "calculated",
        "formula": "(NetIncome_current - NetIncome_previous) / NetIncome_previous * 100",
        "notes": "Year-over-year change in net income."},
    "eps_growth": {"name": "EPS Growth (YoY)", "unit": "%", "classification": "calculated",
        "formula": "(EPS_current - EPS_previous) / EPS_previous * 100",
        "notes": "Uses diluted EPS."},
    "ocf_growth": {"name": "Operating Cash Flow Growth (YoY)", "unit": "%", "classification": "calculated",
        "formula": "(OCF_current - OCF_previous) / OCF_previous * 100",
        "notes": "Year-over-year change in operating cash flow."},
    "fcf_growth": {"name": "Free Cash Flow Growth (YoY)", "unit": "%", "classification": "calculated",
        "formula": "(FCF_current - FCF_previous) / FCF_previous * 100",
        "notes": "Calculated from operating cash flow growth proxy."},
    "revenue_cagr": {"name": "Revenue CAGR", "unit": "%", "classification": "calculated",
        "formula": "(Revenue_end / Revenue_start)^(1/n) - 1",
        "notes": "Requires at least 2 years of data."},
    "net_income_cagr": {"name": "Net Income CAGR", "unit": "%", "classification": "calculated",
        "formula": "(NetIncome_end / NetIncome_start)^(1/n) - 1",
        "notes": "Compound annual growth rate of net income."},
    "eps_cagr": {"name": "EPS CAGR", "unit": "%", "classification": "calculated",
        "formula": "(EPS_end / EPS_start)^(1/n) - 1",
        "notes": "Compound annual growth rate of diluted EPS."},

    # ── Profitability ─────────────────────────────────────────────────────
    "gross_margin": {"name": "Gross Margin", "unit": "%", "classification": "calculated",
        "formula": "Gross Profit / Revenue * 100",
        "notes": "Proportion of revenue retained after cost of goods sold."},
    "operating_margin": {"name": "Operating Margin", "unit": "%", "classification": "calculated",
        "formula": "Operating Income / Revenue * 100",
        "notes": "Proportion of revenue retained after all operating expenses."},
    "pretax_margin": {"name": "Pretax Margin", "unit": "%", "classification": "calculated",
        "formula": "Pretax Income / Revenue * 100",
        "notes": "Profitability before income taxes."},
    "net_margin": {"name": "Net Profit Margin", "unit": "%", "classification": "calculated",
        "formula": "Net Income / Revenue * 100",
        "notes": "Bottom-line profitability per dollar of revenue."},
    "ebitda_margin": {"name": "EBITDA Margin", "unit": "%", "classification": "calculated",
        "formula": "EBITDA / Revenue * 100",
        "notes": "Only available when EBITDA can be derived."},
    "fcf_margin": {"name": "Free Cash Flow Margin", "unit": "%", "classification": "calculated",
        "formula": "Free Cash Flow / Revenue * 100",
        "notes": "Cash generation efficiency relative to revenue."},
    "ocf_margin": {"name": "Operating Cash Flow Margin", "unit": "%", "classification": "calculated",
        "formula": "Operating Cash Flow / Revenue * 100",
        "notes": ""},

    # ── Returns ───────────────────────────────────────────────────────────
    "roa": {"name": "Return on Assets", "unit": "%", "classification": "calculated",
        "formula": "Net Income / Average Total Assets * 100",
        "notes": "Falls back to ending balance if prior year unavailable."},
    "roe": {"name": "Return on Equity", "unit": "%", "classification": "calculated",
        "formula": "Net Income / Average Stockholders' Equity * 100",
        "notes": "Falls back to ending balance if prior year unavailable."},
    "roic": {"name": "Return on Invested Capital", "unit": "%", "classification": "calculated",
        "formula": "NOPAT / Invested Capital * 100",
        "notes": "Uses effective tax rate if available, else 21% default. IC = Debt + Equity - Cash."},
    "roce": {"name": "Return on Capital Employed", "unit": "%", "classification": "calculated",
        "formula": "NOPAT / Capital Employed * 100, where Capital Employed = Total Assets - Current Liabilities",
        "notes": "Uses effective tax rate if available."},

    # ── Cash Flow ─────────────────────────────────────────────────────────
    "free_cash_flow": {"name": "Free Cash Flow", "unit": "USD", "classification": "calculated",
        "formula": "Operating Cash Flow - Capital Expenditures",
        "notes": "CapEx is treated as positive (absolute value). SEC data may report as negative."},
    "cash_conversion": {"name": "Cash Conversion (FCF/Net Income)", "unit": "%", "classification": "calculated",
        "formula": "Free Cash Flow / Net Income * 100",
        "notes": "Measures how much of reported earnings convert to free cash flow."},
    "ocf_to_net_income": {"name": "OCF / Net Income", "unit": "%", "classification": "calculated",
        "formula": "Operating Cash Flow / Net Income * 100",
        "notes": "Measures cash generation quality relative to reported earnings."},
    "capex_intensity": {"name": "CapEx Intensity", "unit": "%", "classification": "calculated",
        "formula": "Capital Expenditures / Revenue * 100",
        "notes": ""},
    "capex_to_ocf": {"name": "CapEx / OCF", "unit": "%", "classification": "calculated",
        "formula": "Capital Expenditures / Operating Cash Flow * 100",
        "notes": ""},
    "cash_flow_to_debt": {"name": "Cash Flow to Debt", "unit": "%", "classification": "calculated",
        "formula": "Operating Cash Flow / Total Debt * 100",
        "notes": ""},

    # ── Liquidity ─────────────────────────────────────────────────────────
    "current_ratio": {"name": "Current Ratio", "unit": "x", "classification": "calculated",
        "formula": "Current Assets / Current Liabilities",
        "notes": ""},
    "quick_ratio": {"name": "Quick Ratio", "unit": "x", "classification": "calculated",
        "formula": "(Cash + ST Investments + Accounts Receivable) / Current Liabilities",
        "notes": ""},
    "cash_ratio": {"name": "Cash Ratio", "unit": "x", "classification": "calculated",
        "formula": "(Cash + ST Investments) / Current Liabilities",
        "notes": "Most conservative liquidity ratio."},
    "net_working_capital": {"name": "Net Working Capital", "unit": "USD", "classification": "calculated",
        "formula": "Current Assets - Current Liabilities",
        "notes": ""},
    "nwc_to_revenue": {"name": "Net Working Capital / Revenue", "unit": "%", "classification": "calculated",
        "formula": "Net Working Capital / Revenue * 100",
        "notes": ""},

    # ── Leverage ──────────────────────────────────────────────────────────
    "debt_to_equity": {"name": "Debt / Equity", "unit": "x", "classification": "calculated",
        "formula": "Total Liabilities / Stockholders' Equity",
        "notes": "Uses total liabilities as total debt proxy."},
    "debt_to_assets": {"name": "Debt / Assets", "unit": "x", "classification": "calculated",
        "formula": "Total Liabilities / Total Assets",
        "notes": ""},
    "debt_to_capital": {"name": "Debt / Capital", "unit": "%", "classification": "calculated",
        "formula": "Total Debt / (Total Debt + Equity) * 100",
        "notes": "Total Debt = Short-term + Long-term debt."},
    "net_debt": {"name": "Net Debt", "unit": "USD", "classification": "calculated",
        "formula": "Total Debt - Cash - ST Investments",
        "notes": "Negative means company has more cash than debt."},
    "debt_to_ebitda": {"name": "Debt / EBITDA", "unit": "x", "classification": "calculated",
        "formula": "Total Debt / EBITDA",
        "notes": "Only when EBITDA derivable."},
    "net_debt_to_ebitda": {"name": "Net Debt / EBITDA", "unit": "x", "classification": "calculated",
        "formula": "Net Debt / EBITDA",
        "notes": "Only when EBITDA derivable."},
    "interest_coverage": {"name": "Interest Coverage", "unit": "x", "classification": "calculated",
        "formula": "Operating Income / Interest Expense",
        "notes": "Interest expense not always available in XBRL."},

    # ── Efficiency ────────────────────────────────────────────────────────
    "asset_turnover": {"name": "Asset Turnover", "unit": "x", "classification": "calculated",
        "formula": "Revenue / Total Assets",
        "notes": "Measures asset utilization efficiency."},
    "receivables_turnover": {"name": "Receivables Turnover", "unit": "x", "classification": "calculated",
        "formula": "Revenue / Accounts Receivable",
        "notes": "How quickly receivables are collected."},
    "inventory_turnover": {"name": "Inventory Turnover", "unit": "x", "classification": "calculated",
        "formula": "Cost of Revenue / Inventory",
        "notes": "Not meaningful for service companies without inventory."},
    "days_sales_outstanding": {"name": "Days Sales Outstanding", "unit": "days", "classification": "calculated",
        "formula": "365 / Receivables Turnover",
        "notes": ""},
    "days_inventory_outstanding": {"name": "Days Inventory Outstanding", "unit": "days", "classification": "calculated",
        "formula": "365 / Inventory Turnover",
        "notes": ""},
    "days_payable_outstanding": {"name": "Days Payable Outstanding", "unit": "days", "classification": "calculated",
        "formula": "365 / Payables Turnover",
        "notes": "Uses Cost of Revenue / Accounts Payable."},
    "cash_conversion_cycle": {"name": "Cash Conversion Cycle", "unit": "days", "classification": "calculated",
        "formula": "DSO + DIO - DPO",
        "notes": "Measures cash conversion efficiency."},

    # ── Per Share ─────────────────────────────────────────────────────────
    "revenue_per_share": {"name": "Revenue per Share", "unit": "USD", "classification": "calculated",
        "formula": "Revenue / Diluted Shares Outstanding",
        "notes": "Revenue attributable to each share on a diluted basis."},
    "fcf_per_share": {"name": "Free Cash Flow per Share", "unit": "USD", "classification": "calculated",
        "formula": "Free Cash Flow / Diluted Shares Outstanding",
        "notes": "Free cash flow attributable to each share."},
    "book_value_per_share": {"name": "Book Value per Share", "unit": "USD", "classification": "calculated",
        "formula": "Stockholders' Equity / Diluted Shares Outstanding",
        "notes": "Equity attributable to each share."},

    # ── Capital Allocation ────────────────────────────────────────────────
    "dividend_payout_ratio": {"name": "Dividend Payout Ratio", "unit": "%", "classification": "calculated",
        "formula": "Dividends Paid / Net Income * 100",
        "notes": ""},
    "buyback_to_fcf": {"name": "Buyback / FCF", "unit": "%", "classification": "calculated",
        "formula": "Share Repurchases / Free Cash Flow * 100",
        "notes": ""},
    "effective_tax_rate": {"name": "Effective Tax Rate", "unit": "%", "classification": "derived",
        "formula": "Income Tax Expense / Pretax Income * 100",
        "notes": "Derived from SEC financial data."},

    # ── EBITDA ────────────────────────────────────────────────────────────
    "ebitda": {"name": "Derived EBITDA", "unit": "USD", "classification": "derived",
        "formula": "Operating Income + Depreciation & Amortization",
        "notes": "Clearly labeled as Derived. D&A not always available."},

    # ── DuPont ────────────────────────────────────────────────────────────
    "dupont": {"name": "DuPont ROE Decomposition", "unit": "%", "classification": "calculated",
        "formula": "Net Margin x Asset Turnover x Equity Multiplier",
        "notes": "Decomposes ROE into profitability, efficiency, and leverage components."},
}


def get_beginner_explanation(metric_id: str) -> str:
    """Return a plain-English explanation for a metric, or empty string."""
    return BEGINNER_EXPLANATIONS.get(metric_id, "")


def get_metric_metadata(metric_id: str) -> dict:
    """Return combined metadata for a metric."""
    meta = METODOLOGY.get(metric_id, {})
    return {
        **meta,
        "beginner": BEGINNER_EXPLANATIONS.get(metric_id, ""),
    }


# ══════════════════════════════════════════════════════════════════════════
# INPUT REQUIREMENT MAP
# Every calculated metric declares its required raw inputs.
# The recovery engine uses this to explain WHY a metric is unavailable.
# ══════════════════════════════════════════════════════════════════════════

INPUT_REQUIREMENTS: dict[str, dict] = {
    # ── Margins ──
    "gross_margin": {"required": ["gross_profit", "revenue"],
        "alternative": ["revenue", "cost_of_revenue"],
        "description": "Gross Profit / Revenue"},
    "operating_margin": {"required": ["operating_income", "revenue"],
        "description": "Operating Income / Revenue"},
    "pretax_margin": {"required": ["pretax_income", "revenue"],
        "description": "Pretax Income / Revenue"},
    "net_margin": {"required": ["net_income", "revenue"],
        "description": "Net Income / Revenue"},
    "ebitda_margin": {"required": ["ebitda", "revenue"],
        "description": "EBITDA / Revenue"},
    "fcf_margin": {"required": ["free_cash_flow", "revenue"],
        "description": "FCF / Revenue"},
    "ocf_margin": {"required": ["operating_cash_flow", "revenue"],
        "description": "Operating Cash Flow / Revenue"},

    # ── Returns ──
    "roa": {"required": ["net_income", "total_assets"],
        "optional": ["prior_total_assets"],
        "description": "Net Income / Average Total Assets"},
    "roe": {"required": ["net_income", "shareholders_equity"],
        "optional": ["prior_shareholders_equity"],
        "description": "Net Income / Average Shareholders' Equity"},
    "roic": {"required": ["operating_income", "shareholders_equity", "cash_and_equivalents", "long_term_debt"],
        "optional": ["short_term_debt", "income_tax_expense", "pretax_income"],
        "description": "NOPAT / Invested Capital"},
    "roce": {"required": ["operating_income", "total_assets", "current_liabilities"],
        "optional": ["income_tax_expense", "pretax_income"],
        "description": "NOPAT / Capital Employed"},
    "dupont": {"required": ["net_income", "revenue", "total_assets", "shareholders_equity"],
        "description": "Net Margin x Asset Turnover x Equity Multiplier"},

    # ── Cash Flow ──
    "free_cash_flow": {"required": ["operating_cash_flow", "capital_expenditures"],
        "description": "OCF - CapEx"},
    "cash_conversion": {"required": ["free_cash_flow", "net_income"],
        "description": "FCF / Net Income"},
    "ocf_to_net_income": {"required": ["operating_cash_flow", "net_income"],
        "description": "OCF / Net Income"},
    "capex_intensity": {"required": ["capital_expenditures", "revenue"],
        "description": "CapEx / Revenue"},
    "capex_to_ocf": {"required": ["capital_expenditures", "operating_cash_flow"],
        "description": "CapEx / OCF"},
    "cash_flow_to_debt": {"required": ["operating_cash_flow", "short_term_debt", "long_term_debt"],
        "description": "OCF / Total Debt"},

    # ── Liquidity ──
    "current_ratio": {"required": ["current_assets", "current_liabilities"],
        "description": "Current Assets / Current Liabilities"},
    "quick_ratio": {"required": ["cash_and_equivalents", "accounts_receivable", "current_liabilities"],
        "optional": ["short_term_investments"],
        "description": "(Cash + ST Inv + AR) / Current Liabilities"},
    "cash_ratio": {"required": ["cash_and_equivalents", "current_liabilities"],
        "optional": ["short_term_investments"],
        "description": "(Cash + ST Inv) / Current Liabilities"},
    "net_working_capital": {"required": ["current_assets", "current_liabilities"],
        "description": "Current Assets - Current Liabilities"},
    "nwc_to_revenue": {"required": ["current_assets", "current_liabilities", "revenue"],
        "description": "NWC / Revenue"},

    # ── Leverage ──
    "debt_to_equity": {"required": ["total_liabilities", "shareholders_equity"],
        "description": "Total Liabilities / Equity"},
    "debt_to_assets": {"required": ["total_liabilities", "total_assets"],
        "description": "Total Liabilities / Total Assets"},
    "debt_to_capital": {"required": ["short_term_debt", "long_term_debt", "shareholders_equity"],
        "description": "Total Debt / (Total Debt + Equity)"},
    "net_debt": {"required": ["short_term_debt", "long_term_debt", "cash_and_equivalents"],
        "optional": ["short_term_investments"],
        "description": "Total Debt - Cash - ST Investments"},
    "debt_to_ebitda": {"required": ["short_term_debt", "long_term_debt", "ebitda"],
        "description": "Total Debt / EBITDA"},
    "net_debt_to_ebitda": {"required": ["net_debt", "ebitda"],
        "description": "Net Debt / EBITDA"},
    "interest_coverage": {"required": ["operating_income", "interest_expense"],
        "description": "Operating Income / Interest Expense"},

    # ── Efficiency ──
    "asset_turnover": {"required": ["revenue", "total_assets"],
        "description": "Revenue / Total Assets"},
    "receivables_turnover": {"required": ["revenue", "accounts_receivable"],
        "description": "Revenue / Accounts Receivable"},
    "inventory_turnover": {"required": ["cost_of_revenue", "inventory"],
        "description": "Cost of Revenue / Inventory"},
    "days_sales_outstanding": {"required": ["revenue", "accounts_receivable"],
        "description": "365 / Receivables Turnover"},
    "days_inventory_outstanding": {"required": ["cost_of_revenue", "inventory"],
        "description": "365 / Inventory Turnover"},
    "days_payable_outstanding": {"required": ["cost_of_revenue", "accounts_payable"],
        "description": "365 / Payables Turnover"},
    "cash_conversion_cycle": {"required": ["days_sales_outstanding", "days_inventory_outstanding", "days_payable_outstanding"],
        "description": "DSO + DIO - DPO"},

    # ── Per Share ──
    "revenue_per_share": {"required": ["revenue", "diluted_shares"],
        "description": "Revenue / Diluted Shares"},
    "fcf_per_share": {"required": ["free_cash_flow", "diluted_shares"],
        "description": "FCF / Diluted Shares"},
    "book_value_per_share": {"required": ["shareholders_equity", "diluted_shares"],
        "description": "Equity / Diluted Shares"},

    # ── Capital Allocation ──
    "dividend_payout_ratio": {"required": ["dividends_paid", "net_income"],
        "description": "Dividends / Net Income"},
    "buyback_to_fcf": {"required": ["share_repurchases", "free_cash_flow"],
        "description": "Buybacks / FCF"},
    "effective_tax_rate": {"required": ["income_tax_expense", "pretax_income"],
        "description": "Tax Expense / Pretax Income"},

    # ── EBITDA ──
    "ebitda": {"required": ["operating_income", "depreciation_amortization"],
        "description": "Operating Income + D&A"},

    # ── Growth ──
    "revenue_growth": {"required": ["revenue"],
        "description": "(Rev_current - Rev_previous) / Rev_previous"},
    "gross_profit_growth": {"required": ["gross_profit"],
        "description": "(GP_current - GP_previous) / GP_previous"},
    "operating_income_growth": {"required": ["operating_income"],
        "description": "(OI_current - OI_previous) / OI_previous"},
    "net_income_growth": {"required": ["net_income"],
        "description": "(NI_current - NI_previous) / NI_previous"},
    "eps_growth": {"required": ["diluted_eps"],
        "description": "(EPS_current - EPS_previous) / EPS_previous"},
    "ocf_growth": {"required": ["operating_cash_flow"],
        "description": "(OCF_current - OCF_previous) / OCF_previous"},
    "fcf_growth": {"required": ["operating_cash_flow"],
        "description": "(FCF_current - FCF_previous) / FCF_previous"},
    "revenue_cagr": {"required": ["revenue"],
        "description": "(Rev_end / Rev_start)^(1/n) - 1"},
    "net_income_cagr": {"required": ["net_income"],
        "description": "(NI_end / NI_start)^(1/n) - 1"},
    "eps_cagr": {"required": ["diluted_eps"],
        "description": "(EPS_end / EPS_start)^(1/n) - 1"},
}


def get_missing_inputs_explanation(metric_id: str, available_inputs: set[str]) -> str:
    """Explain which raw inputs are missing for a given metric.

    Parameters
    ----------
    metric_id : str
        The metric identifier.
    available_inputs : set[str]
        Set of input IDs that are available in the extracted data.

    Returns
    -------
    str
        Human-readable explanation of what is missing.
    """
    req = INPUT_REQUIREMENTS.get(metric_id)
    if not req:
        return "Input requirements not documented for this metric."
    required = req.get("required", [])
    optional = req.get("optional", [])
    missing_required = [r for r in required if r not in available_inputs]
    missing_optional = [o for o in optional if o not in available_inputs]
    parts = []
    if missing_required:
        parts.append(f"Missing required inputs: {', '.join(missing_required)}")
    if missing_optional:
        parts.append(f"Missing optional inputs: {', '.join(missing_optional)}")
    if not parts:
        return "All required inputs are available."
    return "; ".join(parts)


def get_applicability_for_sector(metric_id: str, is_financial: bool) -> str:
    """Determine if a metric is applicable for the given sector.

    Returns 'applicable', 'not_meaningful', or 'caution'.
    """
    if not is_financial:
        return "applicable"
    # Metrics that are economically inappropriate for banks/financial institutions
    NOT_MEANINGFUL_FOR_FINANCIAL = {
        "ebitda", "ebitda_margin", "debt_to_ebitda", "net_debt_to_ebitda",
        "ev_to_ebitda", "ev_to_ebit", "ev_to_fcf",
        "inventory_turnover", "days_inventory_outstanding",
        "cash_conversion_cycle",
        "net_working_capital", "nwc_to_revenue",
    }
    if metric_id in NOT_MEANINGFUL_FOR_FINANCIAL:
        return "not_meaningful"
    return "applicable"
