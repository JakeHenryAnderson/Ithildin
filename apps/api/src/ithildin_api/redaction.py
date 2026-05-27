"""Tool output redaction for governed results."""

from __future__ import annotations

import re
from dataclasses import dataclass
from re import Pattern

from ithildin_schemas import JsonObject, JsonValue

REDACTED_VALUE = "[REDACTED]"
BASELINE_REDACTION_KEYS = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "secret",
        "password",
        "private_key",
    }
)
SENSITIVE_ASSIGNMENT_KEYS = (
    "authorization",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "secret",
    "password",
    "private_key",
)


@dataclass(frozen=True)
class RedactionSummary:
    applied: bool
    count: int
    paths: tuple[str, ...]

    def as_metadata(self) -> JsonObject:
        return {
            "redaction_applied": True,
            "redaction_count": self.count,
            "redaction_paths": list(self.paths),
        }


@dataclass(frozen=True)
class RedactionResult:
    value: JsonObject
    summary: RedactionSummary


class RedactionService:
    def __init__(
        self,
        *,
        extra_keys: set[str] | None = None,
        extra_patterns: list[str] | None = None,
    ) -> None:
        self.keys = set(BASELINE_REDACTION_KEYS) | {
            key.strip().lower() for key in (extra_keys or set()) if key.strip()
        }
        self.patterns = _baseline_patterns()
        self.patterns.extend(_compile_extra_patterns(extra_patterns or []))

    @classmethod
    def from_settings(
        cls,
        *,
        extra_keys: str,
        extra_patterns: str,
    ) -> RedactionService:
        return cls(
            extra_keys={key.strip() for key in extra_keys.split(",") if key.strip()},
            extra_patterns=[pattern for pattern in extra_patterns.splitlines() if pattern.strip()],
        )

    def redact(
        self,
        value: JsonObject,
        *,
        extra_keys: set[str] | None = None,
    ) -> RedactionResult:
        active_keys = self.keys | {
            key.strip().lower() for key in (extra_keys or set()) if key.strip()
        }
        paths: list[str] = []
        redacted = _redact_object(
            value,
            active_keys=active_keys,
            patterns=self.patterns,
            path="$",
            paths=paths,
        )
        unique_paths = tuple(dict.fromkeys(paths))
        return RedactionResult(
            value=redacted,
            summary=RedactionSummary(
                applied=True,
                count=len(paths),
                paths=unique_paths,
            ),
        )


def _redact_object(
    value: JsonObject,
    *,
    active_keys: set[str],
    patterns: list[Pattern[str]],
    path: str,
    paths: list[str],
) -> JsonObject:
    result: JsonObject = {}
    for key, item in value.items():
        item_path = f"{path}.{key}"
        if key.lower() in active_keys:
            result[key] = REDACTED_VALUE
            paths.append(item_path)
            continue
        result[key] = _redact_value(
            item,
            active_keys=active_keys,
            patterns=patterns,
            path=item_path,
            paths=paths,
        )
    return result


def _redact_value(
    value: JsonValue,
    *,
    active_keys: set[str],
    patterns: list[Pattern[str]],
    path: str,
    paths: list[str],
) -> JsonValue:
    if isinstance(value, dict):
        return _redact_object(
            value,
            active_keys=active_keys,
            patterns=patterns,
            path=path,
            paths=paths,
        )
    if isinstance(value, list):
        return [
            _redact_value(
                item,
                active_keys=active_keys,
                patterns=patterns,
                path=f"{path}[{index}]",
                paths=paths,
            )
            for index, item in enumerate(value)
        ]
    if isinstance(value, str):
        redacted = _redact_string(value, patterns)
        if redacted != value:
            paths.append(path)
        return redacted
    return value


def _redact_string(value: str, patterns: list[Pattern[str]]) -> str:
    redacted = value
    for pattern in patterns:
        redacted = pattern.sub(_replacement, redacted)
    return redacted


def _replacement(match: re.Match[str]) -> str:
    prefix = match.groupdict().get("prefix")
    if prefix is not None:
        return f"{prefix}{REDACTED_VALUE}"
    if match.group(0).lower().startswith("bearer "):
        return f"{match.group(0)[:7]}{REDACTED_VALUE}"
    return REDACTED_VALUE


def _baseline_patterns() -> list[Pattern[str]]:
    assignment_keys = "|".join(re.escape(key) for key in SENSITIVE_ASSIGNMENT_KEYS)
    return [
        re.compile(r"Bearer\s+[A-Za-z0-9._~+/\-]+=*", re.IGNORECASE),
        re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}\b"),
        re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
        re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
        re.compile(
            rf"\b(?P<prefix>(?:{assignment_keys})\s*[:=]\s*)([^\s,;]+)",
            re.IGNORECASE,
        ),
        re.compile(
            rf'(?P<prefix>"?(?:{assignment_keys})"?\s*:\s*"?)([^"\s,;]+)',
            re.IGNORECASE,
        ),
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
            re.DOTALL,
        ),
    ]


def _compile_extra_patterns(patterns: list[str]) -> list[Pattern[str]]:
    compiled: list[Pattern[str]] = []
    for pattern in patterns:
        compiled.append(re.compile(pattern, re.MULTILINE))
    return compiled
