"""
Data Loader — Real financial data from SEC EDGAR + pre-built scenarios
SEC EDGAR API: https://data.sec.gov/api/xbrl/companyfacts/{CIK}.json
No API key needed — free public data.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Optional
import httpx

# ── FRED (Federal Reserve Economic Data) ─────────────────────────────────────
FRED_API_KEY = os.environ.get("FRED_API_KEY", "")
FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"
FRED_FALLBACK_RATE = 4.33  # used when no API key or fetch fails


async def fetch_fed_funds_rate() -> float:
    """Fetch the latest effective federal funds rate from FRED.

    Requires FRED_API_KEY env var (free at fred.stlouisfed.org/docs/api/api_key.html).
    Returns the hardcoded fallback if key is missing or request fails.
    """
    if not FRED_API_KEY:
        return FRED_FALLBACK_RATE
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(FRED_BASE, params={
                "series_id":  "FEDFUNDS",
                "api_key":    FRED_API_KEY,
                "sort_order": "desc",
                "limit":      1,
                "file_type":  "json",
            })
            if resp.status_code == 200:
                observations = resp.json().get("observations", [])
                if observations:
                    return float(observations[0]["value"])
    except Exception:
        pass
    return FRED_FALLBACK_RATE


# ── Real SEC EDGAR Fetcher ────────────────────────────────────────────────────
EDGAR_BASE = "https://data.sec.gov/api/xbrl/companyfacts"
EDGAR_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
EDGAR_HEADERS = {"User-Agent": "finance-agent-demo cherry.07.skr@gmail.com"}

TICKER_TO_CIK = {
    # Real companies (CIK numbers from SEC EDGAR)
    "CRM":  "0001108524",  # Salesforce
    "ADBE": "0000796343",  # Adobe
    "NOW":  "0001373715",  # ServiceNow
    "WDAY": "0001327811",  # Workday
    "SNOW": "0001640147",  # Snowflake
}


async def lookup_cik_by_ticker(ticker: str) -> Optional[tuple]:
    """Return (cik_padded, company_name) for any US public ticker via EDGAR."""
    #Central Index Key
    ticker = ticker.upper()
    if ticker in TICKER_TO_CIK:
        return TICKER_TO_CIK[ticker], ticker

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(EDGAR_TICKERS_URL, headers=EDGAR_HEADERS)
            if resp.status_code == 200:
                for entry in resp.json().values():
                    if entry.get("ticker", "").upper() == ticker:
                        cik = str(entry["cik_str"]).zfill(10)
                        return cik, entry.get("title", ticker)
    except Exception:
        pass
    return None


async def fetch_edgar_facts(cik: str) -> Optional[dict]:
    """Fetch company facts from SEC EDGAR (real public data, no auth needed)."""
    url = f"{EDGAR_BASE}/CIK{cik}.json"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=EDGAR_HEADERS)
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return None


def _extract_quarterly(us_gaap: dict, *field_names: str) -> Optional[list]:
    """Merge quarterly entries (≈90 days) across all field names, newest first.

    Collects from every matching field before deduplicating so that companies
    that switched GAAP concepts (e.g. Revenues → RevenueFromContract post-ASC 606)
    return their most recent data rather than stopping at the first field found.
    """
    all_entries = []
    for name in field_names:
        units_usd = us_gaap.get(name, {}).get("units", {}).get("USD", [])
        for u in units_usd:
            if u.get("form") != "10-Q":
                continue
            start, end = u.get("start", ""), u.get("end", "")
            if start and end:
                try:
                    days = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).days
                    if 60 <= days <= 105:
                        all_entries.append(u)
                except ValueError:
                    pass
    if not all_entries:
        return None
    all_entries.sort(key=lambda x: (x.get("end", ""), x.get("filed", "")), reverse=True)
    seen, deduped = set(), []
    for q in all_entries:
        if q["end"] not in seen:
            seen.add(q["end"])
            deduped.append(q)
    return deduped


def build_edgar_scenario(ticker: str, company_name: str, facts: dict, fed_rate: float = FRED_FALLBACK_RATE) -> Optional[dict]:
    """Build an agent-compatible scenario dict from raw EDGAR company facts."""
    us_gaap = facts.get("facts", {}).get("us-gaap", {})

    revenue_data = _extract_quarterly(
        us_gaap,
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
    )
    if not revenue_data:
        return None

    latest = revenue_data[0]
    prior_yr = revenue_data[4] if len(revenue_data) > 4 else revenue_data[-1]
    rev_current = latest.get("val", 0)
    rev_prior = prior_yr.get("val", 0)
    rev_growth = round((rev_current - rev_prior) / rev_prior * 100, 2) if rev_prior else 0.0

    gp_data = _extract_quarterly(us_gaap, "GrossProfit")
    gross_margin = None
    if gp_data and rev_current:
        gross_margin = round(gp_data[0].get("val", 0) / rev_current * 100, 1)

    opex_data = _extract_quarterly(us_gaap, "OperatingExpenses")
    opex = opex_data[0].get("val", 0) if opex_data else 0

    oi_data = _extract_quarterly(us_gaap, "OperatingIncomeLoss")
    da_data = _extract_quarterly(
        us_gaap,
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
    )
    ebitda, ebitda_margin = None, None
    if oi_data:
        oi = oi_data[0].get("val", 0)
        da = da_data[0].get("val", 0) if da_data else 0
        ebitda = oi + da
        ebitda_margin = round(ebitda / rev_current * 100, 1) if rev_current else None

    cfo_data = _extract_quarterly(us_gaap, "NetCashProvidedByUsedInOperatingActivities")
    capex_data = _extract_quarterly(us_gaap, "PaymentsToAcquirePropertyPlantAndEquipment")
    fcf = None
    if cfo_data and capex_data:
        fcf = cfo_data[0].get("val", 0) - capex_data[0].get("val", 0)

    end_date = latest.get("end", "")
    fp = latest.get("fp", "Q?")
    year = int(end_date[:4]) if end_date else 0
    period = f"{fp} {year}" if end_date else "Recent Quarter"

    _next = {"Q1": "Q2", "Q2": "Q3", "Q3": "Q4", "Q4": "Q1"}
    next_fp = _next.get(fp, "Next Q")
    next_year = year + 1 if fp == "Q4" else year
    next_period = f"{next_fp} {next_year}" if year else "Next Quarter"

    return {
        "company": f"{company_name} (NASDAQ/NYSE: {ticker.upper()})",
        "period": period,
        "next_period": next_period,
        "context": f"Live SEC EDGAR data — most recent 10-Q ({end_date})",
        "data_source": f"SEC EDGAR XBRL (10-Q filed {end_date})",
        "financials": {
            "revenue_q3_actual": rev_current,
            "revenue_q3_prior_year": rev_prior,
            "revenue_growth_yoy": rev_growth,
            "gross_margin": gross_margin or 0,
            "operating_expenses": opex,
            "ebitda": ebitda or 0,
            "ebitda_margin": ebitda_margin or 0,
            "free_cash_flow": fcf or 0,
            "net_revenue_retention": None,
            "customer_churn_rate": None,
        },
        "forward_guidance": {
            "q4_revenue_low": int(rev_current * 0.97),
            "q4_revenue_high": int(rev_current * 1.05),
            "q4_opex_projected": int((opex or rev_current * 0.8) * 1.02),
            "fy2024_revenue_target": int(rev_current * 4.1),
        },
        "macro_context": {
            "fed_funds_rate": fed_rate,
            "data_note": "Forward guidance estimated from trailing quarter; macro from public sources",
        },
        "risks": [
            "Forward guidance estimated — check latest earnings call for official outlook",
            "Macro headwinds: elevated interest rates and uncertain consumer demand",
            "Competitive pricing pressure across the sector",
        ],
        "opportunities": [
            "AI integration opportunities across product lines",
            "International expansion potential in underpenetrated markets",
            "Operating leverage as revenue scales",
        ],
    }


def extract_revenue_data(facts: dict) -> Optional[dict]:
    """Extract recent revenue figures from EDGAR facts (legacy helper)."""
    try:
        us_gaap = facts.get("facts", {}).get("us-gaap", {})
        revenues = us_gaap.get("Revenues", us_gaap.get("RevenueFromContractWithCustomerExcludingAssessedTax", {}))
        units = revenues.get("units", {}).get("USD", [])
        quarterly = [u for u in units if u.get("form") == "10-Q" and u.get("fp") in ["Q1","Q2","Q3","Q4"]]
        quarterly.sort(key=lambda x: x.get("end", ""), reverse=True)
        return quarterly[:4] if quarterly else None
    except Exception:
        return None


# ── Pre-Built Realistic Scenarios ──────────────────────────────────────────────
# These are modeled after real company dynamics but are fictional composites.
# Interviewers see real-looking financial data without IP concerns.

SCENARIOS = {
    "TCORP": {
        "company": "TechCorp Inc. (NASDAQ: TCORP)",
        "period": "Q3 2024",
        "next_period": "Q4 2024",
        "context": "Mid-cap SaaS company, $2.1B ARR, facing macro headwinds and competitive pricing pressure",
        "data_source": "Synthetic — modeled after SaaS industry benchmarks (OpenView, Bessemer)",
        "financials": {
            "revenue_q3_actual": 521_000_000,
            "revenue_q3_prior_year": 487_000_000,
            "revenue_growth_yoy": 6.98,
            "gross_margin": 71.2,
            "operating_expenses": 398_000_000,
            "ebitda": 89_000_000,
            "ebitda_margin": 17.1,
            "free_cash_flow": 62_000_000,
            "net_revenue_retention": 108,
            "customer_churn_rate": 4.2,
            "sales_cycle_days": 94,
            "cac_payback_months": 28,
        },
        "forward_guidance": {
            "q4_revenue_low": 530_000_000,
            "q4_revenue_high": 545_000_000,
            "q4_opex_projected": 410_000_000,
            "fy2024_revenue_target": 2_080_000_000,
        },
        "macro_context": {
            "fed_funds_rate": 5.25,
            "enterprise_software_growth_sector": 8.3,
            "customer_segment_IT_budget_freeze_pct": 34,
            "competitor_pricing_cuts_pct": 12,
        },
        "risks": [
            "3 enterprise deals ($47M TCV) slipped to Q4 from Q3",
            "Key sales VP departed; replacement hired but ramping",
            "New EU data residency requirements affecting EMEA expansion",
            "AWS partnership renegotiation pending — potential 2pp margin impact",
        ],
        "opportunities": [
            "AI add-on module launched — $8M ARR in first 60 days",
            "Federal vertical pipeline up 41% YoY",
            "India R&D center reduces engineering cost by ~$15M annualized",
        ],
    },

    "MFGCO": {
        "company": "ManufactureCo Holdings (NYSE: MFGCO)",
        "period": "Q3 2024",
        "next_period": "Q4 2024",
        "context": "Industrial manufacturer, $4.8B revenue, navigating supply chain normalization and energy cost headwinds",
        "data_source": "Synthetic — modeled after S&P 500 industrial sector averages",
        "financials": {
            "revenue_q3_actual": 1_210_000_000,
            "revenue_q3_prior_year": 1_180_000_000,
            "revenue_growth_yoy": 2.54,
            "gross_margin": 34.8,
            "operating_expenses": 398_000_000,
            "ebitda": 218_000_000,
            "ebitda_margin": 18.0,
            "free_cash_flow": 142_000_000,
            "net_revenue_retention": None,  # N/A for manufacturing
            "customer_churn_rate": None,
            "inventory_days": 68,
            "backlog_value": 2_340_000_000,
        },
        "forward_guidance": {
            "q4_revenue_low": 1_180_000_000,
            "q4_revenue_high": 1_220_000_000,
            "q4_opex_projected": 395_000_000,
            "fy2024_revenue_target": 4_810_000_000,
        },
        "macro_context": {
            "fed_funds_rate": 5.25,
            "industrial_pmi": 47.2,  # Contraction territory
            "energy_cost_yoy_increase_pct": 18.4,
            "steel_price_qoq_change_pct": -3.2,
        },
        "risks": [
            "PMI at 47.2 signals potential demand softening in H1 2025",
            "Energy costs up 18% YoY — squeezing gross margins",
            "Two Tier-1 auto customers deferring 2025 orders",
            "Port congestion impacting just-in-time inventory targets",
        ],
        "opportunities": [
            "Defense backlog of $890M — multi-year visibility",
            "Reshoring tailwinds driving domestic capacity inquiries +28%",
            "Automation capex reducing labor cost by est. $22M/year by 2026",
        ],
    },

    "REIT1": {
        "company": "PropTrust Commercial REIT (NYSE: REIT1)",
        "period": "Q3 2024",
        "next_period": "Q4 2024",
        "context": "Diversified commercial REIT, $12B assets, navigating office vacancy and rate environment",
        "data_source": "Synthetic — modeled after NAREIT commercial REIT benchmarks",
        "financials": {
            "revenue_q3_actual": 318_000_000,
            "revenue_q3_prior_year": 309_000_000,
            "revenue_growth_yoy": 2.91,
            "gross_margin": 62.1,
            "operating_expenses": 198_000_000,
            "ebitda": 182_000_000,
            "ebitda_margin": 57.2,
            "funds_from_operations": 156_000_000,  # FFO — key REIT metric
            "occupancy_rate": 87.4,
            "weighted_avg_lease_term_years": 6.2,
            "debt_to_ebitda": 7.8,
        },
        "forward_guidance": {
            "q4_revenue_low": 312_000_000,
            "q4_revenue_high": 325_000_000,
            "q4_opex_projected": 201_000_000,
            "fy2024_ffo_per_share_target": 4.82,
        },
        "macro_context": {
            "fed_funds_rate": 5.25,
            "10yr_treasury_yield": 4.68,
            "office_vacancy_national_pct": 19.6,
            "cap_rate_spread_vs_treasuries_bps": 142,
        },
        "risks": [
            "Office segment vacancy at 23% — well above pre-COVID levels",
            "Debt refinancing: $840M maturing in 2025 at current rate environment",
            "Two anchor tenants (15% of office revenue) not renewing",
            "Rising insurance costs in coastal markets (+31% YoY)",
        ],
        "opportunities": [
            "Industrial/logistics assets now 38% of portfolio — 96.4% occupied",
            "Data center conversion of 2 office buildings — $180M capex, 7.1% yield",
            "Life sciences demand absorbing 400K sqft in Boston/San Diego",
        ],
    },
}


def get_scenario_by_ticker(ticker: str) -> Optional[dict]:
    """Return pre-built scenario or None if ticker not found."""
    return SCENARIOS.get(ticker.upper())


def get_all_scenarios() -> dict:
    return SCENARIOS


async def fetch_real_scenario(ticker: str) -> Optional[dict]:
    """Fetch a live scenario for any US public ticker from SEC EDGAR.

    Falls back to pre-built scenarios first; fetches from EDGAR for all others.
    Fetches EDGAR facts and FRED fed funds rate in parallel.
    """
    ticker = ticker.upper().strip()
    if ticker in SCENARIOS:
        return SCENARIOS[ticker]

    result = await lookup_cik_by_ticker(ticker)
    if not result:
        return None
    cik, company_name = result

    facts, fed_rate = await asyncio.gather(
        fetch_edgar_facts(cik),
        fetch_fed_funds_rate(),
    )
    if not facts:
        return None

    return build_edgar_scenario(ticker, company_name, facts, fed_rate)


# ── Data Source Guide for Interviewers ─────────────────────────────────────────
DATA_SOURCES_GUIDE = """
REAL DATA SOURCES FOR PRODUCTION VERSION
=========================================

1. SEC EDGAR (FREE, no API key)
   - URL: https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json
   - Contains: All GAAP financials from 10-Q/10-K filings
   - Coverage: All US public companies
   - Code: See fetch_edgar_facts() in this file

2. Financial Modeling Prep (FMP)
   - URL: https://financialmodelingprep.com/developer/docs/
   - Free tier: 250 calls/day
   - Contains: Income statement, balance sheet, cash flow, segments
   - Best for: Structured quarterly data, ready to consume

3. Alpha Vantage (FREE tier)
   - URL: https://www.alphavantage.co/
   - Free tier: 25 calls/day
   - Contains: Earnings, revenue estimates, analyst consensus

4. EDGAR Full-Text Search
   - URL: https://efts.sec.gov/LATEST/search-index?q="Q3+2024"&dateRange=custom&startdt=2024-10-01&enddt=2024-11-30&forms=10-Q
   - Use to find actual 10-Q text with MD&A sections

5. OpenBB (Open Source Bloomberg Terminal)
   - GitHub: openbb-finance/OpenBBTerminal
   - Python SDK for standardized financial data from 20+ providers

6. Macro Data (FREE)
   - Fed FRED API: https://fred.stlouisfed.org/docs/api/fred/
   - BLS API: https://www.bls.gov/developers/
   - Contains: Interest rates, CPI, PPI, employment
"""

if __name__ == "__main__":
    print(DATA_SOURCES_GUIDE)
    print("\nAvailable scenarios:", list(SCENARIOS.keys()))
