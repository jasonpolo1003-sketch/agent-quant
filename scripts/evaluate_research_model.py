from __future__ import annotations

import argparse
import json

from quant_brain.config import PROJECT_ROOT
from quant_brain.research.model_eval import evaluate_model, save_evaluation


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate an Ollama model on bounded quant-research quality cases."
    )
    parser.add_argument("--model", default="qwen3:14b")
    parser.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "brain" / "00_Inbox" / "Model_Evaluations" / "qwen-research-eval.json"),
    )
    args = parser.parse_args()

    evaluation = evaluate_model(args.model)
    path = save_evaluation(args.output, evaluation)
    print(
        json.dumps(
            {
                "model": evaluation["model"],
                "passed": evaluation["passed"],
                "cases_passed": evaluation["cases_passed"],
                "cases_total": evaluation["cases_total"],
                "output_path": path,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
