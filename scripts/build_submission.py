"""Build a reproducible review archive without credentials or local caches."""
import argparse
import hashlib
import json
import os
import stat
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOP_FILES = ("README.md", "SUBMISSION.md", ".env.example", ".gitignore", ".gitattributes", "requirements.txt")
TREES = ("src", "tests", "data", "docs", "examples", "scripts")
SKIP_DIRS = {".git", ".venv", "__pycache__", "dist", ".pytest_cache"}


def excluded(name):
    return ((name.startswith(".env") and name != ".env.example")
            or name.endswith((".pyc", ".pyo", ".pem", ".key", ".p12", ".pfx", "~")))


def collect_files(root):
    root = root.resolve()
    files = []
    for name in TOP_FILES:
        path = root / name
        if not path.is_file():
            raise ValueError("Required delivery file missing: " + name)
        files.append(path)
    for name in TREES:
        if not (root / name).is_dir():
            raise ValueError("Required directory missing: " + name)
        for parent, dirs, names in os.walk(root / name, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not excluded(d))
            for directory in dirs:
                if (Path(parent) / directory).is_symlink():
                    raise ValueError("Do not package symbolic links")
            files.extend(Path(parent) / n for n in sorted(names) if not excluded(n))
    for path in files:
        if path.is_symlink():
            raise ValueError("Do not package symbolic links")
        path.resolve().relative_to(root)
    return sorted(files, key=lambda p: p.relative_to(root).as_posix())


def local_secret_values(root):
    values = []
    path = root / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() in ("DASHSCOPE_API_KEY", "LLM_API_KEY"):
                values.append(value.strip().strip("\"").strip("'"))
    values.extend(os.environ.get(k, "") for k in ("DASHSCOPE_API_KEY", "LLM_API_KEY"))
    return [v.encode("utf-8") for v in values if len(v) > 8]


def build_archive(root, output):
    root, output = root.resolve(), output.resolve()
    output.relative_to(root / "dist")
    if output.exists():
        raise ValueError("Output already exists; choose a new archive path")
    files = collect_files(root)
    secrets = local_secret_values(root)
    contents = {}
    for path in files:
        name = path.relative_to(root).as_posix()
        data = path.read_bytes()
        if any(secret in data for secret in secrets):
            raise ValueError("Configured credential found in included file: " + name)
        contents[name] = data
    for line in contents[".env.example"].decode("utf-8-sig").splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() in ("DASHSCOPE_API_KEY", "LLM_API_KEY") and value.strip():
            raise ValueError("Template API keys must be blank")
    source = sorted((root / "src/kb_agent").glob("*.py"))
    revision = hashlib.sha256(b"".join(p.name.encode("utf-8") + p.read_bytes() for p in source)).hexdigest()
    manifest = {"question_id": 3, "status": "local_review_draft", "engine_revision": revision,
                "note": "No claim that all acceptance checks passed. The manifest excludes itself; it is not a Git commit SHA.",
                "files": {name: {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                          for name, data in contents.items()}}
    contents["DELIVERY-MANIFEST.json"] = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(contents.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, data)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix + ".sha256").write_text(digest + "  " + output.name + "\n", encoding="ascii")
    return {"archive": str(output.relative_to(root)), "sha256": digest, "file_count": len(contents),
            "engine_revision": revision, "credentials_and_caches_excluded": True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="dist/rag-question-3.zip")
    args = parser.parse_args(argv)
    try:
        result = build_archive(ROOT, ROOT / args.output)
    except (OSError, ValueError, zipfile.BadZipFile):
        print("Cannot build archive: check required files, credential-free template, symlinks, and a new output path under dist/.", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
