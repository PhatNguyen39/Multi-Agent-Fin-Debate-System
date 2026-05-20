"""
Multi-Agent Finance Debate System
LangGraph-based: Revenue Analyst → Cost Analyst → Risk Officer → CFO Synthesizer
"""

import asyncio
import json
import os
from typing import TypedDict, List, Annotated, Optional
from datetime import datetime
import operator

from langgraph.graph import StateGraph, END
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

# ── LLM Setup ──────────────────────────────────────────────────────────────
def get_llm(temperature: float = 0.7):
    return ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        temperature=temperature,
        max_tokens=1024,
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
    )

# ── State Schema ────────────────────────────────────────────────────────────
class AgentMessage(TypedDict):
    agent: str
    role: str
    phase: str
    content: str
    timestamp: str
    confidence: float
    flags: List[str]

class FinanceState(TypedDict):
    scenario: dict                             # quarter financial scenario
    messages: Annotated[List[AgentMessage], operator.add]
    revenue_analysis: Optional[str]
    cost_analysis: Optional[str]
    risk_assessment: Optional[str]
    debate_log: Annotated[List[dict], operator.add]
    escalation_triggered: bool
    escalation_reason: Optional[str]
    final_recommendation: Optional[str]
    phase: str
    disagreement_score: float                  # 0-1 measure of agent disagreement

# ── Scenario Builder ─────────────────────────────────────────────────────────
SAMPLE_SCENARIO = {
    "company": "TechCorp Inc. (NASDAQ: TCORP)",
    "period": "Q3 2024",
    "context": "Mid-cap SaaS company, $2.1B ARR, facing macro headwinds",
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
}

# ── Agent Prompts ────────────────────────────────────────────────────────────
RA_SYSTEM = """You are the Revenue Analyst at TechCorp's CFO office. 
You are analytically rigorous, optimistic but data-driven, and defend revenue projections with specific metrics.
You cite NRR, pipeline coverage ratios, and cohort retention as your primary evidence.
When challenged, you hold your ground with data but acknowledge legitimate concerns.
Speak in first person. Be specific with numbers. Keep responses to 200-300 words.
Format key metrics as [METRIC: value] inline."""

CA_SYSTEM = """You are the Cost Analyst at TechCorp's CFO office.
You are skeptical of revenue projections and laser-focused on margin compression risks.
You cross-examine assumptions, question CAC payback periods, and flag opex creep.
You are the devil's advocate. You challenge optimistic projections with structural cost arguments.
When debating, be pointed but professional. Keep responses 200-300 words.
Format cost concerns as [RISK: description] inline."""

RO_SYSTEM = """You are the Chief Risk Officer at TechCorp's CFO office.
You synthesize revenue vs cost tensions into a formal risk escalation framework.
You assign probability-weighted impact scores, identify tail risks, and decide escalation.
Your job is to be the honest broker — neither optimistic nor pessimistic, but rigorous.
Produce a structured risk register with LIKELIHOOD (Low/Med/High) and IMPACT (1-5).
Keep responses 250-350 words. End with a clear ESCALATE: YES/NO decision."""

CFO_SYSTEM = """You are the CFO of TechCorp Inc., preparing a board recommendation.
You have received the full debate between Revenue Analyst, Cost Analyst, and Risk Officer.
Your job is to synthesize the debate into a decisive, board-ready recommendation.
Structure your output EXACTLY as:
## EXECUTIVE SUMMARY (2 sentences)
## Q4 GUIDANCE RECOMMENDATION
- Revenue: $[low]M–$[high]M
- EBITDA Margin: X%–Y%
- Key Assumption: [one sentence]
## TOP 3 RISKS TO GUIDANCE
1. [Risk + mitigation]
2. [Risk + mitigation]  
3. [Risk + mitigation]
## BOARD RECOMMENDATION
[MAINTAIN/RAISE/LOWER] guidance. [2-3 sentence rationale]
## DISSENTING VIEW
[Acknowledge the losing argument in 1 sentence]"""

# ── Agent Nodes ──────────────────────────────────────────────────────────────
async def revenue_analyst_node(state: FinanceState) -> dict:
    llm = get_llm(temperature=0.7)
    scenario = state["scenario"]
    fin = scenario["financials"]
    fwd = scenario["forward_guidance"]

    period = scenario.get("period", "Most Recent Quarter")
    next_period = scenario.get("next_period", "Next Quarter")

    prompt = f"""Analyze the {period} results for {scenario['company']} and defend your {next_period} revenue guidance.

{period} ACTUALS:
- Revenue: ${fin['revenue_q3_actual']:,} ({fin['revenue_growth_yoy']:.1f}% YoY)
- Gross Margin: {fin['gross_margin']}%
- NRR: {fin.get('net_revenue_retention', 'N/A')}%
- Churn: {fin.get('customer_churn_rate', 'N/A')}%
- CAC Payback: {fin.get('cac_payback_months', 'N/A')} months

{next_period} GUIDANCE RANGE: ${fwd['q4_revenue_low']:,} – ${fwd['q4_revenue_high']:,}

KEY FACTS:
- {scenario['risks'][0]}
- {scenario['opportunities'][0]}

Provide your revenue analysis and defend the {next_period} guidance range. Be specific about pipeline coverage and NRR expansion assumptions."""

    response = await llm.ainvoke([
        SystemMessage(content=RA_SYSTEM),
        HumanMessage(content=prompt)
    ])

    msg: AgentMessage = {
        "agent": "Revenue Analyst",
        "role": "RA",
        "phase": "Phase 1 — Analysis",
        "content": response.content,
        "timestamp": datetime.now().isoformat(),
        "confidence": 0.78,
        "flags": ["PIPELINE_COVERAGE", "NRR_EXPANSION"]
    }

    return {
        "revenue_analysis": response.content,
        "messages": [msg],
        "phase": "cost_analysis"
    }


async def cost_analyst_node(state: FinanceState) -> dict:
    llm = get_llm(temperature=0.75)
    scenario = state["scenario"]
    fin = scenario["financials"]
    fwd = scenario["forward_guidance"]

    period = scenario.get("period", "Most Recent Quarter")
    next_period = scenario.get("next_period", "Next Quarter")
    macro = scenario.get("macro_context", {})

    prompt = f"""You are the Cost Analyst for {scenario['company']}. First form your own independent view from the raw data, then challenge the Revenue Analyst.

STEP 1 — YOUR INDEPENDENT COST ANALYSIS (from raw data):
- {period} Revenue: ${fin['revenue_q3_actual']:,} ({fin['revenue_growth_yoy']:.1f}% YoY)
- {period} OpEx: ${fin['operating_expenses']:,}
- {next_period} Projected OpEx: ${fwd['q4_opex_projected']:,} (+${fwd['q4_opex_projected'] - fin['operating_expenses']:,} sequential)
- Gross Margin: {fin.get('gross_margin', 'N/A')}%
- EBITDA: ${fin.get('ebitda', 0):,} ({fin.get('ebitda_margin', 'N/A')}% margin)
- Sales Cycle: {fin.get('sales_cycle_days', 'N/A')} days
- CAC Payback: {fin.get('cac_payback_months', 'N/A')} months
- IT Budget Freeze: {macro.get('customer_segment_IT_budget_freeze_pct', 'N/A')}% of customer segment
- Competitor price cuts: {macro.get('competitor_pricing_cuts_pct', 'N/A')}%

STRUCTURAL RISKS TO CONSIDER:
{chr(10).join('- ' + r for r in scenario['risks'])}

STEP 2 — CHALLENGE THE REVENUE ANALYST:
Now read their position and identify where their assumptions conflict with your independent analysis.

REVENUE ANALYST'S POSITION:
{state['revenue_analysis']}

Provide: (1) your independent cost view, (2) specific points where you disagree with the RA and why. Be adversarial but factual. Focus on margin compression, opex ramp, and CAC efficiency."""

    response = await llm.ainvoke([
        SystemMessage(content=CA_SYSTEM),
        HumanMessage(content=prompt)
    ])

    msg: AgentMessage = {
        "agent": "Cost Analyst",
        "role": "CA",
        "phase": "Phase 2 — Cross-Examination",
        "content": response.content,
        "timestamp": datetime.now().isoformat(),
        "confidence": 0.82,
        "flags": ["MARGIN_COMPRESSION", "OPEX_RAMP_RISK"]
    }

    return {
        "cost_analysis": response.content,
        "messages": [msg],
        "phase": "revenue_rebuttal"
    }


async def revenue_rebuttal_node(state: FinanceState) -> dict:
    llm = get_llm(temperature=0.8)

    prompt = f"""The Cost Analyst has challenged your Q4 projections. Rebut their concerns point by point.

COST ANALYST'S CHALLENGE:
{state['cost_analysis']}

Your Q3 context:
- NRR of {state['scenario']['financials']['net_revenue_retention']}% means existing customers will expand
- AI module at ${state['scenario']['opportunities'][0]}
- Federal pipeline: {state['scenario']['opportunities'][1]}

Provide a sharp, data-backed rebuttal. Acknowledge 1-2 valid points from CA but hold your guidance."""

    response = await llm.ainvoke([
        SystemMessage(content=RA_SYSTEM),
        HumanMessage(content=prompt)
    ])

    msg: AgentMessage = {
        "agent": "Revenue Analyst",
        "role": "RA",
        "phase": "Phase 3 — Rebuttal",
        "content": response.content,
        "timestamp": datetime.now().isoformat(),
        "confidence": 0.71,
        "flags": ["REBUTTAL", "CONCESSION_MINOR"]
    }

    debate_entry = {
        "round": 1,
        "ra_position": state["revenue_analysis"],
        "ca_challenge": state["cost_analysis"],
        "ra_rebuttal": response.content,
    }

    return {
        "messages": [msg],
        "debate_log": [debate_entry],
        "phase": "risk_assessment"
    }


async def risk_officer_node(state: FinanceState) -> dict:
    llm = get_llm(temperature=0.5)
    scenario = state["scenario"]

    debate_summary = f"""
REVENUE ANALYST (Initial):
{state['revenue_analysis'][:500]}...

COST ANALYST (Challenge):
{state['cost_analysis'][:500]}...

REVENUE ANALYST (Rebuttal):
{state['messages'][-1]['content'][:400]}...
"""

    macro = scenario.get("macro_context", {})
    next_period = scenario.get("next_period", "Next Quarter")

    fin = scenario["financials"]
    fwd = scenario["forward_guidance"]
    period = scenario.get("period", "Most Recent Quarter")

    prompt = f"""You are the Chief Risk Officer for {scenario['company']}. Form your own independent risk view from the raw data first, then audit the debate.

STEP 1 — YOUR INDEPENDENT RISK ASSESSMENT (from raw financials):
- {period} Revenue: ${fin['revenue_q3_actual']:,} ({fin['revenue_growth_yoy']:.1f}% YoY growth)
- Gross Margin: {fin.get('gross_margin', 'N/A')}% | EBITDA Margin: {fin.get('ebitda_margin', 'N/A')}%
- Free Cash Flow: ${fin.get('free_cash_flow', 0):,}
- {next_period} Revenue Guidance: ${fwd['q4_revenue_low']:,} – ${fwd['q4_revenue_high']:,}
- {next_period} OpEx: ${fwd['q4_opex_projected']:,}
- Fed Funds Rate: {macro.get('fed_funds_rate', 'N/A')}%
- Sector Growth: {macro.get('enterprise_software_growth_sector', macro.get('industrial_pmi', 'N/A'))}

KNOWN RISKS:
{chr(10).join('- ' + r for r in scenario['risks'])}

KNOWN OPPORTUNITIES:
{chr(10).join('- ' + o for o in scenario['opportunities'])}

STEP 2 — AUDIT THE DEBATE:
Now review what the analysts argued and identify where they were right, wrong, or missing key risks.

{debate_summary}

Produce your formal risk register. Score each risk (LIKELIHOOD: Low/Med/High, IMPACT: 1-5), identify gaps in both analysts' views, and decide: ESCALATE: YES or ESCALATE: NO."""

    response = await llm.ainvoke([
        SystemMessage(content=RO_SYSTEM),
        HumanMessage(content=prompt)
    ])

    # Parse escalation decision from response
    escalate = "ESCALATE: YES" in response.content.upper()
    escalation_reason = None
    if escalate:
        lines = response.content.split('\n')
        for i, line in enumerate(lines):
            if "escalate" in line.lower() and "yes" in line.lower():
                escalation_reason = lines[i+1] if i+1 < len(lines) else "Material disagreement on Q4 assumptions"
                break

    msg: AgentMessage = {
        "agent": "Risk Officer",
        "role": "RO",
        "phase": "Phase 4 — Audit",
        "content": response.content,
        "timestamp": datetime.now().isoformat(),
        "confidence": 0.88,
        "flags": ["ESCALATE"] if escalate else ["PASS_TO_CFO"]
    }

    # Compute disagreement score from debate
    disagreement_score = 0.72 if escalate else 0.45  # simplified

    return {
        "risk_assessment": response.content,
        "messages": [msg],
        "escalation_triggered": escalate,
        "escalation_reason": escalation_reason,
        "disagreement_score": disagreement_score,
        "phase": "cfo_synthesis"
    }


async def cfo_synthesis_node(state: FinanceState) -> dict:
    llm = get_llm(temperature=0.4)
    scenario = state["scenario"]
    fwd = scenario["forward_guidance"]

    escalation_note = ""
    if state.get("escalation_triggered"):
        escalation_note = f"\n⚠️ ESCALATION FLAG: Risk Officer has escalated this debate. Reason: {state.get('escalation_reason', 'Material disagreement')}\n"

    next_period = scenario.get("next_period", "Next Quarter")

    prompt = f"""You are the CFO. Produce the board recommendation for {scenario['company']} — {next_period} outlook.

{escalation_note}

FULL DEBATE RECORD:

=== REVENUE ANALYST ===
{state['revenue_analysis']}

=== COST ANALYST ===
{state['cost_analysis']}

=== RISK OFFICER ===
{state['risk_assessment']}

CURRENT GUIDANCE:
- {next_period} Revenue Range: ${fwd['q4_revenue_low']:,} – ${fwd['q4_revenue_high']:,}
- {next_period} OpEx Target: ${fwd['q4_opex_projected']:,}
- Full-Year Target: ${fwd['fy2024_revenue_target']:,}

DISAGREEMENT SCORE: {state.get('disagreement_score', 0.5):.0%} tension between analysts

Produce your structured board recommendation following the exact format in your system instructions."""

    response = await llm.ainvoke([
        SystemMessage(content=CFO_SYSTEM),
        HumanMessage(content=prompt)
    ])

    msg: AgentMessage = {
        "agent": "CFO",
        "role": "CFO",
        "phase": "Phase 5 — Synthesis",
        "content": response.content,
        "timestamp": datetime.now().isoformat(),
        "confidence": 0.91,
        "flags": ["BOARD_RECOMMENDATION", "FINAL"]
    }

    return {
        "final_recommendation": response.content,
        "messages": [msg],
        "phase": "complete"
    }


# ── Graph Assembly ────────────────────────────────────────────────────────────
def build_graph():
    graph = StateGraph(FinanceState) # FinanceState is the shared state

    graph.add_node("revenue_analyst", revenue_analyst_node)
    graph.add_node("cost_analyst", cost_analyst_node)
    graph.add_node("revenue_rebuttal", revenue_rebuttal_node)
    graph.add_node("risk_officer", risk_officer_node)
    graph.add_node("cfo_synthesis", cfo_synthesis_node)

    graph.set_entry_point("revenue_analyst")
    graph.add_edge("revenue_analyst", "cost_analyst")
    graph.add_edge("cost_analyst", "revenue_rebuttal")
    graph.add_edge("revenue_rebuttal", "risk_officer")
    graph.add_edge("risk_officer", "cfo_synthesis")
    graph.add_edge("cfo_synthesis", END)

    return graph.compile()

'''
#testing
# ── Runner ────────────────────────────────────────────────────────────────────
async def run_debate(scenario: dict = None, stream_callback=None) -> FinanceState:
    if scenario is None:
        scenario = SAMPLE_SCENARIO

    initial_state: FinanceState = {
        "scenario": scenario,
        "messages": [],
        "revenue_analysis": None,
        "cost_analysis": None,
        "risk_assessment": None,
        "debate_log": [],
        "escalation_triggered": False,
        "escalation_reason": None,
        "final_recommendation": None,
        "phase": "starting",
        "disagreement_score": 0.0,
    }

    app = build_graph()


    if stream_callback:
        final_state = dict(initial_state)
        async for event in app.astream(initial_state):
            for node_name, node_output in event.items():
                if "messages" in node_output and node_output["messages"]:
                    latest = node_output["messages"][-1]
                    await stream_callback(latest)
                final_state.update(node_output)
        return final_state
    else:
        return await app.ainvoke(initial_state)


if __name__ == "__main__":
    async def main():
        result = await run_debate()
        print("\n" + "="*60)
        print("FINAL CFO RECOMMENDATION")
        print("="*60)
        print(result["final_recommendation"])

    asyncio.run(main())
'''
