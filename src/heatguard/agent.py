"""
agent.py — deliberately thin.

Parses natural language into (question, site, date) and narrates the result.
It calls router.route() and executes the plan it is handed.

IT NEVER PICKS THE ANALYSIS LAYER. If you find yourself asking the model which
filter_type to use, the design has been violated — see CLAUDE.md.

Every decision is appended to data/decisions.jsonl: site, date, question, layer,
rationale, result, action. That file is both the compliance audit trail and the
evidence the system works.
"""

from __future__ import annotations


def answer(question: str, *, site_id: str, date: str) -> dict:
    """route -> execute -> narrate -> log. T9."""
    raise NotImplementedError("T9")
