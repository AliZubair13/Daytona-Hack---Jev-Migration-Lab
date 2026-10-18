"""Step 3: turn Jev's step assessment into candidate architectures."""

ROLES = ["screen", "structure", "route", "verify", "replace", "none"]

# Which roles make sense at which step. A checkpoint after the refund (reply) can't prevent anything.
VALID_ROLES = {
    "read_ticket": {"screen", "structure", "route", "none"},
    "retrieve_order_page": {"screen", "structure", "route", "none"},
    "llm_decision": {"screen", "structure", "route", "verify", "replace", "none"},
    "refund_tool": {"screen", "structure", "route", "verify", "none"},
    "reply": {"none"},
}


def pick_role(step: dict) -> tuple[str, str | None]:
    """Return (role, note). Falls back to the next-highest valid role if Jev's top choice is invalid here."""
    valid = VALID_ROLES.get(step["step"], set(ROLES))
    if step["role"] in valid:
        return step["role"], None
    ranked = sorted(step.get("role_probabilities", {}).items(), key=lambda kv: -kv[1])
    for role, _ in ranked:
        if role in valid:
            return role, f"Jev chose '{step['role']}' (invalid at {step['step']}); used next-highest '{role}'"
    return "none", f"Jev chose '{step['role']}' (invalid at {step['step']}); no valid alternative, used 'none'"


def signature(arch: dict) -> tuple:
    """Two architectures with the same real checkpoints and policy setting behave identically."""
    return (frozenset((c["step"], c["role"]) for c in arch["checkpoints"] if c["role"] != "none"), arch["policy"])


def build(assessment: dict) -> list[dict]:
    return build_with_skipped(assessment)[0]


def build_with_skipped(assessment: dict) -> tuple[list[dict], list[dict]]:
    """Returns (unique candidates, skipped duplicates with the id of the candidate they duplicate)."""
    kept, skipped, seen = [], [], {}
    for c in _build_all(assessment):
        sig = signature(c)
        if sig in seen:
            skipped.append({**c, "duplicate_of": seen[sig]})
        else:
            seen[sig] = c["id"]
            kept.append(c)
    return kept, skipped


def _build_all(assessment: dict) -> list[dict]:
    steps = assessment["steps"]
    resolved = []
    for s in steps:
        role, note = pick_role(s)
        resolved.append({**s, "resolved_role": role, "note": note})
    top = sorted(resolved, key=lambda s: -s["usefulness"])[:3]

    def cp(s):
        return {"step": s["step"], "role": s["resolved_role"], "jev_role": s["role"], "note": s["note"]}

    cands = [{"id": "a0_original", "name": "Original (no checks)", "checkpoints": [], "policy": False,
              "origin": "original"},
             {"id": "a0p_policy_only", "name": "Original + policy only", "checkpoints": [], "policy": True,
              "origin": "control"}]
    for i, s in enumerate(top, 1):
        cands.append({"id": f"a{i}_{s['resolved_role']}_{s['step']}",
                      "name": f"{s['resolved_role']} @ {s['step']}",
                      "checkpoints": [cp(s)], "policy": True, "origin": assessment["source"],
                      "jev_usefulness": s["usefulness"]})
    combined = [cp(s) for s in resolved if s["useful"] == "yes" and s["resolved_role"] != "none"]
    cands.append({"id": "a4_combined", "name": "Combined: " + " + ".join(f"{c['role']}@{c['step']}" for c in combined),
                  "checkpoints": combined, "policy": True, "origin": assessment["source"]})
    return cands


def top_step(assessment: dict) -> str:
    return max(assessment["steps"], key=lambda s: s["usefulness"])["step"]
