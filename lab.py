"""CLI: assess → build candidates → provider cache → run (Daytona, local fallback) → score → print table.

Usage: python lab.py [--local] [--refresh-assessment] [--refresh-cache]
"""
import json
import sys
import time
import uuid
from pathlib import Path

import agent_runtime
import arize_export
import assess
import candidates
import daytona_runner
import provider_cache
import scoring

ROOT = Path(__file__).parent
DATA = ROOT / "data"


def load(name):
    return json.loads((ROOT / name).read_text())


def get_assessment(refresh=False):
    p = DATA / "assessment.json"
    if p.exists() and not refresh:
        return json.loads(p.read_text())
    a = assess.assess_all(load("workflow.json"))
    DATA.mkdir(exist_ok=True)
    p.write_text(json.dumps(a, indent=2))
    return a


def run_local(bundle):
    t0 = time.perf_counter()
    out = agent_runtime.run_bundle(bundle)
    return {a["architecture_id"]: {"results": a["results"], "executor": "local",
                                   "startup_ms": 0.0, "wall_ms": (time.perf_counter() - t0) * 1000}
            for a in out["architectures"]}


def evaluate(assessment, archs, cases, raw):
    metrics = [{**scoring.score_architecture(a, cases, raw[a["id"]]["results"]),
                "executor": raw[a["id"]]["executor"]} for a in archs]
    winner = scoring.pick_winner(metrics)
    pred = candidates.top_step(assessment)
    win_arch = next((a for a in archs if winner and a["id"] == winner["architecture_id"]), None)
    return {
        "metrics": metrics,
        "winner": winner["architecture_id"] if winner else None,
        "winner_reason": scoring.winner_reason(winner, metrics) if winner else "No safe architecture",
        "prediction": {"jev_top_step": pred,
                       "winner_includes_it": bool(win_arch and any(c["step"] == pred for c in win_arch["checkpoints"]))},
    }


def print_table(run):
    print(f"\nrun {run['run_id']}  assessment source: {run['assessment']['source']}")
    print("\nJev step assessment:")
    for s in run["assessment"]["steps"]:
        bar = "█" * round(s["usefulness"] * 20)
        print(f"  {s['step']:<20} {bar:<20} {s['usefulness']:.2f}  role={s['role']}")
    hdr = f"\n{'architecture':<44}{'exec':<7}{'pass':>7}{'unsafe':>8}{'f.block':>9}{'med ms':>9}{'calls/t':>9}{'tokens':>8}  gate"
    print(hdr)
    print("-" * (len(hdr) + 4))
    for m in run["metrics"]:
        star = " ★" if m["architecture_id"] == run["winner"] else ""
        print(f"{m['name'][:43]:<44}{m['executor']:<7}{m['passed']:>3}/{m['total']:<3}{m['unsafe_actions']:>8}"
              f"{m['false_blocks']:>9}{m['median_latency_ms']:>9.0f}{m['calls_per_ticket']:>9.1f}"
              f"{m['total_tokens']:>8}  {'PASS' if m['passes_gate'] else 'FAIL'}{star}")
    print("\nper-case status (P pass, F false block, U unsafe):")
    ids = [c["case_id"] for c in run["metrics"][0]["cases"]]
    print(f"{'':<44}" + " ".join(i[-2:] for i in ids))
    for m in run["metrics"]:
        print(f"{m['name'][:43]:<44}" + "  ".join({"pass": "P", "fail": "F", "unsafe": "U"}[c["status"]] for c in m["cases"]))
    w = run["winner"]
    print(f"\nWinner: {w or 'No safe architecture'} — {run['winner_reason']}")
    p = run["prediction"]
    print(f"Jev's prediction: most useful step = {p['jev_top_step']}; winner includes it: "
          f"{'✅' if p['winner_includes_it'] else '✗'}")
    print("\nsandboxes:")
    for aid, r in run["raw"].items():
        print(f"  {aid:<34} {r['executor']:<8} startup={r['startup_ms']:.0f}ms exec={r['wall_ms']:.0f}ms "
              f"{r.get('sandbox_id') or ''} {('ERROR ' + r['error']) if r.get('error') else ''}")
    if run.get("arize"):
        print(f"\nArize: {json.dumps(run['arize'])}")
    print("Latency = sum of measured provider calls the architecture used + runtime execution time per case.")


def execute_run(local=False, refresh_assessment=False, refresh_cache=False, arize=True,
                on_status=lambda *a: None, on_result=lambda *a: None, on_phase=lambda *a: None):
    cases = load("cases.json")
    workflow = load("workflow.json")
    on_phase("assessment")
    assessment = get_assessment(refresh_assessment)
    archs = candidates.build(assessment)
    on_phase("provider_cache")
    cache = provider_cache.build_all(cases, refresh=refresh_cache)
    bundle = {"workflow": workflow, "cases": cases, "cache": cache, "architectures": archs}
    on_phase("sandboxes")
    if local:
        raw = run_local(bundle)
        for aid, r in raw.items():
            on_result(aid, r)
    else:
        raw = daytona_runner.run_all(bundle, on_status=on_status, on_result=on_result)
    run = {"run_id": "run_" + uuid.uuid4().hex[:10], "created_at": time.time(),
           "cache_built_at": provider_cache.CACHE_PATH.stat().st_mtime,
           "assessment": assessment, "architectures": archs, "raw": raw, **evaluate(assessment, archs, cases, raw)}
    if arize:
        on_phase("arize")
        export_arize(run, cases)
    else:
        save_run(run)
    return run


def save_run(run):
    (DATA / "runs").mkdir(parents=True, exist_ok=True)
    (DATA / "runs" / f"{run['run_id']}.json").write_text(json.dumps(run, indent=2))


def export_arize(run, cases=None):
    try:
        run["arize"] = arize_export.export_run(run, cases or load("cases.json"))
    except Exception as e:  # noqa: BLE001 - tracing must never break a run
        run["arize"] = {"status": "error", "reason": f"{type(e).__name__}: {e}"}
    save_run(run)
    return run["arize"]


def main():
    run = execute_run(local="--local" in sys.argv, refresh_assessment="--refresh-assessment" in sys.argv,
                      refresh_cache="--refresh-cache" in sys.argv, arize="--no-arize" not in sys.argv,
                      on_status=lambda aid, st, sid=None: print(f"[sandbox] {aid:<34} {st} {sid or ''}",
                                                                file=sys.stderr))
    print_table(run)


if __name__ == "__main__":
    main()
