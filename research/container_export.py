"""Bounded, data-only import of a stopped SWE worker's ``docker cp`` TAR.

The caller proves the container has stopped, saves ``docker cp ID:/testbed/. -``
to a private regular file, and supplies the sealed base .git/config hash. This
module never invokes Docker or Git. The returned worktree has no .git directory;
the caller supplies a trusted base .git before networkless patch collection.
"""

import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
import tarfile
import unicodedata


MAX_TAR_BYTES = 2 * 1024**3
MAX_MEMBERS = 200_000  # Includes ignored .git objects.
MAX_PATH_NODES = 100_000  # Bounds collision-check memory, including ignored .git.
MAX_WORKTREE_ENTRIES = 50_000
MAX_WORKTREE_BYTES = 512 * 1024**2
MAX_FILE_BYTES = 64 * 1024**2
MAX_GIT_CONFIG_BYTES = 1024**2
MAX_HEADER_READ = 1024**2  # Bound PAX/GNU extended-header allocation in tarfile.
MAX_PATH_BYTES = 1024
MAX_DEPTH = 64
CHUNK = 64 * 1024


class ExportError(RuntimeError):
    """The captured archive cannot be admitted as a candidate worktree."""


class _BoundedReader:
    """Keep stdlib tarfile from reading a huge extended header into memory."""

    def __init__(self, source):
        self.source = source

    def read(self, size=-1):
        if not 0 <= size <= MAX_HEADER_READ:
            raise ExportError("Oversized TAR metadata read")
        return self.source.read(size)

    def seek(self, *args):
        return self.source.seek(*args)

    def tell(self):
        return self.source.tell()


def _parts(name, archive_root):
    if not isinstance(name, str) or name.startswith("/") or "\\" in name:
        raise ExportError("Unsafe TAR path")
    if name.startswith("./"):
        name = name[2:]
    if name.endswith("/"):
        name = name[:-1]
    if archive_root == ".":
        relative = "" if name == "." else name
    elif name in {archive_root, archive_root + "/."}:
        relative = ""
    elif name.startswith(archive_root + "/"):
        relative = name[len(archive_root) + 1:]
    else:
        raise ExportError("TAR member is outside the pinned archive root")
    if not relative:
        return ()
    parts = tuple(relative.split("/"))
    if (len(parts) > MAX_DEPTH or len(relative.encode("utf-8")) > MAX_PATH_BYTES or
            any(not part or part in {".", ".."} or part.endswith((" ", ".")) or
                ":" in part or len(part.encode("utf-8")) > 255 or
                any(ord(char) < 32 or ord(char) == 127 for char in part)
                for part in parts)):
        raise ExportError("Unsafe or overlong TAR path")
    return parts


def _record(parts, kind, spellings, kinds, explicit):
    """Reject duplicate names and every case/Unicode collision in ancestors."""
    folded = ()
    for index, part in enumerate(parts):
        folded += (unicodedata.normalize("NFC", part).casefold(),)
        spelling = parts[:index + 1]
        previous = spellings.setdefault(folded, spelling)
        if previous != spelling:
            raise ExportError("Case-fold or Unicode-ambiguous TAR path")
        if index < len(parts) - 1:
            if kinds.get(folded) not in {None, "dir"}:
                raise ExportError("TAR non-directory is used as a parent")
            kinds[folded] = "dir"
    if folded in explicit or (folded in kinds and kinds[folded] != kind):
        raise ExportError("Duplicate or conflicting TAR path")
    explicit.add(folded)
    kinds[folded] = kind


def _directory(root_fd, parts, counts):
    current = os.dup(root_fd)
    try:
        for part in parts:
            try:
                os.mkdir(part, 0o700, dir_fd=current)
                counts["directories"] += 1
                if counts["directories"] > MAX_WORKTREE_ENTRIES:
                    raise ExportError("Worktree directory count exceeds limit")
            except FileExistsError:
                pass
            following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                dir_fd=current)
            os.close(current)
            current = following
        return current
    except BaseException:
        os.close(current)
        raise


def _write_file(root_fd, parts, member, archive, counts):
    parent_fd = _directory(root_fd, parts[:-1], counts)
    try:
        fd = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent_fd)
        try:
            os.fchmod(fd, 0o700 if member.mode & 0o111 else 0o600)
            source = archive.extractfile(member)
            if source is None:
                raise ExportError("TAR regular file has no payload")
            remaining = member.size
            while remaining:
                chunk = source.read(min(CHUNK, remaining))
                if not chunk:
                    raise ExportError("Truncated TAR member")
                remaining -= len(chunk)
                view = memoryview(chunk)
                while view:
                    view = view[os.write(fd, view):]
        finally:
            os.close(fd)
    finally:
        os.close(parent_fd)


def _sealed_links(mapping):
    """Validate exact trusted baseline links before reading any candidate bytes."""
    if mapping is None:
        return {}
    if not isinstance(mapping, dict) or len(mapping) > MAX_WORKTREE_ENTRIES:
        raise ExportError("Invalid sealed symlink map")
    links, folded_names = {}, set()
    for name, target in mapping.items():
        parts = _parts(name, ".")
        folded = tuple(unicodedata.normalize("NFC", part).casefold() for part in parts)
        if (not parts or name != "/".join(parts) or ".git" in folded or
                folded in folded_names or not isinstance(target, str) or
                not target or target.startswith("/") or "\\" in target):
            raise ExportError("Invalid sealed symlink path or target")
        folded_names.add(folded)
        components = target.split("/")
        if len(components) > MAX_DEPTH or len(target.encode("utf-8")) > MAX_PATH_BYTES:
            raise ExportError("Overlong sealed symlink target")
        resolved = list(parts[:-1])
        for component in components:
            if component == "..":
                if not resolved:
                    raise ExportError("Sealed symlink escapes the worktree")
                resolved.pop()
            elif (not component or component == "." or component.endswith((" ", ".")) or
                  ":" in component or len(component.encode("utf-8")) > 255 or
                  any(ord(char) < 32 or ord(char) == 127 for char in component) or
                  unicodedata.normalize("NFC", component).casefold() == ".git"):
                raise ExportError("Unsafe sealed symlink target")
            else:
                resolved.append(component)
        if not resolved or len(resolved) > MAX_DEPTH:
            raise ExportError("Sealed symlink target is outside the worktree")
        links[parts] = (target, tuple(resolved))
    return links


def _regular_target(root_fd, parts):
    """Verify a baseline link target exists without following a candidate link."""
    current = os.dup(root_fd)
    try:
        device = os.fstat(root_fd).st_dev
        for part in parts[:-1]:
            following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                dir_fd=current)
            os.close(current)
            current = following
            if os.fstat(current).st_dev != device:
                raise ExportError("Sealed symlink target crosses a volume")
        info = os.stat(parts[-1], dir_fd=current, follow_symlinks=False)
        if not stat.S_ISREG(info.st_mode) or info.st_dev != device:
            raise ExportError("Sealed symlink target is not a regular worktree file")
    except OSError as error:
        raise ExportError("Sealed symlink target is missing or unsafe") from error
    finally:
        os.close(current)


def extract_worktree(tar_path, destination, expected_git_config_sha256, *,
                     archive_root="testbed", baseline_symlinks=None):
    """Validate and extract regular worktree data; never extract untrusted .git.

    The TAR must already be a preserved file from a stopped container. The
    destination must be absent under a canonical parent. On failure it is
    removed; the original TAR is untouched. Limits above are fixed admission
    thresholds, not dynamically relaxed for a candidate.
    """
    links = _sealed_links(baseline_symlinks)
    tar_path, destination = Path(tar_path), Path(destination)
    if (not re.fullmatch(r"[0-9a-f]{64}", expected_git_config_sha256) or
            archive_root not in {"."} and
            (not archive_root or "/" in archive_root or archive_root in {".", ".."}) or
            not destination.is_absolute() or destination.parent != destination.parent.resolve() or
            destination.exists() or destination.is_symlink()):
        raise ExportError("Invalid export destination, archive root, or sealed hash")
    if tar_path.parent != tar_path.parent.resolve():
        raise ExportError("TAR parent must be canonical")
    # O_NONBLOCK prevents a mistaken FIFO path from hanging before fstat rejects it.
    fd = os.open(tar_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    created = False
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or
                info.st_nlink != 1 or info.st_mode & 0o022 or
                not 0 < info.st_size <= MAX_TAR_BYTES):
            raise ExportError("TAR is not a bounded private regular file")
        with os.fdopen(fd, "rb", closefd=False) as source:
            digest = hashlib.sha256()
            while chunk := source.read(CHUNK):
                digest.update(chunk)
            source.seek(0)
            destination.mkdir(mode=0o700)
            created = True
            root_fd = os.open(destination, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                files = entries = total = members = 0
                counts = {"directories": 0}
                config_seen = False
                seen_links = set()
                spellings, kinds, explicit = {}, {}, set()
                with tarfile.open(fileobj=_BoundedReader(source), mode="r:",
                                  stream=True, encoding="utf-8", errors="strict") as archive:
                    for member in archive:
                        members += 1
                        if members > MAX_MEMBERS:
                            raise ExportError("TAR member count exceeds limit")
                        parts = _parts(member.name, archive_root)
                        kind = ("dir" if member.type == tarfile.DIRTYPE else
                                "file" if member.type in {tarfile.REGTYPE, tarfile.AREGTYPE}
                                else "symlink" if member.type == tarfile.SYMTYPE
                                else None)
                        if (kind is None or (kind != "symlink" and member.linkname) or member.sparse or
                                (kind != "dir" and member.name.endswith("/")) or
                                any("sparse" in key.casefold() for key in member.pax_headers) or
                                member.size < 0 or (kind != "file" and member.size)):
                            raise ExportError("TAR contains a hardlink, special entry, or sparse file")
                        if kind == "symlink":
                            if parts not in links or member.linkname != links[parts][0]:
                                raise ExportError("Candidate symlink is new or changed")
                        elif parts in links:
                            raise ExportError("Sealed symlink was replaced")
                        _record(parts, kind, spellings, kinds, explicit)
                        if len(spellings) > MAX_PATH_NODES:
                            raise ExportError("TAR path tree exceeds limit")
                        if not parts:
                            if kind != "dir":
                                raise ExportError("TAR root is not a directory")
                            continue
                        folded = tuple(unicodedata.normalize("NFC", part).casefold()
                                       for part in parts)
                        if ".git" in folded:
                            if parts[0] != ".git" or folded[1:].count(".git"):
                                raise ExportError("Deceptive Git directory path")
                            if parts == (".git", "config"):
                                if kind != "file" or member.size > MAX_GIT_CONFIG_BYTES:
                                    raise ExportError("Invalid candidate Git config")
                                payload = archive.extractfile(member)
                                if payload is None or hashlib.sha256(
                                        payload.read(member.size)).hexdigest() != expected_git_config_sha256:
                                    raise ExportError("Candidate Git config changed")
                                config_seen = True
                            elif parts == (".git",) and kind != "dir":
                                raise ExportError("Candidate Git directory is not a directory")
                            continue
                        entries += 1
                        if entries > MAX_WORKTREE_ENTRIES:
                            raise ExportError("Worktree entry count exceeds limit")
                        if kind == "dir":
                            os.close(_directory(root_fd, parts, counts))
                            continue
                        if kind == "symlink":
                            seen_links.add(parts)
                            continue
                        if member.size > MAX_FILE_BYTES or total + member.size > MAX_WORKTREE_BYTES:
                            raise ExportError("Worktree file bytes exceed limit")
                        _write_file(root_fd, parts, member, archive, counts)
                        files += 1
                        total += member.size
                    source.seek(archive.offset)
                    trailing = 0
                    while chunk := source.read(CHUNK):
                        trailing += len(chunk)
                        if any(chunk):
                            raise ExportError("TAR has nonzero trailing data")
                    if trailing < 1024:
                        raise ExportError("TAR lacks end-of-archive blocks")
                if not config_seen or not files:
                    raise ExportError("TAR lacks a sealed Git config or worktree files")
                if set(links) != seen_links:
                    raise ExportError("A sealed baseline symlink was deleted")
                final = os.fstat(fd)
                if (final.st_size, final.st_mtime_ns, final.st_ctime_ns) != (
                        info.st_size, info.st_mtime_ns, info.st_ctime_ns):
                    raise ExportError("TAR changed during import")
                for _target, resolved in links.values():
                    folded_target = tuple(unicodedata.normalize("NFC", part).casefold()
                                          for part in resolved)
                    if spellings.get(folded_target) != resolved or kinds.get(folded_target) != "file":
                        raise ExportError("Sealed symlink target is missing or non-exact in TAR")
                    _regular_target(root_fd, resolved)
                for parts, (target, _resolved) in links.items():
                    parent_fd = _directory(root_fd, parts[:-1], counts)
                    try:
                        os.symlink(target, parts[-1], dir_fd=parent_fd)
                    finally:
                        os.close(parent_fd)
            finally:
                os.close(root_fd)
        return {"tar_sha256": digest.hexdigest(), "tar_bytes": info.st_size,
                "members": members, "worktree_entries": entries,
                "files": files, "symlinks": len(seen_links),
                "directories": counts["directories"],
                "worktree_bytes": total,
                "git_config_sha256": expected_git_config_sha256}
    except BaseException:
        if created and destination.is_dir() and not destination.is_symlink():
            shutil.rmtree(destination)
        raise
    finally:
        os.close(fd)
