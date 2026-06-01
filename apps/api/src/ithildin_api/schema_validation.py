"""JSON Schema validation helpers that avoid echoing caller values."""

from __future__ import annotations

from collections.abc import Iterable

from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema.exceptions import SchemaError as JsonSchemaSchemaError


def safe_json_schema_error(
    exc: JsonSchemaValidationError | JsonSchemaSchemaError,
) -> str:
    """Return a deterministic validation summary without instance values."""
    validator = getattr(exc, "validator", None)
    validator_name = str(validator) if validator else exc.__class__.__name__
    instance_path = _json_pointer(getattr(exc, "absolute_path", ()))
    schema_path = _json_pointer(getattr(exc, "absolute_schema_path", ()))
    return (
        "JSON Schema validation failed"
        f" at {instance_path}"
        f" using validator {validator_name}"
        f" (schema path {schema_path})"
    )


def _json_pointer(parts: Iterable[object]) -> str:
    encoded = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(encoded) if encoded else "/"
