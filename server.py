"""Stage 4: FastAPI app. One static page + JSON API. Run: uvicorn server:app --port 8000"""
import json
import threading
import time

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

import candidates
import lab
import scoring

app = FastAPI(title="Jev or Nah?")
RUNS = lab.DATA / "runs"
LOCK = threading.Lock()
CURRENT = {"status": "idle"}


def _summary(run: dict) -> dict:
    """Run without heavy step logs: metrics, per-case status, executors, Arize ids."""
    for m in run["metrics"]:  # runs stored before stopped_by existed: fill it from the raw results
        by_id = {r["case_id"]: r for r in run["raw"][m["architecture_id"]]["results"]}
        for c in m["cases"]:
            c.setdefault("stopped_by", by_id[c["case_id"]].get("halted"))
            c.setdefault("refunds", by_id[c["case_id"]].get("refunds", []))
    usage = {}
    for aid, r in run["raw"].items():
        u = {"groq": {"calls": 0, "tokens": 0}, "jev": {"calls": 0, "tokens": 0}}
        for res in r["results"]:
            for c in res["provider_calls"]:
                u[c["provider"]]["calls"] += 1
                u[c["provider"]]["tokens"] += c["tokens"]
        usage[aid] = u
    return {
        "usage": usage, "n_tickets": len(next(iter(run["raw"].values()))["results"]),
        "run_id": run["run_id"], "created_at": run["created_at"], "cache_built_at": run.get("cache_built_at"),
        "assessment_source": run["assessment"]["source"],
        "metrics": run["metrics"], "winner": run["winner"], "winner_reason": run["winner_reason"],
        "prediction": run["prediction"], "arize": run.get("arize"),
        "executors": {aid: {k: r.get(k) for k in ("executor", "sandbox_id", "startup_ms", "wall_ms", "error")}
                      for aid, r in run["raw"].items()},
    }


def _load_run(run_id: str) -> dict:
    p = RUNS / f"{run_id}.json"
    if not p.exists() or "/" in run_id:
        raise HTTPException(404, "run not found")
    return json.loads(p.read_text())


def _latest_run():
    files = sorted(RUNS.glob("run_*.json"), key=lambda p: p.stat().st_mtime, reverse=True) if RUNS.exists() else []
    # Prefer the newest run that actually ran in Daytona and exported to Arize; else newest of any kind.
    runs = [json.loads(p.read_text()) for p in files[:30]]
    for r in runs:
        if all(x["executor"] == "daytona" for x in r["raw"].values()) and (r.get("arize") or {}).get("trace_id"):
            return r
    return runs[0] if runs else None


@app.get("/")
def index():
    return FileResponse(lab.ROOT / "static" / "index.html")


@app.get("/api/state")
def state():
    assessment = lab.get_assessment()
    cases = lab.load("cases.json")
    latest = _latest_run()
    return {
        "workflow": lab.load("workflow.json"),
        "assessment": assessment,
        "candidates": candidates.build(assessment),
        "skipped_candidates": candidates.build_with_skipped(assessment)[1],
        "cases": [{k: c.get(k) for k in ("id", "family", "title", "short", "body", "retrieved_context", "customer_id",
                                          "order_id", "order_value_usd", "requester_is_owner", "refund_eligible",
                                          "prior_refunds", "expected")} for c in cases],
        "latest_run": _summary(latest) if latest else None,
    }


@app.get("/api/run/{run_id}/cell/{arch_id}/{case_id}")
def cell(run_id: str, arch_id: str, case_id: str):
    run = _load_run(run_id)
    raw = run["raw"].get(arch_id)
    if not raw:
        raise HTTPException(404, "architecture not in run")
    res = next((r for r in raw["results"] if r["case_id"] == case_id), None)
    case = next((c for c in lab.load("cases.json") if c["id"] == case_id), None)
    if not res or not case:
        raise HTTPException(404, "case not in run")
    metric = next(m for m in run["metrics"] if m["architecture_id"] == arch_id)
    return {"run_id": run_id, "arize": run.get("arize"), "executor": raw["executor"],
            "sandbox_id": raw.get("sandbox_id"),
            "architecture": next(a for a in run["architectures"] if a["id"] == arch_id),
            "case": case, "result": res, "score": next(s for s in metric["cases"] if s["case_id"] == case_id)}


def _worker(local: bool):
    cases = lab.load("cases.json")
    archs = {a["id"]: a for a in candidates.build(lab.get_assessment())}

    def on_phase(p):
        with LOCK:
            CURRENT["phase"] = p

    def on_status(aid, st, sid=None):
        with LOCK:
            CURRENT["sandboxes"][aid] = {"status": st, "sandbox_id": sid}

    def on_result(aid, res):
        m = scoring.score_architecture(archs[aid], cases, res["results"])
        with LOCK:
            CURRENT["cells"][aid] = {s["case_id"]: s for s in m["cases"]}
            sb = CURRENT["sandboxes"].setdefault(aid, {})
            sb["executor"] = res["executor"]
            if res["executor"] == "local":
                sb["status"] = "local" if local else "failed→local"

    try:
        run = lab.execute_run(local=local, arize=False, on_status=on_status, on_result=on_result, on_phase=on_phase)
        run["arize"] = {"status": "exporting"}
        with LOCK:
            CURRENT.update(status="done", phase="done", run=_summary(run), finished_at=time.time())
        arize = lab.export_arize(run, cases)  # results are already on screen; trace export finishes after
        with LOCK:
            CURRENT["run"]["arize"] = arize
    except Exception as e:  # noqa: BLE001
        with LOCK:
            CURRENT.update(status="error", error=f"{type(e).__name__}: {e}")


@app.post("/api/run")
def start_run(local: bool = False):
    with LOCK:
        if CURRENT.get("status") == "running":
            raise HTTPException(409, "a run is already in progress")
        CURRENT.clear()
        CURRENT.update(status="running", phase="starting", started_at=time.time(), local=local,
                       sandboxes={}, cells={})
    threading.Thread(target=_worker, args=(local,), daemon=True).start()
    return {"ok": True}


@app.get("/api/run/current")
def current():
    with LOCK:
        return json.loads(json.dumps(CURRENT))
