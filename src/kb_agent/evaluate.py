"""Run known cases; automated checks are not a semantic quality verdict."""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

from .agent import Agent
from .assessment import assess_case
from .knowledge import KnowledgeBase, ToolExecutor
from .models import ChatModel, ScriptedModel
from .__main__ import write_artifacts


ROOT = Path(__file__).resolve().parents[2]


def append_report(path, report):
    """Persist each completed run atomically; do not lose it on interruption."""
    previous = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"runs": []}
    previous["runs"].append(report)
    previous["limitations"] = "Checks include status, exact sources and configured facts, but do not prove complete semantic correctness. Real ReAct requires trace review."
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp") as stream:
            temporary = Path(stream.name)
            json.dump(previous, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run actual case traces; Mock is workflow-only")
    parser.add_argument("--mode", choices=("real", "mock"), required=True)
    parser.add_argument("--cases", nargs="+", default=["A01", "A02", "A03", "A04", "A05", "A06"])
    parser.add_argument("--output-dir", default="examples")
    parser.add_argument("--thinking-mode", choices=("on", "off"), help="Explicit experiment override; never modifies .env")
    parser.add_argument("--repeat", type=int, default=1, help="Repeat every case with the same configuration; retain all runs")
    args = parser.parse_args(argv)
    if args.repeat < 1:
        parser.error("repeat must be positive")
    overrides = None if args.thinking_mode is None else {
        "LLM_ENABLE_THINKING": "true" if args.thinking_mode == "on" else "false",
        "LLM_JSON_MODE": "false" if args.thinking_mode == "on" else "true"}
    if args.mode == "mock" and overrides is not None:
        parser.error("thinking-mode applies only to real mode")
    root = ROOT
    manifest = json.loads((root / "tests/fixtures/case-manifest.json").read_text(encoding="utf-8"))
    case_map = {case["case_id"]: case for case in manifest["cases"]}
    if any(case_id not in case_map for case_id in args.cases):
        parser.error("Unknown case ID")
    # Fail before any run if provider configuration is missing. No silent Mock.
    if args.mode == "real":
        try:
            ChatModel.from_env(overrides)
        except ValueError:
            print("Real model configuration missing or invalid; no real cases executed.", file=sys.stderr)
            return 2
    reports = []
    for repeat_index, case_id in ((i, c) for i in range(1, args.repeat + 1) for c in args.cases):
        case = case_map[case_id]
        if args.mode == "mock":
            script = root / "tests/fixtures/mock" / (case_id + ".json")
            if not script.is_file():
                reports.append({"case_id": case_id, "execution": "not_run", "reason": "No offline script"})
                continue
            model = ScriptedModel.load(script)
        else:
            model = ChatModel.from_env(overrides)
        request = json.loads((root / case["input"]).read_text(encoding="utf-8"))
        tools = ToolExecutor(KnowledgeBase.load(root / case["corpus"]), case.get("fault_injection"))
        # Only request and tool observations reach the model. Expectations stay here.
        output, trace = Agent(model, tools).run(request)
        try:
            directory = write_artifacts(args.output_dir, case_id, request, output, trace)
        except OSError:
            print("Artifact write failed; evaluation is incomplete.", file=sys.stderr)
            return 3
        checks = assess_case(case, request, output, trace, tools.knowledge)
        report = {"case_id": case_id, "repeat_index": repeat_index, "execution": "executed", "mode": args.mode,
                        "run_id": output["run_id"], "directory": str(directory),
                        "model": output["model"], "corpus_revision": output["corpus_revision"],
                        "model_configuration": output.get("model_configuration", {}),
                        "runtime_version": output.get("runtime_version"),
                        "engine_revision": output.get("engine_revision"),
                        "fault_injection": case.get("fault_injection"),
                        "status": output["result"]["status"], "checks": checks,
                        "semantic_review": "finite_assertions_only", "react_proven": False if args.mode == "mock" else None}
        reports.append(report)
        try:
            append_report(Path(args.output_dir) / "evaluation-results.json", report)
        except (OSError, ValueError, KeyError):
            print("Cannot append evaluation summary; existing runs are not removed.", file=sys.stderr)
            return 3
        failed = [key for key, ok in checks.items() if not ok]
        print(str(repeat_index) + "/" + str(args.repeat) + " " + case_id + ": " + output["result"]["status"] + " (" + args.mode + ")" + (" FAILED=" + ",".join(failed) if failed else " OK"), flush=True)
    return 0 if all(r.get("checks") and all(r["checks"].values()) for r in reports) else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
