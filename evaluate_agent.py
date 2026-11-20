"""Turn the three tickets into a LangSmith experiment.

    python evaluate_agent.py --create-dataset     once, to upload the tickets
    python evaluate_agent.py                      run the agent and score it

Why this exists
---------------
A trace tells you what ONE run did. You still had to read it and decide
whether you liked it. That does not scale, and it does not catch a
regression three weeks later.

An experiment asks the same fixed questions of every run, every time:

    correct_outcome   did it send a reply when it should, and escalate when
                      the ticket is too vague to answer?
    no_placeholders   does the reply still say "Dear [Customer Name]"?
    grounded          does it claim anything the ticket never said?
    attempts          how many drafts did the reflection loop need?

Two of those are ten lines of Python. One is a judge model. One is just a
number we record. Reach for a judge LAST - only for the question no plain
assertion can answer.
"""

import re
import sys

from langsmith import Client

# importing main also loads .env and installs the corporate-TLS fix
import main
from main import call_anthropic

DATASET = "reflection-agent"

# The answer key. Written by a human, deliberately. An agent that grades its
# own homework proves nothing.
#
# TICKET-003 is the interesting row. It says "Urgent - not working" and names
# no product. There is nothing here to diagnose, so the honest behaviour is to
# escalate rather than invent a plausible-sounding cause. Whether the agent
# agrees is exactly what we want to measure.
EXPECTED = {
    "TICKET-001": {"escalated": False},
    "TICKET-002": {"escalated": False},
    "TICKET-003": {"escalated": True},
}


# --------------------------------------------------------------------------- #
# the dataset
# --------------------------------------------------------------------------- #

def create_dataset():
    client = Client()
    if client.has_dataset(dataset_name=DATASET):
        print(f"dataset {DATASET!r} already exists - nothing to do")
        return

    dataset = client.create_dataset(
        dataset_name=DATASET,
        description="Three support tickets: two answerable, one too vague to answer.",
    )
    client.create_examples(
        dataset_id=dataset.id,
        examples=[
            {"inputs": {"ticket_id": tid}, "outputs": EXPECTED[tid]}
            for tid in sorted(EXPECTED)
        ],
    )
    print(f"created dataset {DATASET!r} with {len(EXPECTED)} examples")
    print("see it under Datasets & Experiments in LangSmith")


# --------------------------------------------------------------------------- #
# the thing being tested
# --------------------------------------------------------------------------- #

def target(inputs: dict) -> dict:
    """One dataset row in, the agent's result out."""
    final = main.graph.invoke({"ticket_id": inputs["ticket_id"]})
    return {
        "draft": final["draft"],
        "escalated": final["escalated"],
        "attempts": final["attempts"],
        "verdict": final["verdict"],
        "triage_notes": final["triage_notes"],
    }


# --------------------------------------------------------------------------- #
# evaluators - each returns {"key": ..., "score": ...}
# --------------------------------------------------------------------------- #

def correct_outcome(outputs: dict, reference_outputs: dict) -> dict:
    """Replied when it should reply, escalated when it should escalate."""
    got, want = bool(outputs["escalated"]), bool(reference_outputs["escalated"])
    return {
        "key": "correct_outcome",
        "score": int(got == want),
        "comment": f"escalated={got}, expected {want}",
    }


# [Customer Name], [Your Name], [Insert date] - anything left in brackets
PLACEHOLDER = re.compile(r"\[[A-Za-z][^\]\n]{1,40}\]")


def no_placeholders(outputs: dict) -> dict:
    """Ten lines of regex that the LLM critic keeps waving through.

    Run this once and look at the result. The critique node reads every draft
    and says PASS, and the draft still opens "Dear [Customer Name]". A judge
    model is looking for reasoning errors; it is bad at noticing a template
    that was never filled in. THIS is the evaluator to show the class first.
    """
    found = PLACEHOLDER.findall(outputs["draft"] or "")
    return {
        "key": "no_placeholders",
        "score": int(not found),
        "comment": ", ".join(sorted(set(found))) if found else "clean",
    }


def attempts(outputs: dict) -> dict:
    """Not pass/fail - just the number, so you can watch it move."""
    return {"key": "attempts", "score": outputs["attempts"]}


JUDGE = (
    "You are checking a support reply for invented facts.\n"
    "You get the customer's original ticket and the reply that was drafted.\n"
    "Grounded means the reply does not assert any technical fact about the "
    "customer's system that the ticket did not state. Asking questions, "
    "suggesting checks and describing general product behaviour are fine. "
    "Stating a cause as established fact when the ticket never said so is not.\n\n"
    "Respond in exactly this format:\n"
    "VERDICT: PASS or FAIL\n"
    "REASON: one sentence"
)


def grounded(inputs: dict, outputs: dict) -> dict:
    """The only evaluator here that costs money. Note that it is also the only
    one whose answer you cannot fully predict."""
    import tickets

    ticket = tickets.get_ticket(inputs["ticket_id"])
    raw = call_anthropic(
        f"{JUDGE}\n\nTICKET:\n{ticket['subject']}\n{ticket['body']}\n\n"
        f"REPLY:\n{outputs['draft']}"
    )
    verdict, reason = main.parse_verdict(raw)
    return {"key": "grounded", "score": int(verdict == "pass"), "comment": reason}


# --------------------------------------------------------------------------- #

def cli() -> int:
    main.check_env()

    if "--create-dataset" in sys.argv:
        create_dataset()
        return 0

    client = Client()
    if not client.has_dataset(dataset_name=DATASET):
        print(f"no dataset {DATASET!r} yet - run: python evaluate_agent.py --create-dataset")
        return 1

    client.evaluate(
        target,
        data=DATASET,
        evaluators=[correct_outcome, no_placeholders, attempts, grounded],
        experiment_prefix="reflection",
        max_concurrency=1,        # one at a time, so the console stays readable
    )
    print()
    print("open the link above, then compare two experiments:")
    print("Datasets & Experiments -> reflection-agent -> tick two rows -> Compare")
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
