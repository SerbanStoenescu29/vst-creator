"""Fake in-memory ticket store for the Triage Lab session.

No network, no keys, no customer data. Three tickets, deliberately chosen:
two are answerable, one is not.
"""

TICKETS = {
    "TICKET-001": {
        "ticket_id": "TICKET-001",
        "subject": "SBC not registering to SIP trunk after maintenance window",
        "product": "Mediant 4000 SBC",
        "body": (
            "Following our scheduled maintenance last night, the SBC no longer "
            "registers to the carrier SIP trunk. The registration attempt is "
            "rejected with 403 Forbidden. Nothing was changed on our side that "
            "we are aware of. Inbound and outbound calls are both down. "
            "This is affecting the main site."
        ),
    },
    "TICKET-002": {
        "ticket_id": "TICKET-002",
        "subject": "One-way audio on outbound calls only",
        "product": "Mediant 1000B Gateway",
        "body": (
            "On outbound calls the called party can hear our user, but our user "
            "hears nothing. Inbound calls are fine. It started sometime last "
            "week. The gateway sits behind a firewall that was recently "
            "updated. Roughly one in three outbound calls is affected."
        ),
    },
    "TICKET-003": {
        "ticket_id": "TICKET-003",
        "subject": "Urgent - not working",
        "product": "",
        "body": (
            "The system is not working. Please advise urgently. Thanks."
        ),
    },
}


def get_ticket(ticket_id: str) -> dict:
    """Return one ticket, or raise if the id is unknown."""
    if ticket_id not in TICKETS:
        known = ", ".join(sorted(TICKETS))
        raise KeyError(f"unknown ticket {ticket_id!r} — try one of: {known}")
    return dict(TICKETS[ticket_id])


def list_ticket_ids() -> list:
    return sorted(TICKETS)
