"""CLI entry point: python -m src.kb_agent."""
import argparse
import json
import re
import sys
from pathlib import Path

from .agent import Agent
from .contracts import ContractError, validate_request
from .knowledge import KnowledgeBase, ToolExecutor
from .models import ChatModel, ScriptedModel


def write_artifacts(root, case_id, request, output, trace):
    directory = Path(root) / case_id / output["run_id"]
    directory.mkdir(parents=True, exist_ok=False)
    for name, value in (("input.json", request), ("output.json", output)):
        (directory / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (directory / "trace.jsonl").open("x", encoding="utf-8") as stream:
        for event in trace:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")
    return directory


def main(argv=None):
    parser = argparse.ArgumentParser(description="企业知识问答 Agent（real 或显式 scripted Mock）")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", help="UTF-8 request JSON file")
    source.add_argument("--question", help="Current question without history")
    parser.add_argument("--corpus", default="data/corpora/normal.json")
    parser.add_argument("--mode", choices=("real", "mock"), default="real")
    parser.add_argument("--thinking-mode", choices=("on", "off"), help="Override model thinking for this run only")
    parser.add_argument("--mock-script", help="Required in Mock mode; preset actions are NOT model decisions")
    parser.add_argument("--fault-file", help="Explicit test-only tool fault JSON")
    parser.add_argument("--case-id", default="manual")
    parser.add_argument("--output-dir", default="examples")
    parser.add_argument("--max-model-calls", type=int, default=12)
    parser.add_argument("--max-tool-calls", type=int, default=6)
    parser.add_argument("--model-timeout", type=float, default=60)
    parser.add_argument("--tool-timeout", type=float, default=10)
    args = parser.parse_args(argv)
    try:
        request = json.loads(Path(args.input).read_text(encoding="utf-8-sig")) if args.input else {"question": args.question}
        validate_request(request)
    except (ContractError, ValueError, OSError):
        print(json.dumps({"error": {"code": "invalid_request", "message": "Invalid request JSON, question or history"}}), file=sys.stderr)
        return 2
    try:
        if re.fullmatch(r"[A-Za-z0-9_-]+", args.case_id) is None:
            raise ContractError("case-id must be a simple identifier")
        if args.mode == "mock":
            if args.thinking_mode is not None:
                raise ContractError("thinking-mode applies only to real mode")
            if not args.mock_script:
                raise ContractError("Mock mode requires --mock-script")
            model = ScriptedModel.load(args.mock_script)
        else:
            if args.mock_script:
                raise ContractError("real mode does not accept --mock-script")
            overrides = None if args.thinking_mode is None else {"LLM_ENABLE_THINKING": "true" if args.thinking_mode == "on" else "false",
                                                                "LLM_JSON_MODE": "false" if args.thinking_mode == "on" else "true"}
            model = ChatModel.from_env(overrides)
        knowledge = KnowledgeBase.load(args.corpus)
        fault = json.loads(Path(args.fault_file).read_text(encoding="utf-8-sig")) if args.fault_file else None
        tools = ToolExecutor(knowledge, fault)
        agent = Agent(model, tools, args.max_model_calls, args.max_tool_calls, args.model_timeout, args.tool_timeout)
    except ContractError as exc:
        print(json.dumps({"error": {"code": "configuration_error", "message": str(exc)}}), file=sys.stderr)
        return 2
    except (OSError, ValueError):
        print(json.dumps({"error": {"code": "configuration_error", "message": "Cannot load corpus, mock script or fault configuration"}}), file=sys.stderr)
        return 2
    output, trace = agent.run(request)
    # Business outcome remains available even if artifact persistence fails.
    print(json.dumps(output, ensure_ascii=False, indent=2))
    try:
        directory = write_artifacts(args.output_dir, args.case_id, request, output, trace)
    except OSError:
        print(json.dumps({"error": {"code": "artifact_write_failed", "message": "Output or trace could not be saved; partial files may exist"}}), file=sys.stderr)
        return 3
    print("Artifacts saved: " + str(directory), file=sys.stderr)
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
