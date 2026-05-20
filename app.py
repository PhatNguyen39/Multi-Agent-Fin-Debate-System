"""
Gradio Interface — HuggingFace Spaces compatible
Run: python app.py
HF Spaces URL: https://huggingface.co/spaces/PhatNguyen39/finance-agent-debate
"""

import asyncio
import os
import re
import tempfile
import json
from datetime import datetime
from dotenv import load_dotenv
import gradio as gr
from fpdf import FPDF

load_dotenv()

from agents import build_graph, FinanceState
from data_loader import get_scenario_by_ticker, fetch_real_scenario, SCENARIOS
from demo_data import (
    DEMO_SCENARIO_MD, DEMO_TRANSCRIPT, DEMO_RA_FULL,
    DEMO_CA, DEMO_RO_BASE, DEMO_CFO, DEMO_META,
)

# ── Color / Style constants ──────────────────────────────────────────────────
AGENT_COLORS = {
    "Revenue Analyst": "#22c55e",
    "Cost Analyst":    "#f97316",
    "Risk Officer":    "#ef4444",
    "CFO":             "#8b5cf6",
}

AGENT_ICONS = {
    "Revenue Analyst": "📈",
    "Cost Analyst":    "🔍",
    "Risk Officer":    "🚨",
    "CFO":             "🏦",
}

PHASE_LABELS = {
    "Phase 1 — Analysis":       "🔵 Phase 1: Independent Analysis",
    "Phase 2 — Cross-Examination": "🟠 Phase 2: Cross-Examination",
    "Phase 3 — Rebuttal":       "🟠 Phase 3: Revenue Rebuttal",
    "Phase 4 — Audit":          "🔴 Phase 4: Risk Audit",
    "Phase 5 — Synthesis":      "🟣 Phase 5: CFO Board Recommendation",
}

# Ordered pipeline of all 5 turns — used to render the live tracker
TURN_PIPELINE = [
    ("revenue_analyst",  "📈 Revenue Analyst",           "Phase 1 — Analysis"),
    ("cost_analyst",     "🔍 Cost Analyst",               "Phase 2 — Cross-Examination"),
    ("revenue_rebuttal", "📈 Revenue Analyst (Rebuttal)", "Phase 3 — Rebuttal"),
    ("risk_officer",     "🚨 Risk Officer",               "Phase 4 — Audit"),
    ("cfo_synthesis",    "🏦 CFO",                        "Phase 5 — Synthesis"),
]


def build_turns_md(completed: set, active: str | None) -> str:
    total = len(TURN_PIPELINE)
    done = len(completed)
    lines = [f"**Phases complete: {done} / {total}**\n"]
    for node, label, phase in TURN_PIPELINE:
        if node in completed:
            lines.append(f"✅ &nbsp;**{label}**  \n&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;*{phase}*")
        elif node == active:
            lines.append(f"🔄 &nbsp;**{label}**  \n&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;*{phase}* — running...")
        else:
            lines.append(f"⬜ &nbsp;{label}  \n&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;*{phase}*")
    return "\n\n".join(lines)


def format_agent_block(msg: dict) -> str:
    agent = msg["agent"]
    icon = AGENT_ICONS.get(agent, "🤖")
    phase = PHASE_LABELS.get(msg["phase"], msg["phase"])
    confidence = msg.get("confidence", 0.8)
    timestamp = msg.get("timestamp", "")[:19]

    return f"""
---
### {icon} {agent}
**{phase}** | Confidence: {confidence:.0%} | {timestamp}

{msg["content"]}
"""


def _fmt(v, prefix="$") -> str:
    if v is None or v == 0:
        return "N/A"
    return f"{prefix}{v:,.0f}"


def scenario_summary_md(scenario: dict) -> str:
    fin = scenario["financials"]
    fwd = scenario["forward_guidance"]
    gross = fin.get("gross_margin") or "N/A"
    ebitda_m = fin.get("ebitda_margin") or "N/A"
    return f"""
## 📊 {scenario['company']}
**Period:** {scenario['period']} | **Context:** {scenario['context']}

| Metric | Most Recent Quarter | Next Quarter Guidance |
|--------|--------------------|-----------------------|
| Revenue | {_fmt(fin.get('revenue_q3_actual'))} | {_fmt(fwd.get('q4_revenue_low'))} – {_fmt(fwd.get('q4_revenue_high'))} |
| YoY Growth | {fin.get('revenue_growth_yoy', 0):.1f}% | — |
| Gross Margin | {gross}{'%' if gross != 'N/A' else ''} | — |
| EBITDA | {_fmt(fin.get('ebitda'))} ({ebitda_m}{'%' if ebitda_m != 'N/A' else ''}) | — |
| Free Cash Flow | {_fmt(fin.get('free_cash_flow'))} | — |

**⚠️ Key Risks**
{chr(10).join(f"- {r}" for r in scenario['risks'][:3])}

**💡 Key Opportunities**
{chr(10).join(f"- {o}" for o in scenario['opportunities'][:3])}

*📁 Data source: {scenario.get('data_source', 'Synthetic')}*
"""


# ── PDF helpers ──────────────────────────────────────────────────────────────
def _clean_for_pdf(text: str) -> str:
    text = re.sub(r'[^\x00-\x7F\u00C0-\u024F]+', ' ', text)   # strip emojis/non-latin
    text = re.sub(r'^#{1,2}\s+(.+)$', lambda m: m.group(1).upper(), text, flags=re.MULTILINE)
    text = re.sub(r'^#{3,6}\s+(.+)$', r'\1', text, flags=re.MULTILINE)
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'^[-*_]{3,}$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\|[-:| ]+\|', '', text)
    text = re.sub(r'\|', '  ', text)
    return text.strip()


class _PDF(FPDF):
    def __init__(self, company: str = ""):
        super().__init__()
        self.company = company
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"CONFIDENTIAL - {self.company}", align="L")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, f"Page {self.page_no()} - Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}", align="C")

    def section_title(self, title: str):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(60, 60, 140)
        self.ln(4)
        self.cell(0, 8, title, ln=True)
        self.set_draw_color(60, 60, 140)
        self.line(self.get_x(), self.get_y(), self.get_x() + 170, self.get_y())
        self.ln(3)
        self.set_text_color(0, 0, 0)

    def body_text(self, text: str):
        self.set_font("Helvetica", size=10)
        self.multi_cell(0, 6, _clean_for_pdf(text))
        self.ln(2)


def generate_transcript_pdf(transcript: str, scenario_md: str, company: str) -> str:
    pdf = _PDF(company=company)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 12, "Multi-Agent Finance Debate", ln=True, align="C")
    pdf.set_font("Helvetica", size=12)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 8, f"Full Debate Transcript - {company}", ln=True, align="C")
    pdf.cell(0, 8, datetime.now().strftime("%B %d, %Y"), ln=True, align="C")
    pdf.ln(10)

    pdf.section_title("Scenario Overview")
    pdf.body_text(scenario_md)

    pdf.section_title("Full Debate Transcript")
    pdf.body_text(transcript)

    path = tempfile.mktemp(suffix=".pdf")
    pdf.output(path)
    return path


def generate_board_report_pdf(cfo_out: str, scenario_md: str, company: str, period: str) -> str:
    pdf = _PDF(company=company)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 14, "BOARD OF DIRECTORS", ln=True, align="C")
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "CFO Quarterly Earnings Review & Recommendation", ln=True, align="C")
    pdf.set_font("Helvetica", size=11)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 8, f"{company}  |  {period}", ln=True, align="C")
    pdf.cell(0, 8, f"Prepared: {datetime.now().strftime('%B %d, %Y')}", ln=True, align="C")
    pdf.ln(10)

    pdf.section_title("Financial Scenario Summary")
    pdf.body_text(scenario_md)

    pdf.section_title("CFO Board Recommendation")
    pdf.body_text(cfo_out)

    pdf.section_title("Disclosure")
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 5,
        "This recommendation was synthesized by an AI-assisted multi-agent debate system "
        "(LangGraph + Anthropic Claude) from publicly available financial data. "
        "It is intended as decision-support material and should be reviewed by qualified "
        "financial professionals before any board action is taken.")

    path = tempfile.mktemp(suffix=".pdf")
    pdf.output(path)
    return path


async def run_full_debate(scenario_key: str, real_ticker: str, api_key: str = "", progress=gr.Progress()):
    real_ticker = (real_ticker or "").strip().upper()
    api_key = (api_key or "").strip()
    if api_key:
        os.environ["ANTHROPIC_API_KEY"] = api_key

    _empty = ("", "", "", "", "", "", build_turns_md(set(), None), "", "", "", "")

    if real_ticker:
        yield ("", f"*Contacting SEC EDGAR for **{real_ticker}**...*", "", "", "", "",
               build_turns_md(set(), None), f"🔄 Fetching EDGAR data for {real_ticker}...", "", "", "")
        scenario = await fetch_real_scenario(real_ticker)
        if not scenario:
            yield (
                "",
                f"❌ Could not retrieve EDGAR data for **{real_ticker}**. "
                "Check the ticker symbol and try again.",
                "", "", "", "",
                build_turns_md(set(), None),
                f"❌ EDGAR lookup failed for {real_ticker}",
                "", "", "",
            )
            return
    else:
        scenario = get_scenario_by_ticker(scenario_key)
        if not scenario:
            yield "❌ Scenario not found", "", "", "", "", "", build_turns_md(set(), None), "", "", "", ""
            return

    # Scenario header
    scenario_md = scenario_summary_md(scenario)

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

    graph = build_graph()

    debate_transcript = ""
    ra_out = ""
    ca_out = ""
    ro_out = ""
    cfo_out = ""
    status = "🔄 Running debate..."
    escalation_md = ""
    completed_turns: set = set()
    active_turn: str | None = None

    progress(0, desc="Starting multi-agent debate...")

    node_progress = {
        "revenue_analyst": 0.15,
        "cost_analyst":    0.35,
        "revenue_rebuttal": 0.55,
        "risk_officer":    0.75,
        "cfo_synthesis":   0.95,
    }

    node_desc = {
        "revenue_analyst": "📈 Revenue Analyst analyzing Q3...",
        "cost_analyst":    "🔍 Cost Analyst cross-examining...",
        "revenue_rebuttal": "⚡ Revenue Analyst rebuts...",
        "risk_officer":    "🚨 Risk Officer auditing tension...",
        "cfo_synthesis":   "🏦 CFO synthesizing recommendation...",
    }

    async for event in graph.astream(initial_state):
        for node_name, node_output in event.items():
            prog_val = node_progress.get(node_name, 0.5)
            desc = node_desc.get(node_name, "Processing...")
            progress(prog_val, desc=desc)

            active_turn = node_name

            if "messages" in node_output and node_output["messages"]:
                for msg in node_output["messages"]:
                    block = format_agent_block(msg)
                    debate_transcript += block

                    agent = msg["agent"]
                    if agent == "Revenue Analyst":
                        if "Rebuttal" in msg["phase"]:
                            ra_out += f"\n\n**[REBUTTAL]**\n{msg['content']}"
                        else:
                            ra_out = msg["content"]
                    elif agent == "Cost Analyst":
                        ca_out = msg["content"]
                    elif agent == "Risk Officer":
                        ro_out = msg["content"]
                    elif agent == "CFO":
                        cfo_out = msg["content"]

            if node_output.get("escalation_triggered"):
                reason = node_output.get("escalation_reason", "Material disagreement detected")
                score = node_output.get("disagreement_score", 0.7)
                escalation_md = f"""
## 🚨 ESCALATION TRIGGERED
**Disagreement Score:** {score:.0%}
**Reason:** {reason}
*The Risk Officer has flagged this debate for CFO review with dissenting views.*
"""
            completed_turns.add(node_name)
            active_turn = None

            yield (
                scenario_md,
                debate_transcript,
                ra_out,
                ca_out,
                ro_out + ("\n\n" + escalation_md if escalation_md else ""),
                cfo_out,
                build_turns_md(completed_turns, active_turn),
                status,
                "", "", "",  # state placeholders during run
            )

    progress(1.0, desc="✅ Debate complete!")
    status = f"✅ Debate complete — {datetime.now().strftime('%H:%M:%S')}"
    company = scenario.get("company", "Company")
    period  = scenario.get("period", "")
    yield (
        scenario_md,
        debate_transcript,
        ra_out,
        ca_out,
        ro_out + ("\n\n" + escalation_md if escalation_md else ""),
        cfo_out,
        build_turns_md(completed_turns, None),
        status,
        debate_transcript,   # → transcript_state
        cfo_out,             # → cfo_state
        json.dumps({"company": company, "period": period, "scenario_md": scenario_md}),  # → meta_state
    )


# ── Gradio UI ────────────────────────────────────────────────────────────────
CSS = """
.gradio-container { max-width: 1300px !important; margin: 0 auto !important; }
footer { display: none !important; }

/* Phase tracker card */
#turns-tracker .wrap { background: #faf5ff !important; border: 1px solid #e9d5ff !important;
                       border-radius: 12px !important; padding: 16px !important; }

/* Scenario card */
#scenario-box .wrap { background: #f8fafc !important; border: 1px solid #e2e8f0 !important;
                      border-radius: 12px !important; padding: 4px 16px !important; }

/* Debate log */
#debate-log .wrap { font-family: 'Georgia', serif !important; font-size: 0.94em !important;
                    line-height: 1.75 !important; }

/* Agent color bars */
#ra-box .wrap  { border-left: 4px solid #22c55e !important; padding-left: 16px !important; }
#ca-box .wrap  { border-left: 4px solid #f97316 !important; padding-left: 16px !important; }
#ro-box .wrap  { border-left: 4px solid #ef4444 !important; padding-left: 16px !important; }
#cfo-box .wrap { border-left: 4px solid #8b5cf6 !important; padding-left: 16px !important;
                 background: #faf5ff !important; border-radius: 0 8px 8px 0 !important; }

"""

with gr.Blocks(title="Multi-Agent Finance Debate System") as demo:

    gr.Markdown("""
# 🏦 Multi-Agent Finance Debate System
### LangGraph × Claude — Quarterly Earnings Debate

**4 AI agents debate a quarterly earnings scenario and produce a board-ready CFO recommendation.**
Built with [LangGraph](https://github.com/langchain-ai/langgraph) + [Anthropic Claude](https://anthropic.com).

| Agent | Role | Phase |
|-------|------|-------|
| 📈 Revenue Analyst | Defends revenue projections | Phase 1 |
| 🔍 Cost Analyst | Cross-examines & challenges | Phase 2 |
| 📈 Revenue Analyst | Rebuts cost analyst | Phase 3 |
| 🚨 Risk Officer | Audits tension, escalates if needed | Phase 4 |
| 🏦 CFO | Synthesizes board recommendation | Phase 5 |
""")

    with gr.Row(elem_id="api-key-row"):
        with gr.Column(scale=4):
            api_key_input = gr.Textbox(
                label="🔑 Anthropic API Key (optional — overrides .env for this session)",
                placeholder="sk-ant-...",
                type="password",
            )
        with gr.Column(scale=3):
            gr.Markdown(
                "Leave blank to use the key from `.env`.  \n"
                "Your key is never stored — only used for the current debate run."
            )

    with gr.Row():
        with gr.Column(scale=2):
            scenario_dropdown = gr.Dropdown(
                choices=[
                    ("TechCorp Inc. — SaaS, $2.1B ARR", "TCORP"),
                    ("ManufactureCo Holdings — Industrial, $4.8B Revenue", "MFGCO"),
                    ("PropTrust Commercial REIT — $12B Assets", "REIT1"),
                ],
                value="TCORP",
                label="📂 Option A — Demo Scenario (instant, full context)",
            )
            gr.Markdown(
                "✅ Rich qualitative data — NRR, churn, sector macro, specific risks & opportunities  \n"
                "✅ No EDGAR/FRED fetch — financial data is pre-built  \n"
                "✅ Best for demos and presentations",
                elem_id="demo-hint",
            )
        with gr.Column(scale=2):
            real_ticker_input = gr.Textbox(
                label="📡 Option B — Live EDGAR Ticker (overrides dropdown)",
                placeholder="e.g. AAPL, MSFT, NVDA, PFE, CRM …",
            )
            gr.Markdown(
                "✅ Real 10-Q financials from SEC EDGAR  \n"
                "✅ Any US public company  \n"
                "⚠️ ~10s network fetch — generic risks/opportunities",
                elem_id="edgar-hint",
            )
        with gr.Column(scale=1):
            run_btn   = gr.Button("🚀 Run Debate", variant="primary", size="lg", elem_id="run-btn")
            demo_btn  = gr.Button("▶ Load Demo", size="lg")

    status_bar = gr.Markdown(
        "*Select a demo scenario or enter a live ticker, then click Run Debate.*",
        elem_id="status-bar",
    )

    with gr.Row():
        with gr.Column(scale=1):
            turns_box = gr.Markdown(
                value=build_turns_md(set(), None),
                label="Debate Progress",
                elem_id="turns-tracker",
            )
        with gr.Column(scale=3):
            scenario_box = gr.Markdown(label="Scenario Overview", elem_id="scenario-box")

    with gr.Tabs():
        with gr.TabItem("🎬 Full Debate Transcript"):
            debate_log = gr.Markdown(
                label="Live Debate Log",
                elem_id="debate-log",
                value="*Debate will appear here in real-time...*"
            )

        with gr.TabItem("📈 Revenue Analyst"):
            ra_box = gr.Markdown(label="Revenue Analyst Output", elem_id="ra-box")

        with gr.TabItem("🔍 Cost Analyst"):
            ca_box = gr.Markdown(label="Cost Analyst Output", elem_id="ca-box")

        with gr.TabItem("🚨 Risk Officer"):
            ro_box = gr.Markdown(label="Risk Officer Output", elem_id="ro-box")

        with gr.TabItem("🏦 CFO Recommendation", id="cfo-tab"):
            cfo_box = gr.Markdown(
                label="CFO Board Recommendation",
                value="*CFO synthesis will appear after the debate completes.*",
                elem_id="cfo-box",
            )

        with gr.TabItem("📚 Data Sources"):
            gr.Markdown(f"""
## Where Does the Data Come From?

### Option A — Demo Scenarios (TCORP, MFGCO, REIT1)
These are **synthetic composites** modeled after real industry benchmarks — safe for demos without IP concerns. No network call required.

### Option B — Live EDGAR Ticker (e.g. MSFT, AAPL, NVDA)
Data is pulled **live from SEC EDGAR** (real 10-Q filings) + **FRED API** (live fed funds rate). Financials are real; risks/opportunities are generated by the agents from that data.

""")

    # ── State stores (hidden) ────────────────────────────────────────────────
    transcript_state = gr.State("")
    cfo_state        = gr.State("")
    meta_state       = gr.State("")

    # ── Download section ─────────────────────────────────────────────────────
    gr.Markdown("---\n### 📥 Download Reports")
    with gr.Row():
        dl_transcript_btn = gr.DownloadButton("📄 Download Full Debate Transcript", scale=1)
        dl_board_btn      = gr.DownloadButton("📊 Download CFO Board Report", variant="primary", scale=1)

    def make_transcript_pdf(transcript: str, meta_json: str):
        if not transcript:
            return None
        meta = json.loads(meta_json) if meta_json else {}
        return generate_transcript_pdf(transcript, meta.get("scenario_md", ""), meta.get("company", "Company"))

    def make_board_pdf(cfo_out: str, meta_json: str):
        if not cfo_out:
            return None
        meta = json.loads(meta_json) if meta_json else {}
        return generate_board_report_pdf(cfo_out, meta.get("scenario_md", ""), meta.get("company", "Company"), meta.get("period", ""))

    def load_demo():
        return (
            DEMO_SCENARIO_MD,
            DEMO_TRANSCRIPT,
            DEMO_RA_FULL,
            DEMO_CA,
            DEMO_RO_BASE,
            DEMO_CFO,
            build_turns_md({"revenue_analyst", "cost_analyst", "revenue_rebuttal", "risk_officer", "cfo_synthesis"}, None),
            "✅ Demo loaded — TechCorp Inc. Q3 2024 (no API call)",
            DEMO_TRANSCRIPT,
            DEMO_CFO,
            DEMO_META,
        )

    run_btn.click(
        fn=run_full_debate,
        inputs=[scenario_dropdown, real_ticker_input, api_key_input],
        outputs=[scenario_box, debate_log, ra_box, ca_box, ro_box, cfo_box, turns_box, status_bar,
                 transcript_state, cfo_state, meta_state],
    )

    demo_btn.click(
        fn=load_demo,
        inputs=[],
        outputs=[scenario_box, debate_log, ra_box, ca_box, ro_box, cfo_box, turns_box, status_bar,
                 transcript_state, cfo_state, meta_state],
    )

    dl_transcript_btn.click(
        fn=make_transcript_pdf,
        inputs=[transcript_state, meta_state],
        outputs=dl_transcript_btn,
    )

    dl_board_btn.click(
        fn=make_board_pdf,
        inputs=[cfo_state, meta_state],
        outputs=dl_board_btn,
    )

    gr.Markdown("""
---
<div style="text-align:center; color:#9ca3af; font-size:0.85em; padding: 8px 0">
Built by <a href="https://github.com/PhatNguyen39" style="color:#7c3aed">Phat Nguyen</a> &nbsp;·&nbsp;
Powered by LangGraph + Claude &nbsp;·&nbsp;
<a href="https://github.com/PhatNguyen39/finance-agent-debate" style="color:#7c3aed">Source Code</a>
</div>
""")

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        theme=gr.themes.Soft(
            primary_hue="violet",
            secondary_hue="blue",
            neutral_hue="slate",
            font=gr.themes.GoogleFont("Inter"),
        ),
        css=CSS,
    )
