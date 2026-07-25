from __future__ import annotations

import re
import shlex
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILES = {
    "api": ROOT / "deploy/Dockerfile.api",
    "node": ROOT / "deploy/Dockerfile.node",
    "ui": ROOT / "deploy/Dockerfile.ui",
    "hermes": ROOT / "deploy/hermes-node-bridge/Dockerfile",
}


def _documents() -> dict[str, str]:
    return {
        name: path.read_text(encoding="utf-8")
        for name, path in DOCKERFILES.items()
    }


def _require(
    failures: list[str],
    condition: bool,
    code: str,
) -> None:
    if not condition:
        failures.append(code)


def _require_order(
    failures: list[str],
    document: str,
    code: str,
    *needles: str,
) -> None:
    cursor = -1
    for needle in needles:
        observed = document.find(needle, cursor + 1)
        if observed < 0:
            failures.append(f"{code}:missing:{needle}")
            return
        cursor = observed


def _validate_unary_tests(name: str, document: str) -> list[str]:
    failures: list[str] = []
    normalized = re.sub(r"\\\n[ \t]*", " ", document)
    for match in re.finditer(
        r"\btest\s+(-[xrw])\s+(.+?)(?=\s+&&|\n|$)",
        normalized,
    ):
        try:
            operands = shlex.split(match.group(2))
        except ValueError:
            failures.append(f"{name}:unary_test_invalid")
            continue
        if len(operands) != 1:
            failures.append(
                f"{name}:grouped_unary_test:{match.group(1)}:"
                f"{match.group(2).strip()}"
            )
    return failures


def _validate_chmod_commands(name: str, document: str) -> list[str]:
    failures: list[str] = []
    normalized = re.sub(r"\\\n[ \t]*", " ", document)
    for match in re.finditer(
        r"\bchmod\s+(?:-R\s+)?(\S+)\s+(.+?)(?=\s+&&|\n|$)",
        normalized,
    ):
        mode = match.group(1)
        try:
            targets = shlex.split(match.group(2))
        except ValueError:
            failures.append(f"{name}:chmod_invalid")
            continue
        if mode == "a+rX":
            continue
        if (mode, tuple(targets)) in {
            ("0444", ("/app/runtime/default.conf",)),
            ("0700", ("/opt/data/scratch",)),
        }:
            continue
        if "w" in mode:
            failures.append(f"{name}:symbolic_write_broadening:{mode}")
            continue
        if re.fullmatch(r"0?[0-7]{3,4}", mode):
            bits = int(mode, 8)
            code = (
                "numeric_group_or_other_write_broadening"
                if bits & 0o022
                else "unexpected_numeric_chmod"
            )
            failures.append(f"{name}:{code}:{mode}")
            continue
        failures.append(f"{name}:chmod_mode_not_allowlisted:{mode}")
    return failures


def _validate_python_image(
    name: str,
    document: str,
    *,
    runtime_user: str,
    service_directory: str,
    assets: tuple[str, str],
    entrypoint: str,
) -> list[str]:
    failures: list[str] = []
    normalization = "chmod -R a+rX /app/.venv /app/apps /app/packages"
    user = f"USER {runtime_user}"
    _require(failures, document.count(user) == 1, f"{name}:runtime_user")
    _require(
        failures,
        re.findall(r"^USER .+$", document, flags=re.MULTILINE) == [user],
        f"{name}:final_user",
    )
    _require_order(
        failures,
        document,
        f"{name}:normalization_order",
        "RUN uv sync --frozen --no-dev",
        normalization,
        user,
        "test -x /app",
        "test -x /app/.venv",
        "test -x /app/.venv/bin",
        "test -x /app/apps",
        f"test -x {service_directory}",
        "test -x /app/.venv/bin/python",
        f"test -r {assets[0]}",
        f"test -r {assets[1]}",
        entrypoint,
    )
    user_offset = document.find(user)
    _require(
        failures,
        user_offset >= 0 and "chmod " not in document[user_offset:],
        f"{name}:chmod_after_runtime_user",
    )
    return failures


def _validate_ui_image(document: str) -> list[str]:
    failures: list[str] = []
    stages = document.split("\nFROM ", 1)
    _require(failures, len(stages) == 2, "ui:stage_count")
    if len(stages) != 2:
        return failures
    build, final = stages
    _require_order(
        failures,
        build,
        "ui:build_order",
        "COPY deploy/nginx.conf /app/runtime/default.conf",
        "COPY apps/ui ./",
        "RUN npm run build",
        "chmod 0444 /app/runtime/default.conf",
        "chmod -R a+rX /app/dist",
        "test -x /app",
        "test -x /app/dist",
        "test -r /app/runtime/default.conf",
        "test -r /app/dist/index.html",
    )
    _require(
        failures,
        final.startswith("nginxinc/nginx-unprivileged:1.27-alpine"),
        "ui:final_base",
    )
    _require(
        failures,
        "COPY --from=build /app/runtime/default.conf "
        "/etc/nginx/conf.d/default.conf" in final,
        "ui:normalized_config_copy",
    )
    _require(
        failures,
        "COPY --from=build /app/dist /usr/share/nginx/html" in final,
        "ui:normalized_dist_copy",
    )
    _require(
        failures,
        "test -x /usr/share/nginx/html" in final
        and "test -r /etc/nginx/conf.d/default.conf" in final
        and "test -r /usr/share/nginx/html/index.html" in final,
        "ui:final_readability_assertion",
    )
    _require(failures, "\nUSER " not in "\n" + final, "ui:user_override")
    _require(failures, "chmod " not in final, "ui:final_stage_chmod")
    _require(
        failures,
        "COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf" not in final,
        "ui:untrusted_direct_config_copy",
    )
    return failures


def _validate_hermes_image(document: str) -> list[str]:
    failures: list[str] = []
    stages = document.split("\nFROM ", 1)
    _require(failures, len(stages) == 2, "hermes:stage_count")
    if len(stages) != 2:
        return failures
    build, final = stages
    _require_order(
        failures,
        build,
        "hermes:bridge_build_order",
        "uv sync --frozen --no-dev --no-editable --python /usr/bin/python3",
        "chmod -R a+rX /opt/ithildin/.venv",
        "/opt/ithildin/.venv/bin/python -c",
    )
    root_user = "USER 0:0"
    runtime_user = "USER 10000:10000"
    _require(
        failures,
        re.findall(r"^USER .+$", final, flags=re.MULTILINE)
        == [root_user, runtime_user],
        "hermes:user_transition",
    )
    _require_order(
        failures,
        final,
        "hermes:final_order",
        "RUN test -x /usr/bin/timeout",
        root_user,
        "COPY --from=bridge-build /opt/ithildin/.venv /opt/ithildin/.venv",
        "COPY deploy/hermes-node-bridge/profile.json "
        "/opt/ithildin/profile.json",
        "COPY deploy/hermes-node-bridge/fixed-instruction.md "
        "/opt/ithildin/fixed-instruction.md",
        "COPY deploy/hermes-node-bridge/config.yaml /opt/data/config.yaml",
        "chmod -R a+rX /opt/ithildin/.venv",
        "chmod a+rX /opt/ithildin /opt/data",
        "chown 10000:10000 /opt/data/scratch",
        "chmod 0700 /opt/data/scratch",
        runtime_user,
        "test -x /opt/ithildin",
        "test -x /opt/ithildin/.venv",
        "test -x /opt/ithildin/.venv/bin",
        "test -x /opt/ithildin/.venv/bin/python",
        "test -x /opt/data",
        "test -x /opt/data/scratch",
        "test -w /opt/data/scratch",
        "test -r /opt/ithildin/profile.json",
        "test -r /opt/ithildin/fixed-instruction.md",
        "test -r /opt/data/config.yaml",
        "import ithildin_mcp_server.node_bridge, ithildin_schemas",
        'ENTRYPOINT ["/opt/hermes/.venv/bin/hermes"]',
    )
    runtime_offset = final.find(runtime_user)
    _require(
        failures,
        runtime_offset >= 0 and "chmod " not in final[runtime_offset:],
        "hermes:chmod_after_runtime_user",
    )
    _require(
        failures,
        re.findall(r"\bchown\s+\S+\s+\S+", final)
        == ["chown 10000:10000 /opt/data/scratch"],
        "hermes:exact_scratch_ownership",
    )
    return failures


def _validate(documents: dict[str, str]) -> list[str]:
    failures: list[str] = []
    _require(
        failures,
        set(documents) == {"api", "node", "ui", "hermes"},
        "scope:exact_four_dockerfiles",
    )
    for name, document in documents.items():
        failures.extend(_validate_unary_tests(name, document))
        failures.extend(_validate_chmod_commands(name, document))
        _require(failures, "--chown=" not in document, f"{name}:chown_only_fix")
        _require(
            failures,
            all(
                forbidden not in document.lower()
                for forbidden in (
                    "docker-compose",
                    "compose.yaml",
                    "snapshot",
                )
            ),
            f"{name}:out_of_scope_runtime_assumption",
        )
    failures.extend(
        _validate_python_image(
            "api",
            documents.get("api", ""),
            runtime_user="10001:10001",
            service_directory="/app/apps/api",
            assets=(
                "/app/apps/api/verified_launch.py",
                "/app/apps/api/src/ithildin_api/app.py",
            ),
            entrypoint='CMD ["python", "apps/api/verified_launch.py"]',
        )
    )
    failures.extend(
        _validate_python_image(
            "node",
            documents.get("node", ""),
            runtime_user="10002:10002",
            service_directory="/app/apps/node",
            assets=(
                "/app/apps/node/src/ithildin_node/__main__.py",
                "/app/apps/node/src/ithildin_node/service.py",
            ),
            entrypoint='ENTRYPOINT ["python", "-m", "ithildin_node"]',
        )
    )
    failures.extend(_validate_ui_image(documents.get("ui", "")))
    failures.extend(_validate_hermes_image(documents.get("hermes", "")))
    return failures


def test_container_images_normalize_only_runtime_readability() -> None:
    assert _validate(_documents()) == []


def test_runtime_readability_validator_rejects_hostile_drift() -> None:
    originals = _documents()
    mutations: list[dict[str, str]] = []

    chmod_777 = dict(originals)
    chmod_777["api"] = chmod_777["api"].replace(
        "chmod -R a+rX /app/.venv /app/apps /app/packages",
        "chmod -R 777 /app",
        1,
    )
    mutations.append(chmod_777)

    grouped_unary_test = dict(originals)
    grouped_unary_test["api"] = grouped_unary_test["api"].replace(
        "test -x /app \\\n"
        "    && test -x /app/.venv",
        "test -x /app /app/.venv",
        1,
    )
    mutations.append(grouped_unary_test)

    symbolic_write = dict(originals)
    symbolic_write["api"] = symbolic_write["api"].replace(
        "    && groupadd --gid 10001 ithildin \\",
        "    && chmod -R a+w /app/apps \\\n"
        "    && groupadd --gid 10001 ithildin \\",
        1,
    )
    mutations.append(symbolic_write)

    numeric_write = dict(originals)
    numeric_write["node"] = numeric_write["node"].replace(
        "    && groupadd --gid 10002 ithildin-node \\",
        "    && chmod -R 0775 /app/apps \\\n"
        "    && groupadd --gid 10002 ithildin-node \\",
        1,
    )
    mutations.append(numeric_write)

    chmod_after_user = dict(originals)
    chmod_after_user["api"] = chmod_after_user["api"].replace(
        "    && chmod -R a+rX /app/.venv /app/apps /app/packages \\\n",
        "",
        1,
    ).replace(
        "USER 10001:10001\n",
        "USER 10001:10001\n\n"
        "RUN chmod -R a+rX /app/.venv /app/apps /app/packages\n",
        1,
    )
    mutations.append(chmod_after_user)

    runtime_root = dict(originals)
    runtime_root["node"] = runtime_root["node"].replace(
        "USER 10002:10002",
        "USER 0:0",
        1,
    )
    mutations.append(runtime_root)

    ui_direct_copy = dict(originals)
    ui_direct_copy["ui"] = ui_direct_copy["ui"].replace(
        "COPY --from=build /app/runtime/default.conf "
        "/etc/nginx/conf.d/default.conf",
        "COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf",
        1,
    )
    mutations.append(ui_direct_copy)

    hermes_runtime_root = dict(originals)
    hermes_runtime_root["hermes"] = hermes_runtime_root["hermes"].replace(
        "USER 10000:10000",
        "USER 0:0",
        1,
    )
    mutations.append(hermes_runtime_root)

    hermes_unwritable_scratch = dict(originals)
    hermes_unwritable_scratch["hermes"] = hermes_unwritable_scratch[
        "hermes"
    ].replace(
        "    && chown 10000:10000 /opt/data/scratch \\\n"
        "    && chmod 0700 /opt/data/scratch\n",
        "",
        1,
    )
    mutations.append(hermes_unwritable_scratch)

    chown_only = dict(originals)
    chown_only["api"] = chown_only["api"].replace(
        "COPY apps ./apps",
        "COPY --chown=10001:10001 apps ./apps",
        1,
    ).replace(
        "    && chmod -R a+rX /app/.venv /app/apps /app/packages \\\n",
        "",
        1,
    )
    mutations.append(chown_only)

    compose_scope = dict(originals)
    compose_scope["node"] += "\nCOPY deploy/docker-compose.yml /tmp/\n"
    mutations.append(compose_scope)

    snapshot_assumption = dict(originals)
    snapshot_assumption["api"] += "\n# Assume snapshot ownership at runtime.\n"
    mutations.append(snapshot_assumption)

    ui_final_chmod = dict(originals)
    ui_final_chmod["ui"] = ui_final_chmod["ui"].replace(
        "\nEXPOSE 8080",
        "\nRUN chmod -R a+rX /usr/share/nginx/html\n\nEXPOSE 8080",
        1,
    )
    mutations.append(ui_final_chmod)

    for mutation in mutations:
        assert _validate(mutation)
