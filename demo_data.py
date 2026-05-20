"""
Pre-recorded demo output for TechCorp Inc. (TCORP) — Q3 2024 debate.
Used by the "Load Demo" button so interviewers can see the full UI
without needing an API key or waiting for a live run.
"""

import json

DEMO_SCENARIO_MD = """
## 📊 TechCorp Inc. (NASDAQ: TCORP)
**Period:** Q3 2024 | **Context:** Mid-cap SaaS company, $2.1B ARR, facing macro headwinds and competitive pricing pressure

| Metric | Most Recent Quarter | Next Quarter Guidance |
|--------|--------------------|-----------------------|
| Revenue | $521,000,000 | $530,000,000 – $545,000,000 |
| YoY Growth | 7.0% | — |
| Gross Margin | 71.2% | — |
| EBITDA | $89,000,000 (17.1%) | — |
| Free Cash Flow | $62,000,000 | — |

**⚠️ Key Risks**
- 3 enterprise deals ($47M TCV) slipped to Q4 from Q3
- Key sales VP departed; replacement hired but ramping
- New EU data residency requirements affecting EMEA expansion

**💡 Key Opportunities**
- AI add-on module launched — $8M ARR in first 60 days
- Federal vertical pipeline up 41% YoY
- India R&D center reduces engineering cost by ~$15M annualized

*📁 Data source: Synthetic — modeled after SaaS industry benchmarks (OpenView, Bessemer)*
"""

DEMO_RA = """
**Q3 2024 Revenue Performance — TechCorp Inc.**

Revenue came in at $521M for Q3, representing 7.0% year-over-year growth against a challenging macro backdrop where 34% of our enterprise IT buyer segment has implemented budget freezes. This result is commendable given those conditions.

**Net Revenue Retention at 108%** is the most telling signal here. Our existing customer base continues to expand spend, which demonstrates genuine product-market fit and pricing power within the installed base. This is the foundation of durable SaaS growth.

**AI Module Launch:** The AI add-on achieved $8M ARR within 60 days of launch — roughly $48M annualized run rate if we hold that trajectory. This is early-stage evidence of a meaningful upsell motion that could structurally improve NRR over the next 4–6 quarters.

**Federal Vertical:** Pipeline up 41% YoY. Federal contracts typically have longer sales cycles but significantly higher retention rates (avg. 94% GRR in our segment). This is a quality-of-revenue improvement, not just a quantity story.

**The 3 slipped enterprise deals** ($47M TCV) are a timing event, not a loss. All three have signed LOIs and verbal commitments from procurement. Two are expected to close in October. The revenue is in the pipeline — it moved right on the calendar, not out of the funnel.

**Guidance reaffirmation:** $530–545M for Q4 is achievable. The slip recovery plus AI module momentum plus Federal close rates give us high-confidence coverage of the low end of that range.
"""

DEMO_CA = """
**Cross-Examination: Q3 2024 Cost & Efficiency Analysis — TechCorp Inc.**

I want to pressure-test the revenue narrative with some structural cost concerns that deserve board attention.

**Opex Ratio Deterioration:** Operating expenses of $398M against $521M revenue yields a 76.4% opex ratio. For a SaaS business at this scale and growth rate, that is elevated. Comparable SaaS companies at similar ARR ($2B+) typically operate at 65–70% opex ratios. The gap suggests we are not yet achieving the operating leverage this business model should deliver.

**CAC Payback at 28 Months Is a Problem:** This is 8–10 months above the SaaS benchmark for efficient growth (18–20 months). At a 5.25% fed funds rate, the cost of capital has materially increased the economic weight of a 28-month payback period. We are effectively lending customers money for over two years before we break even on acquisition cost.

**The Deal Slip Story Deserves Scrutiny:** Three enterprise deals totaling $47M TCV "slipping" in a single quarter is not a random timing event — it is a pattern signal. When deals slip from Q3 to Q4, CFOs must ask: are we seeing elongating sales cycles (a leading indicator of demand softening), or are we seeing sales execution issues following the VP departure? These require different responses.

**Sales Leadership Gap:** The VP of Sales departure mid-year, with a replacement currently ramping, creates a measurable productivity trough. Enterprise SaaS sales reps typically reach full productivity at 9–12 months. We are likely 4–6 months into that ramp. Q4 close rates may be structurally lower than historical averages regardless of pipeline quality.

**AWS Partnership Renegotiation:** A potential 2 percentage point margin impact from AWS renegotiation has not been reflected in Q4 guidance. If that materializes, $545M revenue with compressed margins could produce EBITDA well below the $89M Q3 watermark.

The revenue trajectory is real, but the path to profitable growth requires more aggressive cost discipline than the current opex structure demonstrates.
"""

DEMO_RO_BASE = """
**Risk Audit: Q3 2024 Debate Assessment — TechCorp Inc.**

Having reviewed the Revenue Analyst and Cost Analyst positions, I am flagging two material risks that warrant CFO-level attention before the board presentation.

**Risk 1 — Deal Concentration in Q4 Pipeline (HIGH)**
The $47M TCV now sitting in Q4 represents approximately 8.6% of full-quarter revenue guidance midpoint ($537.5M). If even one of these three deals does not close by December 31, Q4 revenue lands below the $530M guidance floor. This is not a tail risk — it is a base-case dependency. The board should receive scenario analysis showing guidance with and without the slipped pipeline converting.

**Risk 2 — AWS Renegotiation Margin Impact (MEDIUM-HIGH)**
A 2pp gross margin compression on $521M quarterly revenue is approximately $10.4M per quarter, or $41.6M annualized. This has not been modeled into Q4 guidance. If renegotiation completes unfavorably in Q4, EBITDA guidance is materially misstated. The CFO should disclose this contingency in the board package.

**Risk 3 — Sales Productivity Gap (MEDIUM)**
The Cost Analyst correctly identified the sales leadership transition risk. I would add: Q4 is historically the highest-volume quarter for enterprise SaaS closes. Running that quarter with a sales organization in leadership transition amplifies execution risk precisely when it matters most.

**Mitigating Factors:**
- NRR of 108% provides a durable revenue floor — churn alone cannot crater the quarter
- AI module momentum ($8M ARR in 60 days) is a genuine positive signal
- Federal pipeline provides some diversification from commercial sales cycle volatility

**Escalation Assessment:** Disagreement between Revenue and Cost analysts is substantive but not irreconcilable. The core facts are not in dispute — the interpretation of deal slippage causation and CAC trajectory are judgment calls. I am not triggering a formal escalation, but I am recommending the CFO weight the Cost Analyst's structural concerns heavily in the board recommendation.
"""

DEMO_CFO = """
**CFO Board Recommendation — TechCorp Inc. Q3 2024**

*Synthesized from multi-agent debate across Revenue Analysis, Cost Cross-Examination, and Risk Audit*

---

**EXECUTIVE SUMMARY**

**Recommendation: HOLD guidance. Implement targeted cost discipline. Escalate deal monitoring.**

TechCorp delivered a solid Q3 in a difficult environment. The 7% YoY revenue growth, 108% NRR, and early AI module traction demonstrate that the core business is healthy. However, structural cost inefficiencies and concentrated Q4 pipeline risk require proactive management before the board can have full confidence in the full-year target.

---

**FINANCIAL ASSESSMENT**

Q3 revenue of $521M met internal targets. The growth rate, while below our historical 12–15% CAGR, reflects deliberate caution in a macro environment where 34% of enterprise IT buyers are operating under budget freezes. This is a defensible outcome, not a miss.

The more important number is NRR at 108%. In a high-rate environment, retention-driven growth is economically superior to acquisition-driven growth. Our existing customers are expanding — that is the most durable form of SaaS revenue and it de-risks the installed base significantly.

**Q4 Guidance: Maintaining $530–545M range.** This is achievable but requires two conditions: (1) at least two of the three slipped enterprise deals close by December 31, and (2) no adverse AWS renegotiation outcome in Q4. Both are probable but not certain. The board should treat $530M as the floor with explicit contingency planning if slipped deals push into Q1.

---

**COST STRUCTURE: ACTION REQUIRED**

The Cost Analyst raised a valid concern. A 76.4% opex ratio at our scale and growth rate is above peer benchmarks. Operating leverage is the defining financial story of mature SaaS — we need to demonstrate it.

**Recommended Actions:**
1. Freeze net new headcount additions in G&A and non-product-adjacent engineering through Q2 2025
2. Accelerate the India R&D center transition — the $15M annualized savings should be front-loaded
3. Set a hard target: opex ratio below 72% by Q2 2025
4. CAC payback improvement to 24 months within 3 quarters, driven by improved sales productivity as new VP ramps

---

**RISK POSTURE**

I accept the Risk Officer's assessment. The $47M Q4 pipeline dependency is a board disclosure item. I will include scenario analysis (base / bear case) in the board package.

AWS renegotiation will be disclosed as a contingent margin risk with a quantified range ($8–10M quarterly impact if 2pp compression materializes).

---

**STRATEGIC SIGNAL**

The AI module result is strategically significant. $8M ARR in 60 days with no dedicated sales motion suggests strong organic demand. I am recommending we allocate 2 AEs and a dedicated CSM to the AI module in Q4, funded from the G&A freeze savings. If the trajectory holds, AI becomes a separate line item in Q1 2025 board reporting.

---

**CONCLUSION**

TechCorp is navigating a difficult macro environment with its core business intact. The path to re-accelerating growth runs through: (1) closing the slipped pipeline, (2) demonstrating cost discipline, and (3) capitalizing on AI module momentum. The board should expect updated guidance with a wider scenario range at the Q4 earnings call.

*Confidence Level: 82% | Debate Disagreement Score: 41% (moderate — structural cost concerns acknowledged)*
"""

DEMO_REBUTTAL_SUFFIX = """

**[REBUTTAL — Phase 3]**

I want to directly address the Cost Analyst's points on deal slippage and CAC.

On deal slippage: I have visibility into the deal status that the Cost Analyst does not. These are not symptoms of elongating sales cycles across the board — they are specific to two deals that hit procurement delays (one due to a customer merger, one due to fiscal year-end timing on the customer side) and one that required additional security review for a data residency configuration. These are external factors, not sales execution failures.

On CAC payback: The 28-month figure uses trailing 12-month blended CAC. The more relevant forward-looking metric is new cohort CAC, which has been improving for 3 consecutive quarters as we shift mix toward inbound and product-led acquisition. The India R&D center also reduces the denominator — our cost per rep will decrease as engineering costs fall. We expect to report 24-month CAC payback in Q2 2025.

On sales leadership: The new VP comes from a company that scaled from $800M to $2.1B ARR in 3 years. She is not a ramping junior rep — she is an experienced operator who understands enterprise SaaS motion. The Q4 risk is real but manageable.

The structural concerns raised are fair inputs to the CFO recommendation. I am not dismissing them. I am providing the context that changes their severity from "warning signs" to "items to monitor."
"""

DEMO_TRANSCRIPT = f"""
---
### 📈 Revenue Analyst
**🔵 Phase 1: Independent Analysis** | Confidence: 85% | 2024-11-15 09:01:14

{DEMO_RA}

---
### 🔍 Cost Analyst
**🟠 Phase 2: Cross-Examination** | Confidence: 78% | 2024-11-15 09:02:31

{DEMO_CA}

---
### 📈 Revenue Analyst
**🟠 Phase 3: Revenue Rebuttal** | Confidence: 80% | 2024-11-15 09:03:48

{DEMO_REBUTTAL_SUFFIX.replace("[REBUTTAL — Phase 3]", "Rebuttal Response")}

---
### 🚨 Risk Officer
**🔴 Phase 4: Risk Audit** | Confidence: 88% | 2024-11-15 09:05:02

{DEMO_RO_BASE}

---
### 🏦 CFO
**🟣 Phase 5: CFO Board Recommendation** | Confidence: 82% | 2024-11-15 09:06:19

{DEMO_CFO}
"""

DEMO_RA_FULL = DEMO_RA + DEMO_REBUTTAL_SUFFIX

DEMO_META = json.dumps({
    "company": "TechCorp Inc. (NASDAQ: TCORP)",
    "period": "Q3 2024",
    "scenario_md": DEMO_SCENARIO_MD,
})