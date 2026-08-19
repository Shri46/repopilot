"""CLI: python scripts/run_eval.py --project demo --dataset eval/golden_demo.jsonl"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import SessionLocal
from app.eval.runner import run_eval
from app.models.tables import Project


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--dataset", required=True)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        project = db.query(Project).filter_by(name=args.project).first()
        if project is None:
            print(f"No project named '{args.project}'. Ingest it first with scripts/ingest.py.")
            return

        report = run_eval(db, project, args.dataset, dataset_name=Path(args.dataset).name)

        print(f"\n=== Eval report: {report['dataset_name']} ({report['num_examples']} examples) ===")
        print(f"precision@k:     {report['precision_at_k']:.2f}")
        print(f"MRR:             {report['mrr']:.2f}")
        print(f"judge score avg: {report['judge_score_avg']:.2f} / 5")
        print(f"avg latency:     {report['avg_latency_ms']:.0f} ms")
        print(f"avg cost:        ${report['avg_cost_usd']:.5f}")

        out_path = Path("eval_report_latest.json")
        out_path.write_text(json.dumps(report, indent=2))
        print(f"\nFull report written to {out_path}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
