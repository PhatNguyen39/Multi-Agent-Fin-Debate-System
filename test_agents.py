import asyncio
from agents import run_debate
from data_loader import SCENARIOS

asyncio.run(run_debate(SCENARIOS["TCORP"]))
