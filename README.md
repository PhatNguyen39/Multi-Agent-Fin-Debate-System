---
title: Multi-Agent Finance Debate System
emoji: 🏦
colorFrom: purple
colorTo: green
sdk: gradio
sdk_version: 6.14.0
python_version: '3.13'
app_file: app.py
pinned: true
license: mit
short_description: LangGraph multi-agent financial debate system
tags:
  - finance
  - langgraph
  - multi-agent
  - llm
  - portfolio
---

# 🏦 Multi-Agent Finance Debate System

A production-grade demo of a **LangGraph multi-agent system** where four AI agents debate a quarterly financial forecast and produce a board-ready CFO recommendation.

## Architecture

```
Q3 Scenario Input
       │
       ▼
┌─────────────────┐    Phase 1: Independent Analysis
│ Revenue Analyst │ ──► Defends revenue projections with NRR, pipeline data
└────────┬────────┘
         │
         ▼
┌─────────────────┐    Phase 2: Adversarial Cross-Examination  
│  Cost Analyst   │ ──► Challenges assumptions, flags margin compression
└────────┬────────┘
         │ (Revenue Analyst rebuts)
         ▼
┌─────────────────┐    Phase 3: Risk Escalation Audit
│  Risk Officer   │ ──► Scores risks, decides ESCALATE: YES/NO
└────────┬────────┘
         │
         ▼
┌─────────────────┐    Phase 4: Board Synthesis
│      CFO        │ ──► Structured recommendation: MAINTAIN/RAISE/LOWER
└─────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent Framework | [LangGraph](https://github.com/langchain-ai/langgraph) |
| LLM | Anthropic Claude (claude-3-5-haiku) |
| UI | [Gradio](https://gradio.app) |
| State Management | LangGraph `TypedDict` with `Annotated` reducers |
| Data | SEC EDGAR API (free) + synthetic composites |

## Available Scenarios

| Scenario | Sector | Key Tension |
|----------|--------|-------------|
| TechCorp Inc. (SaaS) | Enterprise Software | Growth vs. macro headwinds |
| ManufactureCo Holdings | Industrial | Margin compression vs. backlog strength |
| PropTrust REIT | Commercial Real Estate | Office vacancy vs. industrial opportunity |

## Real Data Integration

```python
# SEC EDGAR — Free, no API key
import httpx
CIK = "0001108524"  # Any public company CIK
url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json"
resp = httpx.get(url, headers={"User-Agent": "your-app your@email.com"})
facts = resp.json()
# Contains all GAAP metrics from 10-Q/10-K filings going back 10+ years
```

## Local Setup

```bash
git clone https://huggingface.co/spaces/PhatNguyen39/Multi-Agent-Fin-Debate-System
cd Multi-Agent-Fin-Debate-System
pip install -r requirements.txt

# Set your Anthropic API key
export ANTHROPIC_API_KEY=sk-ant-...

python app.py
# → http://localhost:7860
```

## Design Patterns Demonstrated

- **Supervisor-less multi-agent pipeline** — each agent has a single responsibility
- **Adversarial debate architecture** — structured disagreement surfaced via CA cross-examination
- **Escalation routing** — Risk Officer acts as a conditional router
- **Structured LLM output** — CFO uses strict format templates for board-ready output
- **State accumulation** — LangGraph `Annotated[List, operator.add]` for message history

---

*Built as a portfolio demo for AI/ML engineering interviews.*  
*Demonstrates: LangGraph, multi-agent design, financial domain knowledge, production-quality code.*