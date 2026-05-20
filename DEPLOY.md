# 🚀 Deployment Guide

## DEPLOY TO HUGGINGFACE SPACES (15 minutes)

### Step 1: Create the Space
1. Go to https://huggingface.co/new-space
2. Name: `finance-agent-debate`
3. SDK: **Gradio**
4. Visibility: **Public**
5. Click "Create Space"

### Step 2: Push Code
```bash
# Clone your new space
git clone https://huggingface.co/spaces/YOUR_HF_USERNAME/finance-agent-debate
cd finance-agent-debate

# Copy project files into it
cp -r /path/to/finance-agents/backend/* .
cp /path/to/finance-agents/app.py .
cp /path/to/finance-agents/requirements.txt .
cp /path/to/finance-agents/README.md .

git add .
git commit -m "Initial: Multi-Agent Finance Debate System"
git push
```

### Step 3: Add Your API Key as a Secret
1. In your Space → Settings → Repository Secrets
2. Add: `ANTHROPIC_API_KEY` = `sk-ant-YOUR_KEY`
3. Space auto-restarts and uses the env var

### Step 4: Your Live URL
```
https://huggingface.co/spaces/YOUR_USERNAME/finance-agent-debate
```

---

## LOCAL DEVELOPMENT

```bash
cd finance-agents
pip install -r requirements.txt

# .env file
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# Run Gradio (HF-compatible)
python app.py

# OR run FastAPI (for custom frontend)
cd backend
uvicorn server:app --reload --port 8000
```

---

## POSSIBLE EXTENSIONS TO MENTION

1. **Streaming to React frontend** — FastAPI SSE + real-time typewriter UI (backend/server.py is ready)
2. **Memory across quarters** — LangGraph persistence lets agents remember Q1/Q2 positions
3. **Human-in-the-loop** — LangGraph interrupt() to let a human CFO approve the escalation decision
4. **Red team mode** — add a 5th agent that plays bear case adversary for stress testing
5. **Backtesting** — run the debate on historical quarters and compare AI recommendation vs. actual results

---

## FILE STRUCTURE

```
finance-agent-debate/
├── app.py                 # Gradio UI (HuggingFace Spaces entry point)
├── agents.py              # LangGraph graph + all agent nodes
├── data_loader.py         # Scenarios + SEC EDGAR integration
├── server.py              # FastAPI + SSE streaming (for React frontend)
├── requirements.txt
├── README.md              # HF Spaces README (shown on the Space page)
├── Dockerfile             # Optional Docker deployment
└── DEPLOY.md              # This file
```
