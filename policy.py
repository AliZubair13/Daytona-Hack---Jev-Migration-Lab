"""Deterministic refund policy. No AI. An LLM decision is a suggestion; this is the authorization."""

MAX_REFUND_USD = 100.0
MIN_REFUND_USD = 0.01


def check(decision: dict, case: dict) -> dict:
    """decision = {refund, order_id, amount}; case carries the account record. Returns {allowed, reasons}."""
    reasons = []
    order_id = str(decision.get("order_id") or "")
    try:
        amount = float(decision.get("amount") or 0)
    except (TypeError, ValueError):
        amount = 0.0
    if order_id != str(case["order_id"]):
        reasons.append(f"order {order_id or '?'} is not on this customer's account")
    if not case["requester_is_owner"]:
        reasons.append("requester does not own the order")
    if not case["refund_eligible"]:
        reasons.append("order is not eligible for refund")
    if not (MIN_REFUND_USD <= amount <= MAX_REFUND_USD):
        reasons.append(f"amount ${amount:.2f} outside ${MIN_REFUND_USD}-${MAX_REFUND_USD:.0f}")
    if amount > float(case["order_value_usd"]) + 1e-9:
        reasons.append(f"amount ${amount:.2f} exceeds order value ${case['order_value_usd']:.2f}")
    if case["prior_refunds"] > 0:
        reasons.append("order was already refunded")
    return {"allowed": not reasons, "reasons": reasons}
