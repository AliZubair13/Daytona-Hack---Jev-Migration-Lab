"""Step 2: ask Jev to assess every workflow step. Falls back to Groq planner, then a fixed list.

Usage: python assess.py            # all steps, saves data/assessment.json
       python assess.py llm_decision   # one live step call, prints raw response
"""
import json
import sys
from pathlib import Path

from pydantic import BaseModel, Field

from providers import ProviderError, groq_chat, jev_call

ROOT = Path(__file__).parent
ROLES = ["screen", "structure", "route", "verify", "replace", "none"]

USEFUL_Q = {
    "type": "choice",
    "instructions": ("Would a structured checkpoint at this step make the agent safer without blocking "
                     "legitimate customers? Consider what the step reads and whether it can move money."),
    "criteria": {"yes": "A checkpoint here prevents a real failure.",
                 "no": "A checkpoint here adds cost without preventing a failure."},
}
ROLE_Q = {
    "type": "choice",
    "instructions": "If a checkpoint were placed at this step, what should it do?",
    "criteria": {
        "screen": "Detect instructions, authority claims, or manipulation in untrusted text and block them.",
        "structure": "Turn untrusted text into fixed fields and take facts from the account record, not the text.",
        "route": "Classify the request and send only genuine refund requests toward the refund path.",
        "verify": "Re-check, right before an action, that the action matches the account record and the policy.",
        "replace": "Make this step's decision instead of the LLM.",
        "none": "No checkpoint needed.",
    },
}


def load_workflow() -> list:
    return json.loads((ROOT / "workflow.json").read_text())


def jev_assess_step(workflow: list, step_id: str) -> dict:
    res = jev_call({"workflow": workflow, "step_under_review": step_id},
                   {"useful": USEFUL_Q, "role": ROLE_Q})
    a = res["answers"]
    role_probs = a["role"].get("probabilities") or {a["role"]["choice"]: 1.0}
    return {"step": step_id,
            "usefulness": float(a["useful"].get("probabilities", {}).get("yes",
                                1.0 if a["useful"]["choice"] == "yes" else 0.0)),
            "useful": a["useful"]["choice"],
            "role": a["role"]["choice"],
            "role_probabilities": role_probs,
            "ms": res["ms"], "usage": res["usage"], "raw": a}


class GroqStepAnswer(BaseModel):
    useful_probability_yes: float = Field(ge=0, le=1)
    role: str
    role_ranking: list[str]


def groq_assess_step(workflow: list, step_id: str) -> dict:
    import os
    prompt = (
        "You review an AI agent workflow.\n" + json.dumps({"workflow": workflow, "step_under_review": step_id})
        + "\n\nQuestion 1: " + USEFUL_Q["instructions"] + " Give useful_probability_yes in [0,1]."
        + "\nQuestion 2: " + ROLE_Q["instructions"] + " Options: " + json.dumps(ROLE_Q["criteria"])
        + '\nReply with JSON only: {"useful_probability_yes": float, "role": str, "role_ranking": [all 6 roles, best first]}'
    )
    res = groq_chat([{"role": "user", "content": prompt}],
                    model=os.environ.get("GROQ_PLANNER_MODEL", "openai/gpt-oss-20b"), json_mode=True)
    ans = GroqStepAnswer.model_validate_json(res["text"])
    if ans.role not in ROLES:
        raise ProviderError(f"invalid role {ans.role}")
    ranking = [r for r in ans.role_ranking if r in ROLES]
    probs = {r: round(1 - i / len(ROLES), 3) for i, r in enumerate(ranking)}
    return {"step": step_id, "usefulness": ans.useful_probability_yes,
            "useful": "yes" if ans.useful_probability_yes >= 0.5 else "no", "role": ans.role,
            "role_probabilities": probs, "ms": res["ms"], "usage": res["usage"]}


FIXED = {  # used only if both Jev and Groq fail
    "llm_decision": ("replace", 0.9), "read_ticket": ("structure", 0.8),
    "refund_tool": ("verify", 0.7), "retrieve_order_page": ("screen", 0.6), "reply": ("none", 0.1),
}


def assess_all(workflow: list) -> dict:
    for source, fn in (("jev", jev_assess_step), ("groq_fallback", groq_assess_step)):
        try:
            steps = [fn(workflow, s["id"]) for s in workflow]
            return {"source": source, "steps": steps}
        except Exception as e:  # noqa: BLE001 - any provider/parse failure moves to the next source
            print(f"[assess] {source} failed: {e}", file=sys.stderr)
    return {"source": "fixed_list", "steps": [
        {"step": s["id"], "usefulness": FIXED[s["id"]][1], "useful": "yes" if FIXED[s["id"]][1] >= 0.5 else "no",
         "role": FIXED[s["id"]][0], "role_probabilities": {FIXED[s["id"]][0]: 1.0}} for s in workflow]}


if __name__ == "__main__":
    wf = load_workflow()
    if len(sys.argv) > 1:
        out = jev_call({"workflow": wf, "step_under_review": sys.argv[1]}, {"useful": USEFUL_Q, "role": ROLE_Q})
        print(json.dumps(out, indent=2))
    else:
        result = assess_all(wf)
        (ROOT / "data").mkdir(exist_ok=True)
        (ROOT / "data" / "assessment.json").write_text(json.dumps(result, indent=2))
        print(f"source: {result['source']}")
        for s in result["steps"]:
            print(f"  {s['step']:<22} useful={s['usefulness']:.2f} ({s['useful']})  role={s['role']}")
