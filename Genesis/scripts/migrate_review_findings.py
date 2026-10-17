"""Explicit local-only projection of genuine stored A5 findings; no model calls."""
from google.api_core.exceptions import AlreadyExists

from backend.config import Settings
from backend.dataset import DATASET_ID
from backend.repository import Repository


def main():
    settings = Settings.load()
    if settings.mode != "local" or settings.project_id != "demo-aml-insight":
        raise RuntimeError("This migration is restricted to local emulators")
    repo = Repository(settings)
    created = 0
    for run in repo.list("pipeline_runs"):
        if run.get("kind") != "EVOLUTION" or run.get("state") != "COMPLETE" or repo.get("recommendations", run["id"]): continue
        result = repo.evolution_detail(run["id"])["result"]
        # Supported legacy proposals already have their original recommendation.
        if not result or result["status"] == "SUPPORTED_PROPOSAL": continue
        payload = {"id": run["id"], "dataset_id": DATASET_ID, "evolution_run_id": run["id"],
            "analytical_snapshot_id": run["analytical_snapshot_id"], "state": "PROPOSED", "revision": 0,
            "candidate": None, "config_version_id": None, "priority": "P2", "hypothesis": result["summary"],
            "support_feedback_ids": [], "sample_sizes": {"conclusive_reviews": result["conclusive_reviews"],
                "target_rule_reviews": result["target_rule_reviews"]}, "limitations": result["limitations"],
            "activation_allowed": False, "projection_source": "EXISTING_VALIDATED_REAL_A5"}
        try: repo.create("recommendations", run["id"], payload)
        except AlreadyExists: continue
        repo.audit("A5_FINDING_PROJECTED", "recommendations", run["id"], "local-migration")
        created += 1
    print(f"Projected {created} existing A5 findings. No model calls, verdicts or policy applications created.")


if __name__ == "__main__": main()
