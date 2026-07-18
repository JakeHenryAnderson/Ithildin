"""Descriptor-relative, create-exclusive trusted-host staging placement."""

from __future__ import annotations

import hashlib
import os
import stat
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


class TrustedHostPlacementError(RuntimeError):
    """A bounded placement failure that never exposes a host path."""

    def __init__(self, reason: str, *, effect_possible: bool = False) -> None:
        super().__init__(reason)
        self.reason = reason
        self.effect_possible = effect_possible


@dataclass(frozen=True)
class TrustedHostPlacementResult:
    staged_sha256: str


class TrustedHostPlacement:
    """Retain the trusted root and place one artifact relative to its descriptor."""

    def __init__(
        self,
        staging_root: Path,
        *,
        after_write_hook: Callable[[], None] | None = None,
    ) -> None:
        if not descriptor_relative_placement_supported():
            raise TrustedHostPlacementError("descriptor_relative_placement_unsupported")
        self._parent_fd = -1
        self._root_fd = -1
        self._root_name = ""
        self._root_identity: tuple[int, int] | None = None
        self._after_write_hook = after_write_hook
        try:
            self._parent_fd, self._root_fd, self._root_name = _open_root(staging_root)
            root_stat = os.fstat(self._root_fd)
            if not _is_managed_directory(root_stat):
                raise TrustedHostPlacementError("staging_root_unsafe")
            self._root_identity = (root_stat.st_dev, root_stat.st_ino)
        except Exception:
            self.close()
            raise

    def __enter__(self) -> TrustedHostPlacement:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        for attribute in ("_root_fd", "_parent_fd"):
            fd = getattr(self, attribute)
            if fd >= 0:
                os.close(fd)
                setattr(self, attribute, -1)

    def place(
        self,
        data: bytes,
        *,
        workspace_id: str,
        proposal_id: str,
        destination_leaf: str,
    ) -> TrustedHostPlacementResult:
        _require_safe_component(workspace_id)
        _require_safe_component(proposal_id)
        _require_safe_component(destination_leaf)
        self._require_root_namespace_match(effect_possible=False)

        workspace_fd = _open_or_create_directory(self._root_fd, workspace_id)
        try:
            proposal_fd = _open_or_create_directory(workspace_fd, proposal_id)
        finally:
            os.close(workspace_fd)
        try:
            return self._write_leaf(proposal_fd, destination_leaf, data)
        finally:
            os.close(proposal_fd)

    def _write_leaf(
        self,
        parent_fd: int,
        leaf: str,
        data: bytes,
    ) -> TrustedHostPlacementResult:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        try:
            fd = os.open(leaf, flags, 0o600, dir_fd=parent_fd)
        except FileExistsError as exc:
            raise TrustedHostPlacementError("destination_conflict") from exc
        except OSError as exc:
            raise TrustedHostPlacementError("destination_creation_failed") from exc

        effect_possible = True
        try:
            opened = os.fstat(fd)
            if (
                not stat.S_ISREG(opened.st_mode)
                or opened.st_nlink != 1
                or opened.st_uid != os.geteuid()
            ):
                raise TrustedHostPlacementError(
                    "destination_object_unsafe",
                    effect_possible=effect_possible,
                )
            view = memoryview(data)
            offset = 0
            while offset < len(view):
                written = os.write(fd, view[offset:])
                if written <= 0:
                    raise TrustedHostPlacementError(
                        "destination_write_failed",
                        effect_possible=effect_possible,
                    )
                offset += written
            os.fsync(fd)
            finished = os.fstat(fd)
            if (
                not stat.S_ISREG(finished.st_mode)
                or finished.st_nlink != 1
                or (finished.st_dev, finished.st_ino) != (opened.st_dev, opened.st_ino)
                or finished.st_size != len(data)
            ):
                raise TrustedHostPlacementError(
                    "destination_evidence_mismatch",
                    effect_possible=effect_possible,
                )
            os.fsync(parent_fd)
        except TrustedHostPlacementError:
            raise
        except OSError as exc:
            raise TrustedHostPlacementError(
                "destination_write_failed",
                effect_possible=effect_possible,
            ) from exc
        finally:
            os.close(fd)

        if self._after_write_hook is not None:
            self._after_write_hook()
        self._require_root_namespace_match(effect_possible=True)
        return TrustedHostPlacementResult(
            staged_sha256="sha256:" + hashlib.sha256(data).hexdigest()
        )

    def _require_root_namespace_match(self, *, effect_possible: bool) -> None:
        if self._root_identity is None:
            raise TrustedHostPlacementError("staging_root_unsafe")
        try:
            namespace_stat = os.stat(
                self._root_name,
                dir_fd=self._parent_fd,
                follow_symlinks=False,
            )
        except OSError as exc:
            raise TrustedHostPlacementError(
                "staging_root_namespace_drift",
                effect_possible=effect_possible,
            ) from exc
        if (
            not _is_managed_directory(namespace_stat)
            or (namespace_stat.st_dev, namespace_stat.st_ino) != self._root_identity
        ):
            raise TrustedHostPlacementError(
                "staging_root_namespace_drift",
                effect_possible=effect_possible,
            )


def descriptor_relative_placement_supported() -> bool:
    required_flags = all(hasattr(os, name) for name in ("O_DIRECTORY", "O_NOFOLLOW"))
    required_dir_fd = all(
        operation in os.supports_dir_fd for operation in (os.open, os.mkdir, os.stat)
    )
    return required_flags and required_dir_fd and hasattr(os, "fsync")


def _open_root(staging_root: Path) -> tuple[int, int, str]:
    absolute = Path(os.path.abspath(os.fspath(staging_root)))
    parts = absolute.parts
    if not absolute.is_absolute() or len(parts) < 2:
        raise TrustedHostPlacementError("staging_root_unsafe")
    current_fd = _open_directory(Path(parts[0]))
    try:
        for component in parts[1:-1]:
            next_fd = _open_directory_component(current_fd, component)
            os.close(current_fd)
            current_fd = next_fd
        parent_fd = current_fd
        root_name = parts[-1]
        root_fd = _open_directory_component(parent_fd, root_name)
        return parent_fd, root_fd, root_name
    except Exception:
        os.close(current_fd)
        raise


def _open_directory(path: Path) -> int:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError as exc:
        raise TrustedHostPlacementError("staging_root_unsafe") from exc
    return _verify_directory(fd)


def _open_directory_component(parent_fd: int, name: str) -> int:
    _require_safe_component(name)
    try:
        fd = os.open(
            name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=parent_fd,
        )
    except OSError as exc:
        raise TrustedHostPlacementError("staging_root_unsafe") from exc
    return _verify_directory(fd)


def _open_or_create_directory(parent_fd: int, name: str) -> int:
    _require_safe_component(name)
    try:
        os.mkdir(name, 0o700, dir_fd=parent_fd)
        os.fsync(parent_fd)
    except FileExistsError:
        pass
    except OSError as exc:
        raise TrustedHostPlacementError("destination_ancestor_unsafe") from exc
    try:
        fd = os.open(
            name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            dir_fd=parent_fd,
        )
    except OSError as exc:
        raise TrustedHostPlacementError("destination_ancestor_unsafe") from exc
    fd = _verify_managed_directory(fd)
    try:
        namespace_stat = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        opened_stat = os.fstat(fd)
        if (
            not stat.S_ISDIR(namespace_stat.st_mode)
            or (namespace_stat.st_dev, namespace_stat.st_ino)
            != (opened_stat.st_dev, opened_stat.st_ino)
        ):
            raise TrustedHostPlacementError("destination_ancestor_unsafe")
        return fd
    except Exception:
        os.close(fd)
        raise


def _verify_directory(fd: int) -> int:
    try:
        if not stat.S_ISDIR(os.fstat(fd).st_mode):
            raise TrustedHostPlacementError("destination_ancestor_unsafe")
        return fd
    except Exception:
        os.close(fd)
        raise


def _verify_managed_directory(fd: int) -> int:
    try:
        if not _is_managed_directory(os.fstat(fd)):
            raise TrustedHostPlacementError("destination_ancestor_unsafe")
        return fd
    except Exception:
        os.close(fd)
        raise


def _is_managed_directory(stat_result: os.stat_result) -> bool:
    return bool(
        stat.S_ISDIR(stat_result.st_mode)
        and stat_result.st_uid == os.geteuid()
        and stat_result.st_mode & 0o022 == 0
    )


def _require_safe_component(value: str) -> None:
    if (
        not value
        or value in {".", ".."}
        or "/" in value
        or "\\" in value
        or "\x00" in value
        or len(value.encode("utf-8")) > 240
    ):
        raise TrustedHostPlacementError("destination_component_unsafe")
