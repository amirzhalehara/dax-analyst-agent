"""
tools.py — the "hands" of the agent.

LESSON: The model can't touch the internet or do reliable maths by itself.
We give it tools: normal Python functions. For each one we also write a
SCHEMA (name + description + inputs) so the model knows when and how to ask
for it. The description is a prompt: write it as if explaining to a new
colleague.
"""

import ast
import operator

import yfinance as yf


# ---------------------------------------------------------------------------
# 1. The Python functions (what actually runs)
# ---------------------------------------------------------------------------

def get_stock_snapshot(ticker: str) -> dict:
    """Company name, sector, price, valuation and dividend data."""
    info = yf.Ticker(ticker).info
    if not info or (info.get("regularMarketPrice") is None and info.get("currentPrice") is None):
        # LESSON: return errors as data. The model reads them and can retry
        # (e.g. add ".DE"), instead of the whole program crashing.
        return {"error": f"No data for '{ticker}'. German stocks need '.DE', e.g. 'SAP.DE'."}
    keys = [
        "longName", "sector", "industry", "currency", "currentPrice",
        "marketCap", "trailingPE", "forwardPE", "priceToBook",
        "dividendYield", "fiftyTwoWeekLow", "fiftyTwoWeekHigh",
        "revenueGrowth", "profitMargins", "debtToEquity",
    ]
    return {k: info.get(k) for k in keys}


def get_price_history(ticker: str, period: str = "6mo") -> dict:
    """Monthly closing prices plus first/last close over the period."""
    hist = yf.Ticker(ticker).history(period=period)
    if hist.empty:
        return {"error": f"No price history for '{ticker}' over '{period}'."}
    closes = hist["Close"]
    # LESSON: keep tool output SHORT. Every character you return costs tokens
    # (money) and can distract the model. Monthly points, not 120 daily rows.
    monthly = closes.resample("ME").last().round(2)
    return {
        "ticker": ticker,
        "period": period,
        "first_close": round(float(closes.iloc[0]), 2),
        "last_close": round(float(closes.iloc[-1]), 2),
        "min_close": round(float(closes.min()), 2),
        "max_close": round(float(closes.max()), 2),
        "monthly_closes": {d.strftime("%Y-%m"): float(v) for d, v in monthly.items()},
    }


_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg,
}


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("Only numbers and + - * / ** are allowed.")


def calculate(expression: str) -> dict:
    """Safe arithmetic. LESSON: LLMs are bad at exact maths, so give them a calculator.
    We never use Python's eval() on model output: that would let the model run any code."""
    try:
        return {"expression": expression, "result": round(_eval(ast.parse(expression, mode="eval").body), 4)}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# 2. The schemas (what the model sees)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "get_stock_snapshot",
        "description": (
            "Get current fundamentals for one stock: name, sector, price, market cap, "
            "P/E, price-to-book, dividend yield, 52-week range, growth and margins. "
            "Use Yahoo Finance tickers: German stocks end in '.DE' (SAP.DE, BMW.DE, SIE.DE)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"ticker": {"type": "string", "description": "Yahoo ticker, e.g. 'SAP.DE'"}},
            "required": ["ticker"],
        },
    },
    {
        "name": "get_price_history",
        "description": (
            "Get closing-price history for one stock: first, last, min and max close, "
            "plus month-end closes. Use this for performance and trend questions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string"},
                "period": {
                    "type": "string",
                    "enum": ["1mo", "3mo", "6mo", "1y", "2y", "5y"],
                    "description": "How far back. Default 6mo.",
                },
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "calculate",
        "description": (
            "Evaluate an arithmetic expression exactly, e.g. '(245.1 - 198.4) / 198.4 * 100'. "
            "ALWAYS use this for returns, percentages and ratios instead of doing maths yourself."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        },
    },
]

# Maps the name the model asks for -> the Python function we run
TOOL_FUNCTIONS = {
    "get_stock_snapshot": get_stock_snapshot,
    "get_price_history": get_price_history,
    "calculate": calculate,
}
