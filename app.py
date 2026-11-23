"""
app.py — a chat web app around the agent.

Run it:   streamlit run app.py
"""

import streamlit as st

from agent import MODEL, run_agent

st.set_page_config(page_title="DAX Analyst Agent", page_icon="📈")
st.title("📈 DAX Analyst Agent")
st.caption(f"An AI agent that pulls live market data with tools · model: {MODEL} · not investment advice")

# st.session_state survives between clicks. We keep two lists:
# - history: the full conversation in API format (what the model needs)
# - chat: what we display (question, tool calls, answer)
if "history" not in st.session_state:
    st.session_state.history = []
    st.session_state.chat = []

for item in st.session_state.chat:
    with st.chat_message(item["role"]):
        for call in item.get("tools", []):
            with st.expander(f"🔧 {call['name']}({call['input']})"):
                st.json(call["result"])
        st.markdown(item["text"])

examples = "e.g. Compare SAP and Siemens over the last year. Which looks cheaper on valuation?"
if question := st.chat_input(examples):
    st.session_state.chat.append({"role": "user", "text": question})
    st.session_state.history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        calls = []

        def show(name, args, result):
            calls.append({"name": name, "input": args, "result": result})
            with st.expander(f"🔧 {name}({args})"):
                st.json(result)

        with st.spinner("Thinking and fetching data..."):
            answer, usage = run_agent(st.session_state.history, on_tool_call=show)
        st.markdown(answer)
        st.caption(f"{usage['steps']} steps · {usage['input_tokens'] + usage['output_tokens']} tokens")

    st.session_state.chat.append({"role": "assistant", "text": answer, "tools": calls})
