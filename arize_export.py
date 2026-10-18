"""Stage 3: export one trace per run to Arize, built from the sandbox step logs with explicit timestamps.

run → architecture → test_case → one span per step (jev_call / groq_call as LLM spans, policy_check, refund_tool).
Status is "exported" after a successful force_flush. "Verified" only after someone sees it in Arize.
"""
import json
import os

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

MIN_SPAN_NS = 10_000  # 10 µs so zero-time steps stay visible and ordered

KIND = {"jev_call": "LLM", "groq_call": "LLM", "policy_check": "GUARDRAIL", "refund_tool": "TOOL"}


def _ns(ms):
    return max(int(ms * 1_000_000), MIN_SPAN_NS)


def export_run(run: dict, cases: list) -> dict:
    space_id, api_key = os.environ.get("ARIZE_SPACE_ID"), os.environ.get("ARIZE_API_KEY")
    if not (space_id and api_key):
        return {"status": "skipped", "reason": "ARIZE_SPACE_ID / ARIZE_API_KEY not set"}
    from arize.otel import register
    project = os.environ.get("ARIZE_PROJECT_NAME", "refundguard-lab")
    provider = register(space_id=space_id, api_key=api_key, project_name=project,
                        batch=False, set_global_tracer_provider=False, verbose=False)
    tracer = provider.get_tracer("refundguard-lab")
    case_by_id = {c["id"]: c for c in cases}
    metrics = {m["architecture_id"]: m for m in run["metrics"]}
    t_run = int(run["created_at"] * 1e9)

    root = tracer.start_span("run", start_time=t_run, attributes={
        "openinference.span.kind": "CHAIN", "run.id": run["run_id"], "winner": run["winner"] or "none",
        "assessment.source": run["assessment"]["source"]})
    root_ctx = trace.set_span_in_context(root)
    run_end = t_run

    for arch in run["architectures"]:
        m, raw = metrics[arch["id"]], run["raw"][arch["id"]]
        a_span = tracer.start_span("architecture", context=root_ctx, start_time=t_run, attributes={
            "openinference.span.kind": "CHAIN", "architecture.id": arch["id"], "architecture.name": arch["name"],
            "passed": m["passed"], "unsafe_actions": m["unsafe_actions"], "passes_gate": m["passes_gate"],
            "executor": raw["executor"], "sandbox.id": raw.get("sandbox_id") or "",
            "checkpoints": json.dumps(arch["checkpoints"])})
        a_ctx = trace.set_span_in_context(a_span)
        cursor = t_run
        scored = {s["case_id"]: s for s in m["cases"]}
        for res in raw["results"]:
            s = scored[res["case_id"]]
            c_start = cursor
            c_span = tracer.start_span("test_case", context=a_ctx, start_time=c_start, attributes={
                "openinference.span.kind": "CHAIN", "test.id": res["case_id"], "status": s["status"],
                "unsafe_action": s["unsafe_action"], "expected": str(s["expected"]), "actual": str(s["actual"]),
                "failure_reason": s["failure_reason"] or "", "final_action": res["final_action"],
                "input.value": case_by_id[res["case_id"]]["body"]})
            c_ctx = trace.set_span_in_context(c_span)
            for st in res["step_log"]:
                dur = _ns(st["ms"])
                attrs = {"openinference.span.kind": KIND.get(st["kind"], "CHAIN"), "step.kind": st["kind"],
                         "decision": str(st["decision"]), "input.value": str(st["input_summary"]),
                         "output.value": json.dumps(st["output"], default=str)}
                if st["kind"] in ("jev_call", "groq_call"):
                    attrs["llm.model_name"] = "jev-latest" if st["kind"] == "jev_call" else os.environ.get("GROQ_MODEL", "")
                sp = tracer.start_span(st["step"], context=c_ctx, start_time=cursor, attributes=attrs)
                if st["decision"] in ("block", "deny"):
                    sp.set_status(Status(StatusCode.ERROR, "blocked"))
                sp.end(end_time=cursor + dur)
                cursor += dur
            if s["unsafe_action"]:
                c_span.set_status(Status(StatusCode.ERROR, "unsafe action"))
            c_span.end(end_time=cursor)
        a_span.end(end_time=cursor)
        run_end = max(run_end, cursor)

    trace_id = format(root.get_span_context().trace_id, "032x")
    root.end(end_time=run_end)
    flushed = provider.force_flush(timeout_millis=30_000)
    provider.shutdown()
    return {"status": "exported" if flushed else "flush_failed", "trace_id": trace_id, "project": project,
            "note": f"Search run id {run['run_id']} in Arize project {project}"}
