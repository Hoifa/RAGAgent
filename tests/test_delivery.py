"""Delivery must exclude configured secrets and reject corrupt or unsafe archives."""
import json
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.build_submission import build_archive, TOP_FILES, TREES
from scripts.verify_delivery import inspect_archive
from scripts.audit_evidence import inside_root


class DeliveryTests(unittest.TestCase):
    def make_project(self, root):
        for name in TOP_FILES:
            (root / name).write_text("Review fixture\n", encoding="utf-8")
        (root / ".env.example").write_text("DASHSCOPE_API_KEY=\nLLM_API_KEY=\n", encoding="utf-8")
        for name in TREES:
            (root / name).mkdir()
        (root / "src/kb_agent").mkdir()
        (root / "src/kb_agent/__init__.py").write_text("# Fixture only\n", encoding="utf-8")

    def test_package_is_reproducible_and_excludes_local_secrets_and_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root)
            (root / ".env").write_text("DASHSCOPE_API_KEY=fixture-only-local-key-value\n", encoding="utf-8")
            (root / "examples/.env.backup").write_text("fixture-only-local-key-value", encoding="utf-8")
            (root / "src/__pycache__").mkdir()
            (root / "src/__pycache__/junk.pyc").write_bytes(b"cache")
            first = build_archive(root, root / "dist/first.zip")
            second = build_archive(root, root / "dist/second.zip")
            self.assertEqual(first["sha256"], second["sha256"])
            with zipfile.ZipFile(root / "dist/first.zip") as archive:
                self.assertIn(".env.example", archive.namelist())
                self.assertNotIn(".env", archive.namelist())
                self.assertNotIn("examples/.env.backup", archive.namelist())
                self.assertFalse(any("__pycache__" in n for n in archive.namelist()))
            self.assertEqual(inspect_archive(root / "dist/first.zip")["question_id"], 3)

    def test_configured_secret_in_included_file_blocks_pack_without_echoing_value(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root)
            secret = "fixture-only-long-secret-value"
            (root / ".env").write_text("DASHSCOPE_API_KEY=" + secret, encoding="utf-8")
            (root / "docs/leak.txt").write_text(secret, encoding="utf-8")
            with self.assertRaises(ValueError) as caught:
                build_archive(root, root / "dist/bad.zip")
            self.assertNotIn(secret, str(caught.exception))
            self.assertFalse((root / "dist/bad.zip").exists())

    def test_nonempty_template_key_cannot_be_packaged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root)
            (root / ".env.example").write_text("DASHSCOPE_API_KEY=fixture-key\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                build_archive(root, root / "dist/bad.zip")

    def test_existing_archive_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root)
            output = root / "dist/review.zip"
            build_archive(root, output)
            before = output.read_bytes()
            with self.assertRaises(ValueError):
                build_archive(root, output)
            self.assertEqual(output.read_bytes(), before)

    def test_modified_file_fails_manifest_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root)
            original, bad = root / "dist/good.zip", root / "dist/bad.zip"
            build_archive(root, original)
            with zipfile.ZipFile(original) as source, zipfile.ZipFile(bad, "w") as target:
                for entry in source.infolist():
                    target.writestr(entry, b"changed bytes" if entry.filename == "README.md" else source.read(entry))
            with self.assertRaises(ValueError):
                inspect_archive(bad)

    def test_traversal_and_symlink_archive_entries_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for index, name in enumerate(("../escape.txt", "C:/escape.txt", "safe\\escape.txt", "symlink")):
                with self.subTest(name=name):
                    path = Path(directory) / (str(index) + ".zip")
                    # ZipInfo normalizes backslashes on Windows at creation;
                    # assign the raw name afterwards to exercise the validator.
                    info = zipfile.ZipInfo("entry")
                    info.filename = name
                    if name == "symlink":
                        info.external_attr = (stat.S_IFLNK | 0o777) << 16
                    with zipfile.ZipFile(path, "w") as archive:
                        archive.writestr(info, "not-extracted")
                    with self.assertRaises(ValueError):
                        inspect_archive(path)

    def test_windows_style_escape_in_saved_report_cannot_leave_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                inside_root(Path(directory), "..\\outside\\output.json")

    def test_engine_hash_is_checked_independently_of_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root)
            original, bad = root / "dist/good.zip", root / "dist/bad.zip"
            build_archive(root, original)
            with zipfile.ZipFile(original) as source, zipfile.ZipFile(bad, "w") as target:
                for entry in source.infolist():
                    data = source.read(entry)
                    if entry.filename == "DELIVERY-MANIFEST.json":
                        value = json.loads(data)
                        value["engine_revision"] = "0" * 64
                        data = json.dumps(value).encode("utf-8")
                    target.writestr(entry, data)
            with self.assertRaises(ValueError):
                inspect_archive(bad)


if __name__ == "__main__":
    unittest.main()
