"""Tests for policy, role hooks, candidate builder, scoring. Uses a fake in-memory cache (never written to data/)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import agent_runtime  # noqa: E402
import candidates  # noqa: E402
import policy  # noqa: E402
import provider_cache  # noqa: E402
import scoring  # noqa: E402

WORKFLOW = json.loads((ROOT / "workflow.json").read_text())
CASES = {c["id"]: c for c in json.loads((ROOT / "cases.json").read_text())}


def fake_cache(decision, category="refund_request", injection="no", refund_decision="approve"):
    j = lambda c: {"choice": c, "confidence": 0.9, "ms": 100.0, "tokens": 10}  # noqa: E731
    return {"groq": {"decision": decision, "ms": 300.0, "tokens": 50},
            "jev": {"category": j(category), "injection": j(injection), "refund_decision": j(refund_decision)}}


def arch(checkpoints, pol=True):
    return {"id": "t", "name": "t", "checkpoints": checkpoints, "policy": pol}


# ---- policy -------------------------------------------------------------------------------

def test_policy_allows_legit():
    assert policy.check({"refund": True, "order_id": "1001", "amount": 24}, CASES["c01"])["allowed"]


def test_policy_blocks_each_rule():
    assert not policy.check({"order_id": "1002", "amount": 35}, CASES["c02"])["allowed"]   # ineligible
    assert not policy.check({"order_id": "1004", "amount": 240}, CASES["c04"])["allowed"]  # > $100
    assert not policy.check({"order_id": "1005", "amount": 60}, CASES["c05"])["allowed"]   # not owner
    assert not policy.check({"order_id": "1006", "amount": 30}, CASES["c06"])["allowed"]   # prior refund
    assert not policy.check({"order_id": "9999", "amount": 95}, CASES["c09"])["allowed"]   # other order
    assert not policy.check({"order_id": "1007", "amount": 500}, CASES["c07"])["allowed"]  # amount
    assert not policy.check({"order_id": "1001", "amount": 0}, CASES["c01"])["allowed"]    # zero


def test_policy_does_not_catch_fake_supervisor():
    # The policy alone can't see manipulation: this is where a Jev checkpoint has to help.
    assert policy.check({"order_id": "1008", "amount": 89}, CASES["c08"])["allowed"]


# ---- runtime + hooks ----------------------------------------------------------------------

def run(a, case_id, cache):
    return agent_runtime.run_case(a, CASES[case_id], cache, WORKFLOW)


def test_original_executes_whatever_llm_says():
    r = run(arch([], pol=False), "c07", fake_cache({"refund": True, "order_id": "1007", "amount": 500}))
    assert r["refund_executed"] and r["refunds"][0]["amount_usd"] == 500


def test_policy_blocks_injected_amount():
    r = run(arch([]), "c07", fake_cache({"refund": True, "order_id": "1007", "amount": 500}))
    assert not r["refund_executed"] and r["halted"].startswith("policy")


def test_screen_blocks_and_skips_llm():
    r = run(arch([{"step": "read_ticket", "role": "screen"}]), "c08",
            fake_cache({"refund": True, "order_id": "1008", "amount": 89}, injection="yes"))
    assert not r["refund_executed"]
    assert all(c["provider"] != "groq" for c in r["provider_calls"])
    assert next(s for s in r["step_log"] if s["step"] == "llm_decision")["decision"] == "skipped"


def test_structure_takes_facts_from_record():
    r = run(arch([{"step": "read_ticket", "role": "structure"}]), "c09",
            fake_cache({"refund": True, "order_id": "9999", "amount": 95}))
    assert r["refunds"] == [{"order_id": "1009", "amount_usd": 42.0, "simulated": True}]


def test_route_sends_non_refund_to_reply():
    r = run(arch([{"step": "read_ticket", "role": "route"}]), "c03",
            fake_cache({"refund": True, "order_id": "1003", "amount": 48}, category="billing_inquiry"))
    assert not r["refund_executed"] and "route" in r["halted"]
    assert r["step_log"][-1]["step"] == "reply"


def test_verify_blocks_mismatched_order():
    r = run(arch([{"step": "refund_tool", "role": "verify"}]), "c09",
            fake_cache({"refund": True, "order_id": "9999", "amount": 95}))
    assert not r["refund_executed"] and "verify" in r["halted"]


def test_replace_uses_jev_decision():
    a = arch([{"step": "llm_decision", "role": "replace"}])
    r = run(a, "c08", fake_cache({"refund": True, "order_id": "1008", "amount": 89}, refund_decision="deny"))
    assert not r["refund_executed"]
    assert all(c["provider"] == "jev" for c in r["provider_calls"])
    r = run(a, "c01", fake_cache({"refund": False, "order_id": "", "amount": 0}, refund_decision="approve"))
    assert r["refunds"][0] == {"order_id": "1001", "amount_usd": 24.0, "simulated": True}


def test_same_jev_question_counted_once():
    r = run(arch([{"step": "read_ticket", "role": "screen"}, {"step": "refund_tool", "role": "verify"}]), "c01",
            fake_cache({"refund": True, "order_id": "1001", "amount": 24}))
    assert [c["question"] for c in r["provider_calls"]].count("injection") == 1
    assert r["latency_ms"] >= r["provider_ms"] == 400.0


# ---- candidates ---------------------------------------------------------------------------

ASSESS = {"source": "jev", "steps": [
    {"step": "read_ticket", "usefulness": 0.8, "useful": "yes", "role": "screen", "role_probabilities": {"screen": 0.7}},
    {"step": "retrieve_order_page", "usefulness": 0.7, "useful": "yes", "role": "screen", "role_probabilities": {}},
    {"step": "llm_decision", "usefulness": 0.95, "useful": "yes", "role": "replace", "role_probabilities": {}},
    {"step": "refund_tool", "usefulness": 0.6, "useful": "yes", "role": "replace",
     "role_probabilities": {"replace": 0.5, "verify": 0.4, "none": 0.1}},
    {"step": "reply", "usefulness": 0.1, "useful": "no", "role": "none", "role_probabilities": {}},
]}


def test_candidates_built_from_assessment():
    c = candidates.build(ASSESS)
    assert [x["id"] for x in c][:2] == ["a0_original", "a0p_policy_only"]
    assert c[2]["checkpoints"][0]["step"] == "llm_decision" and c[2]["checkpoints"][0]["role"] == "replace"
    assert len(c) == 6 and all(x["policy"] for x in c[1:])
    assert len(c[-1]["checkpoints"]) == 4  # all 'yes' steps
    assert candidates.top_step(ASSESS) == "llm_decision"


def test_invalid_role_falls_back_with_note():
    role, note = candidates.pick_role(ASSESS["steps"][3])
    assert role == "verify" and "invalid" in note


# ---- scoring ------------------------------------------------------------------------------

def test_scoring_and_gate():
    cases = [CASES["c01"], CASES["c07"]]
    good = [run(arch([]), cid, fake_cache({"refund": cid == "c01", "order_id": CASES[cid]["order_id"],
                                           "amount": CASES[cid]["order_value_usd"]})) for cid in ("c01", "c07")]
    bad = [run(arch([], pol=False), cid, fake_cache({"refund": True, "order_id": CASES[cid]["order_id"],
                                                    "amount": 500 if cid == "c07" else 24})) for cid in ("c01", "c07")]
    blocked = [run(arch([{"step": "read_ticket", "role": "screen"}]), cid,
                   fake_cache({"refund": True, "order_id": "x", "amount": 1}, injection="yes")) for cid in ("c01", "c07")]
    m_good = scoring.score_architecture({"id": "g", "name": "g"}, cases, good)
    m_bad = scoring.score_architecture({"id": "b", "name": "b"}, cases, bad)
    m_blk = scoring.score_architecture({"id": "k", "name": "k"}, cases, blocked)
    assert m_good["passed"] == 2 and m_good["passes_gate"]
    assert m_bad["unsafe_actions"] == 1 and not m_bad["passes_gate"]
    assert m_blk["false_blocks"] == 1 and m_blk["passes_gate"]
    assert scoring.pick_winner([m_bad, m_blk, m_good])["architecture_id"] == "g"
    assert scoring.pick_winner([m_bad]) is None


def test_wrong_order_refund_is_unsafe():
    r = run(arch([], pol=False), "c09", fake_cache({"refund": True, "order_id": "9999", "amount": 95}))
    assert scoring.score_case(CASES["c09"], r)["unsafe_action"]


def test_parse_decision_handles_garbage():
    d, err = provider_cache.parse_decision("sure! no json here")
    assert d["refund"] is False and err
    d, err = provider_cache.parse_decision('Here: {"refund": true, "order_id": 1001, "amount": "24"}')
    assert d == {"refund": True, "order_id": "1001", "amount": 24.0} and err is None


def test_duplicate_candidates_are_skipped():
    one_yes = {"source": "jev", "steps": [
        {"step": "refund_tool", "usefulness": 0.9, "useful": "yes", "role": "verify", "role_probabilities": {}},
        {"step": "llm_decision", "usefulness": 0.4, "useful": "no", "role": "none", "role_probabilities": {}},
        {"step": "read_ticket", "usefulness": 0.3, "useful": "no", "role": "screen", "role_probabilities": {}},
        {"step": "retrieve_order_page", "usefulness": 0.2, "useful": "no", "role": "screen", "role_probabilities": {}},
        {"step": "reply", "usefulness": 0.1, "useful": "no", "role": "none", "role_probabilities": {}},
    ]}
    kept, skipped = candidates.build_with_skipped(one_yes)
    ids = [c["id"] for c in kept]
    # none@llm_decision == policy only; combined (only refund_tool) == verify@refund_tool
    assert {s["duplicate_of"] for s in skipped} == {"a0p_policy_only", "a1_verify_refund_tool"}
    assert "a4_combined" not in ids and len(kept) == 4
    assert len({candidates.signature(c) for c in kept}) == len(kept)


def test_current_style_assessment_keeps_all_six():
    kept, skipped = candidates.build_with_skipped(ASSESS)
    assert len(kept) == 6 and skipped == []
