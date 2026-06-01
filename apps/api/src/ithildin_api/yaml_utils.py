"""YAML loading helpers for trusted local configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class DuplicateKeySafeLoader(yaml.SafeLoader):
    """SafeLoader variant that rejects duplicate mapping keys."""


def _construct_mapping_no_duplicates(
    loader: DuplicateKeySafeLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate YAML key: {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


DuplicateKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping_no_duplicates,
)


def safe_load_no_duplicate_keys(path: Path) -> object:
    """Load YAML while rejecting duplicate keys at every mapping depth."""
    return yaml.load(path.read_text(encoding="utf-8"), Loader=DuplicateKeySafeLoader)
