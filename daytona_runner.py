"""Stage 2: run every architecture in its own Daytona sandbox, in parallel. Local fallback per architecture.

Only agent_runtime.py, policy.py and a bundle (workflow, cases, provider cache, one architecture) are uploaded.
No provider keys ever enter a sandbox.
"""
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import agent_runtime
from providers import ROOT

FILES = ["agent_runtime.py", "policy.py"]


def _local(bundle, arch, error=None):
    t0 = time.perf_counter()
    out = agent_runtime.run_bundle({**bundle, "architectures": [arch]})
    return {"results": out["architectures"][0]["results"], "executor": "local", "sandbox_id": None,
            "startup_ms": 0.0, "wall_ms": round((time.perf_counter() - t0) * 1000, 1), "error": error}


def _sandbox_run(client, bundle, arch, on_status):
    on_status(arch["id"], "creating")
    t0 = time.perf_counter()
    sb = client.create(timeout=120)
    startup_ms = (time.perf_counter() - t0) * 1000
    try:
        on_status(arch["id"], "running", sb.id)
        work = sb.get_work_dir()
        for name in FILES:
            sb.fs.upload_file((ROOT / name).read_bytes(), f"{work}/{name}")
        payload = json.dumps({**bundle, "architectures": [arch]}).encode()
        sb.fs.upload_file(payload, f"{work}/bundle.json")
        t1 = time.perf_counter()
        resp = sb.process.exec("python3 agent_runtime.py bundle.json", cwd=work, timeout=120)
        exec_wall = (time.perf_counter() - t1) * 1000
        if resp.exit_code != 0:
            raise RuntimeError(f"exit {resp.exit_code}: {resp.result[-300:]}")
        out = json.loads(resp.result)
        on_status(arch["id"], "done", sb.id)
        return {"results": out["architectures"][0]["results"], "executor": "daytona", "sandbox_id": sb.id,
                "startup_ms": round(startup_ms, 1), "wall_ms": round(exec_wall, 1), "error": None}
    finally:
        try:
            sb.delete()
            on_status(arch["id"], "deleted", sb.id)
        except Exception:  # noqa: BLE001 - cleanup failure shouldn't kill the run
            pass


def run_all(bundle, on_status=lambda *a: None, on_result=lambda *a: None):
    archs = bundle["architectures"]
    try:
        from daytona import Daytona, DaytonaConfig
        client = Daytona(DaytonaConfig(api_key=os.environ["DAYTONA_API_KEY"],
                                       api_url=os.environ.get("DAYTONA_API_URL", "https://app.daytona.io/api")))
    except Exception as e:  # noqa: BLE001
        out = {}
        for a in archs:
            on_status(a["id"], "failed→local")
            out[a["id"]] = _local(bundle, a, f"daytona unavailable: {e}")
            on_result(a["id"], out[a["id"]])
        return out

    def one(arch):
        try:
            return arch["id"], _sandbox_run(client, bundle, arch, on_status)
        except Exception as e:  # noqa: BLE001 - fall back to local, labeled as such
            on_status(arch["id"], "failed→local")
            return arch["id"], _local(bundle, arch, f"{type(e).__name__}: {str(e)[:300]}")

    out = {}
    with ThreadPoolExecutor(max_workers=len(archs)) as pool:
        for fut in as_completed([pool.submit(one, a) for a in archs]):
            aid, res = fut.result()
            out[aid] = res
            on_result(aid, res)
    return {a["id"]: out[a["id"]] for a in archs}
