# 📈 DAX Analyst Agent

An AI agent that answers questions about German stocks using **live market data**.
You ask a question in plain language. The agent decides which tools to call
(fundamentals, price history, a calculator), runs them, and writes a short analyst memo.

Built from scratch on the **Anthropic Claude API** with tool calling. No agent framework,
so the whole agent loop is visible in about 80 lines (`agent.py`).

> Example: *"Compare SAP and Siemens over the last year. Which looks cheaper on valuation?"*
> → the agent calls `get_price_history` and `get_stock_snapshot` for both stocks,
> uses `calculate` for the returns, and replies with a table, takeaways and risks.

<!-- TODO: add a screenshot or GIF of the app here -->

## How it works

```
question → Claude decides → needs data? ──yes──→ Python runs the tool → result goes back to Claude ─┐
                 ↑                                                                                   │
                 └───────────────────────────────────────────────────────────────────────────────────┘
                          no → final memo (max 8 loops)
```

| File | What it does |
| --- | --- |
| `tools.py` | Three tools (stock snapshot, price history, safe calculator) and their schemas |
| `agent.py` | The agent loop: call model → run requested tools → send results back → repeat |
| `app.py` | Streamlit chat app that shows every tool call the agent makes |

**Design choices**
- **Calculator tool:** LLMs make arithmetic mistakes, so every return and ratio is computed exactly.
- **Errors returned as data:** if a ticker is wrong, the model sees the error and corrects itself.
- **Short tool outputs:** monthly prices instead of daily rows keep cost and confusion down.
- **Step limit:** the loop stops after 8 steps, so the agent can't run forever.

## Run it

```bash
git clone https://github.com/<your-username>/dax-analyst-agent.git
cd dax-analyst-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then paste your Anthropic API key into .env
python agent.py "How has SAP performed over the last 6 months?"
streamlit run app.py
```

## What I learned

<!-- TODO: write 3–5 bullets in your own words after you've built it -->

## Next steps

- [ ] Add a news tool so the agent can explain *why* a stock moved
- [ ] Add the same agent on the OpenAI API and compare the answers
- [ ] Add a small test set of questions to check answer quality

*Not investment advice. Data from Yahoo Finance via `yfinance`.*
