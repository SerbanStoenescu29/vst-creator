"""Watch the triage loop run.

    streamlit run app.py

The agent itself lives in main.py; this only drives it and draws what happens.
"""

import os

import streamlit as st
from dotenv import load_dotenv

import tickets
import ui
from main import MAX_ATTEMPTS, REQUIRED_ENV_VARS, build_graph

st.set_page_config(page_title="Triage Loop", page_icon="◑", layout="wide")
load_dotenv()

GLOSS = {
    "new_ticket": "loads the ticket",
    "intake": "normalises the fields",
    "triage": "diagnoses the fault",
    "classify_priority": "classifies urgency",
    "draft_reply": "writes the reply",
    "critique": "judges the reply",
    "send_reply": "sends it",
    "escalate_to_human": "hands it over",
}

ALL_NODES = list(GLOSS) + ["verdict"]


def next_node(node: str, state: dict) -> str | None:
    """What the graph will run next — so the panel can show it in flight."""
    straight = {
        "new_ticket": "intake",
        "intake": "triage",
        "triage": "classify_priority",
        "draft_reply": "critique",
    }
    if node in straight:
        return straight[node]
    if node == "classify_priority":
        return "escalate_to_human" if state["priority"] == "high" else "draft_reply"
    if node == "critique":
        if state["verdict"] == "pass":
            return "send_reply"
        if state["attempts"] < MAX_ATTEMPTS:
            return "draft_reply"
        return "escalate_to_human"
    return None


def initial_state(ticket_id: str) -> dict:
    return {
        "ticket_id": ticket_id,
        "subject": "",
        "body": "",
        "product": "",
        "triage_notes": "",
        "draft": "",
        "verdict": "",
        "verdict_reason": "",
        "attempts": 0,
        "escalated": False,
        "priority": "normal",
    }


def render_facts(ticket: dict) -> str:
    rows = [
        ("ticket", ticket["ticket_id"], True),
        ("subject", ticket["subject"], False),
        ("product", ticket["product"] or "not given", False),
        ("reported", ticket["body"], False),
    ]
    out = ['<div class="tl-facts">']
    for key, val, mono in rows:
        cls = " mono" if mono else ""
        out.append(
            f'<div class="tl-fact"><span class="tl-fact-key">{key}</span>'
            f'<span class="tl-fact-val{cls}">{val}</span></div>'
        )
    out.append("</div>")
    return "".join(out)


def run(ticket_id: str, panel, gauge, readout) -> None:
    graph = build_graph()
    state = initial_state(ticket_id)
    status = {n: "idle" for n in ALL_NODES}
    outcome: str | None = None
    history: list[dict] = []
    step = 0

    def redraw(firing: bool = False) -> None:
        panel.markdown(ui.diagram(status, firing=firing), unsafe_allow_html=True)
        gauge.markdown(ui.lamps(state["attempts"], outcome, MAX_ATTEMPTS), unsafe_allow_html=True)

    status["new_ticket"] = "active"
    redraw()

    for chunk in graph.stream(state):
        for node, update in chunk.items():
            # A node that writes no state (send_reply) streams None, not {}.
            state.update(update or {})
            step += 1

            if node == "escalate_to_human":
                status[node] = "failed"
                outcome = "escalated"
            else:
                status[node] = "done"
            if node == "critique":
                status["verdict"] = "done"
            if node == "send_reply":
                outcome = "sent"

            nxt = next_node(node, state)
            looping = node == "critique" and nxt == "draft_reply"
            if nxt:
                status[nxt] = "active"
            redraw(firing=looping)

            with readout:
                _render_step(node, state, step, looping, history)

    st.session_state["last_run"] = {"state": state, "history": history, "outcome": outcome}


def _render_step(node, state, step, looping, history) -> None:
    """One card in the readout, shaped to what the node actually produced."""
    if node == "new_ticket":
        with st.container(key=f"tlstep-{step}"):
            st.markdown(
                ui.step_header(node, GLOSS[node], state["ticket_id"]), unsafe_allow_html=True
            )
        return

    if node == "intake":
        meta = f"{state['product']} &#183; {len(state['body'])} chars"
        with st.container(key=f"tlstep-{step}"):
            st.markdown(ui.step_header(node, GLOSS[node], meta), unsafe_allow_html=True)
        return

    if node == "triage":
        with st.container(key=f"tlstep-{step}"):
            st.markdown(ui.step_header(node, GLOSS[node]), unsafe_allow_html=True)
            with st.container(key=f"tlnote-{step}"):
                st.markdown(state["triage_notes"])
        return

    if node == "classify_priority":
        with st.container(key=f"tlstep-{step}"):
            st.markdown(
                ui.step_header(node, GLOSS[node], f"priority: {state['priority']}"),
                unsafe_allow_html=True,
            )
        return

    if node == "draft_reply":
        meta = f"attempt {state['attempts']} of {MAX_ATTEMPTS}"
        with st.container(key=f"tlstep-{step}"):
            st.markdown(ui.step_header(node, GLOSS[node], meta), unsafe_allow_html=True)
            with st.container(key=f"tlletter-{step}"):
                st.markdown(state["draft"])
        return

    if node == "critique":
        verdict = state["verdict"]
        history.append(
            {"attempt": state["attempts"], "verdict": verdict, "reason": state["verdict_reason"]}
        )
        meta = "rewriting" if looping else ("out of attempts" if verdict == "fail" else "")
        with st.container(key=f"tlstep-{step}"):
            st.markdown(
                ui.step_header(node, GLOSS[node], meta, tone=verdict), unsafe_allow_html=True
            )
            st.markdown(
                f'<span class="tl-chip {verdict}">{verdict}</span>', unsafe_allow_html=True
            )
            with st.container(key=f"tlnote-{step}"):
                st.markdown(state["verdict_reason"])
        return

    if node == "send_reply":
        st.markdown(
            '<div class="tl-outcome"><p class="tl-outcome-head">Reply sent</p>'
            f'<p class="tl-outcome-sub">{state["ticket_id"]} cleared in '
            f'{state["attempts"]} attempt(s)</p></div>',
            unsafe_allow_html=True,
        )
        return

    if node == "escalate_to_human":
        if state["priority"] == "high" and state["attempts"] == 0:
            reason = "Escalated immediately — high priority; no draft attempts used"
        else:
            reason = (f'{state["attempts"]} attempts used, none passed &#183; '
                      f'last objection: {state["verdict_reason"]}')
        st.markdown(
            '<div class="tl-outcome spent"><p class="tl-outcome-head">Handed to a human</p>'
            f'<p class="tl-outcome-sub">{reason}</p></div>',
            unsafe_allow_html=True,
        )


def main() -> None:
    st.markdown(ui.CSS, unsafe_allow_html=True)

    missing = [k for k in REQUIRED_ENV_VARS if not os.getenv(k)]
    if missing:
        st.markdown(
            '<p class="tl-eyebrow">Cannot start</p>'
            '<p class="tl-standfirst">Add these to <code>.env</code>, then reload: '
            f'<strong>{", ".join(missing)}</strong></p>',
            unsafe_allow_html=True,
        )
        st.stop()

    ticket_ids = tickets.list_ticket_ids()

    head, control = st.columns([0.62, 0.38], vertical_alignment="bottom")
    with head:
        st.markdown(
            '<p class="tl-eyebrow">AudioCodes support &#183; LangGraph</p>'
            '<h1 class="tl-title"><span class="a">Triage</span> <span class="b">Loop</span></h1>'
            '<p class="tl-standfirst">A reply gets drafted, then judged by a second model. '
            "High-priority tickets go straight to a human. Otherwise, every rejection "
            "feeds back into drafting; after three failed attempts the ticket goes to a human.</p>",
            unsafe_allow_html=True,
        )
    with control:
        ticket_id = st.segmented_control(
            "Ticket", ticket_ids, default=ticket_ids[0], key="pick", label_visibility="collapsed"
        ) or ticket_ids[0]
        go = st.button("Run triage", use_container_width=True)

    st.markdown('<div class="tl-rule"></div>', unsafe_allow_html=True)

    rail, main_col = st.columns([0.40, 0.60], gap="large")

    with rail:
        st.markdown('<p class="tl-label">The graph</p>', unsafe_allow_html=True)
        panel = st.empty()
        gauge = st.empty()
        st.markdown('<div class="tl-rule"></div>', unsafe_allow_html=True)
        st.markdown('<p class="tl-label">The ticket</p>', unsafe_allow_html=True)
        st.markdown(render_facts(tickets.get_ticket(ticket_id)), unsafe_allow_html=True)

    with main_col:
        st.markdown('<p class="tl-label">Readout</p>', unsafe_allow_html=True)
        readout = st.container()

    if not go:
        panel.markdown(
            ui.diagram({n: "idle" for n in ALL_NODES}), unsafe_allow_html=True
        )
        gauge.markdown(ui.lamps(0, None, MAX_ATTEMPTS), unsafe_allow_html=True)
        with readout:
            st.markdown(
                '<div class="tl-empty"><p>Pick a ticket, then run the triage. '
                "Each node reports here as it finishes, and the teal edge on the left "
                "lights up whenever a draft gets sent back to be rewritten.</p></div>",
                unsafe_allow_html=True,
            )
        return

    try:
        run(ticket_id, panel, gauge, readout)
    except Exception as exc:  # surface the failure where the user is looking
        with readout:
            st.markdown(
                '<div class="tl-outcome spent"><p class="tl-outcome-head">Run failed</p>'
                f'<p class="tl-outcome-sub">{type(exc).__name__}: {exc}</p></div>',
                unsafe_allow_html=True,
            )
        return

    last = st.session_state.get("last_run", {})
    if len(last.get("history", [])) > 1:
        with main_col:
            with st.expander(f"Verdict history &#183; {len(last['history'])} attempts"):
                for h in last["history"]:
                    st.markdown(
                        ui.step_header(
                            f"attempt {h['attempt']}", h["verdict"], tone=h["verdict"]
                        ),
                        unsafe_allow_html=True,
                    )
                    st.markdown(h["reason"])


if __name__ == "__main__":
    main()
