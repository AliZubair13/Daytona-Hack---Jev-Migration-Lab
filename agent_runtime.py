"""Agent runtime. Runs inside a Daytona sandbox (or locally as fallback). Stdlib + policy.py only.

No provider keys here: every LLM/Jev answer comes from the host-computed provider cache.

Usage: python agent_runtime.py bundle.json > result.json
bundle = {workflow, cases, cache, architectures: [{id, name, checkpoints: [{step, role}], policy}]}
"""
import json
import sys
import time

import policy

ROLE_QUESTION = {"screen": "injection", "structure": "category", "route": "category",
                 "verify": "injection", "replace": "refund_decision", "none": None}


class Ctx:
    def __init__(self, case, cache):
        self.case = case
        self.cache = cache
        self.decision = None          # {refund, order_id, amount}
        self.use_record = False       # structure hook: take facts from account record
        self.halted = None            # reason string when a checkpoint stops the refund path
        self.refunds = []             # simulated refund ledger
        self.log = []
        self.calls = []               # provider calls used: [{provider, question, ms, tokens}]

    def record(self, step, kind, input_summary, output, decision, ms=0.0):
        self.log.append({"step": step, "kind": kind, "input_summary": input_summary,
                         "output": output, "decision": decision, "ms": round(ms, 3)})

    def jev(self, question):
        a = self.cache["jev"][question]
        if not any(c["provider"] == "jev" and c["question"] == question for c in self.calls):
            self.calls.append({"provider": "jev", "question": question, "ms": a["ms"], "tokens": a["tokens"]})
        return a

    def apply_record(self):
        if self.decision is not None and self.use_record:
            self.decision = dict(self.decision, order_id=self.case["order_id"],
                                 amount=float(self.case["order_value_usd"]))


def _short(text, n=90):
    text = (text or "").replace("\n", " ")
    return text if len(text) <= n else text[: n - 1] + "…"


# ---- generic role hooks -------------------------------------------------------------------

def hook_screen(ctx, at):
    a = ctx.jev("injection")
    blocked = a["choice"] == "yes"
    if blocked:
        ctx.halted = f"screen@{at}: Jev flagged instructions/authority claims"
    ctx.record(f"jev_screen@{at}", "jev_call", "ticket + page text: injection?",
               {"choice": a["choice"], "confidence": a.get("confidence")},
               "block" if blocked else "pass", a["ms"])


def hook_structure(ctx, at):
    a = ctx.jev("category")
    ctx.use_record = True
    ctx.apply_record()
    ctx.record(f"jev_structure@{at}", "jev_call", "ticket → fixed fields; facts from account record",
               {"category": a["choice"], "order_id": ctx.case["order_id"],
                "amount": ctx.case["order_value_usd"]}, "structured", a["ms"])


def hook_route(ctx, at):
    a = ctx.jev("category")
    ok = a["choice"] == "refund_request"
    if not ok:
        ctx.halted = f"route@{at}: category {a['choice']} goes to reply"
    ctx.record(f"jev_route@{at}", "jev_call", "classify request",
               {"category": a["choice"], "confidence": a.get("confidence")},
               "refund_path" if ok else "reply_only", a["ms"])


def hook_verify(ctx, at):
    a = ctx.jev("injection")
    problems = []
    if a["choice"] == "yes":
        problems.append("Jev flagged injection")
    d = ctx.decision
    if d and d.get("refund"):
        if str(d.get("order_id")) != str(ctx.case["order_id"]):
            problems.append(f"order {d.get('order_id')} not the account order {ctx.case['order_id']}")
        try:
            amt = float(d.get("amount") or 0)
        except (TypeError, ValueError):
            amt = -1
        if amt > float(ctx.case["order_value_usd"]) + 1e-9 or amt <= 0:
            problems.append(f"amount {d.get('amount')} does not match account record")
    if problems:
        ctx.halted = f"verify@{at}: " + "; ".join(problems)
    ctx.record(f"jev_verify@{at}", "jev_call", "re-check action vs account record",
               {"injection": a["choice"], "problems": problems}, "block" if problems else "pass", a["ms"])


def hook_replace(ctx, at):
    # Handled inside llm_decision; recorded there.
    pass


def hook_none(ctx, at):
    pass


HOOKS = {"screen": hook_screen, "structure": hook_structure, "route": hook_route,
         "verify": hook_verify, "replace": hook_replace, "none": hook_none}


# ---- original workflow steps --------------------------------------------------------------

def step_read_ticket(ctx, arch):
    ctx.record("read_ticket", "step", "customer message", _short(ctx.case["body"]), "read")


def step_retrieve_order_page(ctx, arch):
    page = ctx.case.get("retrieved_context") or ""
    ctx.record("retrieve_order_page", "step", "order-status page", _short(page) or "(no page)", "read")


def step_llm_decision(ctx, arch):
    replace = any(c["step"] == "llm_decision" and c["role"] == "replace" for c in arch["checkpoints"])
    if replace:
        a = ctx.jev("refund_decision")
        ctx.decision = {"refund": a["choice"] == "approve", "order_id": ctx.case["order_id"],
                        "amount": float(ctx.case["order_value_usd"])}
        ctx.record("jev_replace@llm_decision", "jev_call", "Jev decides instead of the LLM",
                   {"choice": a["choice"], "confidence": a.get("confidence")}, a["choice"], a["ms"])
    else:
        g = ctx.cache["groq"]
        ctx.calls.append({"provider": "groq", "question": "decision", "ms": g["ms"], "tokens": g["tokens"]})
        ctx.decision = dict(g["decision"])
        ctx.record("llm_decision", "groq_call", "LLM reads ticket + page, decides refund", ctx.decision,
                   "refund" if ctx.decision.get("refund") else "no_refund", g["ms"])
    ctx.apply_record()


def step_refund_tool(ctx, arch):
    d = ctx.decision or {"refund": False}
    if not d.get("refund"):
        ctx.record("refund_tool", "refund_tool", "decision", d, "no_refund_requested")
        return
    if arch.get("policy"):
        res = policy.check(d, ctx.case)
        ctx.record("policy_check", "policy_check", f"order {d.get('order_id')} ${d.get('amount')}", res,
                   "allow" if res["allowed"] else "deny")
        if not res["allowed"]:
            ctx.halted = "policy: " + "; ".join(res["reasons"])
            return
    try:
        amount = float(d.get("amount") or 0)
    except (TypeError, ValueError):
        amount = 0.0
    ctx.refunds.append({"order_id": str(d.get("order_id")), "amount_usd": amount, "simulated": True})
    ctx.record("refund_tool", "refund_tool", "issue refund", ctx.refunds[-1], "refunded (simulated)")


def step_reply(ctx, arch):
    if ctx.refunds:
        msg = f"Refund of ${ctx.refunds[-1]['amount_usd']:.2f} issued for order {ctx.refunds[-1]['order_id']}."
    elif ctx.halted:
        msg = "We couldn't process this automatically; a teammate will follow up."
    else:
        msg = "Thanks for reaching out, here is the information you asked for."
    ctx.record("reply", "step", "outcome", msg, "replied")


STEPS = {"read_ticket": step_read_ticket, "retrieve_order_page": step_retrieve_order_page,
         "llm_decision": step_llm_decision, "refund_tool": step_refund_tool, "reply": step_reply}


def run_case(arch, case, cache, workflow):
    ctx = Ctx(case, cache)
    t0 = time.perf_counter()
    by_step = {}
    for c in arch["checkpoints"]:
        by_step.setdefault(c["step"], []).append(c["role"])
    for s in workflow:
        sid = s["id"]
        roles = by_step.get(sid, [])
        if ctx.halted and sid != "reply":
            ctx.record(sid, "skipped", "", None, "skipped")
            continue
        if sid == "refund_tool":           # checkpoints at the action run before it
            for r in roles:
                HOOKS[r](ctx, sid)
                if ctx.halted:
                    break
            if ctx.halted:
                ctx.record(sid, "skipped", "", None, "skipped")
                continue
            STEPS[sid](ctx, arch)
        else:
            STEPS[sid](ctx, arch)
            if sid != "reply":
                for r in roles:
                    HOOKS[r](ctx, sid)
                    if ctx.halted:
                        break
    exec_ms = (time.perf_counter() - t0) * 1000
    provider_ms = sum(c["ms"] for c in ctx.calls)
    return {
        "case_id": case["id"],
        "refund_executed": bool(ctx.refunds),
        "refunds": ctx.refunds,
        "halted": ctx.halted,
        "final_action": "refund" if ctx.refunds else ("blocked" if ctx.halted else "reply_only"),
        "step_log": ctx.log,
        "provider_calls": ctx.calls,
        "provider_ms": round(provider_ms, 1),
        "exec_ms": round(exec_ms, 3),
        "latency_ms": round(provider_ms + exec_ms, 1),
        "tokens": sum(c["tokens"] for c in ctx.calls),
    }


def run_bundle(bundle):
    out = []
    for arch in bundle["architectures"]:
        results = [run_case(arch, case, bundle["cache"][case["id"]], bundle["workflow"])
                   for case in bundle["cases"]]
        out.append({"architecture_id": arch["id"], "results": results})
    return {"architectures": out}


if __name__ == "__main__":
    with open(sys.argv[1]) as f:
        b = json.load(f)
    json.dump(run_bundle(b), sys.stdout)
