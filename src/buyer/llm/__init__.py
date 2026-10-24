"""THE DIPLOMAT: the LLM reads supplier e-mails and writes ours - fast and safe. See README.md here.

    from buyer.llm import read, to_message

    reading = read(supplier_message, last_decision=previous_decision)      # -> Reading(.signals, ...)
    message, email = to_message(decision, case, thread, profile, reading.signals, known_id=known)
    client.send_message(session_id, decision.supplier_id, message)
"""

from .client import LLMClient, LLMUnavailable, get_client, latency_summary, reset_clients
from .reader import Reading, neutral_signals, read, read_signals, rule_signals
from .template import template_email
from .writer import Email, to_message, write

__all__ = [
    "Email",
    "LLMClient",
    "LLMUnavailable",
    "Reading",
    "get_client",
    "latency_summary",
    "neutral_signals",
    "read",
    "read_signals",
    "reset_clients",
    "rule_signals",
    "template_email",
    "to_message",
    "write",
]
