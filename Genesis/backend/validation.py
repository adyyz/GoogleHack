"""Reject unsupported model outputs before they can become an analyst artifact."""
from pydantic import BaseModel

from .models import Categorization, EvolutionAssessment, Investigation


def validate_model_output(output: BaseModel, evidence: dict) -> dict:
    allowed = set(evidence["evidence_ids"])
    citations = []

    def visit(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "evidence_ids":
                    if not item or set(item) - allowed: raise ValueError("Output cites missing or unknown source evidence")
                    citations.extend(item)
                else: visit(item)
        elif isinstance(value, list):
            for item in value: visit(item)

    payload = output.model_dump(mode="json")
    visit(payload)
    if isinstance(output, EvolutionAssessment):
        from .evolution import sufficiency
        gate = evidence["analytical_inputs"]["detector_gate"]
        actual = sufficiency(gate["conclusive_reviews"], gate["target_rule_reviews"])
        if (output.conclusive_reviews, output.target_rule_reviews) != (actual["conclusive_reviews"], actual["target_rule_reviews"]):
            raise ValueError("A5 cannot change computed sample sizes")
        proposed = output.status == "SUPPORTED_PROPOSAL"
        if actual["status"] == "INSUFFICIENT_EVIDENCE" and output.status != "INSUFFICIENT_EVIDENCE":
            raise ValueError("Insufficient reviews cannot support a detector proposal")
        if actual["status"] == "SUFFICIENT_EVIDENCE" and output.status == "INSUFFICIENT_EVIDENCE":
            raise ValueError("A5 must report the computed sufficiency decision")
        if proposed:
            support = output.support_feedback_ids
            allowed_support = {row["id"] for row in evidence["human_feedback"]
                if row["rule_id"] == "HIGH_VALUE" and row["verdict"] in {"TRUE_POSITIVE", "FALSE_POSITIVE"}}
            if not output.candidate_id or not output.hypothesis or not support or len(set(support)) != len(support) or set(support) - allowed_support:
                raise ValueError("Proposal requires one allowlisted candidate and genuine target-rule support")
        elif output.candidate_id is not None or output.hypothesis is not None or output.support_feedback_ids:
            raise ValueError("A result without a proposal cannot carry a candidate")
    if isinstance(output, Categorization):
        if evidence["missing_context"] and (output.primary_typology == "LOW_RISK" or output.suggested_action == "CLOSE" or output.uncertainty != "HIGH"):
            raise ValueError("Incomplete context requires uncertain classification and human review")
        if evidence["protected_signals"] and (output.primary_typology == "LOW_RISK" or output.suggested_action == "CLOSE"):
            raise ValueError("Protected signals cannot be silently classified for closure")
    if isinstance(output, Investigation):
        def texts(value):
            if isinstance(value, str): return [value]
            if isinstance(value, dict): return [text for key, item in value.items() if key != "evidence_ids" for text in texts(item)]
            if isinstance(value, list): return [text for item in value for text in texts(item)]
            return []
        if len(" ".join(texts(payload)).split()) >= 500: raise ValueError("Investigation brief must be under 500 words")
    return {"output": payload, "citation_id_validity": True, "citation_count": len(citations),
        "semantic_support": "REQUIRES_MANUAL_REVIEW", "validation_version": "grounding-v1"}
