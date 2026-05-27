"""Shared policy engine interfaces."""

from __future__ import annotations

from typing import Protocol

from ithildin_schemas import JsonObject, PolicyDecision, PolicyInput


class PolicyEngine(Protocol):
    engine_name: str

    @property
    def policy_hash(self) -> str:
        """Return the deterministic policy engine/config hash."""

    @property
    def document_version(self) -> str:
        """Return the human policy document/version identifier."""

    @property
    def rule_count(self) -> int:
        """Return the local rule count when available."""

    def evaluate(self, policy_input: PolicyInput) -> PolicyDecision:
        """Evaluate one policy input."""

    def status(self) -> JsonObject:
        """Return admin-safe policy status metadata."""
