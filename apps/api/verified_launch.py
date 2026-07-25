"""Verify runtime-candidate evidence before importing the API application."""

from __future__ import annotations

import json
import logging
import os
import stat
from pathlib import Path

from runtime_candidate_bootstrap import (
    RuntimeCandidateVerificationError,
    verifier_from_environment,
)

STARTUP_STATUS_DIRECTORY = Path("/run/ithildin-startup")
STARTUP_STATUS_FILE = "api-startup-stage.json"
STARTUP_STATUS_TEMP_FILE = ".api-startup-stage.tmp"
STARTUP_STAGES = frozenset(
    {
        "launcher_entered",
        "runtime_candidate_verification_entered",
        "application_import_entered",
        "application_factory_entered",
        "server_run_entered",
        "lifespan_configuration_entered",
        "lifespan_persistence_entered",
        "lifespan_governance_entered",
        "lifespan_services_entered",
        "startup_ready",
        "shutdown_entered",
        "shutdown_complete",
    }
)


def _directory_flags() -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    return flags


def _file_flags() -> int:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    return flags


def write_closed_startup_stage(stage: str) -> None:
    """Best-effort CLOSED startup marker; failures never affect the service."""
    directory_fd = -1
    temporary_fd = -1
    try:
        if stage not in STARTUP_STAGES:
            return
        directory_fd = os.open(STARTUP_STATUS_DIRECTORY, _directory_flags())
        directory = os.fstat(directory_fd)
        if (
            not stat.S_ISDIR(directory.st_mode)
            or stat.S_IMODE(directory.st_mode) != 0o700
            or directory.st_uid != os.geteuid()
            or directory.st_gid != os.getegid()
        ):
            return
        try:
            os.unlink(STARTUP_STATUS_TEMP_FILE, dir_fd=directory_fd)
        except FileNotFoundError:
            pass
        payload = (
            json.dumps(
                {
                    "record_type": "ithildin_api_closed_startup_stage",
                    "schema_version": "1",
                    "stage": stage,
                },
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        ).encode("ascii")
        temporary_fd = os.open(
            STARTUP_STATUS_TEMP_FILE,
            _file_flags(),
            0o600,
            dir_fd=directory_fd,
        )
        os.fchmod(temporary_fd, 0o600)
        view = memoryview(payload)
        while view:
            written = os.write(temporary_fd, view)
            if written <= 0:
                raise OSError("startup stage write made no progress")
            view = view[written:]
        os.fsync(temporary_fd)
        os.close(temporary_fd)
        temporary_fd = -1
        os.replace(
            STARTUP_STATUS_TEMP_FILE,
            STARTUP_STATUS_FILE,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
        )
        os.fsync(directory_fd)
    except Exception:
        pass
    finally:
        if temporary_fd >= 0:
            try:
                os.close(temporary_fd)
            except Exception:
                pass
        if directory_fd >= 0:
            try:
                os.unlink(STARTUP_STATUS_TEMP_FILE, dir_fd=directory_fd)
            except Exception:
                pass
            try:
                os.close(directory_fd)
            except Exception:
                pass


def main() -> int:
    write_closed_startup_stage("launcher_entered")
    write_closed_startup_stage("runtime_candidate_verification_entered")
    verifier = verifier_from_environment()
    verified_payload: dict[str, str] | None = None
    try:
        verified_payload = verifier.verify()
    except RuntimeCandidateVerificationError as exc:
        logging.basicConfig(level=logging.INFO)
        logging.getLogger(__name__).warning(
            "runtime candidate is unreviewed; trusted-host promotion remains unavailable: %s",
            exc,
        )

    write_closed_startup_stage("application_import_entered")
    import uvicorn
    from ithildin_api.app import create_app
    from ithildin_api.promotion_authority import RuntimeCandidateRecord

    write_closed_startup_stage("application_factory_entered")
    candidate = (
        RuntimeCandidateRecord.model_validate(verified_payload)
        if verified_payload is not None
        else None
    )

    def reverify_candidate() -> RuntimeCandidateRecord:
        return RuntimeCandidateRecord.model_validate(verifier.verify())

    application = create_app(
        runtime_candidate=candidate,
        runtime_candidate_verifier=(
            reverify_candidate if verified_payload is not None else None
        ),
        startup_stage_reporter=write_closed_startup_stage,
    )
    write_closed_startup_stage("server_run_entered")
    uvicorn.run(
        application,
        host="0.0.0.0",
        port=8000,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
