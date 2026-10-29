"""Offline audit of saved runs. Does not call a model or rewrite raw evidence."""
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.kb_agent.assessment import assess_case
from src.kb_agent.knowledge import KnowledgeBase, ToolExecutor


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def inside_root(root, value):
    # Reports are untrusted file references; never follow a path outside the repo.
    # Saved Windows paths must also work after a Linux/macOS checkout.
    path = (root / str(value).replace("\\", "/")).resolve()
    path.relative_to(root.resolve())
    return path


def label(action):
    if action.get("action") == "finish":
        return "finish:" + action["result"]["status"]
    return action.get("tool_name", "unknown")


def inspect_run(case, request, output, trace, knowledge, recorded):
    """Reuse business validators, independently check saved trace integrity."""
    checks = assess_case(case, request, output, trace, knowledge)
    start, end = trace[0], trace[-1]
    checks["trace_envelope"] = (
        start["type"] == "run_started" and end["type"] == "run_finished"
        and sum(e["type"] == "run_started" for e in trace) == 1
        and sum(e["type"] == "run_finished" for e in trace) == 1
        and end["data"] == output
        and all(start["data"].get(k) == output.get(k) for k in
                ("run_id", "mode", "model", "runtime_version", "engine_revision",
                 "model_configuration", "corpus_revision", "budgets")))
    steps = [e["step"] for e in trace]
    checks["trace_sequence"] = (
        [e["event_id"] for e in trace] == list(range(1, len(trace) + 1))
        and all(type(s) is int and 0 <= s <= output["model_calls"] for s in steps)
        and steps == sorted(steps) and steps[0] == 0 and steps[-1] == output["model_calls"])
    checks["report_matches_artifacts"] = all(recorded.get(k) == output.get(k) for k in
        ("run_id", "mode", "model", "engine_revision", "corpus_revision", "model_configuration"))
    checks["report_matches_artifacts"] &= recorded["status"] == output["result"]["status"]
    checks["input_matches_fixture"] = request == load_json(ROOT / case["input"])
    checks["fault_config_matches"] = start["data"].get("fault_injection") == case.get("fault_injection")

    actions = [e for e in trace if e["type"] == "model_action"]
    attempted = [e for e in actions if e["data"].get("call_id")]
    returned = [e for e in trace if e["type"] == "tool_result"]
    ids = [e["data"]["call_id"] for e in returned]
    checks["actual_tool_counts"] = (
        output["tool_calls"] == len(returned) == len(attempted)
        and ids == ["tool-" + str(i) for i in range(1, len(returned) + 1)]
        and ids == [e["data"]["call_id"] for e in attempted])
    # Every model-call step must leave at least an action, error, resolution or
    # review marker. Resolver failure is the documented exception (no event).
    marked = {e["step"] for e in trace if e["type"] in
              ("model_action", "validation_error", "model_error", "request_resolution", "review_started")}
    missing_steps = set(range(1, output["model_calls"] + 1)) - marked
    resolver_failed = (output["model_calls"] == 1 and not returned
                       and output["result"]["status"] == "incomplete"
                       and output["result"]["reason_code"] in ("model_failure", "invalid_model_output"))
    checks["model_count_has_trace_markers"] = not missing_steps or (missing_steps == {1} and resolver_failed)

    replay = ToolExecutor(knowledge, case.get("fault_injection"))
    attempts = {e["data"]["call_id"]: e for e in attempted}
    links_valid = True
    replay_valid = True
    transitions = []
    for event in returned:
        item = event["data"]
        action_event = attempts.get(item["call_id"])
        if action_event is None:
            links_valid = False
            continue
        action = action_event["data"]
        links_valid &= (action_event["event_id"] < event["event_id"]
                        and action_event["step"] == event["step"])
        actual, injected = replay.execute(action["tool_name"], action["arguments"], 10)
        # Injected errors and empty results must replay exactly. Real timeouts
        # need no deterministic replay, but are kept as explicit exceptions.
        recorded_result = item["result"]
        transient = (not recorded_result["ok"] and not item["injected"]
                     and recorded_result["error"]["code"] in ("timeout", "internal_error"))
        replay_valid &= ((actual == recorded_result or transient) and injected == item["injected"])
        later = next((e for e in actions if e["event_id"] > event["event_id"]), None)
        transitions.append({"step": event["step"], "tool": action["tool_name"],
            "arguments": action["arguments"], "purpose": action["reason"],
            "observation_summary": item["summary"], "injected": item["injected"],
            "next_step": later["step"] if later else None,
            "next_action": label(later["data"]) if later else None,
            "next_arguments": later["data"].get("arguments") if later else None,
            "next_basis": (later["data"].get("reason") or later["data"].get("decision_basis")) if later else None})
    checks["tool_call_links"] = bool(links_valid)
    checks["tool_observations_replay"] = bool(replay_valid)
    duration = (datetime.fromisoformat(end["timestamp"]) - datetime.fromisoformat(start["timestamp"])).total_seconds()
    return {"checks": checks, "passed": all(checks.values()), "status": output["result"]["status"],
            "reason_code": output["result"]["reason_code"], "answer": output["result"]["answer"],
            "follow_up_question": output["result"]["follow_up_question"], "gaps": output["result"]["gaps"],
            "citations": output["result"]["citations"], "model_calls": output["model_calls"],
            "tool_calls": output["tool_calls"], "duration_seconds": round(duration, 3),
            "observed_action_after_tool": any(t["next_action"] for t in transitions),
            "transitions": transitions, "mode": output["mode"], "model": output["model"],
            "engine_revision": output["engine_revision"], "model_configuration": output["model_configuration"],
            "corpus_revision": output["corpus_revision"], "budgets": output["budgets"], "request": request}


def quote(run, doc="D01", passage="P01"):
    return next((c["quote"] for c in run.get("citations", []) if c["document_id"] == doc and c["passage_id"] == passage), "")


def pair_checks(left, right, kind):
    same_config = all(left[k] == right[k] for k in ("engine_revision", "model_configuration", "budgets", "mode", "model"))
    checks = {"same_configuration": same_config, "both_run_checks_passed": left["passed"] and right["passed"]}
    if kind == "paraphrase":
        checks["same_snapshot"] = left["corpus_revision"] == right["corpus_revision"]
        checks["same_original_rule"] = bool(quote(left)) and quote(left) == quote(right)
        checks["both_answered"] = left["status"] == right["status"] == "answered"
    elif kind == "replacement":
        checks["same_request"] = left["request"] == right["request"]
        checks["changed_snapshot"] = left["corpus_revision"] != right["corpus_revision"]
        checks["rule_and_answer_changed"] = (bool(re.search(r"30\s*天", left["answer"]))
            and bool(re.search(r"45\s*天", right["answer"])) and quote(left) != quote(right))
    elif kind in ("conflict", "conflict_scenario"):
        if kind == "conflict":
            checks["same_request"] = left["request"] == right["request"]
        checks["changed_snapshot"] = left["corpus_revision"] != right["corpus_revision"]
        checks["changed_outcome"] = left["status"] == "answered" and right["reason_code"] == "document_conflict"
        checks["both_sides_cited"] = bool(quote(right)) and bool(quote(right, "D02"))
        checks["changed_tool_path"] = [t["arguments"] for t in left["transitions"]] != [t["arguments"] for t in right["transitions"]]
    else:
        raise ValueError("Unknown pair kind")
    return checks


def audit_reports(report_paths, manifest, root=ROOT):
    root = root.resolve()
    report_paths = [path.resolve() for path in report_paths]
    cases = {c["case_id"]: c for c in manifest["cases"]}
    runs, problems, seen = [], [], set()
    for report_path in report_paths:
        try:
            reports = load_json(report_path)["runs"]
        except (OSError, ValueError, KeyError, TypeError):
            problems.append({"code": "report_unreadable", "report": str(report_path)})
            continue
        for recorded in reports:
            cid = recorded.get("case_id")
            base = {"case_id": cid, "source_report": str(report_path.relative_to(root)),
                    "repeat_index": recorded.get("repeat_index"), "run_id": recorded.get("run_id")}
            if recorded.get("execution") != "executed":
                runs.append(dict(base, passed=False, error="not_executed"))
                continue
            try:
                if recorded["run_id"] in seen:
                    raise ValueError("duplicate")
                seen.add(recorded["run_id"])
                case = cases[cid]
                directory = inside_root(root, recorded["directory"])
                paths = [directory / n for n in ("input.json", "output.json", "trace.jsonl")]
                for path in paths:
                    path.resolve().relative_to(root.resolve())
                request, output = [load_json(p) for p in paths[:2]]
                trace = [json.loads(line) for line in paths[2].read_text(encoding="utf-8").splitlines() if line.strip()]
                kb = KnowledgeBase.load(inside_root(root, case["corpus"]))
                run = inspect_run(case, request, output, trace, kb, recorded)
                run.update(base, directory=str(directory.relative_to(root)),
                           artifact_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
                runs.append(run)
            except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError):
                # Do not quote arbitrary corrupted file contents or credentials.
                runs.append(dict(base, passed=False, error="missing_invalid_or_duplicate_evidence"))
    pairs = []
    for left in runs:
        if left["case_id"] != "A01" or "checks" not in left:
            continue
        for kind, cid in (("paraphrase", "A04"), ("replacement", "B01"), ("conflict", "B02"), ("conflict_scenario", "A02")):
            right = next((r for r in runs if r["case_id"] == cid and r["source_report"] == left["source_report"]
                          and r["repeat_index"] == left["repeat_index"] and "checks" in r), None)
            if right:
                checks = pair_checks(left, right, kind)
                pairs.append({"kind": kind, "left_run": left["run_id"], "right_run": right["run_id"],
                              "checks": checks, "passed": all(checks.values())})
    return runs, pairs, problems


def summarize(runs):
    cases = {}
    for cid in sorted({r["case_id"] for r in runs}, key=str):
        items = [r for r in runs if r["case_id"] == cid]
        cases[cid] = {"recorded": len(items), "audit_passed": sum(r["passed"] for r in items),
                      "status_counts": dict(Counter(r.get("status", "invalid_evidence") for r in items))}
    return cases


def markdown(report, root, destination):
    def link(relative):
        import os
        return Path(os.path.relpath(root / relative, destination.parent)).as_posix()
    lines = ["# Saved-evidence audit", "", "Offline recheck; no model requests. Business validators are reused; trace integrity and paired comparisons are additional checks.",
             "", "Finite checks do not establish full semantic correctness or causal model reasoning. AI review is separate from candidate independent verification.", "",
             "Recorded runs: {}; audit passes: {}. Not-executed, missing, malformed and duplicate records fail closed.".format(len(report["runs"]), sum(r["passed"] for r in report["runs"])),
             "", "## Outcomes by case", "", "| Case | Records | Audit passes | Actual outcomes |", "|---|---|---|---|"]
    for cid, stats in report["by_case"].items():
        lines.append("| {} | {} | {} | {} |".format(cid, stats["recorded"], stats["audit_passed"], json.dumps(stats["status_counts"])))
    lines += ["", "## Run evidence", "", "| Case | Round | Status | Audit | Model/tools | Input | Output | Trace |", "|---|---|---|---|---|---|---|---|"]
    for r in report["runs"]:
        if "directory" not in r:
            lines.append("| {} | {} | invalid evidence | FAIL | - | - | - | - |".format(r["case_id"], r["repeat_index"]))
            continue
        p = r["directory"]
        lines.append("| {} | {} | {} | {} | {}/{} | [input]({}) | [output]({}) | [trace]({}) |".format(
            r["case_id"], r["repeat_index"], r["status"], "PASS" if r["passed"] else "FAIL", r["model_calls"], r["tool_calls"],
            link(p + "/input.json"), link(p + "/output.json"), link(p + "/trace.jsonl")))
    lines += ["", "## Paired comparisons", "", "| Comparison | Left run | Right run | Result |", "|---|---|---|---|"]
    for p in report["pairs"]:
        lines.append("| {} | {} | {} | {} |".format(p["kind"], p["left_run"], p["right_run"], "PASS" if p["passed"] else "FAIL"))
    lines += ["", "Every tool argument, observation summary and next model action is indexed in audit.json under runs[].transitions. Artifact hashes are audit-time checksums, not signatures or proof against deliberate forgery.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="append", required=True, help="Saved evaluation-results.json; repeat for multiple batches")
    parser.add_argument("--output-dir", default="examples/stage5/audit")
    parser.add_argument("--require-cases", nargs="+", default=["A01", "A02", "A03", "A04", "A05", "A06"])
    parser.add_argument("--min-runs-per-case", type=int, default=2)
    args = parser.parse_args(argv)
    if args.min_runs_per_case < 1:
        parser.error("min-runs-per-case must be positive")
    try:
        paths = [inside_root(ROOT, p) for p in args.report]
        destination = inside_root(ROOT, args.output_dir)
        if any(destination == p.parent or destination in p.parents for p in paths):
            raise ValueError("Audit destination must be separate from raw reports")
        manifest = load_json(ROOT / "tests/fixtures/case-manifest.json")
        runs, pairs, problems = audit_reports(paths, manifest)
        counts = summarize(runs)
        coverage = {cid: counts.get(cid, {}).get("recorded", 0) >= args.min_runs_per_case for cid in args.require_cases}
        pair_counts = Counter(p["kind"] for p in pairs)
        paired_coverage = {kind: pair_counts[kind] >= args.min_runs_per_case
                           for kind, other in (("paraphrase", "A04"), ("replacement", "B01"), ("conflict", "B02"))
                           if "A01" in args.require_cases and other in args.require_cases}
        report = {"limitations": ["Finite assertions only; no automatic full semantic verdict.",
                  "Observed next actions are evidence for review, not proof of internal reasoning.",
                  "Groups may span code revisions; paired checks require equal code/configuration.",
                  "Checksums capture audit-time bytes; they are not authenticated provenance."],
                  "runs": runs, "pairs": pairs, "by_case": counts, "coverage": coverage,
                  "paired_coverage": paired_coverage, "problems": problems}
        report["passed"] = bool(runs) and not problems and all(r["passed"] for r in runs) and all(coverage.values()) and all(paired_coverage.values()) and all(p["passed"] for p in pairs)
        destination.mkdir(parents=True, exist_ok=False)
        (destination / "audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (destination / "README.md").write_text(markdown(report, ROOT, destination / "README.md"), encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError):
        print("Audit failed: invalid paths/configuration, unreadable report, or output already exists.", file=sys.stderr)
        return 2
    print("Saved audit: {} runs, {} passes, {} pairs; result={}".format(len(runs), sum(r["passed"] for r in runs), len(pairs), report["passed"]))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
