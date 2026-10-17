"""Rule definitions and read-only operational statistics, without reference labels."""
from .engine import RULES, PROTECTED
from .dataset import content_hash
from .review_metrics import review_summary

RULE_DETAILS = {
    "HIGH_VALUE": ("Volume", "AUD equivalent strictly above $10,000"),
    "CRYPTO": ("Asset type", "Trigger transaction type is CRYPTO"),
    "PEP": ("Profile", "Customer has a politically exposed person flag"),
    "POST_DEATH": ("Identity", "Trigger occurs after the recorded deceased date"),
    "DORMANT": ("Behaviour", "At least 365 days since the account's last activity"),
    "MULTI_CURRENCY": ("Pattern", "At least three currencies in the 30-day window"),
    "CASH_INTENSITY": ("Volume", "Cash is strictly above 50% of 30-day AUD-equivalent volume"),
    "FOREIGN_WIRE": ("Wire", "Trigger is a WIRE transaction in a non-AUD currency"),
    "STRUCTURING": ("Pattern", "At least three cash credits of AUD8,000 to below AUD10,000 within 72 hours, totaling above AUD20,000"),
}


def catalog():
    return [{"id": rule, "name": name, "category": RULE_DETAILS[rule][0], "condition": RULE_DETAILS[rule][1],
        "protected": rule in PROTECTED, "detector_application_supported": rule == "HIGH_VALUE"}
        for rule, name in RULES.items()]


def operational_rows(repo):
    cases = [row for row in repo.list("cases") if row.get("split") in {"DEMO", "CALIBRATION_DISCOVERY"}]
    ids = {row["id"] for row in cases}
    alerts = [row for row in repo.list("alerts") if row["case_id"] in ids]
    alert_ids = {row["id"] for row in alerts}
    feedback = [row for row in repo.list("feedback_events") if row.get("alert_id") in alert_ids]
    steps = [row for row in repo.list("step_runs") if row.get("alert_id") in alert_ids]
    return cases, repo.list("customers"), alerts, feedback, steps


def statistics(cases, customers, alerts, feedback, steps):
    identities = {row["customer_id"] for row in cases}
    customers = [row for row in customers if row["id"] in identities]
    result = review_summary(cases, customers, alerts, feedback, steps)
    result["scope"] = "DEMO_AND_DISCOVERY"
    result["signal_codes"] = [row["name"] for row in result["groups"]["signal"]]
    result["signal_overlap_note"] = "An alert may have multiple signals and secondary typologies; those totals overlap."
    return result


def matrix(repo):
    from .calibration import active_label_policy
    cases, customers, alerts, feedback, steps = operational_rows(repo)
    totals = statistics(cases, customers, alerts, feedback, steps)
    groups = {row["name"]: row for row in totals["groups"]["rule"]}
    detector = repo.active_policy()
    labels = active_label_policy(repo)
    recommendations = repo.list("recommendations")
    a0 = {row["run_id"]: row["output"] for row in steps if row.get("leg_id") == "A0" and row.get("state") == "SUCCEEDED" and row.get("execution_provenance") == "DETERMINISTIC"}
    assessments = {row["id"]: row for row in repo.list("auto_label_assessments")}
    output = []
    for definition in catalog():
        rule = definition["id"]
        counts = groups.get(rule, {"reviewed_alerts": 0, "true_positive": 0, "false_positive": 0,
            "inconclusive": 0, "compared": 0, "agreed": 0, "suggestion_unavailable": 0,
            "machine_uncertain": 0, "agreement_rate": None})
        conclusive = counts["true_positive"] + counts["false_positive"]
        from collections import Counter
        machine = Counter()
        for alert in alerts:
            if alert["rule_id"] != rule: continue
            assessment = assessments.get(alert.get("latest_assessment_id"))
            if assessment and content_hash(assessment["body"]) != assessment["content_hash"]: raise ValueError("Assessment integrity failed")
            current = assessment["body"] if assessment else a0.get(alert.get("current_run_id"), {})
            machine[current.get("predicted_verdict") or "NOT_RECORDED"] += 1
        output.append({**definition, **counts, "alert_count": sum(row["rule_id"] == rule for row in alerts),
            "machine_distribution": {key: machine[key] for key in ("AUTO_TP", "AUTO_FP", "AUTO_UNCERTAIN", "NOT_RECORDED")},
            "reviewed_fp_proportion": counts["false_positive"] / conclusive if conclusive else None,
            "conclusive_reviews": conclusive, "a0_thresholds": labels["rules"][rule],
            "active_detector": detector["candidate"] if rule == "HIGH_VALUE" else None,
            "recommendations": [{"id": row["id"], "state": row["state"], "hypothesis": row["hypothesis"]}
                for row in recommendations if row.get("rule_id", "HIGH_VALUE") == rule],
            "learning_status": "PROTECTED_OVERRIDE" if definition["protected"] else "REVIEW_REQUIRED" if conclusive >= 15 and totals["true_positive"] + totals["false_positive"] >= 30 else "INSUFFICIENT_EVIDENCE"})
    return {"rules": output, "statistics": totals, "detector_policy": detector, "auto_label_policy": labels}
