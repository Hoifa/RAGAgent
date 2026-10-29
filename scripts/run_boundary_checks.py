"""Persist controlled executor experiments, explicitly not real model decisions."""
import argparse
import copy
import io
import json
import sys
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.kb_agent.agent import Agent
from src.kb_agent.models import ScriptedModel
from src.kb_agent.knowledge import KnowledgeBase, ToolExecutor
from src.kb_agent.__main__ import write_artifacts, main as cli


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="examples/stage5/controlled-boundaries")
    args = parser.parse_args(argv)
    target = (ROOT / args.output_dir).resolve()
    try:
        target.relative_to(ROOT)
        target.mkdir(parents=True, exist_ok=False)
    except (ValueError, OSError):
        print("Use a new output directory inside this repository.", file=sys.stderr)
        return 2
    request = json.loads((ROOT / "tests/fixtures/inputs/A01.json").read_text(encoding="utf-8"))
    actions = json.loads((ROOT / "tests/fixtures/mock/A01.json").read_text(encoding="utf-8"))
    bad = copy.deepcopy(actions[-1])
    bad["result"]["citations"][0]["quote"] = "fabricated original text"
    scenarios = [
        ("B05-model-budget", actions, {"max_model_calls": 2}, "incomplete", "budget_exhausted"),
        ("B05-tool-budget", actions, {"max_tool_calls": 1}, "incomplete", "budget_exhausted"),
        ("B06-forged-quote", actions[:2] + [bad], {"max_model_calls": 3}, "incomplete", "budget_exhausted"),
        ("B06-repair", actions[:2] + [bad, actions[-1]], {"max_model_calls": 4}, "answered", None),
        ("B13-final-allowed-call", actions, {"max_model_calls": 3, "max_tool_calls": 2}, "answered", None),
    ]
    reports = []
    for cid, script, limits, status, reason in scenarios:
        kb = KnowledgeBase.load(ROOT / "data/corpora/normal.json")
        output, trace = Agent(ScriptedModel(script), ToolExecutor(kb), **limits).run(request)
        directory = write_artifacts(target, cid, request, output, trace)
        checks = {"status_matches": output["result"]["status"] == status,
                  "reason_matches": output["result"]["reason_code"] == reason,
                  "bounded": output["model_calls"] <= output["budgets"]["max_model_calls"]
                    and output["tool_calls"] <= output["budgets"]["max_tool_calls"]}
        if cid.startswith("B06"):
            checks["forgery_rejected"] = any(e["type"] == "validation_error" and "Quote" in e["data"]["message"] for e in trace)
            checks["no_forged_final_quote"] = all(c["quote"] != "fabricated original text" for c in output["result"]["citations"])
        reports.append({"case_id": cid, "mode": "mock", "react_proven": False,
                        "directory": str(directory.relative_to(ROOT)), "checks": checks, "passed": all(checks.values())})
    invalid = [
        ("B10-empty", {"question": ""}),
        ("B10-whitespace", {"question": "   "}),
        ("B10-invalid-role", {"question": "verify", "history": [{"role": "system", "content": "invalid"}]}),
    ]
    for cid, value in invalid:
        directory = target / cid
        directory.mkdir()
        dump(directory / "input.json", value)
        out, err = io.StringIO(), io.StringIO()
        with patch("src.kb_agent.__main__.ScriptedModel.load") as model_load, redirect_stdout(out), redirect_stderr(err):
            code = cli(["--mode", "mock", "--input", str(directory / "input.json"),
                        "--mock-script", "unused", "--output-dir", str(directory)])
        checks = {"exit_code_2": code == 2, "invalid_request": json.loads(err.getvalue())["error"]["code"] == "invalid_request",
                  "model_not_loaded": model_load.call_count == 0, "no_business_output": not out.getvalue()}
        execution = {"exit_code": code, "error": json.loads(err.getvalue()), "model_load_count": model_load.call_count,
                     "boundary": "Rejected before model/tool execution; no Agent Trace exists."}
        dump(directory / "execution-report.json", execution)
        reports.append({"case_id": cid, "mode": "controlled_input", "react_proven": False,
                        "directory": str(directory.relative_to(ROOT)), "checks": checks, "passed": all(checks.values())})
    directory = target / "B14-write-failure"
    directory.mkdir()
    blocked = directory / "blocked-output-file"
    blocked.write_text("Deliberate file/directory collision for write-failure experiment.\n", encoding="utf-8")
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cli(["--mode", "mock", "--input", str(ROOT / "tests/fixtures/inputs/A01.json"),
                    "--mock-script", str(ROOT / "tests/fixtures/mock/A01.json"), "--output-dir", str(blocked)])
    dump(directory / "execution-report.json", {"exit_code": code, "stdout": out.getvalue(), "stderr": err.getvalue(),
         "boundary": "Output was printed; artifact saving failed. No saved Trace is claimed."})
    checks = {"exit_code_3": code == 3, "explicit_write_error": json.loads(err.getvalue())["error"]["code"] == "artifact_write_failed",
              "no_false_saved_message": "Artifacts saved" not in err.getvalue()}
    reports.append({"case_id": "B14-write-failure", "mode": "mock", "react_proven": False,
                    "directory": str(directory.relative_to(ROOT)), "checks": checks, "passed": all(checks.values())})
    dump(target / "boundary-results.json", {"description": "Controlled executor checks; scripted actions do not prove model decisions.", "runs": reports})
    print("Controlled boundaries: {}/{} passed".format(sum(r["passed"] for r in reports), len(reports)))
    return 0 if all(r["passed"] for r in reports) else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
