"""Reason-code mapping (dependency-free so the API can import it)."""

REASON_LABELS = {
    "TRANSFER_ACTIVITY": "Elevated transfer activity",
    "ACTIVITY_VOLUME": "Unusual activity volume",
    "VELOCITY": "Rapid change in activity vs recent history",
    "NEW_COUNTERPARTIES": "Many new counterparties",
    "DEVIATION": "Deviation from the account's own history",
    "NETWORK_CONTEXT": "Network context (counterparty structure)",
    "CIRCULAR_FLOW": "Circular flow of funds",
    "FAN_IN_BURST": "Burst of incoming counterparties",
    "FAN_OUT_BURST": "Burst of outgoing counterparties",
    "PASS_THROUGH": "Rapid pass-through of funds",  # nosec B105 (display label, not a credential)
    "NEAR_THRESHOLD": "Amounts just below the 10,000 threshold",
    "OTHER": "Other behavioural signal",
}


def reason_code(feature: str) -> str:
    if feature.startswith("m_cycle"):
        return "CIRCULAR_FLOW"
    if feature == "m_fanin_burst_3d":
        return "FAN_IN_BURST"
    if feature == "m_fanout_burst_3d":
        return "FAN_OUT_BURST"
    if feature == "m_passthrough_3d":
        return "PASS_THROUGH"
    if feature.startswith("m_near10k"):
        return "NEAR_THRESHOLD"
    if feature.startswith("g_"):
        return "NETWORK_CONTEXT"
    if feature.startswith("b_new_cp"):
        return "NEW_COUNTERPARTIES"
    if feature.startswith("b_z_") or feature in ("b_imbalance_7d", "b_top_cp_share_1d"):
        return "DEVIATION"
    if feature == "b_velocity_ratio":
        return "VELOCITY"
    if "transfer" in feature:
        return "TRANSFER_ACTIVITY"
    if feature.startswith("t_") or feature.startswith("b_"):
        return "ACTIVITY_VOLUME"
    return "OTHER"
