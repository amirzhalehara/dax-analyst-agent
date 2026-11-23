"""
agent.py — the "brain loop". This is Lesson 1's loop, made real.

Run it in the terminal:   python agent.py "Compare SAP and Siemens over the last year"
"""

import json
import os
import sys

import anthropic
from dotenv import load_dotenv

from tools import TOOL_FUNCTIONS, TOOLS

load_dotenv()  # reads ANTHROPIC_API_KEY (and optional MODEL) from your .env file

MODEL = os.getenv("MODEL", "claude-haiku-5-5")  # cheapest; try claude-sonnet-5-5 for better analysis
MAX_STEPS = 8  # LESSON: always cap the loop, or a confused agent can run (and bill you) forever

# LESSON: the system prompt is the agent's job description. Be specific.
SYSTEM_PROMPT = """You are a careful equity research assistant focused on German (DAX) stocks.

Rules:
- Use your tools to get data. Never invent numbers.
- Use the calculate tool for every return, percentage or ratio.
- German stocks use Yahoo tickers ending in .DE (SAP.DE, SIE.DE, BMW.DE, ALV.DE, DTE.DE).
- If a tool returns an error, fix the input and try again once.
- Finish with a short memo: 1) key numbers in a markdown table, 2) three bullet-point
  takeaways, 3) one line on risks. Say clearly that this is not investment advice.
"""


def run_agent(messages, on_tool_call=None):
    """Run the agent loop until the model gives a final answer.

    messages: conversation so far (list of {"role", "content"} dicts). Modified in place.
    on_tool_call: optional callback(name, input, result) so a UI can show what happens.
    Returns (final_text, usage_totals).
    """
    client = anthropic.Anthropic()
    usage = {"input_tokens": 0, "output_tokens": 0, "steps": 0}

    for step in range(MAX_STEPS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )
        usage["input_tokens"] += response.usage.input_tokens
        usage["output_tokens"] += response.usage.output_tokens
        usage["steps"] = step + 1

        # The model's turn always goes into the history, tool requests included
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            text = "".join(b.text for b in response.content if b.type == "text")
            return text, usage

        # Run every tool the model asked for (it can ask for several at once)
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            func = TOOL_FUNCTIONS.get(block.name)
            try:
                result = func(**block.input) if func else {"error": f"Unknown tool {block.name}"}
            except Exception as e:  # noqa: BLE001  network down, bad ticker, ...
                result = {"error": f"{type(e).__name__}: {e}"}
            if on_tool_call:
                on_tool_call(block.name, block.input, result)
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,  # LESSON: links each result to its request
                "content": json.dumps(result, default=str),
                "is_error": "error" in result,
            })
        messages.append({"role": "user", "content": results})

    return "Stopped: reached the step limit before finishing.", usage


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "How has SAP performed over the last 6 months?"
    history = [{"role": "user", "content": question}]

    def show(name, args, result):
        print(f"  -> tool: {name}({args})")

    answer, used = run_agent(history, on_tool_call=show)
    print("\n" + answer)
    print(f"\n[{used['steps']} steps, {used['input_tokens']} input + {used['output_tokens']} output tokens]")
