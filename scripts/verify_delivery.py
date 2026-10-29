"""Verify archive integrity, then exercise an extracted copy without model keys."""
import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.build_submission import excluded, SKIP_DIRS

CASES = "A01 A02 A03 A04 A05 A06 B01 B02 B03 B04 B07 B08 B09 B11 B12 B15 B16 B17".split()


def inspect_archive(path):
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        names = [e.filename for e in entries]
        if len({n.casefold() for n in names}) != len(names):
            raise ValueError("Duplicate archive names")
        for entry in entries:
            raw_name = entry.orig_filename
            parts = raw_name.split("/")
            if (raw_name.startswith("/") or "\\" in raw_name or ":" in raw_name
                    or any(p in ("", ".", "..") or p in SKIP_DIRS or excluded(p) for p in parts)
                    or stat.S_ISLNK(entry.external_attr >> 16)):
                raise ValueError("Unsafe or excluded archive entry")
        if sum(e.file_size for e in entries) > 200_000_000:
            raise ValueError("Review archive exceeds supported size")
        manifest = json.loads(archive.read("DELIVERY-MANIFEST.json").decode("utf-8"))
        if set(names) != set(manifest["files"]) | {"DELIVERY-MANIFEST.json"}:
            raise ValueError("Inventory mismatch")
        for name, expected in manifest["files"].items():
            data = archive.read(name)
            if len(data) != expected["size"] or hashlib.sha256(data).hexdigest() != expected["sha256"]:
                raise ValueError("Artifact hash mismatch")
        source = sorted(n for n in names if n.startswith("src/kb_agent/") and n.endswith(".py") and n.count("/") == 2)
        revision = hashlib.sha256(b"".join(PurePosixPath(n).name.encode("utf-8") + archive.read(n) for n in source)).hexdigest()
        if manifest.get("question_id") != 3 or revision != manifest["engine_revision"]:
            raise ValueError("Engine revision mismatch")
        return manifest


def verify_delivery(archive_path, destination):
    destination = destination.resolve()
    destination.relative_to((ROOT / "dist").resolve())
    manifest = inspect_archive(archive_path)
    destination.mkdir(parents=True, exist_ok=False)
    work = destination / "workspace"
    work.mkdir()
    with zipfile.ZipFile(archive_path) as archive:
        for name in archive.namelist():
            target = work / name
            target.resolve().relative_to(work.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(archive.read(name))
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith("LLM_") and key not in ("DASHSCOPE_API_KEY", "OPENAI_API_KEY", "PYTHONPATH")}
    environment.update(PYTHONUTF8="1", PYTHONNOUSERSITE="1")
    steps = []

    def run(name, arguments, expected):
        command = [sys.executable, "-X", "utf8"] + arguments
        try:
            result = subprocess.run(command, cwd=work, env=environment, capture_output=True,
                                    text=True, encoding="utf-8", timeout=120)
            code, stdout, stderr = result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            code, stdout, stderr = 124, "", "Verification step timed out."
        (destination / (name + ".log")).write_text(stdout + stderr, encoding="utf-8")
        step = {"name": name, "arguments": arguments, "exit_code": code,
                "expected_exit_code": expected, "exit_matches": code == expected}
        steps.append(step)
        return stdout + stderr

    log = run("unit-tests", ["-m", "unittest", "discover", "-s", "tests", "-v"], 0)
    match = re.search(r"Ran (\d+) tests?", log)
    test_count = int(match[1]) if match else 0
    run("mock-evaluation", ["-m", "src.kb_agent.evaluate", "--mode", "mock", "--output-dir", "run-artifacts/mock"], 0)
    run("cli-smoke", ["-m", "src.kb_agent", "--mode", "mock", "--input", "tests/fixtures/inputs/A01.json",
                      "--mock-script", "tests/fixtures/mock/A01.json", "--case-id", "A01", "--output-dir", "run-artifacts/cli"], 0)
    run("controlled-boundaries", ["scripts/run_boundary_checks.py", "--output-dir", "run-artifacts/controlled"], 0)
    run("real-evidence-audit", ["scripts/audit_evidence.py", "--report", "examples/stage5/verified-candidate/evaluation-results.json",
                               "--require-cases"] + CASES + ["--output-dir", "run-artifacts/audit"], 1)
    checks = {"no_local_env": not (work / ".env").exists(), "tests_executed": test_count > 0,
              "command_exit_codes": all(s["exit_matches"] for s in steps)}
    try:
        def read(relative):
            return json.loads((work / relative).read_text(encoding="utf-8"))
        mock = read("run-artifacts/mock/evaluation-results.json")["runs"]
        checks["six_mock_cases_passed"] = (len(mock) == 6 and {r["case_id"] for r in mock} == set(CASES[:6])
            and all(r["mode"] == "mock" and r["react_proven"] is False and all(r["checks"].values()) for r in mock))
        smoke = list((work / "run-artifacts/cli").glob("A01/*/output.json"))
        checks["cli_answered_in_mock"] = len(smoke) == 1 and json.loads(smoke[0].read_text(encoding="utf-8"))["result"]["status"] == "answered"
        boundaries = read("run-artifacts/controlled/boundary-results.json")["runs"]
        checks["nine_controlled_cases_passed"] = len(boundaries) == 9 and all(r["passed"] and r["react_proven"] is False for r in boundaries)
        audit = read("run-artifacts/audit/audit.json")
        rows = audit["runs"]
        checks["real_evidence_reproduces_known_failures"] = (len(rows) == 36 and sum(r["passed"] for r in rows) == 30
            and audit["passed"] is False and not audit["problems"] and all("checks" in r for r in rows)
            and sum(r["passed"] for r in rows if r["case_id"].startswith("A")) == 12
            and all(audit["coverage"].values()) and all(audit["paired_coverage"].values()))
        integrity_keys = ("trace_envelope", "trace_sequence", "actual_tool_counts", "tool_call_links", "tool_observations_replay", "input_matches_fixture")
        checks["all_real_artifacts_intact"] = all(all(r["checks"][key] for key in integrity_keys) for r in rows)
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        checks["generated_reports_readable"] = False
    report = {"archive_sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
              "engine_revision": manifest["engine_revision"], "archive_files": len(manifest["files"]) + 1,
              "python_version": sys.version.split()[0], "model_credentials_removed_from_child_environment": True,
              "unit_test_count": test_count, "steps": steps, "checks": checks, "passed": all(checks.values()),
              "meaning": "Package reproducibility only. Known business failures are preserved; this is not full semantic acceptance.",
              "workspace": "workspace/ (retained for inspection; no original project files rewritten)"}
    (destination / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--output-dir", default="dist/verification")
    args = parser.parse_args(argv)
    try:
        archive = (ROOT / args.archive).resolve()
        archive.relative_to((ROOT / "dist").resolve())
        report = verify_delivery(archive, ROOT / args.output_dir)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile):
        print("Delivery verification failed: check archive integrity and a new output directory under dist/.", file=sys.stderr)
        return 2
    print(json.dumps({"passed": report["passed"], "unit_test_count": report["unit_test_count"],
                      "checks": report["checks"]}, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
