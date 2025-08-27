#!/usr/bin/env python3
"""
Evaluation harness for RHCP chatbot classifier.

Loads labeled JSONL data and outputs comprehensive metrics including:
- Per-intent precision/recall/F1
- Macro/micro averages
- Confusion matrix
- Low-confidence gating analysis
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.inference import run_inference
from app.infra.logging import get_logger, setup_logging


def load_eval_data(data_path: str) -> list[dict[str, Any]]:
    """Load evaluation data from JSONL file.

    Args:
        data_path: Path to JSONL file

    Returns:
        List of labeled examples with text, intent, entities

    Raises:
        FileNotFoundError: If data file doesn't exist
        ValueError: If data format is invalid
    """
    data_path = Path(data_path)
    if not data_path.exists():
        raise FileNotFoundError(f"Evaluation data file not found: {data_path}")

    examples = []
    with open(data_path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                example = json.loads(line)
                required_fields = ["text", "intent"]
                if not all(field in example for field in required_fields):
                    raise ValueError(f"Missing required fields: {required_fields}")

                # Ensure entities field exists
                if "entities" not in example:
                    example["entities"] = []

                examples.append(example)

            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON at line {line_num}: {e}")

    if not examples:
        raise ValueError(f"No valid examples found in {data_path}")

    return examples


def run_classification(
    examples: list[dict[str, Any]],
) -> tuple[list[str], list[str], list[float]]:
    """Run classification on evaluation examples.

    Args:
        examples: List of labeled examples

    Returns:
        Tuple of (true_intents, predicted_intents, confidence_scores)
    """
    logger = get_logger(__name__)
    logger.info(f"Running classification on {len(examples)} examples...")

    true_intents = []
    predicted_intents = []
    confidence_scores = []

    for i, example in enumerate(examples):
        try:
            # Run inference
            response = run_inference(example["text"])

            true_intents.append(example["intent"])
            predicted_intents.append(response.intent)
            confidence_scores.append(response.confidence)

            if (i + 1) % 10 == 0:
                logger.info(f"Processed {i + 1}/{len(examples)} examples")

        except Exception as e:
            logger.error(f"Error processing example {i + 1}: {e}")
            # Use fallback values
            true_intents.append(example["intent"])
            predicted_intents.append("unknown")
            confidence_scores.append(0.0)

    return true_intents, predicted_intents, confidence_scores


def analyze_gating_performance(
    true_intents: list[str],
    predicted_intents: list[str],
    confidence_scores: list[float],
    confidence_threshold: float = 0.60,
) -> dict[str, Any]:
    """Analyze low-confidence gating performance.

    Args:
        true_intents: Ground truth intents
        predicted_intents: Predicted intents
        confidence_scores: Confidence scores
        confidence_threshold: Threshold for gating to "unknown"

    Returns:
        Dictionary with gating analysis metrics
    """
    # Count examples below confidence threshold
    low_confidence_mask = [conf < confidence_threshold for conf in confidence_scores]
    low_confidence_count = sum(low_confidence_mask)
    low_confidence_rate = low_confidence_count / len(confidence_scores)

    # Analyze gating to "unknown"
    gated_to_unknown = [pred == "unknown" for pred in predicted_intents]
    correctly_gated = 0
    incorrectly_gated = 0

    for i, (true_intent, pred_intent, conf, gated) in enumerate(
        zip(true_intents, predicted_intents, confidence_scores, gated_to_unknown, strict=False)
    ):
        if gated:
            if conf < confidence_threshold:
                correctly_gated += 1
            else:
                incorrectly_gated += 1

    total_gated = sum(gated_to_unknown)
    gating_accuracy = correctly_gated / total_gated if total_gated > 0 else 0.0

    return {
        "confidence_threshold": confidence_threshold,
        "low_confidence_count": low_confidence_count,
        "low_confidence_rate": low_confidence_rate,
        "total_gated_to_unknown": total_gated,
        "correctly_gated": correctly_gated,
        "incorrectly_gated": incorrectly_gated,
        "gating_accuracy": gating_accuracy,
    }


def print_metrics(
    true_intents: list[str],
    predicted_intents: list[str],
    confidence_scores: list[float],
    gating_analysis: dict[str, Any],
):
    """Print comprehensive evaluation metrics.

    Args:
        true_intents: Ground truth intents
        predicted_intents: Predicted intents
        confidence_scores: Confidence scores
        gating_analysis: Gating performance analysis
    """
    print("\n" + "=" * 60)
    print("RHCP CHATBOT CLASSIFIER EVALUATION")
    print("=" * 60)

    # Basic counts
    print(f"\nDataset Size: {len(true_intents)} examples")
    print(f"Unique Intents: {len(set(true_intents))}")
    print(f"Intent Classes: {sorted(set(true_intents))}")

    # Overall accuracy
    accuracy = accuracy_score(true_intents, predicted_intents)
    print(f"\nOverall Accuracy: {accuracy:.4f}")

    # Per-intent metrics
    print("\n" + "-" * 40)
    print("PER-INTENT METRICS")
    print("-" * 40)

    # Get unique intents for consistent ordering
    all_intents = sorted(set(true_intents) | set(predicted_intents))

    # Calculate per-intent metrics
    precision, recall, f1, support = precision_recall_fscore_support(
        true_intents,
        predicted_intents,
        labels=all_intents,
        average=None,
        zero_division=0,
    )

    # Print per-intent metrics
    for i, intent in enumerate(all_intents):
        print(
            f"{intent:20} | P: {precision[i]:.4f} | R: {recall[i]:.4f} | F1: {f1[i]:.4f} | Support: {support[i]}"
        )

    # Macro and micro averages
    macro_precision, macro_recall, macro_f1, _ = precision_recall_fscore_support(
        true_intents, predicted_intents, average="macro", zero_division=0
    )

    micro_precision, micro_recall, micro_f1, _ = precision_recall_fscore_support(
        true_intents, predicted_intents, average="micro", zero_division=0
    )

    print("\n" + "-" * 40)
    print("AGGREGATE METRICS")
    print("-" * 40)
    print(
        f"Macro Avg | P: {macro_precision:.4f} | R: {macro_recall:.4f} | F1: {macro_f1:.4f}"
    )
    print(
        f"Micro Avg | P: {micro_precision:.4f} | R: {micro_recall:.4f} | F1: {micro_f1:.4f}"
    )

    # Confidence analysis
    print("\n" + "-" * 40)
    print("CONFIDENCE ANALYSIS")
    print("-" * 40)
    print(f"Mean Confidence: {np.mean(confidence_scores):.4f}")
    print(f"Std Confidence: {np.std(confidence_scores):.4f}")
    print(f"Min Confidence: {np.min(confidence_scores):.4f}")
    print(f"Max Confidence: {np.max(confidence_scores):.4f}")

    # Gating performance
    print("\n" + "-" * 40)
    print("LOW-CONFIDENCE GATING PERFORMANCE")
    print("-" * 40)
    print(f"Confidence Threshold: {gating_analysis['confidence_threshold']}")
    print(
        f"Low Confidence Rate: {gating_analysis['low_confidence_rate']:.4f} ({gating_analysis['low_confidence_count']}/{len(true_intents)})"
    )
    print(
        f"Gated to Unknown: {gating_analysis['total_gated_to_unknown']}/{len(true_intents)} ({gating_analysis['total_gated_to_unknown'] / len(true_intents):.4f})"
    )
    print(
        f"Gating Accuracy: {gating_analysis['gating_accuracy']:.4f} ({gating_analysis['correctly_gated']}/{gating_analysis['total_gated_to_unknown']})"
    )

    # Confusion matrix
    print("\n" + "-" * 40)
    print("CONFUSION MATRIX")
    print("-" * 40)

    cm = confusion_matrix(true_intents, predicted_intents, labels=all_intents)

    # Print confusion matrix
    print("True\\Pred", end="")
    for intent in all_intents:
        print(f"{intent:>8}", end="")
    print()

    for i, true_intent in enumerate(all_intents):
        print(f"{true_intent:8}", end="")
        for j, pred_intent in enumerate(all_intents):
            print(f"{cm[i, j]:>8}", end="")
        print()

    # Save confusion matrix plot
    try:
        plt.figure(figsize=(10, 8))
        sns.heatmap(
            cm,
            annot=True,
            fmt="d",
            cmap="Blues",
            xticklabels=all_intents,
            yticklabels=all_intents,
        )
        plt.title("Confusion Matrix")
        plt.xlabel("Predicted Intent")
        plt.ylabel("True Intent")
        plt.xticks(rotation=45, ha="right")
        plt.yticks(rotation=0)
        plt.tight_layout()

        output_path = Path("data/results/confusion_matrix_eval.png")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        print(f"\nConfusion matrix plot saved to: {output_path}")
        plt.close()

    except Exception as e:
        print(f"\nWarning: Could not save confusion matrix plot: {e}")


def main():
    """Main evaluation function."""
    parser = argparse.ArgumentParser(description="Evaluate RHCP chatbot classifier")
    parser.add_argument("--data", required=True, help="Path to evaluation JSONL file")
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.60,
        help="Confidence threshold for gating analysis (default: 0.60)",
    )
    parser.add_argument("--output", help="Path to save detailed results JSON")

    args = parser.parse_args()

    # Setup logging
    setup_logging(level="INFO", format_type="json", debug=False)
    logger = get_logger(__name__)

    try:
        # Load evaluation data
        logger.info(f"Loading evaluation data from: {args.data}")
        examples = load_eval_data(args.data)
        logger.info(f"Loaded {len(examples)} examples")

        # Run classification
        true_intents, predicted_intents, confidence_scores = run_classification(
            examples
        )

        # Analyze gating performance
        gating_analysis = analyze_gating_performance(
            true_intents,
            predicted_intents,
            confidence_scores,
            args.confidence_threshold,
        )

        # Print metrics
        print_metrics(
            true_intents, predicted_intents, confidence_scores, gating_analysis
        )

        # Save detailed results if requested
        if args.output:
            results = {
                "dataset_path": args.data,
                "dataset_size": len(examples),
                "confidence_threshold": args.confidence_threshold,
                "true_intents": true_intents,
                "predicted_intents": predicted_intents,
                "confidence_scores": confidence_scores,
                "gating_analysis": gating_analysis,
                "per_intent_metrics": {},
            }

            # Calculate per-intent metrics
            all_intents = sorted(set(true_intents) | set(predicted_intents))
            precision, recall, f1, support = precision_recall_fscore_support(
                true_intents,
                predicted_intents,
                labels=all_intents,
                average=None,
                zero_division=0,
            )

            for i, intent in enumerate(all_intents):
                results["per_intent_metrics"][intent] = {
                    "precision": float(precision[i]),
                    "recall": float(recall[i]),
                    "f1": float(f1[i]),
                    "support": int(support[i]),
                }

            # Save results
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            logger.info(f"Detailed results saved to: {output_path}")

        logger.info("Evaluation completed successfully")

    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
