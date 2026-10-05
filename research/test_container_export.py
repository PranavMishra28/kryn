"""Host-only adversarial checks for stopped-container TAR admission."""

import hashlib
import io
import os
from pathlib import Path
import stat
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import container_export as export


CONFIG = b"[core]\n\trepositoryformatversion = 0\n"
CONFIG_SHA = hashlib.sha256(CONFIG).hexdigest()
LINK = "docs/_theme/djangodocs-epub/static/docicons-a.png"
TARGET = "../../djangodocs/static/docicons-a.png"
BASELINE_LINKS = {LINK: TARGET}


def archive(path, entries):
    """Write a small Docker-cp-shaped fixture; entries are (name, type, data)."""
    with tarfile.open(path, "w") as output:
        for name, kind, payload in entries:
            item = tarfile.TarInfo(name)
            item.type = kind
            if kind in {tarfile.REGTYPE, tarfile.AREGTYPE}:
                item.size = len(payload)
            if kind in {tarfile.SYMTYPE, tarfile.LNKTYPE}:
                item.linkname = payload.decode()
            if name.endswith("run.sh"):
                item.mode = 0o755
            output.addfile(item, io.BytesIO(payload) if item.size else None)


def base_entries():
    return [("testbed", tarfile.DIRTYPE, b""),
            ("testbed/.git", tarfile.DIRTYPE, b""),
            ("testbed/.git/config", tarfile.REGTYPE, CONFIG),
            ("testbed/.git/index", tarfile.REGTYPE, b"untrusted index"),
            ("testbed/docs", tarfile.DIRTYPE, b""),
            ("testbed/docs/release notes.txt", tarfile.REGTYPE, b"public text\n")]


def linked_entries():
    return base_entries() + [
        ("testbed/docs/_theme/djangodocs/static/docicons-a.png", tarfile.REGTYPE, b"PNG"),
        ("testbed/" + LINK, tarfile.SYMTYPE, TARGET.encode()),
    ]


class ContainerExportTest(unittest.TestCase):
    def test_metadata_iteration_does_not_accumulate_tar_members(self):
        original = tarfile.TarFile.next
        counts = []
        def bounded_next(archive):
            counts.append(len(archive.members))
            return original(archive)
        entries = base_entries() + [
            ("testbed/item" + str(i), tarfile.REGTYPE, b"x") for i in range(100)]
        archive(self.tar, entries)
        with patch.object(tarfile.TarFile, "next", bounded_next):
            result = export.extract_worktree(self.tar, self.destination, CONFIG_SHA)
        self.assertEqual(result["files"], 101)
        self.assertLessEqual(max(counts), 1)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="kryn-container-export-", dir="/private/tmp")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.tar = self.root / "stopped.tar"
        self.destination = self.root / "captured"

    def extract(self, entries, **kwargs):
        archive(self.tar, entries)
        before = hashlib.sha256(self.tar.read_bytes()).hexdigest()
        result = export.extract_worktree(self.tar, self.destination, CONFIG_SHA, **kwargs)
        self.assertEqual(before, hashlib.sha256(self.tar.read_bytes()).hexdigest())
        return result

    def assert_rejected(self, entries, *, expected=None, **kwargs):
        archive(self.tar, entries)
        before = hashlib.sha256(self.tar.read_bytes()).hexdigest()
        with self.assertRaises(export.ExportError) as failure:
            export.extract_worktree(self.tar, self.destination, CONFIG_SHA, **kwargs)
        if expected:
            self.assertIn(expected, str(failure.exception))
        self.assertFalse(self.destination.exists())
        self.assertFalse((self.root / "escape").exists())
        self.assertEqual(before, hashlib.sha256(self.tar.read_bytes()).hexdigest())

    def test_regular_worktree_and_git_executable_bit_only(self):
        entries = base_entries() + [
            ("testbed/bin", tarfile.DIRTYPE, b""),
            ("testbed/bin/run.sh", tarfile.REGTYPE, b"#!/bin/sh\nexit 0\n"),
            ("testbed/new file.py", tarfile.REGTYPE, b"value = 2\n"),
        ]
        result = self.extract(entries)
        self.assertEqual((result["files"], result["worktree_bytes"]),
                         (3, len(b"public text\n#!/bin/sh\nexit 0\nvalue = 2\n")))
        self.assertEqual((self.destination / "docs/release notes.txt").read_bytes(), b"public text\n")
        self.assertEqual((self.destination / "new file.py").read_bytes(), b"value = 2\n")
        self.assertFalse((self.destination / ".git").exists())
        self.assertEqual(stat.S_IMODE((self.destination / "bin/run.sh").stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((self.destination / "new file.py").stat().st_mode), 0o600)

    def test_docker_cp_dot_root_and_keyword_api(self):
        entries = [("." if name == "testbed" else "./" + name[len("testbed/"):],
                    kind, data) for name, kind, data in base_entries()]
        archive(self.tar, entries)
        result = export.extract_worktree(
            self.tar, self.destination,
            expected_git_config_sha256=CONFIG_SHA, archive_root=".")
        self.assertEqual(result["files"], 1)
        self.assertEqual((self.destination / "docs/release notes.txt").read_bytes(),
                         b"public text\n")
        self.assertFalse((self.destination / ".git").exists())

    def test_paths_and_types_cannot_escape_or_shadow_git(self):
        hazards = [
            ([("testbed/../escape", tarfile.REGTYPE, b"x")], "Unsafe"),
            ([("/testbed/escape", tarfile.REGTYPE, b"x")], "Unsafe"),
            ([("other/escape", tarfile.REGTYPE, b"x")], "outside"),
            ([("testbed/docs/release notes.txt", tarfile.REGTYPE, b"x")], "Duplicate"),
            ([("testbed/DOCS/other.txt", tarfile.REGTYPE, b"x")], "ambiguous"),
            ([("testbed/pkg/.git/config", tarfile.REGTYPE, b"x")], "Git"),
            ([("testbed/.GIT/config", tarfile.REGTYPE, b"x")], "ambiguous"),
            ([("testbed/name\\escape", tarfile.REGTYPE, b"x")], "Unsafe"),
            ([("testbed/a/./b", tarfile.REGTYPE, b"x")], "Unsafe"),
            ([("testbed/link", tarfile.SYMTYPE, b"/etc/passwd")], "link"),
            ([("testbed/hard", tarfile.LNKTYPE, b"testbed/docs/release notes.txt")], "link"),
            ([("testbed/device", tarfile.CHRTYPE, b"")], "special"),
            ([("testbed/pipe", tarfile.FIFOTYPE, b"")], "special"),
            ([("testbed/regular/", tarfile.REGTYPE, b"x")], "special"),
        ]
        for extra, message in hazards:
            with self.subTest(extra=extra):
                self.assert_rejected(base_entries() + extra, expected=message)

    def test_unicode_normalization_and_casefold_collision(self):
        self.assert_rejected(base_entries() + [
            ("testbed/caf\u00e9.txt", tarfile.REGTYPE, b"one"),
            ("testbed/cafe\u0301.txt", tarfile.REGTYPE, b"two"),
        ], expected="ambiguous")

    def test_only_sealed_relative_symlinks_are_created_after_regular_data(self):
        result = self.extract(linked_entries(), baseline_symlinks=BASELINE_LINKS)
        self.assertEqual(result["symlinks"], 1)
        link = self.destination / LINK
        self.assertTrue(link.is_symlink())
        self.assertEqual(os.readlink(link), TARGET)
        self.assertEqual(link.read_bytes(), b"PNG")
        self.assertFalse((self.destination / ".git").exists())

    def test_dot_root_and_link_before_target_still_import_safely(self):
        entries = linked_entries()
        entries[-2:] = [entries[-1], entries[-2]]
        entries = [("." if name == "testbed" else "./" + name[len("testbed/"):],
                    kind, data) for name, kind, data in entries]
        result = self.extract(entries, archive_root=".", baseline_symlinks=BASELINE_LINKS)
        self.assertEqual(result["symlinks"], 1)
        self.assertEqual((self.destination / LINK).read_bytes(), b"PNG")

    def test_new_changed_deleted_or_shadowing_symlink_fails_closed(self):
        self.assert_rejected(linked_entries(), expected="new or changed")
        wrong = linked_entries()[:-1] + [("testbed/" + LINK, tarfile.SYMTYPE,
                                           b"../../../escape")]
        self.assert_rejected(wrong, expected="new or changed",
                             baseline_symlinks=BASELINE_LINKS)
        self.assert_rejected(linked_entries()[:-1], expected="deleted",
                             baseline_symlinks=BASELINE_LINKS)
        replaced = linked_entries()[:-1] + [("testbed/" + LINK, tarfile.REGTYPE, b"fake")]
        self.assert_rejected(replaced, expected="replaced",
                             baseline_symlinks=BASELINE_LINKS)
        new_link = linked_entries() + [("testbed/docs/extra", tarfile.SYMTYPE, TARGET.encode())]
        self.assert_rejected(new_link, expected="new or changed",
                             baseline_symlinks=BASELINE_LINKS)
        descendant = linked_entries() + [("testbed/" + LINK + "/child", tarfile.REGTYPE, b"x")]
        self.assert_rejected(descendant, expected="parent",
                             baseline_symlinks=BASELINE_LINKS)
        slash = linked_entries()[:-1] + [("testbed/" + LINK + "/", tarfile.SYMTYPE,
                                          TARGET.encode())]
        self.assert_rejected(slash, expected="special",
                             baseline_symlinks=BASELINE_LINKS)
        before_link = linked_entries()[:-1] + [
            ("testbed/" + LINK + "/child", tarfile.REGTYPE, b"x"),
            linked_entries()[-1]]
        self.assert_rejected(before_link, expected="conflicting",
                             baseline_symlinks=BASELINE_LINKS)

    def test_sealed_map_and_targets_cannot_escape_or_chain(self):
        for target in ("/etc/passwd", "../../../../../escape",
                       "../../djangodocs/.git/config"):
            with self.subTest(target=target):
                expected = "escapes" if target == "../../../../../escape" else "target"
                self.assert_rejected(linked_entries(), expected=expected,
                                     baseline_symlinks={LINK: target})
        missing = "../../missing.png"
        self.assert_rejected(linked_entries()[:-1] + [
            ("testbed/" + LINK, tarfile.SYMTYPE, missing.encode())],
            expected="missing", baseline_symlinks={LINK: missing})
        wrong_case = "../../DJANGODOCS/static/docicons-a.png"
        self.assert_rejected(linked_entries()[:-1] + [
            ("testbed/" + LINK, tarfile.SYMTYPE, wrong_case.encode())],
            expected="non-exact", baseline_symlinks={LINK: wrong_case})
        self.assert_rejected(linked_entries(), expected="path",
                             baseline_symlinks={"../escape": TARGET})
        self.assert_rejected(linked_entries(), expected="path",
                             baseline_symlinks={".git/secret": TARGET})
        chained = linked_entries() + [
            ("testbed/docs/_theme/djangodocs/static/second.png", tarfile.SYMTYPE,
             b"docicons-a.png")]
        self.assert_rejected(chained, expected="new or changed",
                             baseline_symlinks=BASELINE_LINKS)

    def test_git_config_must_match_and_is_never_extracted(self):
        wrong = [(name, kind, b"changed" if name == "testbed/.git/config" else data)
                 for name, kind, data in base_entries()]
        self.assert_rejected(wrong, expected="config changed")
        self.assert_rejected([entry for entry in base_entries()
                              if entry[0] != "testbed/.git/config"], expected="lacks")
        self.assert_rejected(base_entries() + [
            ("testbed/.git/config", tarfile.REGTYPE, CONFIG)], expected="Duplicate")

    def test_budgets_and_extended_header_are_bounded(self):
        with patch.object(export, "MAX_FILE_BYTES", 3):
            self.assert_rejected(base_entries(), expected="bytes exceed")
        with patch.object(export, "MAX_WORKTREE_BYTES", 3):
            self.assert_rejected(base_entries(), expected="bytes exceed")
        with patch.object(export, "MAX_WORKTREE_ENTRIES", 1):
            self.assert_rejected(base_entries(), expected="entry count")
        with patch.object(export, "MAX_WORKTREE_ENTRIES", 2):
            self.assert_rejected(base_entries()[:3] + [
                ("testbed/a/b/c/file.py", tarfile.REGTYPE, b"x")],
                expected="directory count")
        with patch.object(export, "MAX_MEMBERS", 2):
            self.assert_rejected(base_entries(), expected="member count")
        with patch.object(export, "MAX_PATH_NODES", 2):
            self.assert_rejected(base_entries(), expected="path tree")
        with patch.object(export, "MAX_HEADER_READ", 1024):
            with tarfile.open(self.tar, "w") as output:
                for name, kind, data in base_entries():
                    item = tarfile.TarInfo(name); item.type = kind
                    item.size = len(data) if kind == tarfile.REGTYPE else 0
                    if name == "testbed/docs/release notes.txt":
                        item.pax_headers = {"comment": "x" * 2048}
                    output.addfile(item, io.BytesIO(data) if item.size else None)
            with self.assertRaisesRegex(export.ExportError, "metadata read"):
                export.extract_worktree(self.tar, self.destination, CONFIG_SHA)
            self.assertFalse(self.destination.exists())

    def test_tar_trailing_data_and_linked_input_fail_closed(self):
        archive(self.tar, base_entries())
        with self.tar.open("ab") as output:
            output.write(b"malicious trailing bytes")
        with self.assertRaisesRegex(export.ExportError, "trailing data"):
            export.extract_worktree(self.tar, self.destination, CONFIG_SHA)
        self.assertFalse(self.destination.exists())
        link = self.root / "linked.tar"; link.symlink_to(self.tar)
        with self.assertRaises(OSError):
            export.extract_worktree(link, self.destination, CONFIG_SHA)
        fifo = self.root / "fifo.tar"; os.mkfifo(fifo)
        with self.assertRaisesRegex(export.ExportError, "regular file"):
            export.extract_worktree(fifo, self.destination, CONFIG_SHA)

    def test_truncated_tar_removes_partial_worktree_and_preserves_input(self):
        archive(self.tar, base_entries())
        self.tar.write_bytes(self.tar.read_bytes()[:2048])
        before = self.tar.read_bytes()
        with self.assertRaises(Exception):
            export.extract_worktree(self.tar, self.destination, CONFIG_SHA)
        self.assertFalse(self.destination.exists())
        self.assertEqual(self.tar.read_bytes(), before)

    def test_sparse_pax_metadata_is_rejected(self):
        with tarfile.open(self.tar, "w") as output:
            for name, kind, data in base_entries():
                item = tarfile.TarInfo(name)
                item.type = kind
                item.size = len(data) if kind == tarfile.REGTYPE else 0
                if name == "testbed/docs/release notes.txt":
                    item.pax_headers = {"SCHILY.sparse.map": "0,12"}
                output.addfile(item, io.BytesIO(data) if item.size else None)
        with self.assertRaisesRegex(export.ExportError, "sparse file"):
            export.extract_worktree(self.tar, self.destination, CONFIG_SHA)
        self.assertFalse(self.destination.exists())

    def test_fresh_destination_is_required(self):
        archive(self.tar, base_entries())
        self.destination.mkdir()
        marker = self.destination / "preserve"; marker.write_text("owner")
        with self.assertRaisesRegex(export.ExportError, "destination"):
            export.extract_worktree(self.tar, self.destination, CONFIG_SHA)
        self.assertEqual(marker.read_text(), "owner")


if __name__ == "__main__":
    unittest.main()
