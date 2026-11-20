"""Support-ticket triage agent: draft a reply, critique it, retry, or escalate.

Run it three ways:

    python main.py TICKET-001            the terminal
    streamlit run app.py                 the web UI
    langgraph dev --allow-blocking       LangGraph Studio, in the browser

With LANGSMITH_TRACING=true in .env, all three are traced to LangSmith.
Search this file for LANGSMITH and LANGGRAPH STUDIO to see everything that
makes that work - it is about fifteen lines.
"""

# CORPORATE TLS: networks that inspect HTTPS present their own certificate.
# Python trusts only the public CAs bundled in certifi, so those connections
# fail with "self-signed certificate in certificate chain". truststore makes
# Python use the operating system's certificate store instead - where the
# corporate root CA is already installed, which is why browsers work fine.
# Must run before anything opens a connection. Harmless if truststore is not
# installed, and a no-op on a network that does not inspect traffic.
try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

import argparse
import os
import sys
from typing import TypedDict, Literal

import httpx
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langsmith import traceable

import tickets

# Load .env here, at import time. main() used to do it, but LangGraph Studio
# never calls main() - it imports this file - so the keys have to be in place
# before anything else in the module runs.
load_dotenv()

MAX_ATTEMPTS = 3

# OpenAI model used for triage and drafting (override in .env)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")

REQUIRED_ENV_VARS = [
    "OPENAI_API_KEY",
]

# The critique (judge) also runs on OpenAI. Use a different model from the
# writer so the agent is not grading its own homework with the same brain.
JUDGE_MODEL = os.getenv("OPENAI_JUDGE_MODEL", "gpt-4.1-mini")


class TicketInput(TypedDict):
    """What the graph is invoked WITH.

    The full TicketState has ten fields. Studio builds its input form from
    whatever schema you give it, so this makes a run one box - a ticket id -
    instead of ten. new_ticket fills in the other nine.
    """

    ticket_id: str


class TicketState(TypedDict):
    ticket_id: str
    subject: str
    body: str
    product: str
    triage_notes: str
    draft: str
    verdict: str
    verdict_reason: str
    attempts: int
    escalated: bool
    priority: Literal["high", "normal"]


# ---------------------------------------------------------------------------
# Model calls
#
# LANGSMITH: @traceable is the whole of the tracing setup. It records the
# function as one span in the trace. run_type="llm" is what makes LangSmith
# draw it as a chat exchange with token counts, instead of an anonymous
# function call.
#
# LangSmith does not know or care that these are hand-rolled httpx calls. It
# recognises them because of the SHAPE of the data:
#     in   ->  messages=[{"role": ..., "content": ...}, ...]
#     out  ->  {"messages": [...], "usage_metadata": {"input_tokens": ...}}
# Hand it those two shapes and any provider is traced like a first-class one.
# ---------------------------------------------------------------------------

@traceable(
    run_type="llm",
    name="openai",
    metadata={"ls_provider": "openai", "ls_model_name": OPENAI_MODEL},
)
def _openai_llm(messages, temperature):
    url = os.getenv("OPENAI_CHAT_URL", "https://api.openai.com/v1/chat/completions")
    api_key = os.environ["OPENAI_API_KEY"]
    response = httpx.post(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": OPENAI_MODEL, "messages": messages, "temperature": temperature},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    usage = data.get("usage") or {}
    return {
        "messages": [data["choices"][0]["message"]],
        "usage_metadata": {
            "input_tokens": int(usage.get("prompt_tokens", 0)),
            "output_tokens": int(usage.get("completion_tokens", 0)),
            "total_tokens": int(usage.get("total_tokens", 0)),
        },
    }


def call_openai(messages, temperature=0.3):
    return _openai_llm(messages, temperature)["messages"][0]["content"]


@traceable(
    run_type="llm",
    name="judge",
    metadata={"ls_provider": "openai", "ls_model_name": JUDGE_MODEL},
)
def _judge_llm(messages, max_tokens):
    url = os.getenv("OPENAI_CHAT_URL", "https://api.openai.com/v1/chat/completions")
    api_key = os.environ["OPENAI_API_KEY"]
    response = httpx.post(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": JUDGE_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    usage = data.get("usage") or {}
    return {
        "messages": [data["choices"][0]["message"]],
        "usage_metadata": {
            "input_tokens": int(usage.get("prompt_tokens", 0)),
            "output_tokens": int(usage.get("completion_tokens", 0)),
            "total_tokens": int(usage.get("total_tokens", 0)),
        },
    }


def call_anthropic(prompt, max_tokens=300):
    """Kept under the old name so evaluate_agent.py still works - now runs on OpenAI."""
    messages = [{"role": "user", "content": prompt}]
    return _judge_llm(messages, max_tokens)["messages"][0]["content"]


def parse_verdict(raw):
    verdict = "fail"
    reason = raw.strip()
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("VERDICT"):
            if "PASS" in stripped.upper():
                verdict = "pass"
            elif "FAIL" in stripped.upper():
                verdict = "fail"
        elif stripped.upper().startswith("REASON"):
            reason = stripped.split(":", 1)[1].strip() if ":" in stripped else stripped
    return verdict, reason


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def new_ticket(state: TicketState) -> dict:
    """Entry node. Takes {"ticket_id": "TICKET-001"} and fills the rest of the
    state, so neither Studio nor the terminal has to supply ten empty fields."""
    ticket = tickets.get_ticket(state["ticket_id"])
    print(f"[new_ticket] fetched {state['ticket_id']}: {ticket['subject']}")
    return {
        "subject": ticket["subject"],
        "body": ticket["body"],
        "product": ticket["product"],
        "triage_notes": "",
        "draft": "",
        "verdict": "",
        "verdict_reason": "",
        "attempts": 0,
        "escalated": False,
        "priority": "normal"
    }


def intake(state: TicketState) -> dict:
    product = state["product"].strip()
    defaulted = not product
    if defaulted:
        product = "unspecified"
    subject = state["subject"].strip()
    body = state["body"].strip()
    note = " (product defaulted)" if defaulted else ""
    print(f"[intake] product={product!r}, body={len(body)} chars{note}")
    return {"product": product, "subject": subject, "body": body}


def triage(state: TicketState) -> dict:
    prompt = (
        f"Ticket subject: {state['subject']}\n"
        f"Product: {state['product']}\n"
        f"Body: {state['body']}\n\n"
        "Diagnose what is actually wrong with this ticket in 1-3 sentences. "
        "Be specific and technical where possible."
    )
    triage_notes = call_openai([
        {"role": "system", "content": "You are a technical support triage assistant. Diagnose issues concisely."},
        {"role": "user", "content": prompt},
    ]).strip()
    print(f"[triage] diagnosis: {triage_notes}")
    return {"triage_notes": triage_notes}


#TODO: ba boule, e tot triage, copy-paste-uit. Ca ai un copil care paste
def classify_priority(state: TicketState) -> dict:
    prompt = (
        f"Ticket subject: {state['subject']}\n"
        f"Product: {state['product']}\n"
        f"Body: {state['body']}\n"
        f"Diagnosis: {state['triage_notes']}\n\n"
        "Classify this ticket's priority as high or normal."
    )
    priority = call_openai([
        {"role": "system", "content": """
You are an IT support ticket priority classifier.

Classify tickets using these strict criteria:

HIGH priority:
- Complete production outage affecting an entire site or organization.
- Critical business operations are completely blocked.
- Confirmed security incident or serious data loss.

NORMAL priority:
- Partial service degradation.
- Intermittent failures.
- Problems affecting only some users or some calls.
- Issues without enough information to establish a critical outage.
- Any issue that does not explicitly meet the HIGH criteria.

IMPORTANT RULES:
- HIGH is the exception, not the default.
- Do not infer business impact that is not explicitly stated.
- Words like "urgent", "critical", or "ASAP" alone do not justify HIGH.
- If information is insufficient, classify as NORMAL.
- Return exactly one lowercase word: high or normal.
"""},
        {"role": "user", "content": prompt},
    ]).strip()
    print(f"[classify_priority] priority: {priority}")
    return {"priority": priority}


def draft_reply(state: TicketState) -> dict:
    attempts = state["attempts"] + 1
    feedback_block = ""
    if attempts > 1 and state.get("verdict_reason"):
        feedback_block = (
            f"\n\nYour previous draft was rejected for this reason - address it: {state['verdict_reason']}"
        )
    prompt = (
        f"Ticket subject: {state['subject']}\n"
        f"Product: {state['product']}\n"
        f"Body: {state['body']}\n"
        f"Diagnosis: {state['triage_notes']}{feedback_block}\n\n"
        "Write a professional, customer-facing support reply that addresses the diagnosis above."
    )
    draft = call_openai([
        {"role": "system", "content": (
            "You are a support engineer writing replies to customer tickets. "
            "Sign off as 'AudioCodes Support'. Never use bracketed placeholders "
            "such as [Your Name] or [Customer Name] - the reply is sent to the "
            "customer exactly as you write it."
        )},
        {"role": "user", "content": prompt},
    ]).strip()
    print(f"[draft_reply] attempt {attempts}/{MAX_ATTEMPTS} — drafting reply...")
    print(draft)
    return {"attempts": attempts, "draft": draft}


def critique(state: TicketState) -> dict:
    prompt = (
        f"Ticket subject: {state['subject']}\n"
        f"Product: {state['product']}\n"
        f"Body: {state['body']}\n"
        f"Diagnosis: {state['triage_notes']}\n\n"
        f"Proposed reply:\n{state['draft']}\n\n"
        "Judge this reply. Check: does it address the actual problem from the diagnosis, "
        "is it factually consistent with the ticket, does it avoid promising anything the "
        "ticket doesn't support, and is the tone professional.\n"
        "Be strict. A reply only PASSES if it gives the customer a concrete answer "
        "or concrete next steps for a real, identified problem. If the ticket names "
        "no product or no actual problem, so the reply can only ask for more "
        "information, that is a FAIL - such tickets need a human.\n\n"
        "Respond in exactly this format:\n"
        "VERDICT: PASS or FAIL\n"
        "REASON: one to two sentence explanation"
    )
    raw = call_anthropic(prompt).strip()
    verdict, reason = parse_verdict(raw)
    print(f"[critique] verdict={verdict} — {reason}")
    return {"verdict": verdict, "verdict_reason": reason}


def escalate_to_human(state: TicketState) -> dict:
    print(f"[escalate_to_human] giving up after {state['attempts']} attempts. Reason: {state['verdict_reason']}")
    print(f"Ticket: {state['ticket_id']} — {state['subject']}")
    print(f"Product: {state['product']}")
    print(f"Body: {state['body']}")
    print("Last draft:")
    print(state["draft"])
    return {"escalated": True}


def send_reply(state: TicketState) -> dict:
    print(f"[send_reply] ticket {state['ticket_id']} resolved after {state['attempts']} attempt(s)")
    print(state["draft"])
    return {}


def route_after_critique(state: TicketState) -> str:
    verdict = state["verdict"]
    attempts = state["attempts"]
    if verdict == "pass":
        next_node = "send_reply"
    elif attempts < MAX_ATTEMPTS:
        next_node = "draft_reply"
    else:
        next_node = "escalate_to_human"
    print(f"[router] verdict={verdict}, attempts={attempts} -> routing to {next_node}")
    return next_node


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

def build_graph():
    builder = StateGraph(TicketState, input_schema=TicketInput)
    builder.add_node("new_ticket", new_ticket)
    builder.add_node("intake", intake)
    builder.add_node("triage", triage)
    builder.add_node("classify_priority", classify_priority)
    builder.add_node("draft_reply", draft_reply)
    builder.add_node("critique", critique)
    builder.add_node("escalate_to_human", escalate_to_human)
    builder.add_node("send_reply", send_reply)

    builder.add_edge(START, "new_ticket")
    builder.add_edge("new_ticket", "intake")
    builder.add_edge("intake", "triage")
    builder.add_edge("triage", "classify_priority")
    
    builder.add_conditional_edges(
        "classify_priority",
        lambda state: state["priority"],
        {
            "high": "escalate_to_human",
            "normal": "draft_reply"
        }
    )
    builder.add_edge("draft_reply", "critique")
    builder.add_conditional_edges(
        "critique",
        route_after_critique,
        {
            "send_reply": "send_reply",
            "draft_reply": "draft_reply",
            "escalate_to_human": "escalate_to_human",
        },
    )
    builder.add_edge("send_reply", END)
    builder.add_edge("escalate_to_human", END)

    return builder.compile()


# ---------------------------------------------------------------------------
# LANGGRAPH STUDIO: langgraph.json points at this name - "main.py:graph".
# Studio imports this module and picks the object up, so the graph has to
# exist at import time. Building it is cheap: no HTTP, no model calls.
# ---------------------------------------------------------------------------

graph = build_graph()


def check_env():
    missing = [k for k in REQUIRED_ENV_VARS if not os.getenv(k)]
    if missing:
        print(f"Missing required .env values: {', '.join(missing)}")
        raise SystemExit(1)


def main():
    load_dotenv()
    check_env()

    valid_ids = tickets.list_ticket_ids()
    parser = argparse.ArgumentParser(description="Run the support-ticket triage agent on one ticket.")
    parser.add_argument("ticket_id", help=f"one of: {', '.join(valid_ids)}")
    args = parser.parse_args()

    if args.ticket_id not in valid_ids:
        print(f"Unknown ticket id {args.ticket_id!r}. Valid ids: {', '.join(valid_ids)}")
        raise SystemExit(1)

    graph.invoke({"ticket_id": args.ticket_id})


if __name__ == "__main__":
    sys.exit(main() or 0)
